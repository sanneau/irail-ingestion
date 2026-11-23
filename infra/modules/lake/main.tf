resource "azurerm_storage_account" "lake" {
  name                            = "stsncbtfas${var.env}26"
  resource_group_name             = var.resource_group_name
  location                        = var.location
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  account_kind                    = "StorageV2"
  is_hns_enabled                  = true
  min_tls_version                 = "TLS1_2"
  allow_nested_items_to_be_public = false
  tags                            = var.tags
  lifecycle {
    prevent_destroy = true
  }
}

resource "azurerm_role_assignment" "me_lake" {
  scope                = azurerm_storage_account.lake.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = var.writer_principal_id

}

resource "azurerm_storage_data_lake_gen2_filesystem" "layers" {
  for_each           = toset(["bronze", "silver", "gold"])
  name               = each.key
  storage_account_id = azurerm_storage_account.lake.id
  depends_on         = [azurerm_role_assignment.me_lake]
  lifecycle {
    prevent_destroy = true
  }
}
