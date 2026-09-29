# Schéma de la table silver `departures`

> Contrat des données de la couche silver. À relire et valider **avant** de coder la transformation.

## Grain
**1 ligne = 1 départ d'un train depuis une gare, à une heure prévue.**

## Colonnes

**Les types disponibles :** `str` · `int` (en pandas : `Int64`, qui accepte les valeurs manquantes) · `bool` (en pandas : `boolean`) · `float` · `datetime UTC` (en pandas : `datetime64[ns, UTC]`)
**Nullable :** la colonne peut-elle contenir une valeur manquante (`None` / `NULL`) ? `oui` / `non`

| Colonne silver | Type | Vient de (dans le bronze) | Règle de conversion | Nullable | Commentaire |
|---|---|---|---|---|---|
| `departure_station_id` | `str` | `stationinfo.id` (premier niveau) | telle quelle | non | La gare interrogée = la gare de départ. **Clé naturelle** |
| `departure_station_name` | `str` | `stationinfo.standardname` (premier niveau) | telle quelle | non | Le nom officiel, indépendant de `lang`. Sert à l'affichage, jamais aux jointures |
| `snapshot_at` | `datetime UTC` | L'horodatage du **nom du fichier** (`..._20260928T082740Z.json`) | `strptime(..., "%Y%m%dT%H%M%SZ")`, puis `.replace(tzinfo=UTC)` (le `Z` garantit l'UTC) | non | L'instant de **notre** appel, à la seconde près. Sert au dédoublonnage |
| `scheduled_at` | `datetime UTC` | `departures.departure[].time` | `datetime.fromtimestamp(int(v), tz=UTC)` | non | L'heure de départ **prévue**. **Clé naturelle** |
| `delay_s` | `int` | `departures.departure[].delay` | `int(v)` ; une valeur non numérique → la ligne est rejetée | non | **L'unité dans le nom**. Observé : de 0 à 3 300 s. ⚠️ Une valeur manquante n'est **jamais** remplacée par 0 : 0 voudrait dire « à l'heure », ce qui serait faux |
| `canceled` | `bool` | `departures.departure[].canceled` | Correspondance stricte `{"0": False, "1": True}` ; toute autre valeur → erreur | non | ⚠️ Jamais `bool()`. Observé : toujours `"0"` sur 4 jours (aucune annulation vue pour l'instant) |
| `is_extra` | `bool` | `departures.departure[].isExtra` | Correspondance stricte | non | Un train supplémentaire, hors horaire. Observé : toujours `"0"` |
| `destination_station_id` | `str` | `departures.departure[].stationinfo.id` | telle quelle | non | ⚠️ Le `station` d'un départ = la **destination** |
| `destination_station_name` | `str` | `departures.departure[].stationinfo.standardname` | telle quelle | non | Pour l'affichage |
| `vehicle_id` | `str` | `departures.departure[].vehicle` | telle quelle | non | Par exemple `BE.NMBS.IC410`. **Clé naturelle** |
| `train_type` | `str` | `departures.departure[].vehicleinfo.type` | telle quelle | non | Observé : IC, EC, L, P, S1…S64, T, EXT, **BUS** (un bus de remplacement) → une future dimension |
| `platform` | `str` | `departures.departure[].platform` | `"?"` → `None` ; sinon telle quelle | oui | Un identifiant de quai (peut contenir des lettres). `"?"` est une **valeur sentinelle** (le quai n'est pas encore connu) : observée 326 fois (3 %) |
| `platform_changed` | `bool` | `departures.departure[].platforminfo.normal` | ⚠️ **Inversée** : `"1"` (quai habituel) → `False`, `"0"` → `True` | non | Observé : les deux valeurs existent → des changements de quai ont lieu |
| `occupancy` | `str` | `departures.departure[].occupancy.name` | `"unknown"` → `None` ; valeurs autorisées : `low`, `medium`, `high` ; toute autre valeur → erreur | oui | `"unknown"` est une **valeur sentinelle** |
| `source_file` | `str` | Le nom du fichier bronze | telle quelle | non | Le **lignage** : retrouver le fichier d'origine d'une ligne, pour le débogage et l'audit |

## Observations du profiling (bronze du 25/09 au 28/09/2026)
Obtenues avec `jq` sur les fichiers bronze, soit 12 186 départs :

**Les valeurs sentinelles (« je ne sais pas »)**
| Champ | Sentinelle | Occurrences | Traitement en silver |
|---|---|---|---|
| `occupancy.name` | `"unknown"` | 2 580 (21 %) | → `None` |
| `platform` (et `platforminfo.name`) | `"?"` | 326 (3 %) | → `None` |
| `vehicleinfo.locationX` et `locationY` | `"0"` | 12 186 (100 %) | Colonnes écartées |

⚠️ **Ce qui n'est PAS une sentinelle**, même si ça y ressemble : `delay = "0"` (un train à l'heure : c'est une vraie valeur), `canceled`, `left`, `isExtra` et `platforminfo.normal` = `"0"` (de vrais booléens), `departures.number = "0"` (aucun départ dans la fenêtre). **Les sentinelles se décident colonne par colonne.**

Vérification croisée : les 326 quais `"?"` ont tous `platforminfo.normal = "1"` → un quai inconnu n'est jamais signalé comme changé.

**Les autres observations**
| Observation | Conséquence |
|---|---|
| `canceled`, `left` et `isExtra` valent **toujours** `"0"` | La correspondance stricte est gardée (une autre valeur arrivera un jour) ; `left` semble inutile pour le liveboard |
| `vehicleinfo.locationX` et `locationY` valent **toujours** `"0"` | Ils ne contiennent aucune information → écartés |
| `occupancy.name` ∈ {`low`, `medium`, `high`, `unknown`} | `unknown` → `NULL` |
| `platforminfo.normal` ∈ {`"0"`, `"1"`} | Les changements de quai existent → `platform_changed` |
| `delay` : de 0 à 3 300 s, **jamais négatif** | Aucun train en avance n'a été observé |
| Le `timestamp` du JSON est **arrondi à la minute** : deux appels faits à 17:23:20 et 17:23:58 renvoient le même `timestamp` | Un indice pour la décision n° 3 |
| Les `train_type` incluent `BUS`, `EXT` et `T` | Pas uniquement des trains : à prendre en compte dans l'analyse |

**Les champs écartés (proposition) :** `id` (une simple position), `departureConnection` (redondant avec la clé naturelle), toutes les `@id` (redondantes avec les identifiants), `vehicleinfo.name` et `shortname` (redondants), `vehicleinfo.locationX/Y` (toujours `"0"`), `occupancy.@id` (redondant), les coordonnées des gares (elles iront dans la **dimension gare**, en semaine 2).

## Les décisions de conception

**1. La clé naturelle**
> `departure_station_id` + `vehicle_id` + `scheduled_at`. Le champ `id` n'en fait pas partie : c'est une simple position dans la liste, qui change d'une photo à l'autre.

**2. Le dédoublonnage**
> On garde la **dernière photo** de chaque départ (le `snapshot_at` le plus récent) : c'est l'état le plus proche du moment du départ.
> ⚠️ **Limite connue :** le liveboard ne montre que les trains **pas encore partis** (`left` vaut toujours `"0"`). `delay_s` mesure donc **le dernier retard annoncé avant le départ**, et non le retard réel à l'arrivée. Pour suivre l'évolution du retard le long du trajet, il faudra l'endpoint `vehicle` (les arrêts d'un train) ou le liveboard des arrivées (`arrdep=arrival`).

**3. La source de `snapshot_at`**
> **Le nom du fichier.** C'est l'instant de **notre** appel, précis à la seconde, toujours présent, et cohérent avec la partition. Le `timestamp` du JSON est arrondi à la minute : deux appels dans la même minute renvoient la même valeur (sans doute un cache côté API).
> *Le risque :* on dépend de la convention de nommage des fichiers bronze. Si elle change, l'analyse du nom échoue (bruyamment, grâce à `strptime`).

**4. L'organisation du code**
> L'ingestion (bronze) et la transformation (silver) doivent être **indépendantes à l'exécution** : chacune a son propre rythme (collecte toutes les 10 min, transformation par exemple toutes les heures) et ses propres échecs. → Un **nouveau module** `transform.py` dans le même package, avec son **propre point d'entrée** `irail-transform` dans `[project.scripts]`. Elles partagent la configuration, le logging et les exceptions.

**5. Les colonnes écartées**
> Celles qui n'apportent aucune information ou qui sont redondantes : `id` (une position), `departureConnection` (redondant avec la clé naturelle), `vehicleinfo.locationX/Y` (toujours `"0"`), `vehicleinfo.name` et `shortname` (redondants avec `vehicle`), `occupancy.@id` (redondant avec `occupancy.name`), toutes les autres `@id`, `platforminfo.name` (identique à `platform`), `left` (toujours `"0"` : le liveboard ne montre que les trains pas encore partis), `vehicleinfo.number` (redondant avec `vehicle_id`, qui contient déjà le numéro), et les coordonnées des gares (elles iront dans la dimension gare, en semaine 2).

**6. Les bus de remplacement (`BUS`, `EXT`, `T`)**
> Gardés dans la silver, puisqu'ils remplacent des trains. `train_type` permet de les **filtrer** dans l'analyse si besoin.
> *Question ouverte :* que signifient exactement `EXT` et `T` ?
