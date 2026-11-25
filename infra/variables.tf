variable "env" {
  type        = string
  description = "Give us the environment we are in dev or prod"
  validation {
    condition     = contains(["dev", "prod", "sbx"], var.env)
    error_message = "environment should be dev, prod or sdbx"
  }
}

# Avant : data.azurerm_client_config.current.object_id = « celui qui lance Terraform ».
# Sur ton PC c'était toi, dans la CI c'est l'application gh-terraform-sncb : le plan de la CI voulait
# retirer tes droits pour les donner à la CI. Un identifiant écrit en dur ne dépend plus de qui lance Terraform.
variable "me_object_id" {
  type        = string
  description = "Object ID Entra ID of the developer who gets write access to the lake and the Key Vault (not a secret)"
}
