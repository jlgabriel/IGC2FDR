#!/usr/bin/env python3
"""
IGC file parser module for IGC to FDR converter
"""

import math
from datetime import date, datetime, timedelta
from typing import TextIO

from igc_model import FileType, FdrFlight, FdrTrackPoint, FlightMeta
from igc_utils import calculateDistance, calculateHeading, wrapHeading, wrapAttitude
from igc_summary import flightSummary
from igc_constants import (
    DEFAULT_ROLL_FACTOR,
    DEFAULT_PITCH_FACTOR,
    DEFAULT_SMOOTHING_FACTOR,
    DEFAULT_STRIP_PREFIXES,
    DEFAULT_UNKNOWN_TEXT,
    DEFAULT_NA_TEXT,
    IGC_HEADER_PILOT,
    IGC_HEADER_GLIDER_TYPE,
    IGC_HEADER_GLIDER_ID,
    IGC_HEADER_GPS,
    IGC_HEADER_SITE,
    IGC_HEADER_DATE,
    IGC_RECORD_POSITION,
    IGC_ALTITUDE_MARKER,
    FEET_PER_METER,
    KNOTS_PER_MPS,
    SECONDS_PER_MINUTE,
    EARTH_GRAVITY,
    RADIANS_PER_DEGREE
)


def strip_prefixes(text, prefixes):
    """Remove common prefixes from a text string"""
    if not text:
        return text

    for prefix in prefixes:
        if text.startswith(prefix):
            return text[len(prefix):]

    return text


def getFiletype(file: TextIO) -> FileType:
    """Determine the file type based on content"""
    filetype = FileType.UNKNOWN
    startingPos = file.tell()

    # Try to detect IGC first (they typically start with 'A' followed by manufacturer code)
    line = file.readline()
    if isinstance(line, bytes):
        line = line.decode('utf-8', errors='ignore')
    if line.startswith('A'):
        # Check if the second line is a header record
        line2 = file.readline()
        if isinstance(line2, bytes):
            line2 = line2.decode('utf-8', errors='ignore')
        if line2.startswith('H'):
            filetype = FileType.IGC
    # Reset position to check other formats if not IGC
    file.seek(startingPos)

    if filetype == FileType.UNKNOWN:
        line = file.readline()
        if isinstance(line, bytes):
            line = line.decode('utf-8', errors='ignore')
        if not line.startswith('<?xml'):
            filetype = FileType.CSV
        else:
            line = file.readline()
            if isinstance(line, bytes):
                line = line.decode('utf-8', errors='ignore')
            if line.startswith('<kml'):
                filetype = FileType.KML
            elif line.startswith('<gpx'):
                filetype = FileType.GPX

    file.seek(startingPos)
    return filetype


def apply_attitude_smoothing(fdrPoint, prev_point, tailConfig):
    """Apply smoothing and scaling to attitude values"""
    # Get smoothing factors from config or use defaults
    roll_factor = DEFAULT_ROLL_FACTOR
    pitch_factor = DEFAULT_PITCH_FACTOR

    if 'rollfactor' in tailConfig:
        try:
            roll_factor = float(tailConfig['rollfactor'])
        except ValueError:
            pass

    if 'pitchfactor' in tailConfig:
        try:
            pitch_factor = float(tailConfig['pitchfactor'])
        except ValueError:
            pass

    # Scale the values to be less extreme
    fdrPoint.ROLL = fdrPoint.ROLL * roll_factor
    fdrPoint.PITCH = fdrPoint.PITCH * pitch_factor

    # Apply simple smoothing if we have a previous point
    if prev_point:
        smoothing = DEFAULT_SMOOTHING_FACTOR  # Smoothing factor (0=no smoothing, 1=no change)
        fdrPoint.HEADING = prev_point.HEADING * smoothing + fdrPoint.HEADING * (1 - smoothing)
        fdrPoint.PITCH = prev_point.PITCH * smoothing + fdrPoint.PITCH * (1 - smoothing)
        fdrPoint.ROLL = prev_point.ROLL * smoothing + fdrPoint.ROLL * (1 - smoothing)

    # Apply attitude correction from config
    fdrPoint.HEADING = round(wrapHeading(fdrPoint.HEADING + tailConfig['headingtrim']), 3)
    fdrPoint.PITCH = round(wrapAttitude(fdrPoint.PITCH + tailConfig['pitchtrim']), 3)
    fdrPoint.ROLL = round(wrapAttitude(fdrPoint.ROLL + tailConfig['rolltrim']), 3)


