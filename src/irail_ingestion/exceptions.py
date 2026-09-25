"""Exceptions métier du projet irail-ingestion."""


class MissingSettingError(Exception):
    """Levée quand une variable d'environnement obligatoire est absente ou vide."""

class DateIsNotRightError(Exception):
    """Levée quand une date ne respecte pas les critere de création de bronze"""



class IRailAPIError(Exception):
    """Erreur liée à un appel à l'API iRail (classe de base)."""

    def __init__(
        self, message: str, station_id: str, status_code: int | None = None
    ) -> None:
        super().__init__(message)
        self.station_id = station_id
        self.status_code = status_code


class TransientAPIError(IRailAPIError):
    """When:  Raised when connexion is down, timeout on API, HTTP429, HTTP5xx
    , RETRY: Yes"""


class InvalidRequestError(IRailAPIError):
    """When: Raised when occurs an HTTP 400 or 404,
    RETRY : No, Client error"""


class InvalidResponseError(IRailAPIError):
    """When: Raised when HTTP 200 but data of response is not what we are waiting for.
    Retry: No"""

class PayloadIsEmptyError(IRailAPIError):
    """When a payload has no departures, he is empty"""
