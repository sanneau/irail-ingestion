import logging


def setup_logging(level: int = logging.INFO) -> None:
    """Setuping the logger for the entire project"""
    logging.basicConfig(
        format="{asctime} - {name} - {levelname} - {message}",
        style="{",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=level,
    )
