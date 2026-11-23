terraform {
  required_version = ">= 1.6"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }
  backend "azurerm" {
    resource_group_name  = "rg-sncb-tfstate"
    storage_account_name = "stacctfsa26"
    container_name       = "tfstate"
    key                  = "sncb/dev.tfstate"
    use_azuread_auth     = true
  }
}

provider "azurerm" {
  features {}
  storage_use_azuread = true
}

locals {
  tags = { project = "sncb", env = var.env, managed_by = "terraform", owner = "Simon" }
}


resource "azurerm_resource_group" "rg" {
  name     = "rg-sncb-tf-${var.env}"
  location = "francecentral"
  tags     = local.tags
}


data "azurerm_client_config" "current" {}

module "lake" {
  source              = "./modules/lake"
  env                 = var.env
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  tags                = local.tags
  writer_principal_id = data.azurerm_client_config.current.object_id
}

moved {
  from = azurerm_storage_account.lake
  to   = module.lake.azurerm_storage_account.lake
}
moved {
  from = azurerm_role_assignment.me_lake
  to   = module.lake.azurerm_role_assignment.me_lake
}
moved {
  from = azurerm_storage_data_lake_gen2_filesystem.layers
  to   = module.lake.azurerm_storage_data_lake_gen2_filesystem.layers
}

resource "azurerm_data_factory" "adf" {
  name                = "adf-sncb-tf-${var.env}-as26"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  tags                = local.tags
  identity {
    type = "SystemAssigned"
  }
}

resource "azurerm_role_assignment" "adf_lake" {
  scope                = module.lake.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_data_factory.adf.identity[0].principal_id
}

resource "azurerm_data_factory_linked_service_data_lake_storage_gen2" "adf_linked_service_lake" {
  name                 = "ls_lake"
  data_factory_id      = azurerm_data_factory.adf.id
  url                  = module.lake.dfs_endpoint
  use_managed_identity = true
}

### Le Key Vault (coffre à secrets, droits en mode RBAC)
resource "azurerm_key_vault" "kv" {
  name                       = "kv-sncb-tf-${var.env}-as26"
  location                   = azurerm_resource_group.rg.location
  resource_group_name        = azurerm_resource_group.rg.name
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  sku_name                   = "standard"
  rbac_authorization_enabled = true
  soft_delete_retention_days = 7
  tags                       = local.tags
}

### Toi, tu écris les secrets (lecture et écriture)
resource "azurerm_role_assignment" "kv_me" {
  scope                = azurerm_key_vault.kv.id
  role_definition_name = "Key Vault Secrets Officer"
  principal_id         = data.azurerm_client_config.current.object_id
}

### ADF lit les secrets (lecture seule)
resource "azurerm_role_assignment" "kv_adf" {
  scope                = azurerm_key_vault.kv.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_data_factory.adf.identity[0].principal_id
}

### La connexion d'ADF vers le coffre (service lié)
resource "azurerm_data_factory_linked_service_key_vault" "adf_linked_service_kv" {
  name            = "ls_keyvault"
  data_factory_id = azurerm_data_factory.adf.id
  key_vault_id    = azurerm_key_vault.kv.id
}

output "storage_account_name" { value = module.lake.name }
output "dfs_endpoint" { value = module.lake.dfs_endpoint }
