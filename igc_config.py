#!/usr/bin/env python3
"""
Configuration handling for IGC to FDR converter

This module provides configuration management for the IGC to FDR converter.
It handles command line arguments, config file loading, and aircraft-specific settings.
"""

import configparser
import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union, Any, cast

from igc_utils import secondsFromString, numberOrString
from igc_constants import (
    DEFAULT_TIMEZONE,
    DEFAULT_OUT_PATH,
    DEFAULT_AIRCRAFT,
    DEFAULT_HEADING_TRIM,
    DEFAULT_PITCH_TRIM,
    DEFAULT_ROLL_TRIM,
    FDR_COLUMN_WIDTH,
    CONFIG_SECTION_DEFAULTS,
    DEFAULT_DREF_GROUND_SPEED
)

# Configure logger
logger = logging.getLogger(__name__)


@dataclass
class TimezoneSettings:
    """Timezone settings for different file types"""
    default: int = DEFAULT_TIMEZONE
    csv: Optional[int] = None
    kml: Optional[int] = None
    igc: Optional[int] = None
    
    def get_for_file_type(self, file_type: str) -> int:
        """Get timezone offset for a specific file type"""
        if file_type.lower() == 'csv' and self.csv is not None:
            return self.csv
        elif file_type.lower() == 'kml' and self.kml is not None:
            return self.kml
        elif file_type.lower() == 'igc' and self.igc is not None:
            return self.igc
        return self.default


@dataclass
class DrefDefinition:
    """DataRef definition for X-Plane"""
    instrument: str
    expression: str
    scale: str = "1.0"
    name: Optional[str] = None
    
    def get_column_name(self) -> str:
        """Get the column name for this DREF"""
        if self.name:
            return self.name
        # Extract name from instrument path
        parts = self.instrument.split('/')
        name = parts[-1] if parts else self.instrument
        # Truncate to fit column width if needed
        return name[:FDR_COLUMN_WIDTH]
    
    def get_definition(self) -> str:
        """Get the DREF definition string for FDR file"""
        return f'{self.instrument}\t{self.scale}\t\t// source: {self.expression}'


@dataclass
class AircraftSettings:
    """Settings for a specific aircraft"""
    path: str
    tail_numbers: List[str] = field(default_factory=list)
    drefs: List[DrefDefinition] = field(default_factory=list)
    strip_prefixes: List[str] = field(default_factory=list)
    heading_trim: float = DEFAULT_HEADING_TRIM
    pitch_trim: float = DEFAULT_PITCH_TRIM
    roll_trim: float = DEFAULT_ROLL_TRIM
    roll_factor: float = 0.6
    pitch_factor: float = 0.8
    
    def matches_tail(self, tail: str) -> bool:
        """Check if this aircraft matches the given tail number"""
        return tail in self.tail_numbers


