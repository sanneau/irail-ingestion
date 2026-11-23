output "id" {
  value = azurerm_storage_account.lake.id
}

output "name" {
  value = azurerm_storage_account.lake.name
}

output "dfs_endpoint" {
  value = azurerm_storage_account.lake.primary_dfs_endpoint
}
