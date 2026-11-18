# ═════════════════════════════════════════════════════════════════════════════
# Le lake de dev, en code. Lire de haut en bas : chaque bloc = une chose.
# Forme de TOUS les blocs :   mot_clé "type" "nom_local" { argument = valeur ... }
# ═════════════════════════════════════════════════════════════════════════════

# ── 1. Les réglages du projet : quelle version de Terraform, quels plugins (providers) ──
terraform {
  required_version = ">= 1.6"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0" # toute version 4.x, jamais la 5 sans le décider
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

# ── 2. Comment parler à Azure (il réutilise ton `az login` + ARM_SUBSCRIPTION_ID) ──
provider "azurerm" {
  features {}                # obligatoire, même vide
  storage_use_azuread = true # créer les conteneurs avec TON identité, pas avec la clé du compte (moindre privilège)
}

# ── 3. Des valeurs écrites une fois, réutilisées partout : local.tags ──
locals {
  tags = { project = "sncb", env = var.env, managed_by = "terraform", owner = "Simon" }
}

# ── 4. Le groupe de ressources (T3, déjà créé) ──
resource "azurerm_resource_group" "rg" { # "type"  "nom local" (le nom pour Terraform, pas pour Azure)
  name     = "rg-sncb-tf-${var.env}"     # le nom dans Azure
  location = "francecentral"
  tags     = local.tags
}

# ── 5. Le compte de stockage : ✅ TON BLOC, juste du premier coup (je n'ai changé que l'alignement) ──
resource "azurerm_storage_account" "lake" {
  name                            = "stsncbtfas${var.env}26"           # 15 caractères, a-z0-9 : valide (ton E1 !)
  resource_group_name             = azurerm_resource_group.rg.name     # RÉFÉRENCE : « le name du bloc azurerm_resource_group nommé rg »
  location                        = azurerm_resource_group.rg.location # → Terraform sait qu'il faut créer le groupe AVANT
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

# ── 6a. QUI SUIS-JE ? Un bloc « data » LIT quelque chose qui existe déjà. Il ne crée rien. ──
# ❌ Tu avais mis ici scope / role_definition_name / principal_id : ce sont les arguments du RÔLE (6b), pas de cette lecture.
# Ce bloc ne prend AUCUN argument : il demande juste à Azure « qui est connecté ? » (toi, via az login).
# Il fournit ensuite des attributs qu'on lit ailleurs : data.azurerm_client_config.current.object_id = TON identifiant Entra ID.
data "azurerm_client_config" "current" {}

# ── 6b. TON RÔLE sur le lake : la commande `az role assignment create` de jeudi, en code ──
# ❌ Ce bloc manquait. Tes trois arguments étaient les bons, il fallait juste un bloc « resource » à eux.
# La phrase à retenir : QUI (principal_id) + QUEL RÔLE (role_definition_name) + OÙ (scope).
resource "azurerm_role_assignment" "me_lake" {
  scope                = azurerm_storage_account.lake.id              # OÙ : l'id du compte de stockage (bloc 5), par référence
  role_definition_name = "Storage Blob Data Contributor"              # QUEL RÔLE : ✅ c'était juste
  principal_id         = data.azurerm_client_config.current.object_id # QUI : toi, lu par le bloc 6a (préfixe « data. »)
}

# ── 7. Les trois conteneurs bronze / silver / gold, en UN seul bloc ──
# ❌ Tu avais écrit une boucle façon Python (« each.key in toset(...) : »). Terraform n'a pas de « for » ici :
#    on met un ARGUMENT spécial, for_each, et Terraform crée un exemplaire du bloc par élément.
resource "azurerm_storage_data_lake_gen2_filesystem" "layers" {
  for_each           = toset(["bronze", "silver", "gold"]) # la liste à parcourir (toset = un ensemble, comme le set() de ce matin)
  name               = each.key                            # à chaque exemplaire : "bronze", puis "silver", puis "gold"
  storage_account_id = azurerm_storage_account.lake.id     # DANS quel compte : celui du bloc 5, par référence
  depends_on         = [azurerm_role_assignment.me_lake]   # ⚠️ créer les conteneurs APRÈS ton rôle, sinon 403
  # ❓ Ton « ? » : c'était bien depends_on. Pourquoi faut-il le dire ? Aucun argument de ce bloc ne mentionne le rôle,
  #    donc Terraform ne devine pas le lien. Or créer un conteneur avec ton identité exige le rôle. On le lui dit.
}

# ── 9. T9 : la Data Factory, son badge (identité), son droit (rôle), sa consigne (service lié) ──
resource "azurerm_data_factory" "adf" {
  name                = "adf-sncb-tf-${var.env}-as26"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  tags                = local.tags # ❌ tu avais local.tags.owner = UN texte ("Simon") ; tags attend un MAP (même erreur qu'hier au T6)
  identity {                       # ❌ manquait : sans ce bloc, pas de badge → identity[0] n'existe pas, le rôle plus bas ne peut rien lire
    type = "SystemAssigned"        # Azure crée l'identité avec la Data Factory et la supprime avec elle
  }
}

resource "azurerm_role_assignment" "adf_lake" {
  scope                = azurerm_storage_account.lake.id                   # OÙ : le lake ✅
  role_definition_name = "Storage Blob Data Contributor"                   # QUEL RÔLE ✅
  principal_id         = azurerm_data_factory.adf.identity[0].principal_id # QUI : le numéro de badge de la Data Factory
  # ❌ tu avais azurerm_data_factory.adf.id = l'ADRESSE de la ressource ("/subscriptions/.../factories/adf-...") :
  #    c'est où elle habite, pas son badge. Un rôle se donne à un principal_id (un GUID d'Entra ID), jamais à un id de ressource.
}

resource "azurerm_data_factory_linked_service_data_lake_storage_gen2" "adf_linked_service_lake" {
  name                 = "ls_lake"                                         # ❌ manquait (argument obligatoire) : le nom du service lié tel qu'il apparaîtra dans le Studio ADF
  data_factory_id      = azurerm_data_factory.adf.id                       # ✅ ici c'est bien l'adresse de la ressource qu'on veut
  url                  = azurerm_storage_account.lake.primary_dfs_endpoint # ✅
  use_managed_identity = true                                              # ✅ « utilise ton badge, pas la clé »
}

# ── 8. Ce que Terraform affiche à la fin de l'apply (et que d'autres outils peuvent lire) ──
output "storage_account_name" { value = azurerm_storage_account.lake.name }
output "dfs_endpoint" { value = azurerm_storage_account.lake.primary_dfs_endpoint }
