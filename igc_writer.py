#!/usr/bin/env python3
"""
FDR file writer module for IGC to FDR converter
"""

from datetime import datetime, timezone
from typing import Dict, List, TextIO

from igc_model import FdrFlight
from igc_utils import toMDY

# Width for FDR output columns
FdrColumnWidth = 19

def writeOutputFile(config, fdrFile: TextIO, fdrFlight: FdrFlight):
    """Write an FDR file from the flight data"""
    timestamp = datetime.now(timezone.utc).strftime('%Y/%m/%d %H:%M:%SZ')
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
        tzOffsetExplanation = "All timestamps below this line are in the same timezone as the original file."

    fdrFile.writelines([
        'A\n4\n',
        '\n',
        fdrComment(f'Generated on [{timestamp}]'),
        fdrComment(f'This X-Plane compatible FDR file was converted from an IGC track file using igc2fdr.py'),
        fdrComment('Based on 42fdr.py (https://github.com/MadReasonable/42fdr)'),
        '\n',
        fdrComment(tzOffsetExplanation),
        '\n',
        fdrComment(fdrFlight.summary),
        '\n\n',
        fdrComment("Fields below define general data for this flight."),
        fdrComment("Only position data is available from IGC files, attitude (heading/pitch/roll) is estimated."),
        '\n',
        f'ACFT, {config.aircraftPathForTail(fdrFlight.TAIL)}\n',
        f'TAIL, {fdrFlight.TAIL}\n',
        f'DATE, {toMDY(fdrFlight.DATE)}\n',
        '\n\n',
        fdrComment('DREFs below (if any) define additional columns beyond the 7th (Roll)'),
        fdrComment('in the flight track data that follows.'),
        '\n',
        fdrDrefs(drefDefines),
        '\n\n',
        fdrComment('The remainder of this file consists of GPS track points with estimated attitude.'),
        '\n',
        fdrColNames(drefSources.keys()),
    ])

    for point in fdrFlight.track:
        time    = point.TIME.strftime('%H:%M:%S.%f')
        long    = str.rjust(str(point.LONG), FdrColumnWidth)
        lat     = str.rjust(str(point.LAT), FdrColumnWidth)
        altMSL  = str.rjust(str(point.ALTMSL), FdrColumnWidth)
        heading = str.rjust(str(point.HEADING), FdrColumnWidth)
        pitch   = str.rjust(str(point.PITCH), FdrColumnWidth)
        roll    = str.rjust(str(point.ROLL), FdrColumnWidth)
        fdrFile.write(f'{time}, {long}, {lat}, {altMSL}, {heading}, {pitch}, {roll}')

        drefValues = []
        for dref in drefSources:
            drefValues.append(str.rjust(str(point.drefs[dref]), FdrColumnWidth))
        fdrFile.write(', '+ ', '.join(drefValues) +'\n')


def fdrComment(comment: str) -> str:
    """Format a comment for an FDR file"""
    return 'COMM, '+ '\nCOMM, '.join(comment.splitlines()) +'\n'


def fdrDrefs(drefDefines: List[str]) -> str:
    """Format DREF definitions for an FDR file"""
    if not drefDefines:
        return ""
    return 'DREF, ' + '\nDREF, '.join(drefDefines) +'\n'


def fdrColNames(drefNames: Dict[str, str]) -> str:
    """Format column names for an FDR file"""
    names = '''COMM,                        degrees,             degrees,              ft msl,                 deg,                 deg,                 deg
COMM,                      Longitude,            Latitude,              AltMSL,             Heading,               Pitch,                Roll'''

    for drefName in drefNames:
        names += ', '+ str.rjust(drefName, FdrColumnWidth)

    return names +'\n'
