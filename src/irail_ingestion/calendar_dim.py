import dataclasses
from datetime import date, time, timedelta

import holidays

name_day = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]

name_month = [
    "Janvier",
    "Février",
    "Mars",
    "Avril",
    "Mai",
    "Juin",
    "Juillet",
    "Août",
    "Septembre",
    "Octobre",
    "Novembre",
    "Décembre",
]


@dataclasses.dataclass(frozen=True)
class TimeRow:
    """Représente une ligne de la table dim_time."""

    time_key: int
    full_time: time
    hour: int
    minute: int
    time_band: str
    is_peak: bool


@dataclasses.dataclass(frozen=True)
class DateRow:
    """Représente une ligne de la table dim_date."""

    date_key: int
    full_date: date
    year: int
    quarter: int
    month: int
    month_name: str
    iso_week: int
    day_of_month: int
    day_of_week: int
    day_name: str
    is_weekend: bool
    is_holiday: bool
    holiday_name: str | None


def build_date_rows(start: date, end: date) -> list[DateRow]:
    """Construit une liste de DateRow pour toutes les dates entre start
    et end (inclus)."""
    rows = []
    jours_feries = holidays.Belgium(
        years=range(start.year, end.year + 1), language="fr"
    )
    current_date = start
    while current_date <= end:
        rows.append(
            DateRow(
                date_key=int(current_date.strftime("%Y%m%d")),
                full_date=current_date,
                year=current_date.year,
                quarter=(current_date.month - 1) // 3 + 1,
                month=current_date.month,
                month_name=name_month[current_date.month - 1],
                iso_week=current_date.isocalendar()[1],
                day_of_month=current_date.day,
                day_of_week=current_date.isoweekday(),
                day_name=name_day[current_date.weekday()],
                is_weekend=current_date.weekday() >= 5,
                is_holiday=current_date in jours_feries,
                holiday_name=jours_feries.get(current_date),
            )
        )
        current_date += timedelta(days=1)
    return rows


def build_time_rows() -> list[TimeRow]:
    """Construit une liste de TimeRow pour toutes les heures et minutes
    d'une journée."""
    rows = []
    for hour in range(24):
        for minute in range(60):
            rows.append(
                TimeRow(
                    time_key=hour * 100 + minute,
                    full_time=time(hour, minute),
                    hour=hour,
                    minute=minute,
                    time_band=time_band(hour),
                    is_peak=time_band(hour) in ["morning_peak", "evening_peak"],
                )
            )
    return rows


def time_band(hour: int) -> str:
    """Retourne la tranche horaire pour une heure donnée."""
    if 0 <= hour < 6:
        return "night"
    elif 6 <= hour < 9:
        return "morning_peak"
    elif 9 <= hour < 12:
        return "morning"
    elif 12 <= hour < 14:
        return "noon"
    elif 14 <= hour < 17:
        return "afternoon"
    elif 17 <= hour < 20:
        return "evening_peak"
    elif 20 <= hour < 24:
        return "evening"
    else:
        raise ValueError("L'heure doit être comprise entre 0 et 23.")
