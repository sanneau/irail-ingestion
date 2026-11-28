resource "azurerm_container_registry" "acr" {
  name                = "acrsncbtfas${var.env}26"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  sku                 = "Basic"
  admin_enabled       = false
  tags                = local.tags
}

resource "azurerm_user_assigned_identity" "ingest" {
  location            = azurerm_resource_group.rg.location
  name                = "id-irail-ingest-${var.env}"
  resource_group_name = azurerm_resource_group.rg.name
  tags                = local.tags
}

resource "azurerm_role_assignment" "ingest_acr" {
  scope                = azurerm_container_registry.acr.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.ingest.principal_id ## l'identité du job
}

resource "azurerm_role_assignment" "ingest_lake" {
  scope                = module.lake.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.ingest.principal_id ## l'identité du job
}

resource "azurerm_log_analytics_workspace" "logs" {
  name                = "log-sncb-${var.env}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  retention_in_days   = 30
  sku                 = "PerGB2018"
  tags                = local.tags
}

resource "azurerm_container_app_environment" "env" {
  name                       = "cae-sncb-${var.env}"
  location                   = azurerm_resource_group.rg.location
  resource_group_name        = azurerm_resource_group.rg.name
  log_analytics_workspace_id = azurerm_log_analytics_workspace.logs.id
  tags                       = local.tags
  workload_profile {
    name                  = "Consumption"
    workload_profile_type = "Consumption"
  }
}

resource "azurerm_container_app_job" "ingest" {
  name                         = "caj-irail-ingest-${var.env}"
  location                     = azurerm_resource_group.rg.location
  resource_group_name          = azurerm_resource_group.rg.name
  container_app_environment_id = azurerm_container_app_environment.env.id
  tags                         = local.tags

  replica_timeout_in_seconds = 300
  replica_retry_limit        = 0

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.ingest.id]
  }

  registry {
    server   = azurerm_container_registry.acr.login_server
    identity = azurerm_user_assigned_identity.ingest.id
  }


  schedule_trigger_config {
    cron_expression = "*/5 * * * *"
  }

  template {
    container {
      image  = "${azurerm_container_registry.acr.login_server}/irail-ingest:v2" # login_server de l'ACR + nom:tag
      name   = "ingest"
      cpu    = 0.25
      memory = "0.5Gi"
      env {
        name  = "IRAIL_BASE_URL"
        value = "https://api.irail.be/v1"
      }
      env {
        name  = "IRAIL_STATION_IDS"
        value = "BE.NMBS.008813003,BE.NMBS.008892007,BE.NMBS.008873007,BE.NMBS.008896149,BE.NMBS.008841400"
      }
      env {
        name  = "IRAIL_USER_AGENT"
        value = "irail-ingestion/0.1 (https://github.com/sanneau/irail-ingestion)"
      }
      env {
        name  = "IRAIL_ADLS_ACCOUNT"
        value = module.lake.name
      }
      env {
        name  = "AZURE_CLIENT_ID"
        value = azurerm_user_assigned_identity.ingest.client_id
      }
    }
  }
  depends_on = [azurerm_role_assignment.ingest_acr, azurerm_role_assignment.ingest_lake]
}
