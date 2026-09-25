"""Chargement et validation de la configuration depuis les variables d'environnement."""

import os
from dataclasses import dataclass
from pathlib import Path

from irail_ingestion.exceptions import MissingSettingError

DEFAULT_DATA_DIR = "data/raw"
DEFAULT_TIMEOUT_S = "10"


@dataclass(frozen=True)
class Settings:
    base_url: str
    user_agent: str
    station_ids: tuple[str, ...]
    data_dir: Path
    timeout_s: float


def _require_env(name: str) -> str:
    """Renvoie la valeur de la variable `name`, ou lève MissingSettingError si elle manque ou est vide."""
    try:
        value = os.environ[name]
    except KeyError as e:
        raise MissingSettingError(f"Variable d'environnement manquante : {name}") from e
    if not value.strip():
        raise MissingSettingError(f"Variable d'environnement vide : {name}")
    return value


def split_stations(raw: str) -> tuple[str, ...]:
    """Découpe 'A, B,C' en ('A', 'B', 'C') en ignorant les éléments vides."""
    stations = tuple(s.strip() for s in raw.split(",") if s.strip())
    if not stations:
        raise MissingSettingError("IRAIL_STATION_IDS ne contient aucune gare")
    return stations


def load_settings() -> Settings:
    """Lit, convertit et valide la configuration depuis les variables d'environnement."""
    return Settings(
        base_url=_require_env("IRAIL_BASE_URL"),
        user_agent=_require_env("IRAIL_USER_AGENT"),
        station_ids=split_stations(_require_env("IRAIL_STATION_IDS")),
        data_dir=Path(os.environ.get("IRAIL_DATA_DIR", DEFAULT_DATA_DIR)),
        timeout_s=float(os.environ.get("IRAIL_TIMEOUT_S", DEFAULT_TIMEOUT_S)),
    )