@dataclass
class TailSettings:
    """Settings specific to a tail number"""
    heading_trim: float = DEFAULT_HEADING_TRIM
    pitch_trim: float = DEFAULT_PITCH_TRIM
    roll_trim: float = DEFAULT_ROLL_TRIM
    roll_factor: float = 0.6
    pitch_factor: float = 0.8
    drefs: List[DrefDefinition] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for compatibility with existing code"""
        return {
            'headingtrim': self.heading_trim,
            'pitchtrim': self.pitch_trim,
            'rolltrim': self.roll_trim,
            'rollfactor': self.roll_factor,
            'pitchfactor': self.pitch_factor,
        }


class ConfigParser:
    """
    Handles parsing of configuration files and command line arguments.
    Separates the parsing logic from the configuration storage.
    """
    
    def __init__(self):
        """Initialize the config parser"""
        self.parser = configparser.RawConfigParser()
        
    def find_config_file(self, cli_path: Optional[str] = None) -> Optional[str]:
        """Find a configuration file to use"""
        if cli_path and os.path.isfile(cli_path):
            logger.info(f"Using configuration file: {cli_path}")
            return cli_path
        
        # Look in standard locations
        paths = ('.', os.path.dirname(os.path.abspath(__file__)))
        files = ('igc2fdr.conf', 'igc2fdr.ini', '42fdr.conf', '42fdr.ini')
        
        for path in paths:
            for file in files:
                full_path = os.path.join(path, file)
                if Path(full_path).is_file():
                    logger.info(f"Found configuration file: {full_path}")
                    return full_path

        logger.warning("No configuration file found, using defaults")
        return None
    
    def load_config_file(self, file_path: Optional[str] = None) -> bool:
        """Load configuration from file"""
        config_file = self.find_config_file(file_path)
        if not config_file:
            return False
            
        try:
            self.parser.read(config_file)
            return True
        except Exception as e:
            logger.error(f"Error reading config file: {e}")
            return False
    
    def get_section(self, section_name: str) -> Dict[str, str]:
        """Get a section from the configuration file"""
        if section_name in self.parser:
            return dict(self.parser[section_name])
        return {}
    
    def get_sections(self) -> List[str]:
        """Get all section names from the configuration file"""
        return self.parser.sections()
    
    def parse_dref_config(self, key: str, val: str) -> DrefDefinition:
        """Parse a DREF configuration line"""
        if not key.lower().startswith('dref '):
            raise ValueError(f"Invalid DREF key (must start with 'DREF '): {key}")

        # Extract instrument name
        instrument = key[5:].strip().replace('\\', '/')

        # Parse expression and options
        expr_end = None
        depth = 0
        for i, char in enumerate(val):
            if char == '(':
                depth += 1
            elif char == ')':
                depth -= 1
                if depth < 0:
                    raise ValueError(f"Unmatched closing parenthesis in DREF expression: {val}")
            elif char == ',' and depth == 0:
                expr_end = i
                break

        if depth != 0:
            raise ValueError(f"Unmatched parenthesis in DREF expression: {val}")

        if expr_end is not None:
            expr = val[:expr_end].strip()
            rest = [x.strip() for x in val[expr_end+1:].split(',', 1)]
            scale = rest[0] if len(rest) > 0 else '1.0'
            name = rest[1] if len(rest) > 1 else None
        else:
            expr = val.strip()
            scale = '1.0'
            name = None

        return DrefDefinition(instrument, expr, scale, name)
    
    def get_drefs_from_section(self, section_name: str) -> List[DrefDefinition]:
        """Extract all DREFs from a configuration section"""
        drefs = []
        
        if section_name not in self.parser:
            return drefs
            
        section = self.parser[section_name]
        for key, val in section.items():
            if key.lower().startswith('dref '):
                try:
                    dref = self.parse_dref_config(key, val)
                    drefs.append(dref)
                except ValueError as e:
                    logger.warning(f"Invalid DREF in section {section_name}: {e}")
                    
        return drefs
    
    def get_aircraft_settings(self) -> Dict[str, AircraftSettings]:
        """Extract aircraft settings from configuration"""
        aircraft_settings = {}
        
        for section_name in self.parser.sections():
            if section_name.lower().replace('\\', '/').startswith('aircraft/'):
                section = self.parser[section_name]
                
                # Create aircraft settings
                aircraft = AircraftSettings(
                    path=section_name.replace('\\', '/'),
                )
                
                # Add tail numbers
                if 'tails' in section:
                    aircraft.tail_numbers = [
                        tail.strip() for tail in section['tails'].split(',')
                        if tail.strip()
                    ]
                
                # Add strip prefixes
                if 'stripprefixes' in section:
                    aircraft.strip_prefixes = [
                        prefix.strip() for prefix in section['stripprefixes'].split(',')
                        if prefix.strip()
                    ]
                
                # Add trim values if present
                if 'headingtrim' in section:
                    aircraft.heading_trim = numberOrString(section['headingtrim'])
                if 'pitchtrim' in section:
                    aircraft.pitch_trim = numberOrString(section['pitchtrim'])
                if 'rolltrim' in section:
                    aircraft.roll_trim = numberOrString(section['rolltrim'])
                if 'rollfactor' in section:
                    aircraft.roll_factor = numberOrString(section['rollfactor'])
                if 'pitchfactor' in section:
                    aircraft.pitch_factor = numberOrString(section['pitchfactor'])
                
                # Add DREFs
                aircraft.drefs = self.get_drefs_from_section(section_name)
                
                # Store by path
                aircraft_settings[section_name] = aircraft
                
        return aircraft_settings
    
    def get_tail_settings(self) -> Dict[str, TailSettings]:
        """Extract tail-specific settings from configuration"""
        tail_settings = {}
        
        for section_name in self.parser.sections():
            # Check if section is a tail number (not an aircraft or defaults)
            if (not section_name.lower().replace('\\', '/').startswith('aircraft/') and 
                section_name != CONFIG_SECTION_DEFAULTS):
                
                section = self.parser[section_name]
                
                # Create tail settings with defaults
                settings = TailSettings()
                
                # Add trim values if present
                if 'headingtrim' in section:
                    settings.heading_trim = numberOrString(section['headingtrim'])
                if 'pitchtrim' in section:
                    settings.pitch_trim = numberOrString(section['pitchtrim'])
                if 'rolltrim' in section:
                    settings.roll_trim = numberOrString(section['rolltrim'])
                if 'rollfactor' in section:
                    settings.roll_factor = numberOrString(section['rollfactor'])
                if 'pitchfactor' in section:
                    settings.pitch_factor = numberOrString(section['pitchfactor'])
                
                # Add DREFs
                settings.drefs = self.get_drefs_from_section(section_name)
                
                # Store by tail number
                tail_settings[section_name] = settings
                
        return tail_settings
    
    def get_default_settings(self) -> Dict[str, Any]:
        """Get default settings from configuration"""
        defaults = {}
        
        if CONFIG_SECTION_DEFAULTS in self.parser:
            section = self.parser[CONFIG_SECTION_DEFAULTS]
            
            # Copy all values from defaults section
            for key, value in section.items():
                defaults[key] = value
                
            # Convert numeric values
            for key in ['headingtrim', 'pitchtrim', 'rolltrim', 'rollfactor', 'pitchfactor']:
                if key in defaults:
                    defaults[key] = numberOrString(defaults[key])
                    
        return defaults


class Config:
    """Main configuration class for IGC to FDR converter"""
    
    def __init__(self, cli_args):
        """Initialize with command line arguments"""
        self.parser = ConfigParser()
        self.cli_args = cli_args
        
        # Initialize defaults
        self.aircraft = DEFAULT_AIRCRAFT
        self.out_path = DEFAULT_OUT_PATH
        self.timezone_settings = TimezoneSettings()
        self.cli_aircraft = False
        
        # Maps for settings
        self.aircraft_settings: Dict[str, AircraftSettings] = {}
        self.tail_settings: Dict[str, TailSettings] = {}
        self.default_drefs: List[DrefDefinition] = []
        
        # Load configuration
        self._load_config()
        
    def _load_config(self):
        """Load and process configuration"""
        # Load config file
        self.parser.load_config_file(self.cli_args.config)
        
        # Get default settings
        defaults = self.parser.get_default_settings()
        
        # Apply CLI arguments (override config file)
        if self.cli_args.aircraft:
            self.aircraft = self.cli_args.aircraft.replace('\\', '/')
            self.cli_aircraft = True
        elif 'aircraft' in defaults:
            self.aircraft = defaults['aircraft'].replace('\\', '/')
        
        # Set timezone
        if self.cli_args.timezone:
            self.timezone_settings.default = secondsFromString(self.cli_args.timezone)
        else:
            if 'timezone' in defaults:
                self.timezone_settings.default = secondsFromString(defaults['timezone'])
            if 'timezonecsv' in defaults:
                self.timezone_settings.csv = secondsFromString(defaults['timezonecsv'])
            if 'timezonekml' in defaults:
                self.timezone_settings.kml = secondsFromString(defaults['timezonekml'])
            if 'timezoneigc' in defaults:
                self.timezone_settings.igc = secondsFromString(defaults['timezoneigc'])
        
        # Set output path
        if self.cli_args.output:
            self.out_path = self.cli_args.output
        elif 'outpath' in defaults:
            self.out_path = defaults['outpath']
        
        # Load aircraft and tail settings
        self.aircraft_settings = self.parser.get_aircraft_settings()
        self.tail_settings = self.parser.get_tail_settings()
        
        # Load default DREFs
        self.default_drefs = self.parser.get_drefs_from_section(CONFIG_SECTION_DEFAULTS)
        
        # Add default ground speed DREF if not overridden
        self._add_default_ground_speed_dref()
    
    def _add_default_ground_speed_dref(self):
        """Add default ground speed DREF if not already present"""
        # Check if we already have a ground speed DREF
        ground_speed_names = {'groundspeed', 'gndspd', 'ground_speed'}
        
        has_ground_speed = False
        for dref in self.default_drefs:
            if dref.get_column_name().lower() in ground_speed_names:
                has_ground_speed = True
                break
                
        if not has_ground_speed:
            # Add default ground speed DREF
            self.default_drefs.append(
                DrefDefinition(
                    DEFAULT_DREF_GROUND_SPEED,
                    'round({Speed}, 4)',
                    '1.0',
                    'GndSpd'
                )
            )
    
    @property
    def timezone(self) -> int:
        """Get default timezone offset in seconds"""
        return self.timezone_settings.default
    
    @property
    def timezoneIGC(self) -> Optional[int]:
        """Get IGC timezone offset in seconds"""
        return self.timezone_settings.igc
    
    @property
    def timezoneCSV(self) -> Optional[int]:
        """Get CSV timezone offset in seconds"""
        return self.timezone_settings.csv
    
    @property
    def timezoneKML(self) -> Optional[int]:
        """Get KML timezone offset in seconds"""
        return self.timezone_settings.kml
    
    @property
    def outPath(self) -> str:
        """Get output path"""
        return self.out_path
    
    def get_aircraft_for_tail(self, tail_number: str) -> str:
        """Get aircraft path for a tail number"""
        if self.cli_aircraft:
            return self.aircraft
            
        # Check if tail matches any aircraft
        for aircraft in self.aircraft_settings.values():
            if aircraft.matches_tail(tail_number):
                return aircraft.path
                
        return self.aircraft
    
    def acftByTail(self, tail_number: str) -> Optional[str]:
        """Get aircraft section name for a tail number (backward compatibility)"""
        if self.cli_aircraft:
            return None
            
        # Check if tail matches any aircraft
        for section_name, aircraft in self.aircraft_settings.items():
            if aircraft.matches_tail(tail_number):
                return section_name
                
        return self.aircraft
    
    def aircraftPathForTail(self, tail_number: str) -> str:
        """Get aircraft path for a tail number (backward compatibility)"""
        section = self.acftByTail(tail_number)
        return section.replace('\\', '/') if section else self.aircraft
    
    def get_strip_prefixes(self, tail_number: str) -> List[str]:
        """Get strip prefixes for a tail number"""
        # Check if we have a matching aircraft with strip prefixes
        aircraft_section = self.acftByTail(tail_number)
        if aircraft_section in self.aircraft_settings:
            prefixes = self.aircraft_settings[aircraft_section].strip_prefixes
            if prefixes:
                return prefixes
                
        return []
    
    def get_tail_settings(self, tail_number: str) -> TailSettings:
        """Get settings for a specific tail number"""
        # First check tail-specific settings
        if tail_number in self.tail_settings:
            return self.tail_settings[tail_number]
            
        # Then check if there's an aircraft for this tail
        aircraft_section = self.acftByTail(tail_number)
        if aircraft_section in self.aircraft_settings:
            aircraft = self.aircraft_settings[aircraft_section]
            return TailSettings(
                heading_trim=aircraft.heading_trim,
                pitch_trim=aircraft.pitch_trim,
                roll_trim=aircraft.roll_trim,
                roll_factor=aircraft.roll_factor,
                pitch_factor=aircraft.pitch_factor,
                drefs=aircraft.drefs
            )
            
        # If nothing found, return defaults
        return TailSettings()
    
    def tail(self, tail_number: str) -> Dict[str, Any]:
        """Get tail settings as dictionary (backward compatibility)"""
        return self.get_tail_settings(tail_number).to_dict()
    
    def drefsByTail(self, tail_number: str) -> Tuple[Dict[str, str], List[str]]:
        """Get DREFs for a tail number (backward compatibility)"""
        sources: Dict[str, str] = {}
        defines: List[str] = []
        
        # Add default DREFs
        for dref in self.default_drefs:
            column_name = dref.get_column_name()
            sources[column_name] = dref.expression
            defines.append(dref.get_definition())
            
        # Add aircraft DREFs
        aircraft_section = self.acftByTail(tail_number)
        if aircraft_section in self.aircraft_settings:
            for dref in self.aircraft_settings[aircraft_section].drefs:
                column_name = dref.get_column_name()
                sources[column_name] = dref.expression
                defines.append(dref.get_definition())
                
        # Add tail-specific DREFs
        if tail_number in self.tail_settings:
            for dref in self.tail_settings[tail_number].drefs:
                column_name = dref.get_column_name()
                sources[column_name] = dref.expression
                defines.append(dref.get_definition())
                
        return sources, defines
