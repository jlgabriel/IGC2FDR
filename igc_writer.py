#!/usr/bin/env python3
"""
FDR file writer module for IGC to FDR converter
"""

from datetime import datetime, timezone
from typing import Dict, List, TextIO

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

def writeOutputFile(config, fdrFile: TextIO, fdrFlight: FdrFlight):
    """Write an FDR file from the flight data"""
    timestamp = datetime.now(timezone.utc).strftime(TIMESTAMP_FORMAT)
    drefSources, drefDefines = config.drefsByTail(fdrFlight.TAIL)

    tzOffset = fdrFlight.timezone
    if tzOffset:
        totalMinutes = abs(int(tzOffset)) // 60
        hours, minutes = divmod(totalMinutes, 60)
        direction = "added to" if tzOffset > 0 else "subtracted from"
        parts = []
        if hours:
            parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
        if minutes:
            parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
        tzComment = " and ".join(parts)
        tzOffsetExplanation = f"All timestamps below this line have had {tzComment} {direction} their original values."
    else:
        tzOffsetExplanation = FDR_COMMENT_TIMEZONE

    fdrFile.writelines([
        FDR_HEADER,
        '\n',
        fdrComment(f'Generated on [{timestamp}]'),
        fdrComment(FDR_COMMENT_INTRO),
        fdrComment(FDR_COMMENT_BASED_ON),
        '\n',
        fdrComment(tzOffsetExplanation),
        '\n',
        fdrComment(fdrFlight.summary),
        '\n\n',
        fdrComment(FDR_COMMENT_FIELDS),
        fdrComment(FDR_COMMENT_ATTITUDE),
        '\n',
        f'{FDR_SECTION_ACFT}, {config.aircraftPathForTail(fdrFlight.TAIL)}\n',
        f'{FDR_SECTION_TAIL}, {fdrFlight.TAIL}\n',
        f'{FDR_SECTION_DATE}, {toMDY(fdrFlight.DATE)}\n',
        '\n\n',
        fdrComment(FDR_COMMENT_DREFS),
        fdrComment(FDR_COMMENT_DREFS_TRACK),
        '\n',
        fdrDrefs(drefDefines),
        '\n\n',
        fdrComment(FDR_COMMENT_TRACK),
        '\n',
        fdrColNames(drefSources.keys()),
    ])

    for point in fdrFlight.track:
        time    = point.TIME.strftime(TIME_FORMAT_HMS_MS)
        long    = str.rjust(str(point.LONG), FDR_COLUMN_WIDTH)
        lat     = str.rjust(str(point.LAT), FDR_COLUMN_WIDTH)
        altMSL  = str.rjust(str(point.ALTMSL), FDR_COLUMN_WIDTH)
        heading = str.rjust(str(point.HEADING), FDR_COLUMN_WIDTH)
        pitch   = str.rjust(str(point.PITCH), FDR_COLUMN_WIDTH)
        roll    = str.rjust(str(point.ROLL), FDR_COLUMN_WIDTH)
        fdrFile.write(f'{time}, {long}, {lat}, {altMSL}, {heading}, {pitch}, {roll}')

        drefValues = []
        for dref in drefSources:
            drefValues.append(str.rjust(str(point.drefs[dref]), FDR_COLUMN_WIDTH))
        fdrFile.write(', '+ ', '.join(drefValues) +'\n')


def fdrComment(comment: str) -> str:
    """Format a comment for an FDR file"""
    return f'{FDR_SECTION_COMM}, '+ f'\n{FDR_SECTION_COMM}, '.join(comment.splitlines()) +'\n'


def fdrDrefs(drefDefines: List[str]) -> str:
    """Format DREF definitions for an FDR file"""
    if not drefDefines:
        return ""
    return f'{FDR_SECTION_DREF}, ' + f'\n{FDR_SECTION_DREF}, '.join(drefDefines) +'\n'


def fdrColNames(drefNames: Dict[str, str]) -> str:
    """Format column names for an FDR file"""
    names = FDR_COLUMN_HEADERS

    for drefName in drefNames:
        names += ', '+ str.rjust(drefName, FDR_COLUMN_WIDTH)

    return names +'\n'
