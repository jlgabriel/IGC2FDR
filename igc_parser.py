#!/usr/bin/env python3
"""
IGC file parser module for IGC to FDR converter

This module handles parsing of IGC files including header metadata extraction,
position data processing, and attitude estimation based on trajectory.

🔧 FIXED: apply_smoothing() method moved INSIDE AttitudeCalculator class
"""

import math
import logging
from datetime import date, datetime, timedelta
from typing import TextIO, Dict, List, Tuple, Optional, Any

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
    RADIANS_PER_DEGREE,
    DEGREES_IN_CIRCLE
)

# Configure logger
logger = logging.getLogger(__name__)


class IgcFileDetector:
    """
    Detects the file type of a given file based on its content.
    Specialized in recognizing IGC, CSV, KML and GPX formats.
    """
    
    @staticmethod
    def detect_filetype(file: TextIO) -> FileType:
        """Determine the file type based on content"""
        filetype = FileType.UNKNOWN
        starting_pos = file.tell()

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
        file.seek(starting_pos)

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

        file.seek(starting_pos)
        return filetype


class IgcHeaderParser:
    """
    Parses header records from IGC files and extracts metadata.
    Handles different header types and formats.
    """
    
    def __init__(self, prefixes_to_strip: List[str] = None):
        """
        Initialize with optional list of prefixes to strip from header values
        """
        self.prefixes_to_strip = prefixes_to_strip or DEFAULT_STRIP_PREFIXES
    
    @staticmethod
    def strip_prefixes(text: str, prefixes: List[str]) -> str:
        """Remove common prefixes from a text string"""
        if not text:
            return text

        for prefix in prefixes:
            if text.startswith(prefix):
                return text[len(prefix):]

        return text
    
    def parse_header_line(self, line: str, flight_meta: FlightMeta, flight_date: Optional[date] = None) -> Tuple[FlightMeta, Optional[date]]:
        """
        Parse a single header line and update flight metadata
        Returns updated FlightMeta and flight_date
        """
        if len(line) < 5 or line[0] != 'H':  # Ensure we have enough characters
            return flight_meta, flight_date
            
        header_type = line[1:5]

        if header_type == IGC_HEADER_PILOT and len(line) > 5:  # Pilot
            pilot_value = line[5:].strip()
            flight_meta.Pilot = self.strip_prefixes(pilot_value, self.prefixes_to_strip)
        
        elif header_type == IGC_HEADER_GLIDER_TYPE and len(line) > 5:  # Glider type
            type_value = line[5:].strip()
            flight_meta.DeviceModel = self.strip_prefixes(type_value, self.prefixes_to_strip)
        
        elif header_type == IGC_HEADER_GLIDER_ID and len(line) > 5:  # Glider ID/Registration
            id_value = line[5:].strip()
            flight_meta.TailNumber = self.strip_prefixes(id_value, self.prefixes_to_strip)
        
        elif header_type == IGC_HEADER_GPS and len(line) > 5:  # GPS source
            flight_meta.GPSSource = f"IGC Flight Logger (DOP={line[5:].strip()})"
        
        elif header_type == IGC_HEADER_SITE and len(line) > 5:  # Site/Takeoff
            flight_meta.DerivedOrigin = line[5:].strip()
        
        elif header_type == IGC_HEADER_DATE and len(line) > 11:  # Date (DDMMYY)
            try:
                day = int(line[5:7])
                month = int(line[7:9])
                year = 2000 + int(line[9:11])  # Assuming 2000+
                flight_date = date(year, month, day)
            except (ValueError, IndexError):
                # If date parsing fails, use current date
                flight_date = datetime.today().date()
                logger.warning("Invalid date format in IGC header, using current date")
        
        return flight_meta, flight_date


