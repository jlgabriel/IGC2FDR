#!/usr/bin/env python3
"""
Utility functions for IGC to FDR converter
"""

import re
import math
from datetime import datetime, date
from typing import Union

from igc_constants import (
    EARTH_RADIUS_METERS,
    DEGREES_IN_CIRCLE,
    MAX_ATTITUDE_ANGLE,
    DATE_FORMAT_MDY,
    DATE_FORMAT_YMD,
    TIME_FORMAT_HM
)

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
    return degrees % DEGREES_IN_CIRCLE


def wrapAttitude(degrees: float) -> float:
    """Normalize pitch/roll to -180 to +180 degrees"""
    mod = DEGREES_IN_CIRCLE if degrees >= 0 else -DEGREES_IN_CIRCLE
    degrees = degrees % mod
    if degrees > MAX_ATTITUDE_ANGLE:
        return degrees - DEGREES_IN_CIRCLE
    elif degrees < -MAX_ATTITUDE_ANGLE:
        return degrees + DEGREES_IN_CIRCLE
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
    
    return EARTH_RADIUS_METERS * c


def calculateHeading(lat1: float, lon1: float, lat2: float, lon2: float, fallback_heading: float = None) -> float:
    """
    Calculate the initial heading between two points in decimal degrees.
    Handles identical or very close GPS points by using fallback heading.
    
    Args:
        lat1, lon1: Starting point coordinates
        lat2, lon2: Ending point coordinates  
        fallback_heading: Heading to return if points are too close (default: None)
        
    Returns:
        Heading in degrees (0-360), or fallback_heading if points are identical/very close
    """
    # Check if points are identical or very close (within ~1 meter)
    distance = calculateDistance(lat1, lon1, lat2, lon2)
    if distance < 1.0:  # Less than 1 meter apart
        if fallback_heading is not None:
            return fallback_heading
        else:
            # Return 360 instead of 0 to avoid discontinuity issues
            return 360.0
    
    # Convert to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    # Calculate heading
    y = math.sin(lon2_rad - lon1_rad) * math.cos(lat2_rad)
    x = math.cos(lat1_rad) * math.sin(lat2_rad) - math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(lon2_rad - lon1_rad)
    
    # Handle edge case where both x and y are very small (near zero)
    if abs(x) < 1e-10 and abs(y) < 1e-10:
        if fallback_heading is not None:
            return fallback_heading
        else:
            return 360.0  # Avoid returning 0 to prevent discontinuities
    
    heading_rad = math.atan2(y, x)
    
    # Convert to degrees and normalize to 0-360
    heading_deg = (math.degrees(heading_rad) + DEGREES_IN_CIRCLE) % DEGREES_IN_CIRCLE
    
    # Handle very small headings that might cause issues
    if heading_deg < 0.001:
        return 360.0
    
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
        return time_input.strftime(DATE_FORMAT_MDY)
    
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
        return time_input.strftime(DATE_FORMAT_YMD)
    
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
        return time_input.strftime(TIME_FORMAT_HM)
    
    return str(time_input)  # Fallback
