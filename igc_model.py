#!/usr/bin/env python3
"""
Data models and enums for IGC to FDR converter
"""

from enum import Enum
from datetime import date, datetime, timedelta
from typing import Dict, List, Tuple

class FileType(Enum):
    UNKNOWN = 0
    CSV = 1
    KML = 2
    GPX = 3
    IGC = 4

class FdrTrackPoint:
    TIME: datetime
    LONG: float
    LAT: float
    ALTMSL: float
    HEADING: float = 0
    PITCH: float = 0
    ROLL: float = 0

    drefs: Dict[str, float] = None

    def __init__(self):
        self.drefs = {}


class FdrFlight:
    ACFT: str = ''
    TAIL: str = ''
    DATE: date = datetime.today().date()
    PRES: float = 0
    DISA: int = 0
    WIND: Tuple[int, int] = (0, 0)

    timezone: int = 0
    track: List[FdrTrackPoint] = None

    def __init__(self):
        self.track = []
        self.summary = ''


class FlightMeta:
    Pilot: str = None
    TailNumber: str = None
    DerivedOrigin: str = None
    StartLatitude: float = None
    StartLongitude: float = None
    DerivedDestination: str = None
    EndLatitude: float = None
    EndLongitude: float = None
    StartTime: datetime = None
    EndTime: datetime = None
    TotalDuration: timedelta = None
    TotalDistance: float = None
    InitialAttitudeSource: str = None
    DeviceModel: str = None
    DeviceDetails: str = None
    DeviceVersion: str = None
    BatteryLevel: float = None
    BatteryState: str = None
    GPSSource: str = None
    MaximumVerticalError: float = None
    MinimumVerticalError: float = None
    AverageVerticalError: float = None
    MaximumHorizontalError: float = None
    MinimumHorizontalError: float = None
    AverageHorizontalError: float = None
    ImportedFrom: str = None
    RouteWaypoints: str = None