class IgcPositionParser:
    """
    Parses position records (B records) from IGC files.
    Extracts time, coordinates, and altitude data.
    """
    
    @staticmethod
    def parse_time(line: str, flight_date: Optional[date]) -> datetime:
        """Extract time from a B record"""
        hour = int(line[1:3])
        minute = int(line[3:5])
        second = int(line[5:7])

        if flight_date:
            point_time = datetime.combine(flight_date, datetime.min.time())
            point_time = point_time.replace(hour=hour, minute=minute, second=second)
        else:
            # If we don't have a date, use today
            point_time = datetime.now().replace(hour=hour, minute=minute, second=second)
            
        return point_time
    
    @staticmethod
    def parse_latitude(line: str) -> float:
        """Extract latitude from a B record"""
        lat_deg = int(line[7:9])
        lat_min = int(line[9:11])
        lat_frac = int(line[11:14]) / 1000
        lat_dir = line[14]

        latitude = lat_deg + (lat_min + lat_frac) / 60.0
        if lat_dir == 'S':
            latitude = -latitude
            
        return latitude
    
    @staticmethod
    def parse_longitude(line: str) -> float:
        """Extract longitude from a B record"""
        lon_deg = int(line[15:18])
        lon_min = int(line[18:20])
        lon_frac = int(line[20:23]) / 1000
        lon_dir = line[23]

        longitude = lon_deg + (lon_min + lon_frac) / 60.0
        if lon_dir == 'W':
            longitude = -longitude
            
        return longitude
    
    @staticmethod
    def parse_altitude(line: str) -> Tuple[int, int]:
        """
        Extract pressure and GPS altitude from a B record
        Returns tuple of (pressure_altitude, gps_altitude) in meters
        """
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
                logger.warning(f"Could not parse altitude from line: {line}")
                alt_pressure = 0
                alt_gps = 0
                
        return alt_pressure, alt_gps
    
    def parse_position_record(self, line: str, flight_date: Optional[date], timezone_offset: int = 0) -> FdrTrackPoint:
        """
        Parse a complete B record and return a FdrTrackPoint
        """
        # Create a new track point
        point = FdrTrackPoint()
        
        # Parse time
        point.TIME = self.parse_time(line, flight_date) + timedelta(seconds=timezone_offset)
        
        # Parse coordinates
        point.LAT = round(self.parse_latitude(line), 9)
        point.LONG = round(self.parse_longitude(line), 9)
        
        # Parse altitude
        _, alt_gps = self.parse_altitude(line)
        
        # Convert meters to feet for X-Plane
        point.ALTMSL = round(alt_gps * FEET_PER_METER, 4)
        
        # Initialize attitude values
        point.HEADING = 0
        point.PITCH = 0
        point.ROLL = 0
        
        return point


