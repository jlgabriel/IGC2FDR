#!/usr/bin/env python3
"""
Configuration handling for IGC to FDR converter
"""

import configparser
import os
import re
from pathlib import Path
from typing import Dict, List, MutableMapping, Tuple, Union

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

class Config:
    aircraft: str = DEFAULT_AIRCRAFT
    outPath: str = DEFAULT_OUT_PATH
    timezone: int = DEFAULT_TIMEZONE
    timezoneCSV: int = None
    timezoneKML: int = None
    timezoneIGC: int = None

    file: MutableMapping = None

    def __init__(self, cliArgs):
        self.file = configparser.RawConfigParser()
        configFile = self.findConfigFile(cliArgs.config)
        if configFile:
            self.file.read(configFile)

        defaults = self.file[CONFIG_SECTION_DEFAULTS] if CONFIG_SECTION_DEFAULTS in self.file else {}

        self.cliAircraft = False
        if cliArgs.aircraft:
            self.aircraft = cliArgs.aircraft.replace('\\', '/')
            self.cliAircraft = True
        elif 'aircraft' in defaults:
            self.aircraft = defaults['aircraft'].replace('\\', '/')

        if cliArgs.timezone:
            self.timezone = secondsFromString(cliArgs.timezone)
        else:
            if 'timezone' in defaults:
                self.timezone = secondsFromString(defaults['timezone'])
            if 'timezonecsv' in defaults:
                self.timezoneCSV = secondsFromString(defaults['timezonecsv'])
            if 'timezonekml' in defaults:
                self.timezoneKML = secondsFromString(defaults['timezonekml'])
            if 'timezoneigc' in defaults:
                self.timezoneIGC = secondsFromString(defaults['timezoneigc'])

        if cliArgs.outputFolder:
            self.outPath = cliArgs.outputFolder
        elif 'outpath' in defaults:
            self.outPath = defaults['outpath']

    def acftByTail(self, tailNumber: str):
        if self.cliAircraft:
            return None  # Aircraft passed on the command-line has priority
        for section in self.file.sections():
            if section.lower().replace('\\', '/').startswith('aircraft/'):
                aircraft = self.file[section]
                if 'tails' in aircraft:  # Check if Tails exists in the section
                    if tailNumber in [tail.strip() for tail in aircraft['Tails'].split(',')]:
                        return section
        return self.aircraft

    def aircraftPathForTail(self, tailNumber: str) -> str:
        section = self.acftByTail(tailNumber)
        return section.replace('\\', '/') if section else self.aircraft

    def drefsByTail(self, tailNumber: str) -> Tuple[Dict[str, str], List[str]]:
        sources: Dict[str, str] = {}
        defines: List[str] = []

        def add(instrument: str, value: str, scale: str = '1.0', name: str = None):
            name = name or instrument.rpartition('/')[2][:FDR_COLUMN_WIDTH]
            sources[name] = value
            defines.append(f'{instrument}\t{scale}\t\t// source: {value}')

        def fromSection(sectionName: str):
            if sectionName and sectionName in self.file:
                for key, val in self.file[sectionName].items():
                    if key.lower().startswith('dref '):
                        instrument, expr, scale, name = parseDrefConfig(key, val)
                        add(instrument, expr, scale, name)

        def parseDrefConfig(key: str, val: str) -> Tuple[str, str, str, Union[str, None]]:
            if not key.lower().startswith('dref '):
                raise ValueError(f"Invalid DREF key (must start with 'DREF '): {key}")

            instrument = key[5:].strip().replace('\\', '/')

            exprEnd = None
            depth = 0
            for i, char in enumerate(val):
                if char == '(':
                    depth += 1
                elif char == ')':
                    depth -= 1
                    if depth < 0:
                        raise ValueError(f"Unmatched closing parenthesis in DREF expression: {val}")
                elif char == ',' and depth == 0:
                    exprEnd = i
                    break

            if depth != 0:
                raise ValueError(f"Unmatched parenthesis in DREF expression: {val}")

            if exprEnd is not None:
                expr = val[:exprEnd].strip()
                rest = [x.strip() for x in val[exprEnd+1:].split(',', 1)]
                scale = rest[0] if len(rest) > 0 else '1.0'
                name = rest[1] if len(rest) > 1 else None
            else:
                expr = val.strip()
                scale = '1.0'
                name = None

            return instrument, expr, scale, name

        # Always include the default ground speed DREF
        add(DEFAULT_DREF_GROUND_SPEED, 'round({Speed}, 4)', '1.0', 'GndSpd')

        fromSection(CONFIG_SECTION_DEFAULTS)
        fromSection(self.acftByTail(tailNumber))
        fromSection(tailNumber)

        return sources, defines

    def tail(self, tailNumber: str):
        tailConfig = {}
        for section in self.file.sections():
            if section.lower() == tailNumber.lower():
                tailSection = self.file[section]
                for key in self.file[section]:
                    tailConfig[key] = numberOrString(tailSection[key])
                break

        if 'headingtrim' not in tailConfig:
            tailConfig['headingtrim'] = DEFAULT_HEADING_TRIM
        if 'pitchtrim' not in tailConfig:
            tailConfig['pitchtrim'] = DEFAULT_PITCH_TRIM
        if 'rolltrim' not in tailConfig:
            tailConfig['rolltrim'] = DEFAULT_ROLL_TRIM

        return tailConfig

    def findConfigFile(self, cliPath: str):
        if cliPath:
            return cliPath
        
        paths = ('.', os.path.dirname(os.path.abspath(__file__)))
        files = ('igc2fdr.conf', 'igc2fdr.ini', '42fdr.conf', '42fdr.ini')
        for path in paths:
            for file in files:
                fullPath = os.path.join(path, file)
                if Path(fullPath).is_file():
                    return fullPath

        return None
