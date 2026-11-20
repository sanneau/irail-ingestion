terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~>4.0"
    }
  }
  backend "azurerm" {
    resource_group_name  = "rg-sncb-tfstate"
    storage_account_name = "stacctfsa26"
    container_name       = "tfstate"
    key                  = "sncb/databricks-dev.tfstate"
    use_azuread_auth     = true
  }
}

provider "azurerm" {
  features {}
}

locals {
  tags = {
    project    = "sncb"
    env        = var.env
    managed_by = "terraform"
    owner      = "AS"
  }
}

data "azurerm_resource_group" "rg" {
  name = "rg-sncb-tf-${var.env}"
}

data "azurerm_data_factory" "manuel" {
  name                = "adf-sncb-dev-as26"
  resource_group_name = "rg-sncb-dev"
}

resource "azurerm_databricks_workspace" "dbw" {
  name                        = "dbw-sncb-tf-${var.env}-as26"
  resource_group_name         = data.azurerm_resource_group.rg.name
  location                    = data.azurerm_resource_group.rg.location
  sku                         = "premium"
  managed_resource_group_name = "rg-sncb-tf-${var.env}-dbw-managed"
  tags                        = local.tags
}

resource "azurerm_role_assignment" "adf_dbw" {
  scope                = azurerm_databricks_workspace.dbw.id
  role_definition_name = "Contributor"
  principal_id         = data.azurerm_data_factory.manuel.identity[0].principal_id
}

output "workspace_url" {
  value = azurerm_databricks_workspace.dbw.workspace_url
}