class AttitudeCalculator:
    """
    Calculates aircraft attitude (heading, pitch, roll) based on position data.
    Applies smoothing and calibration to the values.
    """
    
    @staticmethod
    def calculate_derived_values(current_point: FdrTrackPoint, 
                                 prev_point: FdrTrackPoint, 
                                 time_diff: float) -> Dict[str, float]:
        """
        Calculate derived values such as ground speed, heading, and vertical speed
        Returns a dictionary of calculated values
        """

        if prev_point.HEADING == 0.0 or current_point.HEADING == 0.0:
                print(f"DEBUG: prev_heading={prev_point.HEADING:.1f}deg, time_diff={time_diff:.1f}s")

        derived_values = {
            'Speed': 0,
            'Course': 0,
            'VerticalSpeed': 0,
            'Pitch': 0,
            'Bank': 0
        }
        
        if time_diff <= 0:
            return derived_values
            
        # Calculate distance between points using haversine formula
        dist = calculateDistance(
            prev_point.LAT, prev_point.LONG, 
            current_point.LAT, current_point.LONG
        )

        # Calculate ground speed in knots
        speed_kts = (dist / time_diff) * KNOTS_PER_MPS  # m/s to knots
        derived_values['Speed'] = round(speed_kts, 2)

        # Calculate heading based on change in position
        # FIXED: Pass previous heading as fallback for close/identical GPS points
        heading = calculateHeading(
            prev_point.LAT, prev_point.LONG, 
            current_point.LAT, current_point.LONG,
            fallback_heading=prev_point.HEADING  # Use previous heading if points too close
        )

        if (46.80 < current_point.LAT < 46.81 and 12.88 < current_point.LONG < 12.89):
            print(f"PROBLEM COORDS DEBUG - TIME: {current_point.TIME.strftime('%H:%M:%S')}")
            print(f"  From: {prev_point.LAT:.6f}, {prev_point.LONG:.6f}")
            print(f"  To:   {current_point.LAT:.6f}, {current_point.LONG:.6f}")
            print(f"  Distance: {calculateDistance(prev_point.LAT, prev_point.LONG, current_point.LAT, current_point.LONG):.3f}m")
            print(f"  Calculated heading: {heading:.3f}deg")
            print(f"  Previous heading: {prev_point.HEADING:.3f}deg")
            print(f"  --- END DEBUG ---")


        current_point.HEADING = round(heading, 3)
        derived_values['Course'] = heading

        # Calculate vertical speed (feet per minute)
        alt_change = current_point.ALTMSL - prev_point.ALTMSL
        vert_speed = (alt_change / time_diff) * SECONDS_PER_MINUTE  # feet per minute
        derived_values['VerticalSpeed'] = round(vert_speed, 2)

        # Estimate pitch from vertical speed and ground speed
        if dist > 0:
            # Convert distance to feet for consistent units
            dist_ft = dist * FEET_PER_METER
            # Simple trigonometry: pitch = arctan(altitude change / distance)
            pitch_angle = math.degrees(math.atan2(alt_change, dist_ft))
            current_point.PITCH = round(pitch_angle, 3)
            derived_values['Pitch'] = pitch_angle

        # Estimate roll from rate of heading change
        # This is very simplified - real aircraft roll relates to turn rate and airspeed
        heading_change = abs(current_point.HEADING - prev_point.HEADING)
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
                EARTH_GRAVITY
            ))

            # Determine roll direction (left/right turn)
            heading_diff = (current_point.HEADING - prev_point.HEADING + 360) % 360
            if heading_diff > 180:
                roll_angle = -roll_angle  # Left turn

            current_point.ROLL = round(roll_angle, 3)
            derived_values['Bank'] = roll_angle
            
        return derived_values
    
    @staticmethod
    def apply_smoothing(current_point: FdrTrackPoint, 
                        prev_point: Optional[FdrTrackPoint], 
                        tail_config: Dict[str, Any]) -> None:
        """
        🔧 FIXED: This method is now INSIDE the AttitudeCalculator class
        Apply smoothing and scaling to attitude values.
        Updates the point in place.
        """
        # Get smoothing factors from config or use defaults
        roll_factor = DEFAULT_ROLL_FACTOR
        pitch_factor = DEFAULT_PITCH_FACTOR

        if 'rollfactor' in tail_config:
            try:
                roll_factor = float(tail_config['rollfactor'])
            except ValueError:
                pass

        if 'pitchfactor' in tail_config:
            try:
                pitch_factor = float(tail_config['pitchfactor'])
            except ValueError:
                pass

        # Scale the values to be less extreme
        current_point.ROLL = current_point.ROLL * roll_factor
        current_point.PITCH = current_point.PITCH * pitch_factor

        # Apply simple smoothing if we have a previous point
        if prev_point:
            smoothing = DEFAULT_SMOOTHING_FACTOR  # Smoothing factor (0=no smoothing, 1=no change)
            
            # FIX: Handle 360/0 degree wrap-around for heading smoothing
            current_heading = current_point.HEADING
            prev_heading = prev_point.HEADING
            
            # Calculate the shortest angular distance
            heading_diff = current_heading - prev_heading
            if heading_diff > 180:
                heading_diff -= 360
            elif heading_diff < -180:
                heading_diff += 360
            
            # Apply smoothing using the corrected difference
            smoothed_heading = prev_heading + heading_diff * (1 - smoothing)
            
            # Normalize to 0-360 range
            if smoothed_heading < 0:
                smoothed_heading += 360
            elif smoothed_heading >= 360:
                smoothed_heading -= 360
            
            current_point.HEADING = smoothed_heading
            current_point.PITCH = prev_point.PITCH * smoothing + current_point.PITCH * (1 - smoothing)
            current_point.ROLL = prev_point.ROLL * smoothing + current_point.ROLL * (1 - smoothing)

        # Apply attitude correction from config
        # Ensure heading is valid before applying trim
        if current_point.HEADING is None or current_point.HEADING == 0:
            # If heading is invalid, calculate it from previous point if available
            if prev_point and hasattr(prev_point, 'HEADING') and prev_point.HEADING != 0:
                current_point.HEADING = prev_point.HEADING  # Use previous heading as fallback
            else:
                current_point.HEADING = 0  # Last resort fallback

        # DEBUG: capture original value before trim
        original_heading = current_point.HEADING

        # NUEVO DEBUG: Mostrar todo el proceso
        print(f"TRIM DEBUG: Before trim={current_point.HEADING:.3f}deg, headingtrim={tail_config['headingtrim']}")
        print(f"TRIM DEBUG: After add: {current_point.HEADING + tail_config['headingtrim']:.3f}deg")
        print(f"TRIM DEBUG: After wrap: {wrapHeading(current_point.HEADING + tail_config['headingtrim']):.3f}deg")

        current_point.HEADING = round(wrapHeading(current_point.HEADING + tail_config['headingtrim']), 3)

        print(f"TRIM DEBUG: Final result: {current_point.HEADING:.3f}deg")

        # DEBUG: detect when heading gets lost
        if original_heading > 0 and current_point.HEADING == 0:
            print(f"HEADING LOST: {original_heading:.3f}deg -> 0.0deg (headingtrim={tail_config['headingtrim']})")

        # DETECTAR DISCONTINUIDADES
        if original_heading > 0:
            heading_change = abs(current_point.HEADING - original_heading)
            if heading_change > 180:
                heading_change = 360 - heading_change
            if heading_change > 45:  # Cambio mayor a 45deg
                print(f"TRIM DISCONTINUITY: {original_heading:.3f}deg → {current_point.HEADING:.3f}deg (change={heading_change:.1f}deg, trim={tail_config['headingtrim']})")

                current_point.PITCH = round(wrapAttitude(current_point.PITCH + tail_config['pitchtrim']), 3)
                current_point.ROLL = round(wrapAttitude(current_point.ROLL + tail_config['rolltrim']), 3)


