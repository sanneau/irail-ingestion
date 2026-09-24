# Exploration de l'API iRail

> Date de l'exploration : 2026-09-24 — Source : https://docs.irail.be

## 1. Endpoints
|   endpoint    |   rôle               |   utile pour notre projet ? | info suplémentaire         |
|---------------|----------------------|-----------------------------|----------------------------|
|   stations    |get station           |             oui             |joindre sur stationinfo@id  | 
|   liveboards  |snapshot des train    |             oui             |                            |
|   connections |get connection(walk,.)|             non             |                            |
|   vehicles    |get vehicle info      |             oui             |                            |
|   compositions|                      |             non             |                            |
|   disturbances|get the trafic issue  |             oui             |                            |
|   occupancy   |post info occupancy   |             non             |                            |
|   Logs        |get log               |             non             |                            |

## 2. Paramètres de `liveboard`

|   paramètre|   obligatoire |   valeurs possibles |
|------------|---------------|---------------------|
|    station |   YES (ou id) | Gent-Sint-Pieters   | 
|    id      |   YES (ou id) | BE.NMBS.008892007   | 
|    arrdep  |      NO       | departure/arrival   |
|    alerts  |      NO       | false/true          |
|    time    |      NO       | 1230 format:HHMM    |
|    date    |      NO       | 240926 format:ddMMYY|
|    format  |      NO       | json/xml/jsonp      |
|    lang    |      NO       | en                  |

## 3. Structure d'un départ

Chemin dans la réponse : `.departures.departure[]` (une liste de départs).
⚠️ Tous les champs sont des **chaînes de caractères** (`string`), y compris les nombres et les booléens.

| Champ | Type dans le JSON | Signification | Exemple |
|---|---|---|---|
| `id` | string | Position du départ dans la liste. **Ce n'est pas un identifiant stable** | `"0"` |
| `station` | string | Nom de la gare de **destination**, dans la langue `lang` demandée | `"Louvain"` |
| `stationinfo.@id` | string (URI) | Identifiant de la gare de destination, sous forme d'URI | `"http://irail.be/stations/NMBS/008833001"` |
| `stationinfo.id` | string | Identifiant unique de la gare de destination | `"BE.NMBS.008833001"` |
| `stationinfo.name` | string | Nom de la gare, dans la langue `lang` demandée | `"Louvain"` |
| `stationinfo.standardname` | string | Nom officiel de la gare (langue de la région), indépendant de `lang` | `"Leuven"` |
| `stationinfo.locationX` | string (décimal) | **Longitude** de la gare de destination | `"4.715866"` |
| `stationinfo.locationY` | string (décimal) | **Latitude** de la gare de destination | `"50.88228"` |
| `time` | string (entier) | Heure de départ **prévue** : timestamp Unix en secondes, UTC | `"1790258640"` |
| `delay` | string (entier) | Retard en **secondes** | `"0"` |
| `canceled` | string (`"0"` / `"1"`) | Le départ est-il annulé ? | `"0"` |
| `left` | string (`"0"` / `"1"`) | Le train a-t-il déjà quitté la gare ? *(à confirmer)* | `"0"` |
| `isExtra` | string (`"0"` / `"1"`) | Train supplémentaire, hors horaire normal ? *(à confirmer)* | `"0"` |
| `vehicle` | string | Identifiant du train | `"BE.NMBS.S23765"` |
| `vehicleinfo.name` | string | Identifiant du train (identique à `vehicle`) | `"BE.NMBS.S23765"` |
| `vehicleinfo.shortname` | string | Nom court du train, pour l'affichage | `"S2 3765"` |
| `vehicleinfo.number` | string (entier) | Numéro du train | `"3765"` |
| `vehicleinfo.type` | string | Type de train (IC, S2, P, L…) | `"S2"` |
| `vehicleinfo.locationX` | string (décimal) | Longitude du train. `"0"` = **inconnue** (valeur sentinelle) | `"0"` |
| `vehicleinfo.locationY` | string (décimal) | Latitude du train. `"0"` = **inconnue** (valeur sentinelle) | `"0"` |
| `vehicleinfo.@id` | string (URI) | Identifiant du train, sous forme d'URI | `"http://irail.be/vehicle/S23765"` |
| `platform` | string | Quai de départ | `"3"` |
| `platforminfo.name` | string | Quai de départ (identique à `platform`) | `"3"` |
| `platforminfo.normal` | string (`"0"` / `"1"`) | `"1"` = quai habituel, `"0"` = changement de quai *(à confirmer)* | `"1"` |
| `occupancy.@id` | string (URI) | Niveau d'affluence, sous forme d'URI | `"http://api.irail.be/terms/low"` |
| `occupancy.name` | string | Niveau d'affluence : `low`, `medium`, `high` ou `unknown` (valeur sentinelle) | `"low"` |
| `departureConnection` | string (URI) | URI du départ : `.../connections/<gare de départ>/<date AAAAMMJJ>/<train>` | `"http://irail.be/connections/8813003/20260924/S23765"` |

**Exemple réel** (le premier départ de Bruxelles-Central, le 24/09/2026) :

```json
{
  "id": "0",
  "station": "Louvain",
  "stationinfo": {
    "@id": "http://irail.be/stations/NMBS/008833001",
    "id": "BE.NMBS.008833001",
    "name": "Louvain",
    "locationX": "4.715866",
    "locationY": "50.88228",
    "standardname": "Leuven"
  },
  "time": "1790258640",
  "delay": "0",
  "canceled": "0",
  "left": "0",
  "isExtra": "0",
  "vehicle": "BE.NMBS.S23765",
  "vehicleinfo": {
    "name": "BE.NMBS.S23765",
    "shortname": "S2 3765",
    "number": "3765",
    "type": "S2",
    "locationX": "0",
    "locationY": "0",
    "@id": "http://irail.be/vehicle/S23765"
  },
  "platform": "3",
  "platforminfo": {
    "name": "3",
    "normal": "1"
  },
  "occupancy": {
    "@id": "http://api.irail.be/terms/low",
    "name": "low"
  },
  "departureConnection": "http://irail.be/connections/8813003/20260924/S23765"
}
```

## 4. Pièges identifiés
- Bcp de chiffre ou boolean apparaissent en string
- prendre l'id de station et non pas station le string
- Utilisé standartname quand on doit avoir un string de gare
- locationY -> latitude et location X -> longitude
- time utilise timestamp Unix donc c'est a dire nombre de seconde depuis 01/01/1970
- canceled est "0" veut dire en route et le string veut dire false
- On pourrais crée une clé naturelle en utilisant 8813003/20260924/S23765" (a definir)
- l'URL sans /v1/ → redirection 303, corps vide ;
- id n'est qu'une position et station désigne la destination (manquant) ;
- les valeurs sentinelles ("0" pour une position, "unknown" pour l'affluence) ;
- l'encodage des accents dans l'URL (Liège → 404) ;
- une gare inconnue renvoie un 400, pas un 404 ;
- une date invalide est ignorée en silence (200, données d'aujourd'hui) ;
- une date passée → 200 avec 0 départ : pas d'historique ;
- le nombre de départs est variable (fenêtre de temps).

## 5. Règles d'usage et erreurs
- Limite de 3 requete par secondes.
- mettre le user agent pour pouvoir etre contactées si difficultés

## 6. Questions ouvertes
- je n'ai pas pu verifier si un train canceled etait egale a "1"
- time est-il en heure belge ou en UTC ?
- la profondeur exacte de la fenêtre du liveboard ;
- left, isExtra et platforminfo.normal, à confirmer.
