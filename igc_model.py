#!/usr/bin/env python3
"""
Data models and enums for IGC to FDR converter
"""

from dataclasses import dataclass, field
from enum import Enum
from datetime import date, datetime, timedelta
from typing import Dict, List, Tuple, Optional

from igc_constants import (
    DEFAULT_TIMEZONE, DEGREES_IN_CIRCLE, MAX_ATTITUDE_ANGLE
)

# Note: Using Enum from igc_constants instead
from igc_constants import FileType as FileTypeConstants

class FileType(Enum):
    UNKNOWN = FileTypeConstants.UNKNOWN
    CSV = FileTypeConstants.CSV
    KML = FileTypeConstants.KML
    GPX = FileTypeConstants.GPX
    IGC = FileTypeConstants.IGC


@dataclass
class FdrTrackPoint:
    """Represents a single track point in the FDR file with position and attitude data"""
    TIME: datetime = None
    LONG: float = 0.0
    LAT: float = 0.0
    ALTMSL: float = 0.0
    HEADING: float = 0.0
    PITCH: float = 0.0
    ROLL: float = 0.0
    drefs: Dict[str, float] = field(default_factory=dict)


@dataclass
class FdrFlight:
    """Represents a complete flight with aircraft details and track points"""
    ACFT: str = ''
    TAIL: str = ''
    DATE: date = field(default_factory=datetime.today().date)
    PRES: float = 0.0
    DISA: int = 0
    WIND: Tuple[int, int] = (0, 0)
    timezone: int = DEFAULT_TIMEZONE
    track: List[FdrTrackPoint] = field(default_factory=list)
    summary: str = ''


@dataclass
class FlightMeta:
    """Metadata about a flight for summary generation and additional information"""
    Pilot: Optional[str] = None
    TailNumber: Optional[str] = None
    DerivedOrigin: Optional[str] = None
    StartLatitude: Optional[float] = None
    StartLongitude: Optional[float] = None
    DerivedDestination: Optional[str] = None
    EndLatitude: Optional[float] = None
    EndLongitude: Optional[float] = None
    StartTime: Optional[datetime] = None
    EndTime: Optional[datetime] = None
    TotalDuration: Optional[timedelta] = None
    TotalDistance: Optional[float] = None
    InitialAttitudeSource: Optional[str] = None
    DeviceModel: Optional[str] = None
    DeviceDetails: Optional[str] = None
    DeviceVersion: Optional[str] = None
    BatteryLevel: Optional[float] = None
    BatteryState: Optional[str] = None
    GPSSource: Optional[str] = None
    MaximumVerticalError: Optional[float] = None
    MinimumVerticalError: Optional[float] = None
    AverageVerticalError: Optional[float] = None
    MaximumHorizontalError: Optional[float] = None
    MinimumHorizontalError: Optional[float] = None
    AverageHorizontalError: Optional[float] = None
    ImportedFrom: Optional[str] = None
    RouteWaypoints: Optional[str] = None