class TrackBuilder:
    """
    Builds a complete flight track from IGC position records.
    FIXED VERSION: Properly interpolates all values including heading, pitch, roll.
    """
    
    def __init__(self, config):
        """Initialize with configuration"""
        self.config = config
        self.position_parser = IgcPositionParser()
        self.attitude_calculator = AttitudeCalculator()
    
    def _select_best_duplicate_point(self, 
                                     candidates: List[FdrTrackPoint], 
                                     prev_point: Optional[FdrTrackPoint]) -> FdrTrackPoint:
        """
        Select the best point from duplicates with same timestamp.
        Simple version that just picks the most consistent one.
        """
        if len(candidates) == 1:
            return candidates[0]
            
        if not prev_point:
            return candidates[0]
        
        best_point = None
        best_distance = float('inf')
        
        # Pick the point closest to the expected trajectory
        for candidate in candidates:
            distance = calculateDistance(
                prev_point.LAT, prev_point.LONG,
                candidate.LAT, candidate.LONG
            )
            
            if distance < best_distance:
                best_distance = distance
                best_point = candidate
        
        return best_point
    
    def _interpolate_heading(self, start_heading: float, end_heading: float, factor: float) -> float:
        """
        Interpolate heading considering wrap-around (0deg/360deg).
        
        Args:
            start_heading: Starting heading in degrees
            end_heading: Ending heading in degrees  
            factor: Interpolation factor (0.0 to 1.0)
            
        Returns:
            Interpolated heading in degrees
        """
        # Handle wrap-around for heading interpolation
        diff = end_heading - start_heading
        
        # Choose shortest path
        if diff > 180:
            diff -= 360
        elif diff < -180:
            diff += 360
        
        interpolated = start_heading + (diff * factor)
        
        # Normalize to 0-360 range
        while interpolated < 0:
            interpolated += 360
        while interpolated >= 360:
            interpolated -= 360
            
        return interpolated
    
    def _fill_time_gap(self, 
                       start_point: FdrTrackPoint, 
                       end_point: FdrTrackPoint, 
                       gap_seconds: int) -> List[FdrTrackPoint]:
        """
        Fill a time gap between two points with properly interpolated points.
        FIXED: Now interpolates ALL values including heading, pitch, roll.
        """
        gap_points = []
        
        # Don't fill if gap is too large (more than 10 seconds)
        if gap_seconds > 10:
            return gap_points
        
        # Pre-calculate end_point heading if it doesn't have one yet
        if not hasattr(end_point, 'HEADING') or end_point.HEADING == 0:
            # Calculate heading from start to end
            end_point.HEADING = calculateHeading(
                start_point.LAT, start_point.LONG,
                end_point.LAT, end_point.LONG
            )
        
        # Create points for each missing second
        for i in range(1, gap_seconds):
            # Interpolation factor (0.0 to 1.0)
            factor = i / gap_seconds
            
            # Create interpolated point
            gap_point = FdrTrackPoint()
            
            # Interpolate position
            gap_point.LAT = start_point.LAT + (end_point.LAT - start_point.LAT) * factor
            gap_point.LONG = start_point.LONG + (end_point.LONG - start_point.LONG) * factor
            gap_point.ALTMSL = start_point.ALTMSL + (end_point.ALTMSL - start_point.ALTMSL) * factor
            
            # Interpolate time
            gap_point.TIME = start_point.TIME + timedelta(seconds=i)
            
            # Interpolate heading (considering wrap-around)
            gap_point.HEADING = self._interpolate_heading(
                start_point.HEADING, end_point.HEADING, factor
            )
            
            # Interpolate attitude
            gap_point.PITCH = start_point.PITCH + (end_point.PITCH - start_point.PITCH) * factor
            gap_point.ROLL = start_point.ROLL + (end_point.ROLL - start_point.ROLL) * factor
            
            # Initialize drefs
            gap_point.drefs = {}
            
            gap_points.append(gap_point)
        
        return gap_points
        
    def build_track_from_lines(self, 
                               lines: List[str], 
                               flight_meta: FlightMeta, 
                               flight_date: Optional[date], 
                               timezone_offset: int) -> Tuple[List[FdrTrackPoint], float]:
        """
        Process all position records and build a complete track.
        FIXED VERSION: Properly handles heading interpolation.
        
        Args:
            lines: Raw IGC file lines
            flight_meta: Flight metadata
            flight_date: Date of the flight
            timezone_offset: Timezone adjustment in seconds
            
        Returns:
            Tuple of (track_points, total_distance_miles)
        """
        track_points = []
        prev_point = None
        prev_time = None
        total_distance = 0.0
        
        # Dictionary to group points by timestamp (second precision)
        points_by_second = {}
        
        # Get tail number or use default
        tail_number = flight_meta.TailNumber or DEFAULT_UNKNOWN_TEXT
        
        # First pass: group points by timestamp (second precision only)
        for line in lines:
            if isinstance(line, bytes):
                line = line.decode('utf-8', errors='ignore')
            line = line.strip()
            
            if not line or len(line) < 35 or line[0] != 'B':  # IGC position record
                continue
                
            try:
                # Parse position record
                point = self.position_parser.parse_position_record(
                    line, flight_date, timezone_offset
                )
                
                # Use timestamp with SECOND precision as key (ignore milliseconds)
                timestamp_key = point.TIME.strftime("%H%M%S")
                
                if timestamp_key not in points_by_second:
                    points_by_second[timestamp_key] = []
                    
                points_by_second[timestamp_key].append(point)
                
            except (ValueError, IndexError):
                # Skip invalid B records silently
                continue
        
        # Second pass: process points and fill gaps
        sorted_times = sorted(points_by_second.keys())
        
        for i, timestamp_key in enumerate(sorted_times):
            points_at_time = points_by_second[timestamp_key]
            
            # Handle duplicate points at same timestamp
            if len(points_at_time) == 1:
                # Single point - process normally
                processed_points = points_at_time
            else:
                # Multiple points - select best one (don't interpolate within same second)
                best_point = self._select_best_duplicate_point(points_at_time, prev_point)
                processed_points = [best_point]
            
            # Process the point(s) for this timestamp
            for point in processed_points:
                # Store data for DREF calculations
                track_data = {
                    'Timestamp': point.TIME.timestamp(),
                    'Latitude': point.LAT,
                    'Longitude': point.LONG,
                    'Altitude': point.ALTMSL,
                    'Course': 0,
                    'Pitch': 0,
                    'Bank': 0,
                    'Speed': 0,
                    'VerticalSpeed': 0
                }
                
                # Calculate derived values if we have a previous point
                if prev_point and prev_time:
                    # Time difference in seconds
                    time_diff = (point.TIME - prev_time).total_seconds()
                    
                    # Check for time gaps (missing seconds)
                    if time_diff > 1.5:  # Gap larger than 1.5 seconds
                        # IMPORTANT: Calculate attitude for current point BEFORE gap filling
                        if time_diff > 0:
                            # Calculate heading, pitch, roll for current point
                            derived_values = self.attitude_calculator.calculate_derived_values(
                                point, prev_point, time_diff
                            )
                            track_data.update(derived_values)
                        
                        # Now fill the gap with properly interpolated points
                        gap_points = self._fill_time_gap(prev_point, point, int(time_diff))
                        
                        # Add gap-filling points to track
                        for gap_point in gap_points:
                            # Process gap point
                            gap_track_data = {
                                'Timestamp': gap_point.TIME.timestamp(),
                                'Latitude': gap_point.LAT,
                                'Longitude': gap_point.LONG,
                                'Altitude': gap_point.ALTMSL,
                                'Course': gap_point.HEADING,  # Use interpolated heading
                                'Pitch': gap_point.PITCH,
                                'Bank': gap_point.ROLL,
                                'Speed': 0,  # Will be calculated
                                'VerticalSpeed': 0
                            }
                            
                            # Calculate derived values for gap point
                            gap_time_diff = (gap_point.TIME - prev_time).total_seconds()
                            if gap_time_diff > 0:
                                gap_derived = self.attitude_calculator.calculate_derived_values(
                                    gap_point, prev_point, gap_time_diff
                                )
                                gap_track_data.update(gap_derived)
                                
                                # Override heading with our interpolated value (more accurate)
                                gap_point.HEADING = self._interpolate_heading(
                                    prev_point.HEADING, point.HEADING, 
                                    gap_time_diff / time_diff
                                )
                            
                            # Apply smoothing
                            tail_settings = self.config.get_tail_settings(tail_number)
                            self.attitude_calculator.apply_smoothing(
                                gap_point, prev_point, tail_settings.to_dict()
                            )
                            
                            # Evaluate DREFs
                            dref_sources, _ = self.config.drefsByTail(tail_number)
                            for name in dref_sources:
                                try:
                                    value = dref_sources[name]
                                    meta_vars = vars(flight_meta)
                                    point_vars = vars(gap_point)
                                    gap_point.drefs[name] = eval(value.format(**meta_vars, **point_vars, **gap_track_data))
                                except Exception:
                                    gap_point.drefs[name] = 0
                            
                            # Add gap point to track
                            track_points.append(gap_point)
                            
                            # Update distance
                            if prev_point:
                                dist_miles = calculateDistance(
                                    prev_point.LAT, prev_point.LONG,
                                    gap_point.LAT, gap_point.LONG
                                ) * 0.000621371
                                total_distance += dist_miles
                            
                            # Update previous point
                            prev_point = gap_point
                            prev_time = gap_point.TIME
                    
                    # Now process the current point normally
                    time_diff = (point.TIME - prev_time).total_seconds()
                    if time_diff > 0:
                        # Calculate speed, heading, pitch, roll, etc.
                        derived_values = self.attitude_calculator.calculate_derived_values(
                            point, prev_point, time_diff
                        )
                        
                        if point.HEADING == 0.0:
                            print(f"HEADING=0 after calculation! Line ~{len(track_points)+45}")

                        # Update track data with calculated values
                        track_data.update(derived_values)
                            
                    else:
                        # Very small or zero time difference - use previous values
                        if prev_point:
                            point.HEADING = prev_point.HEADING
                            point.PITCH = prev_point.PITCH
                            point.ROLL = prev_point.ROLL
                
                # Apply smoothing and attitude corrections
                tail_settings = self.config.get_tail_settings(tail_number)
                self.attitude_calculator.apply_smoothing(
                    point, 
                    prev_point, 
                    tail_settings.to_dict()
                )
                
                # Evaluate DREFs for this point
                dref_sources, _ = self.config.drefsByTail(tail_number)
                for name in dref_sources:
                    try:
                        value = dref_sources[name]
                        meta_vars = vars(flight_meta)
                        point_vars = vars(point)
                        point.drefs[name] = eval(value.format(**meta_vars, **point_vars, **track_data))
                    except Exception:
                        # Set to 0 if DREF evaluation fails
                        point.drefs[name] = 0
                
                # Add point to the track
                track_points.append(point)
                
                # Update total distance for the flight
                if prev_point:
                    dist_miles = calculateDistance(
                        prev_point.LAT, prev_point.LONG,
                        point.LAT, point.LONG
                    ) * 0.000621371  # meters to miles
                    total_distance += dist_miles
                
                # Store current point as previous for next iteration
                prev_point = point
                prev_time = point.TIME
        
        return track_points, total_distance


