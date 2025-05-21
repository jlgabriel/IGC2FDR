# IGC to FDR Converter

**A Python script to convert IGC flight logs to X-Plane compatible FDR files for glider flights.**

This tool allows glider pilots to replay their real-world or simulated flights in X-Plane. It converts IGC files (the standard flight recording format for gliders) to FDR files (X-Plane's flight data recorder format).

Based on [42fdr](https://github.com/MadReasonable/42fdr) by MadReasonable, which handles ForeFlight CSV and KML files.

## Features

- Processes IGC files from any source (flight recorders, Condor, XCSoar, SeeYou, etc.)
- Estimates attitude (pitch and roll) based on flight trajectory and physics
- Configurable aircraft selection based on tail number
- Customizable DREFs for X-Plane instrument panel support
- Timezone adjustment for correct replay timing
- Smoothing for realistic flight dynamics
- Detailed flight summary with metadata

## Installation

1. Clone or download this repository
2. Ensure you have Python 3.6 or newer installed
3. No additional dependencies required - uses only standard library modules

## Usage

```bash
python igc2fdr.py [-c config] [-a aircraft] [-t timezone] [-o outputFolder] file.igc [file2.igc ...]
```

### Options

| Option | Description |
|--------|-------------|
| `-c`   | Specify a config file (defaults to igc2fdr.conf in the current directory) |
| `-a`   | Choose an X-Plane aircraft (overrides the one in the config file) |
| `-t`   | Adjust timezone (IGC files are typically in UTC) |
| `-o`   | Set output folder for the generated FDR files |

## Config File

The config file allows you to:

- Set default aircraft and timezone settings
- Define DREFs for X-Plane instrument panel support
- Map tail numbers to specific X-Plane aircraft
- Apply calibration to heading, pitch, and roll
- Adjust smoothing factors for more realistic flight dynamics

Example config file structure:

```ini
[Defaults]
Aircraft = Aircraft/Laminar Research/Schleicher ASK 21/ASK21.acf
Timezone = 0
OutPath = .
RollFactor = 0.6
PitchFactor = 0.8

DREF sim/cockpit2/gauges/indicators/airspeed_kts_pilot = round({Speed}, 4), 1.0, IAS
# More DREFs...

[Aircraft/Laminar Research/Schleicher ASK 21/ASK21.acf]
Tails = D-XXXX, EC-XXX, N1234, CC-JUGA
StripPrefixes = GLIDERID:, PILOT:, GLIDERTYPE:

# Aircraft-specific DREFs...

[CC-JUGA]
headingTrim = 0.5
pitchTrim = -0.2
rollTrim = 0.0
```

## How It Works

IGC files contain GPS position and altitude data but lack attitude information (pitch, roll). This tool:

1. Parses the IGC file to extract the flight track and metadata
2. Calculates heading from position changes
3. Estimates pitch from altitude changes and ground speed
4. Estimates roll from heading change rate (turn rate)
5. Applies smoothing for more realistic flight dynamics
6. Applies any configured calibration values
7. Generates an FDR file with properly formatted header and track data

## Using in X-Plane

1. Generate the FDR file using this tool
2. Copy the .fdr file to your X-Plane's `Output/FDR` folder
3. In X-Plane, select "Replay a Flight" from the File menu
4. Choose your FDR file from the list

## Limitations

- Attitude estimation is approximate and based on trajectory, not actual measurements
- Very small or rapid changes in heading may not be accurately captured
- Very slow ground speeds can result in exaggerated attitude estimates
- X-Plane may adjust flight times to fit its internal scheduling

## Project Structure

- `igc2fdr.py` - Main script
- `igc_model.py` - Data model definitions
- `igc_config.py` - Configuration handling
- `igc_parser.py` - IGC file parsing
- `igc_summary.py` - Flight summary generation
- `igc_utils.py` - Utility functions
- `igc_writer.py` - FDR file generation
- `igc2fdr.conf` - Example configuration file

## Acknowledgments

- Based on [42fdr](https://github.com/MadReasonable/42fdr) by MadReasonable
- IGC file format specifications from the [FAI/IGC](https://www.fai.org/igc-documents)
- FDR format based on X-Plane documentation and examples
- Code assistance provided by Anthropic Claude 3.7 Sonnet

## Contributing

Contributions are welcome! Areas for improvement include:
- Enhanced attitude estimation algorithms
- Support for additional glider-specific instruments
- Interpolation for smoother replay of flights with sparse data points
- GUI for easier configuration and file selection

## License

This project is licensed under the [Licencia MIT](LICENSE) - see the LICENSE file for details.
