from dataclasses import dataclass

@dataclass(frozen=True)
class Location:
    name: str
    city: str
    latitude: float
    longitude: float

@dataclass(frozen=True)
class Route:
    start: Location
    end: Location
