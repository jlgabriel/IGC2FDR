#!/usr/bin/env python3
"""
Constants for IGC to FDR converter
"""
import math

# File types
class FileType:
    UNKNOWN = 0
    CSV = 1
    KML = 2
    GPX = 3
    IGC = 4

# Default configuration values
DEFAULT_TIMEZONE = 0
DEFAULT_OUT_PATH = "."
DEFAULT_ROLL_FACTOR = 0.6
DEFAULT_PITCH_FACTOR = 0.8
DEFAULT_SMOOTHING_FACTOR = 0.3
DEFAULT_AIRCRAFT = "Aircraft/Laminar Research/Schleicher ASK 21/ASK21.acf"
DEFAULT_HEADING_TRIM = 0.0
DEFAULT_PITCH_TRIM = 0.0
DEFAULT_ROLL_TRIM = 0.0
DEFAULT_UNKNOWN_TEXT = "UNKNOWN"
DEFAULT_NA_TEXT = "N/A"
DEFAULT_BAROMETER = 29.92

# FDR file format
FDR_COLUMN_WIDTH = 19
FDR_HEADER = "A\n4\n"
FDR_FOOTER = "\n"

# IGC file constants
IGC_HEADER_PILOT = "FPLT"
IGC_HEADER_GLIDER_TYPE = "FGTY"
IGC_HEADER_GLIDER_ID = "FGID"
IGC_HEADER_GPS = "FDOP"
IGC_HEADER_SITE = "FSIT"
IGC_HEADER_DATE = "FDTE"
IGC_RECORD_POSITION = "B"
IGC_ALTITUDE_MARKER = "A"

# Standard prefixes to strip from IGC headers
DEFAULT_STRIP_PREFIXES = ["GLIDERID:", "PILOT:", "GLIDERTYPE:"]

# Earth radius in meters (for distance calculations)
EARTH_RADIUS_METERS = 6371000

# Date and time formats
DATE_FORMAT_MDY = "%m/%d/%Y"
DATE_FORMAT_YMD = "%Y/%m/%d"
TIME_FORMAT_HM = "%H:%M"
TIME_FORMAT_HMS = "%H:%M:%S"
TIMESTAMP_FORMAT = "%Y/%m/%d %H:%M:%SZ"
TIME_FORMAT_HMS_MS = "%H:%M:%S.%f"

# FDR file sections
FDR_SECTION_ACFT = "ACFT"
FDR_SECTION_TAIL = "TAIL"
FDR_SECTION_DATE = "DATE"
FDR_SECTION_DREF = "DREF"
FDR_SECTION_COMM = "COMM"

# Comments for FDR file
FDR_COMMENT_INTRO = "This X-Plane compatible FDR file was converted from an IGC track file using igc2fdr.py"
FDR_COMMENT_BASED_ON = "Based on 42fdr.py (https://github.com/MadReasonable/42fdr)"
FDR_COMMENT_TIMEZONE = "All timestamps below this line are in the same timezone as the original file."
FDR_COMMENT_FIELDS = "Fields below define general data for this flight."
FDR_COMMENT_ATTITUDE = "Only position data is available from IGC files, attitude (heading/pitch/roll) is estimated."
FDR_COMMENT_DREFS = "DREFs below (if any) define additional columns beyond the 7th (Roll)"
FDR_COMMENT_DREFS_TRACK = "in the flight track data that follows."
FDR_COMMENT_TRACK = "The remainder of this file consists of GPS track points with estimated attitude."

# Column headers for FDR file
FDR_COLUMN_HEADERS = """COMM,                        degrees,             degrees,              ft msl,                 deg,                 deg,                 deg
COMM,                      Longitude,            Latitude,              AltMSL,             Heading,               Pitch,                Roll"""

# Default DREFs
DEFAULT_DREF_GROUND_SPEED = "sim/cockpit2/gauges/indicators/ground_speed_kt"
DEFAULT_DREF_AIRSPEED = "sim/cockpit2/gauges/indicators/airspeed_kts_pilot"
DEFAULT_DREF_ALTITUDE = "sim/cockpit2/gauges/indicators/altitude_ft_pilot"
DEFAULT_DREF_COMPASS = "sim/cockpit2/gauges/indicators/compass_heading_deg_mag"
DEFAULT_DREF_VVI = "sim/cockpit2/gauges/indicators/vvi_fpm_pilot"
DEFAULT_DREF_BAROMETER = "sim/cockpit2/gauges/actuators/barometer_setting_in_hg_pilot"
DEFAULT_DREF_SLIP_BALL = "sim/cockpit2/gauges/indicators/slip_ball_deflection_dots"
DEFAULT_DREF_TURN_RATE = "sim/cockpit2/gauges/indicators/turn_rate_heading_deg_pilot"

# Configuration sections
CONFIG_SECTION_DEFAULTS = "Defaults"

# Math constants
DEGREES_IN_CIRCLE = 360
MAX_ATTITUDE_ANGLE = 180
FEET_PER_METER = 3.28084
KNOTS_PER_MPS = 1.94384
EARTH_GRAVITY = 9.81
RADIANS_PER_DEGREE = math.pi / 180
SECONDS_PER_MINUTE = 60 