from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class Departure:
    """Represent a depart of a train and use the columns write in silver-schema.md"""

    departure_station_id: str
    departure_station_name: str
    snapshot_at: datetime
    scheduled_at: datetime
    delay_s: int
    canceled: bool
    is_extra: bool
    destination_station_id: str
    destination_station_name: str
    vehicle_id: str
    train_type: str
    platform: str | None
    platform_changed: bool
    occupancy: str | None
    source_file: str


@dataclass(frozen=True, slots=True, kw_only=True)
class Station:
    """Represent a station wich is a name, locationX and Y and id"""

    station_id: str
    standard_name: str
    longitude: float
    latitude: float
    api_generated_at: datetime
    snapshot_at: datetime
    source_file: str
