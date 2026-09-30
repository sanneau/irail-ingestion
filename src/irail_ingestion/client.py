"""Client HTTP pour l'API iRail : appels, traduction des erreurs et validation."""

import logging
from datetime import date

import requests
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_random_exponential,
)

from irail_ingestion.config import Settings
from irail_ingestion.exceptions import (
    InvalidRequestError,
    InvalidResponseError,
    TransientAPIError,
)

MAX_ATTEMPTS = 4
MAX_WAIT_S = 20

logger = logging.getLogger(__name__)


def build_session(settings: Settings) -> requests.Session:
    """Crée une session HTTP qui envoie le User-Agent à chaque requête"""
    session = requests.Session()
    session.headers.update({"User-Agent": settings.user_agent})
    return session


def format_irail_date(day: date) -> str:
    """Formate une date au format jjmmaa attendu par iRail"""
    return day.strftime("%d%m%y")


def validate_liveboard(payload: dict, station_id: str) -> None:
    """Vérifie qu'une réponse est exploitable et qu'elle est la gare demandée"""
    if "stationinfo" not in payload or "departures" not in payload:
        raise InvalidResponseError(
            "Payload vide sur stationinfo ou departures", station_id=station_id
        )

    if payload["stationinfo"].get("id") != station_id:
        raise InvalidResponseError(
            f"Station get is not the same than asked : Station Asked {station_id} "
            f"and station Get {payload['stationinfo'].get('id')}",
            station_id=station_id,
        )

    if int(payload["departures"]["number"]) != len(payload["departures"]["departure"]):
        raise InvalidResponseError(
            f"Not the same number of departure Payload:number = "
            f"{payload['departures']['number']} ->"
            f" Payload:departures = {len(payload['departures']['departure'])}",
            station_id=station_id,
        )

    if int(payload["departures"]["number"]) == 0:
        logger.warning("Aucun départ pour %s", station_id)


def _get_json(
    session: requests.Session,
    settings: Settings,
    path: str,
    params: dict,
    station_id: str | None = None,
) -> tuple[dict, float]:
    """GET {base_url}/{path} : traduit les erreurs HTTP en exceptions métier.

    Renvoie le JSON décodé et la durée de l'appel (en secondes).
    """
    target = f"/{path} (station {station_id})" if station_id else f"/{path}"
    try:
        response = session.get(
            f"{settings.base_url}/{path}", params=params, timeout=settings.timeout_s
        )
    except (requests.Timeout, requests.ConnectionError) as e:
        raise TransientAPIError(
            f"No answer from iRail {target}", station_id=station_id
        ) from e

    if response.status_code == 429 or response.status_code >= 500:
        raise TransientAPIError(
            f"HTTP {response.status_code} (temporary) on {target}",
            station_id=station_id,
            status_code=response.status_code,
        )
    if 400 <= response.status_code <= 499:
        raise InvalidRequestError(
            f"HTTP {response.status_code} on {target} : {response.text[:200]}",
            station_id=station_id,
            status_code=response.status_code,
        )
    try:
        payload = response.json()
    except requests.JSONDecodeError as e:
        raise InvalidResponseError(
            f"Invalid JSON from {target}", station_id=station_id
        ) from e

    return payload, response.elapsed.total_seconds()


@retry(
    retry=retry_if_exception_type(TransientAPIError),
    stop=stop_after_attempt(MAX_ATTEMPTS),
    wait=wait_random_exponential(multiplier=1, min=1, max=MAX_WAIT_S),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def fetch_liveboard(
    session: requests.Session, settings: Settings, station_id: str
) -> dict:
    """Récupère le liveboard d'une gare, le valide et le renvoie."""
    params = {"id": station_id, "format": "json", "lang": "en"}
    payload, elapsed_s = _get_json(session, settings, "liveboard", params, station_id)

    validate_liveboard(payload, station_id)
    logger.info(
        "gare : %s, nombre de départs : %s, durée de l'appel : %.2f s",
        station_id,
        int(payload["departures"]["number"]),
        elapsed_s,
    )
    return payload


@retry(
    retry=retry_if_exception_type(TransientAPIError),
    stop=stop_after_attempt(MAX_ATTEMPTS),
    wait=wait_random_exponential(multiplier=1, min=1, max=MAX_WAIT_S),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def fetch_stations(session: requests.Session, settings: Settings) -> dict:
    """Récupère la liste des gares, la valide et la renvoie."""
    params = {"format": "json", "lang": "en"}
    payload, elapsed_s = _get_json(session, settings, "stations", params)

    if not payload.get("station"):
        raise InvalidResponseError(
            "Réponse /stations sans liste de gares (clé absente ou liste vide)"
        )

    logger.info(
        "gares reçues : %d, durée de l'appel : %.2f s",
        len(payload["station"]),
        elapsed_s,
    )

    return payload