def parseIgcFile(config, trackFile: TextIO) -> FdrFlight:
    """
    Parse an IGC file into an FdrFlight object.

    IGC files contain flight tracks for gliders with position, altitude and time data.
    They do not directly provide attitude (pitch, roll) which must be estimated.
    """
    flightMeta = FlightMeta()
    fdrFlight = FdrFlight()

    # Set default timezone for IGC (typically UTC)
    fdrFlight.timezone = config.timezoneIGC if config.timezoneIGC is not None else config.timezone

    # Variables to store flight date and previous points for calculations
    flight_date = None
    prev_point = None
    prev_time = None
    total_distance = 0.0

    # Read all lines from the file
    lines = trackFile.readlines()

    # Get prefix stripping list from config if available
    prefixes_to_strip = DEFAULT_STRIP_PREFIXES  # Default prefixes to strip from constants
    try:
        # Try to get aircraft-specific prefixes to strip
        aircraft_section = config.acftByTail("DEFAULT")  # Use DEFAULT as fallback
        if aircraft_section and aircraft_section in config.file:
            aircraft_config = config.file[aircraft_section]
            if 'stripprefixes' in aircraft_config:
                prefixes_to_strip = [p.strip() for p in aircraft_config['stripprefixes'].split(',')]
    except Exception:
        pass  # Ignore if there's an error getting prefixes

    # First pass: extract header information
    for line in lines:
        if isinstance(line, bytes):
            line = line.decode('utf-8', errors='ignore')
        line = line.strip()
        if not line:
            continue

        record_type = line[0]

        # Process header records (H)
        if record_type == 'H':
            if len(line) < 5:  # Ensure we have enough characters
                continue

            header_type = line[1:5]

            if header_type == IGC_HEADER_PILOT and len(line) > 5:  # Pilot
                pilot_value = line[5:].strip()
                flightMeta.Pilot = strip_prefixes(pilot_value, prefixes_to_strip)
            elif header_type == IGC_HEADER_GLIDER_TYPE and len(line) > 5:  # Glider type
                type_value = line[5:].strip()
                flightMeta.DeviceModel = strip_prefixes(type_value, prefixes_to_strip)
            elif header_type == IGC_HEADER_GLIDER_ID and len(line) > 5:  # Glider ID/Registration
                id_value = line[5:].strip()
                flightMeta.TailNumber = strip_prefixes(id_value, prefixes_to_strip)
                fdrFlight.TAIL = flightMeta.TailNumber or DEFAULT_UNKNOWN_TEXT
            elif header_type == IGC_HEADER_GPS and len(line) > 5:  # GPS source
                flightMeta.GPSSource = f"IGC Flight Logger (DOP={line[5:].strip()})"
            elif header_type == IGC_HEADER_SITE and len(line) > 5:  # Site/Takeoff
                flightMeta.DerivedOrigin = line[5:].strip()
            elif header_type == IGC_HEADER_DATE and len(line) > 11:  # Date (DDMMYY)
                try:
                    day = int(line[5:7])
                    month = int(line[7:9])
                    year = 2000 + int(line[9:11])  # Assuming 2000+
                    flight_date = date(year, month, day)
                    fdrFlight.DATE = flight_date
                except (ValueError, IndexError):
                    # If date parsing fails, use current date
                    flight_date = datetime.today().date()
                    fdrFlight.DATE = flight_date

        # If we found a B record, stop processing headers
        if record_type == IGC_RECORD_POSITION:
            break

    # Initialize IGC-specific metadata
    flightMeta.InitialAttitudeSource = "Estimated from IGC trajectory"
    flightMeta.ImportedFrom = "IGC Flight Logger"

    # Second pass: process B records (position fixes)
    for line in lines:
        if isinstance(line, bytes):
            line = line.decode('utf-8', errors='ignore')
        line = line.strip()
        if not line or len(line) < 35:  # B records are typically 35+ chars
            continue

        if line[0] == IGC_RECORD_POSITION:
            try:
                # Time (HHMMSS)
                hour = int(line[1:3])
                minute = int(line[3:5])
                second = int(line[5:7])

                # Create datetime object
                if flight_date:
                    point_time = datetime.combine(flight_date, datetime.min.time())
                    point_time = point_time.replace(hour=hour, minute=minute, second=second)
                else:
                    # If we don't have a date, use today
                    point_time = datetime.now().replace(hour=hour, minute=minute, second=second)

                # Latitude (DDMM.mmmN/S format: degrees, minutes, north/south)
                lat_deg = int(line[7:9])
                lat_min = int(line[9:11])
                lat_frac = int(line[11:14]) / 1000
                lat_dir = line[14]

                latitude = lat_deg + (lat_min + lat_frac) / 60.0
                if lat_dir == 'S':
                    latitude = -latitude

                # Longitude (DDDMM.mmmE/W format: degrees, minutes, east/west)
                lon_deg = int(line[15:18])
                lon_min = int(line[18:20])
                lon_frac = int(line[20:23]) / 1000
                lon_dir = line[23]

                longitude = lon_deg + (lon_min + lon_frac) / 60.0
                if lon_dir == 'W':
                    longitude = -longitude

                # Altitude - using the corrected method for IGC format
                # Find 'A' which indicates the altitude section in IGC format
                a_pos = line.find(IGC_ALTITUDE_MARKER, 23)
                if a_pos > 0:
                    # Extract altitude values based on 'A' position
                    alt_pressure = int(line[a_pos + 1:a_pos + 6])
                    # Check if GPS altitude is available after pressure altitude
                    if len(line) >= a_pos + 11:
                        try:
                            alt_gps = int(line[a_pos + 6:a_pos + 11])
                        except ValueError:
                            alt_gps = alt_pressure  # Use pressure altitude if GPS altitude is invalid
                    else:
                        alt_gps = alt_pressure
                else:
                    # Fallback to fixed positions if 'A' is not found
                    try:
                        alt_pressure = int(line[25:30])
                        alt_gps = alt_pressure
                        if len(line) >= 36:
                            try:
                                alt_gps = int(line[30:35])
                            except ValueError:
                                pass  # Use pressure altitude if GPS altitude is invalid
                    except ValueError:
                        print(f"Warning: Could not parse altitude from line: {line}")
                        alt_pressure = 0
                        alt_gps = 0

                # Create a new track point
                fdrPoint = FdrTrackPoint()
                fdrPoint.TIME = point_time + timedelta(seconds=fdrFlight.timezone)
                fdrPoint.LAT = round(latitude, 9)
                fdrPoint.LONG = round(longitude, 9)

                # Use GPS altitude if available, otherwise pressure altitude
                # Convert meters to feet for X-Plane
                fdrPoint.ALTMSL = round(alt_gps * FEET_PER_METER, 4)

                # Default values for heading, pitch, and roll
                fdrPoint.HEADING = 0
                fdrPoint.PITCH = 0
                fdrPoint.ROLL = 0

                # Store variables for DREF calculations
                trackData = {
                    'Timestamp': fdrPoint.TIME.timestamp(),
                    'Latitude': fdrPoint.LAT,
                    'Longitude': fdrPoint.LONG,
                    'Altitude': fdrPoint.ALTMSL,
                    'Course': 0,
                    'Pitch': 0,
                    'Bank': 0,
                    'Speed': 0,
                    'VerticalSpeed': 0
                }

                # Calculate derived values if we have a previous point
                if prev_point and prev_time:
                    # Time difference in seconds
                    time_diff = (fdrPoint.TIME - prev_time).total_seconds()

                    if time_diff > 0:
                        # Calculate distance between points using haversine formula
                        dist = calculateDistance(prev_point.LAT, prev_point.LONG, fdrPoint.LAT, fdrPoint.LONG)

                        # Calculate ground speed in knots
                        speed_kts = (dist / time_diff) * KNOTS_PER_MPS  # m/s to knots
                        trackData['Speed'] = round(speed_kts, 2)

                        # Calculate heading based on change in position
                        heading = calculateHeading(prev_point.LAT, prev_point.LONG, fdrPoint.LAT, fdrPoint.LONG)
                        fdrPoint.HEADING = round(heading, 3)
                        trackData['Course'] = heading

                        # Calculate vertical speed (feet per minute)
                        alt_change = fdrPoint.ALTMSL - prev_point.ALTMSL
                        vert_speed = (alt_change / time_diff) * SECONDS_PER_MINUTE  # feet per minute
                        trackData['VerticalSpeed'] = round(vert_speed, 2)

                        # Estimate pitch from vertical speed and ground speed
                        if dist > 0:
                            # Convert distance to feet for consistent units
                            dist_ft = dist * FEET_PER_METER
                            # Simple trigonometry: pitch = arctan(altitude change / distance)
                            pitch_angle = math.degrees(math.atan2(alt_change, dist_ft))
                            fdrPoint.PITCH = round(pitch_angle, 3)
                            trackData['Pitch'] = pitch_angle

                        # Estimate roll from rate of heading change
                        # This is very simplified - real aircraft roll relates to turn rate and airspeed
                        heading_change = abs(fdrPoint.HEADING - prev_point.HEADING)
                        if heading_change > 180:  # Handle wrap-around (e.g. 359 -> 1)
                            heading_change = 360 - heading_change

                        # Simple formula to estimate bank angle from turn rate
                        if heading_change > 0:
                            turn_rate = heading_change / time_diff  # degrees per second
                            # Approximation: roll ≈ arctan(v * turn_rate / g)
                            # Where v is speed in m/s, turn_rate in rad/s, g is 9.81 m/s²
                            speed_ms = speed_kts * 0.51444  # knots to m/s
                            roll_angle = math.degrees(math.atan2(
                                speed_ms * turn_rate * RADIANS_PER_DEGREE, 
                                EARTH_GRAVITY))

                            # Determine roll direction (left/right turn)
                            heading_diff = (fdrPoint.HEADING - prev_point.HEADING + 360) % 360
                            if heading_diff > 180:
                                roll_angle = -roll_angle  # Left turn

                            fdrPoint.ROLL = round(roll_angle, 3)
                            trackData['Bank'] = roll_angle

                # Apply smoothing and attitude corrections
                tailConfig = config.tail(fdrFlight.TAIL)
                apply_attitude_smoothing(fdrPoint, prev_point, tailConfig)

                # Evaluate DREFs for this point
                drefSources, _ = config.drefsByTail(fdrFlight.TAIL)
                for name in drefSources:
                    try:
                        value = drefSources[name]
                        meta = vars(flightMeta)
                        point = vars(fdrPoint)
                        fdrPoint.drefs[name] = eval(value.format(**meta, **point, **trackData))
                    except Exception as e:
                        print(f"Warning: Failed to evaluate DREF {name}: {e}")
                        fdrPoint.drefs[name] = 0

                # Add point to the flight track
                fdrFlight.track.append(fdrPoint)

                # Update total distance for the flight
                if prev_point:
                    dist_miles = calculateDistance(prev_point.LAT, prev_point.LONG,
                                                   fdrPoint.LAT, fdrPoint.LONG) * 0.000621371  # meters to miles
                    total_distance += dist_miles

                # Store current point as previous for next iteration
                prev_point = fdrPoint
                prev_time = fdrPoint.TIME

            except (ValueError, IndexError) as e:
                print(f"Warning: Skipping invalid B record: {line[:35]}... ({e})")

    # Complete flight metadata if we have track points
    if fdrFlight.track:
        flightMeta.StartTime = fdrFlight.track[0].TIME
        flightMeta.StartLatitude = fdrFlight.track[0].LAT
        flightMeta.StartLongitude = fdrFlight.track[0].LONG

        flightMeta.EndTime = fdrFlight.track[-1].TIME
        flightMeta.EndLatitude = fdrFlight.track[-1].LAT
        flightMeta.EndLongitude = fdrFlight.track[-1].LONG

        flightMeta.TotalDuration = flightMeta.EndTime - flightMeta.StartTime
        flightMeta.TotalDistance = total_distance

    # Generate flight summary
    fdrFlight.summary = flightSummary(flightMeta)

    return fdrFlight