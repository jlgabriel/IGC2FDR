#!/usr/bin/env python3
"""
FDR file writer module for IGC to FDR converter

This module handles writing flight data to X-Plane FDR format
with proper formatting of headers, comments, and track data.
"""

from datetime import datetime, timezone
from typing import Dict, List, TextIO, Set, Any

from igc_model import FdrFlight
from igc_utils import toMDY
from igc_constants import (
    FDR_COLUMN_WIDTH,
    FDR_HEADER,
    FDR_FOOTER,
    FDR_SECTION_ACFT,
    FDR_SECTION_TAIL,
    FDR_SECTION_DATE,
    FDR_SECTION_DREF,
    FDR_SECTION_COMM,
    FDR_COMMENT_INTRO,
    FDR_COMMENT_BASED_ON,
    FDR_COMMENT_TIMEZONE,
    FDR_COMMENT_FIELDS,
    FDR_COMMENT_ATTITUDE,
    FDR_COMMENT_DREFS,
    FDR_COMMENT_DREFS_TRACK,
    FDR_COMMENT_TRACK,
    FDR_COLUMN_HEADERS,
    TIMESTAMP_FORMAT,
    TIME_FORMAT_HMS_MS
)


class FdrWriter:
    """
    Handles writing FDR format files for X-Plane.
    Formats track data with proper headers, comments, and data records.
    """
    
    def __init__(self, config):
        """Initialize with configuration"""
        self.config = config
    
    @staticmethod
    def format_comment(comment: str) -> str:
        """Format a comment for an FDR file"""
        return f'{FDR_SECTION_COMM}, '+ f'\n{FDR_SECTION_COMM}, '.join(comment.splitlines()) +'\n'
    
    @staticmethod
    def format_drefs(dref_defines: List[str]) -> str:
        """Format DREF definitions for an FDR file"""
        if not dref_defines:
            return ""
        return f'{FDR_SECTION_DREF}, ' + f'\n{FDR_SECTION_DREF}, '.join(dref_defines) +'\n'
    
    @staticmethod
    def format_column_names(dref_names: Set[str]) -> str:
        """Format column names for an FDR file"""
        names = FDR_COLUMN_HEADERS

        for dref_name in dref_names:
            names += ', '+ str.rjust(dref_name, FDR_COLUMN_WIDTH)

        return names +'\n'
    
    def get_timezone_explanation(self, tz_offset: int) -> str:
        """Generate timezone offset explanation text"""
        if not tz_offset:
            return FDR_COMMENT_TIMEZONE
            
        total_minutes = abs(int(tz_offset)) // 60
        hours, minutes = divmod(total_minutes, 60)
        direction = "added to" if tz_offset > 0 else "subtracted from"
        
        parts = []
        if hours:
            parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
        if minutes:
            parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
            
        tz_comment = " and ".join(parts)
        return f"All timestamps below this line have had {tz_comment} {direction} their original values."
    
    def write_header(self, fdr_file: TextIO, fdr_flight: FdrFlight, dref_sources: Dict[str, Any], dref_defines: List[str]) -> None:
        """Write the FDR file header section"""
        # Generate timestamp
        timestamp = datetime.now(timezone.utc).strftime(TIMESTAMP_FORMAT)
        
        # Get timezone explanation
        tz_explanation = self.get_timezone_explanation(fdr_flight.timezone)
        
        # Write header sections
        fdr_file.writelines([
            FDR_HEADER,
            '\n',
            self.format_comment(f'Generated on [{timestamp}]'),
            self.format_comment(FDR_COMMENT_INTRO),
            self.format_comment(FDR_COMMENT_BASED_ON),
            '\n',
            self.format_comment(tz_explanation),
            '\n',
            self.format_comment(fdr_flight.summary),
            '\n\n',
            self.format_comment(FDR_COMMENT_FIELDS),
            self.format_comment(FDR_COMMENT_ATTITUDE),
            '\n',
            f'{FDR_SECTION_ACFT}, {self.config.aircraftPathForTail(fdr_flight.TAIL)}\n',
            f'{FDR_SECTION_TAIL}, {fdr_flight.TAIL}\n',
            f'{FDR_SECTION_DATE}, {toMDY(fdr_flight.DATE)}\n',
            '\n\n',
            self.format_comment(FDR_COMMENT_DREFS),
            self.format_comment(FDR_COMMENT_DREFS_TRACK),
            '\n',
            self.format_drefs(dref_defines),
            '\n\n',
            self.format_comment(FDR_COMMENT_TRACK),
            '\n',
            self.format_column_names(dref_sources.keys()),
        ])
    
    def write_track_points(self, fdr_file: TextIO, track_points: List, dref_sources: Dict[str, Any]) -> None:
        """Write all track points to the FDR file"""
        for point in track_points:
            # Format standard data fields
            time = point.TIME.strftime(TIME_FORMAT_HMS_MS)  # Ensure this format is correct
            long = str.rjust(str(point.LONG), FDR_COLUMN_WIDTH)
            lat = str.rjust(str(point.LAT), FDR_COLUMN_WIDTH)
            alt_msl = str.rjust(str(point.ALTMSL), FDR_COLUMN_WIDTH)
            heading = str.rjust(str(point.HEADING), FDR_COLUMN_WIDTH)
            pitch = str.rjust(str(point.PITCH), FDR_COLUMN_WIDTH)
            roll = str.rjust(str(point.ROLL), FDR_COLUMN_WIDTH)
            
            # Write standard fields
            fdr_file.write(f'{time}, {long}, {lat}, {alt_msl}, {heading}, {pitch}, {roll}')

            # Format and write DREF values
            dref_values = []
            for dref in dref_sources:
                dref_values.append(str.rjust(str(point.drefs[dref]), FDR_COLUMN_WIDTH))
            
            if dref_values:
                fdr_file.write(', '+ ', '.join(dref_values))
                
            fdr_file.write('\n')
    
    def write_file(self, fdr_file: TextIO, fdr_flight: FdrFlight) -> None:
        """Write a complete FDR file from flight data"""
        # Get DREFs for this tail number
        dref_sources, dref_defines = self.config.drefsByTail(fdr_flight.TAIL)
        
        # Write header sections
        self.write_header(fdr_file, fdr_flight, dref_sources, dref_defines)
        
        # Write track points
        self.write_track_points(fdr_file, fdr_flight.track, dref_sources)
        
        # Write footer if needed
        if FDR_FOOTER:
            fdr_file.write(FDR_FOOTER)


# Public function - maintain backward compatibility
def writeOutputFile(config, fdr_file: TextIO, fdr_flight: FdrFlight) -> None:
    """Write an FDR file from the flight data"""
    writer = FdrWriter(config)
    writer.write_file(fdr_file, fdr_flight)
