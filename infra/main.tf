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

resource "azurerm_storage_account" "lake" {
  name                            = "stsncbtfas${var.env}26"
  resource_group_name             = azurerm_resource_group.rg.name
  location                        = azurerm_resource_group.rg.location
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  account_kind                    = "StorageV2"
  is_hns_enabled                  = true
  min_tls_version                 = "TLS1_2"
  allow_nested_items_to_be_public = false
  tags                            = local.tags
  lifecycle {
    prevent_destroy = true
  }
}

data "azurerm_client_config" "current" {}

resource "azurerm_role_assignment" "me_lake" {
  scope                = azurerm_storage_account.lake.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = data.azurerm_client_config.current.object_id
}

resource "azurerm_storage_data_lake_gen2_filesystem" "layers" {
  for_each           = toset(["bronze", "silver", "gold"])
  name               = each.key
  storage_account_id = azurerm_storage_account.lake.id
  depends_on         = [azurerm_role_assignment.me_lake]
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
  scope                = azurerm_storage_account.lake.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_data_factory.adf.identity[0].principal_id
}

resource "azurerm_data_factory_linked_service_data_lake_storage_gen2" "adf_linked_service_lake" {
  name                 = "ls_lake"
  data_factory_id      = azurerm_data_factory.adf.id
  url                  = azurerm_storage_account.lake.primary_dfs_endpoint
  use_managed_identity = true
}

output "storage_account_name" { value = azurerm_storage_account.lake.name }
output "dfs_endpoint" { value = azurerm_storage_account.lake.primary_dfs_endpoint }
