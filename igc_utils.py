#!/usr/bin/env python3
"""
Utility functions for IGC to FDR converter
"""

import re
import math
from datetime import datetime, date
from typing import Union

def secondsFromString(timezone: str) -> int:
    """Convert a timezone string to seconds offset"""
    seconds = 0

    timezone = numberOrString(timezone)
    if isinstance(timezone, (float, int)):
        seconds = timezone * 3600
    elif isinstance(timezone, str):
        indexAfterSign = int(timezone[0] in ['+','-'])
        zone = timezone[indexAfterSign:].split(':')

        seconds = float(zone.pop())
        seconds += float(zone.pop()) * 60
        if len(zone):
            seconds += float(zone.pop()) * 3600
        else:
            seconds *= 60

        seconds *= -1 if timezone[0] == '-' else 1

    return int(seconds)


def numberOrString(value: str) -> Union[float, str]:
    """Convert a string to a number if possible, otherwise keep as string"""
    if re.sub('^[+-]', '', re.sub('\\.', '', value)).isnumeric():
        return float(value)
    else:
        return value


def wrapHeading(degrees: float) -> float:
    """Normalize heading to 0-360 degrees"""
    return degrees % 360


def wrapAttitude(degrees: float) -> float:
    """Normalize pitch/roll to -180 to +180 degrees"""
    mod = 360 if degrees >= 0 else -360
    degrees = degrees % mod
    if degrees > 180:
        return degrees - 360
    elif degrees < -180:
        return degrees + 360
    else:
        return degrees


def calculateDistance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points on earth.
    Returns distance in meters.
    """
    # Convert decimal degrees to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    # Haversine formula
    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    r = 6371000  # Radius of earth in meters
    
    return r * c


def calculateHeading(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the initial heading between two points in decimal degrees.
    Returns heading in degrees (0-360).
    """
    # Convert to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    # Calculate heading
    y = math.sin(lon2_rad - lon1_rad) * math.cos(lat2_rad)
    x = math.cos(lat1_rad) * math.sin(lat2_rad) - math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(lon2_rad - lon1_rad)
    heading_rad = math.atan2(y, x)
    
    # Convert to degrees and normalize to 0-360
    heading_deg = (math.degrees(heading_rad) + 360) % 360
    
    return heading_deg


def toMDY(time_input: Union[datetime, date, int, str]) -> str:
    """Convert a time to MM/DD/YYYY format"""
    if isinstance(time_input, str):
        try:
            time_input = float(time_input)
        except ValueError:
            # If not convertible to float, try parsing as datetime
            try:
                time_input = datetime.fromisoformat(time_input)
            except ValueError:
                return time_input  # Return original if cannot convert
    
    if isinstance(time_input, (int, float)):
        # Assuming timestamp in milliseconds
        time_input = datetime.fromtimestamp(time_input / 1000)
    
    if isinstance(time_input, (datetime, date)):
        return time_input.strftime('%m/%d/%Y')
    
    return str(time_input)  # Fallback


def toYMD(time_input: Union[datetime, date, int, str]) -> str:
    """Convert a time to YYYY/MM/DD format"""
    if isinstance(time_input, str):
        try:
            time_input = float(time_input)
        except ValueError:
            # If not convertible to float, try parsing as datetime
            try:
                time_input = datetime.fromisoformat(time_input)
            except ValueError:
                return time_input  # Return original if cannot convert
    
    if isinstance(time_input, (int, float)):
        # Assuming timestamp in milliseconds
        time_input = datetime.fromtimestamp(time_input / 1000)
    
    if isinstance(time_input, (datetime, date)):
        return time_input.strftime('%Y/%m/%d')
    
    return str(time_input)  # Fallback


def toHM(time_input: Union[datetime, date, int, str]) -> str:
    """Convert a time to HH:MM format"""
    if isinstance(time_input, str):
        try:
            time_input = float(time_input)
        except ValueError:
            # If not convertible to float, try parsing as datetime
            try:
                time_input = datetime.fromisoformat(time_input)
            except ValueError:
                return time_input  # Return original if cannot convert
    
    if isinstance(time_input, (int, float)):
        # Assuming timestamp in milliseconds
        time_input = datetime.fromtimestamp(time_input / 1000)
    
    if isinstance(time_input, (datetime, date)):
        return time_input.strftime('%H:%M')
    
    return str(time_input)  # Fallback
