# Schéma de la table silver `stations`

> Contrat des données de la couche silver. À relire et valider **avant** de coder la transformation.

## Grain
**1 ligne = 1 station.**

## Colonnes


| Colonne silver | Type | Vient de (dans le bronze) | Règle de conversion | Nullable | Commentaire |
|---|---|---|---|---|---|
| `station_id` | `str` | `station[].id` | telle quelle | non | **Clé naturelle** (unique : 715 id pour 715 gares). Sert aux jointures avec `departures` |
| `standard_name` | `str` | `station[].standardname` | telle quelle | non | Nom officiel, indépendant de `lang` : même source que `departure_station_name` dans `departures` |
| `longitude` | `float` | `station[].locationX` | texte → `float` (stricte : une valeur non numérique rejette la ligne) | non | X = longitude. Observé : de -1.67 à 16.38 |
| `latitude` | `float` | `station[].locationY` | texte → `float` (stricte) | non | Y = latitude. Observé : de 42.69 à 52.53 |

**Colonnes écartées :** `@id` (une URI redondante avec `id`), `name` (dépend du paramètre `lang` : différent de `standardname` pour 37 gares, par exemple `Antwerp-Central` / `Antwerpen-Centraal`).


## Observations du profiling
Obtenues avec `jq` sur les fichiers bronze, soit 715 gare :

```json
{
    "timestamp": "1790752736",
    "version" : "1.4",
    "station" : {
        "@id": "http://irail.be/stations/NMBS/008400319",
        "id": "BE.NMBS.008400319",
        "name": "'s Hertogenbosch",
        "locationX": "5.294278",
        "locationY": "51.69042",
        "standardname": "'s Hertogenbosch"
    }
    ,
    {
    "@id": "http://irail.be/stations/NMBS/008015345",
    "id": "BE.NMBS.008015345",
    "name": "Aachen Hbf",
    "locationX": "6.105275",
    "locationY": "50.770832",
    "standardname": "Aachen Hbf"
    }
}
```
1. Les champs : quels champs a une gare ? Lesquels servent pour une dimension gare (celle qu'on joindra aux départs) ?
    -> C'est le champs station qui a une gare
2.  Les types : locationX et locationY sont-ils des nombres ou du texte dans le JSON ?
    -> C'est du text qui sera a passé en nombre.
    Lequel est la longitude, lequel la latitude ?
    -> location X -> Longitude et Location Y -> Latitude
3.  Les sentinelles : y a-t-il des coordonnées à "0", des noms vides ?
    -> Il n'y as pas de coordonées a 0 et de noms vides
4.  L'unicité de la clé : l'id est-il unique ?
    Chaque station et Unique et la clé naturelle est l'id
5.  La couverture : tes 5 gares de départ (dans ton .env) sont-elles présentes ?
    Les 5 gares de mon .env sont présentes (recherche par `id`). ⚠️ Une recherche par **nom** est trompeuse : `name` dépend de la langue.
6.  Les gares étrangères : les coordonnées vont jusqu'au sud de la France (latitude 42.7) et à Vienne (longitude 16.4) → iRail liste aussi les gares desservies par des trains internationaux. Une règle de validation « latitude belge » rejetterait des gares réelles.

## Décisions

**1. Un seul fichier silver, écrasé à chaque exécution** (`data/silver/stations/stations.parquet`)
> Une dimension doit donner la valeur **actuelle** de chaque gare, et la jointure reste simple (pas de partition à choisir). On perd l'historique dans la silver (si une gare change de nom, l'ancien nom disparaît), mais **le bronze garde chaque réponse brute horodatée** : l'historique reste reconstructible. C'est une dimension de type **SCD 1** (on écrase) ; la SCD 2 (historique avec dates de validité) sera vue en semaine 2.

**2. Fréquence : une fois par jour**
> La liste des gares change quelques fois par an. Une gare manquante se **détecte** par un contrôle (anti-jointure `departures` × `stations`), pas par une collecte plus fréquente.
