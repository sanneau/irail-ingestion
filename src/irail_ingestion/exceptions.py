"""Exceptions métier du projet irail-ingestion."""


class MissingSettingError(Exception):
    """Levée quand une variable d'environnement obligatoire est absente ou vide."""
