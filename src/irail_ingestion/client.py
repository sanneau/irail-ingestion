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
    """Récupère le liveboard d'une gare -> JSON brute -> validation"""
    url = f"{settings.base_url}/liveboard"
    params = {"id": station_id, "format": "json", "lang": "en"}

    try:
        response = session.get(url, params=params, timeout=settings.timeout_s)
    except (requests.Timeout, requests.ConnectionError) as e:
        raise TransientAPIError(
            f"No answer or impossible connection for {station_id}",
            station_id=station_id,
        ) from e

    if response.status_code == 429 or response.status_code >= 500:
        raise TransientAPIError(
            f"HTTP {response.status_code} : erreur temporaire : station {station_id}",
            station_id=station_id,
            status_code=response.status_code,
        )

    if response.status_code >= 400 and response.status_code <= 499:
        raise InvalidRequestError(
            f"message : {response.text[:200]}", station_id=station_id
        )

    try:
        payload = response.json()
    except requests.JSONDecodeError as e:
        raise InvalidResponseError("JSON Error code", station_id=station_id) from e

    validate_liveboard(payload, station_id)
    logger.info(
        "gare : %s, nombre de départs : %s , durée de l'appel : %s",
        station_id,
        int(payload["departures"]["number"]),
        response.elapsed.total_seconds(),
    )

    return payload