class IgcParser:
    """
    Main parser class for IGC files. Orchestrates the parsing process
    using specialized components.
    """
    
    def __init__(self, config):
        """Initialize with configuration"""
        self.config = config
        self.file_detector = IgcFileDetector()
        self.header_parser = IgcHeaderParser()
        self.track_builder = TrackBuilder(config)
        
    def parse_file(self, track_file: TextIO) -> FdrFlight:
        """
        Parse an IGC file into an FdrFlight object.
        Main entry point for IGC parsing.
        """
        flight_meta = FlightMeta()
        fdr_flight = FdrFlight()
        
        # Set default timezone for IGC (typically UTC)
        fdr_flight.timezone = (
            self.config.timezoneIGC 
            if self.config.timezoneIGC is not None 
            else self.config.timezone
        )
        
        # Variables to store flight date and lines
        flight_date = None
        lines = track_file.readlines()
        
        # Get prefix stripping list from config if available
        self.header_parser.prefixes_to_strip = self.config.get_strip_prefixes("DEFAULT") or DEFAULT_STRIP_PREFIXES
        
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
                flight_meta, flight_date = self.header_parser.parse_header_line(
                    line, flight_meta, flight_date
                )
                
            # If we found a B record, stop processing headers
            if record_type == IGC_RECORD_POSITION:
                break
                
        # Update flight metadata
        fdr_flight.TAIL = flight_meta.TailNumber or DEFAULT_UNKNOWN_TEXT
        if flight_date:
            fdr_flight.DATE = flight_date
            
        # Initialize IGC-specific metadata
        flight_meta.InitialAttitudeSource = "Estimated from IGC trajectory"
        flight_meta.ImportedFrom = "IGC Flight Logger"
        
        # Second pass: process B records (position fixes) and build track
        track_points, total_distance = self.track_builder.build_track_from_lines(
            lines, flight_meta, flight_date, fdr_flight.timezone
        )
        
        # Add track points to flight
        fdr_flight.track = track_points
        
        # Complete flight metadata if we have track points
        if fdr_flight.track:
            flight_meta.StartTime = fdr_flight.track[0].TIME
            flight_meta.StartLatitude = fdr_flight.track[0].LAT
            flight_meta.StartLongitude = fdr_flight.track[0].LONG

            flight_meta.EndTime = fdr_flight.track[-1].TIME
            flight_meta.EndLatitude = fdr_flight.track[-1].LAT
            flight_meta.EndLongitude = fdr_flight.track[-1].LONG

            flight_meta.TotalDuration = flight_meta.EndTime - flight_meta.StartTime
            flight_meta.TotalDistance = total_distance
            
        # Generate flight summary
        fdr_flight.summary = flightSummary(flight_meta)
        
        return fdr_flight


# Public functions - maintain backward compatibility

def strip_prefixes(text, prefixes):
    """Remove common prefixes from a text string"""
    return IgcHeaderParser.strip_prefixes(text, prefixes)

def getFiletype(file: TextIO) -> FileType:
    """Determine the file type based on content"""
    return IgcFileDetector.detect_filetype(file)

def apply_attitude_smoothing(fdr_point, prev_point, tail_config):
    """Apply smoothing and scaling to attitude values"""
    AttitudeCalculator.apply_smoothing(fdr_point, prev_point, tail_config)

def parseIgcFile(config, track_file: TextIO) -> FdrFlight:
    """
    Parse an IGC file into an FdrFlight object.
    Main entry point for IGC parsing.
    """
    parser = IgcParser(config)
    return parser.parse_file(track_file)