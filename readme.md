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
- Time gap interpolation for smooth playback
- Heading discontinuity fixes for accurate replay

## Quick Start

```bash
# 1. Convert an IGC file
python igc2fdr.py -c igc2fdr.conf my_flight.igc

# 2. Copy the generated FDR file to X-Plane
cp my_flight.fdr /path/to/X-Plane/Output/FDR/

# 3. In X-Plane: File → Replay a Flight → my_flight.fdr
```

**Example output:**
```
2025-11-19 19:06:21 - INFO - Processing JUGA-2025-05-09.igc
2025-11-19 19:06:21 - INFO - Created ./JUGA-2025-05-09.fdr
2025-11-19 19:06:21 - INFO - Processed 1 files: 1 succeeded, 0 failed
```

## Installation

### For Users

1. Clone or download this repository
2. Ensure you have Python 3.6 or newer installed
3. No additional dependencies required - uses only standard library modules

### For Developers

If you plan to contribute or run tests:

```bash
# Clone the repository
git clone https://github.com/jlgabriel/IGC2FDR.git
cd IGC2FDR

# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest
```

## Usage

```bash
python igc2fdr.py [-c config] [-a aircraft] [-t timezone] [-o outputFolder] file.igc [file2.igc ...]
```
Examples:

python igc2fdr.py -c igc2fdr.conf JUGA-2025-05-09.igc

python igc2fdr.py -c igc2fdr.conf JUGA-2025-05-11.igc

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

## Advanced Tools

### FDR Analyzer

The project includes a diagnostic tool to analyze FDR files and detect potential issues:

```bash
python tools/fdr_analyzer.py my_flight.fdr

# Optional: Export issues to CSV
python tools/fdr_analyzer.py my_flight.fdr --export-csv issues.csv

# Adjust detection thresholds
python tools/fdr_analyzer.py my_flight.fdr --heading-threshold 60 --speed-threshold 40
```

This tool detects:
- Heading discontinuities and abrupt changes
- Time gaps in the data
- Speed anomalies (unrealistic or sudden changes)
- Extreme attitude values (pitch/roll)
- Position jumps

## Limitations

- Attitude estimation is approximate and based on trajectory, not actual measurements
- Very small or rapid changes in heading may not be accurately captured
- Very slow ground speeds can result in exaggerated attitude estimates
- X-Plane may adjust flight times to fit its internal scheduling

## Project Structure

### Core Modules
- `igc2fdr.py` - Main script and entry point
- `igc_model.py` - Data model definitions (FdrFlight, FdrTrackPoint, etc.)
- `igc_config.py` - Configuration file parsing and management
- `igc_parser.py` - IGC file parsing with attitude estimation
- `igc_summary.py` - Flight summary generation
- `igc_utils.py` - Utility functions (distance, heading, timezone conversion)
- `igc_writer.py` - FDR file generation and formatting
- `igc_constants.py` - Constants and configuration defaults

### Configuration & Tools
- `igc2fdr.conf` - Example configuration file
- `tools/fdr_analyzer.py` - FDR file analysis tool for detecting discontinuities

### Testing (93.72% coverage)
- `tests/` - Comprehensive test suite with 168 tests
  - `test_igc_utils.py` - Utility function tests
  - `test_igc_model.py` - Data model tests
  - `test_igc_config.py` - Configuration tests
  - `test_igc_parser.py` - IGC parsing tests
  - `test_igc_writer.py` - FDR writing tests
  - `test_igc_summary.py` - Summary generation tests
  - `test_igc2fdr.py` - End-to-end integration tests
- `pytest.ini` - Test configuration
- `requirements-dev.txt` - Development dependencies

## Acknowledgments

- Based on [42fdr](https://github.com/MadReasonable/42fdr) by MadReasonable
- IGC file format specifications from the [FAI/IGC](https://www.fai.org/igc-documents)
- FDR format based on X-Plane documentation and examples
- Code assistance provided by Anthropic Claude 3.7 Sonnet

## Development & Testing

This project has comprehensive test coverage (93.72%) to ensure code quality and reliability.

### Running Tests

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest

# Run tests with coverage report
pytest --cov=. --cov-report=html

# View coverage report
open htmlcov/index.html
```

### Test Coverage by Module

- ✅ `igc_constants.py` - 100%
- ✅ `igc_model.py` - 100%
- ✅ `igc_summary.py` - 100%
- ✅ `igc_writer.py` - 100%
- ✅ `igc_config.py` - 87%
- ✅ `igc2fdr.py` - 84%
- ✅ `igc_parser.py` - 83%
- ⚠️ `igc_utils.py` - 72%

## Contributing

Contributions are welcome! Please follow these guidelines:

1. **Fork the repository** and create a feature branch
2. **Write tests** for any new functionality
3. **Ensure all tests pass** with `pytest`
4. **Maintain code coverage** above 80%
5. **Update documentation** as needed
6. **Submit a pull request** with a clear description

### Areas for Improvement

- Enhanced attitude estimation algorithms
- Support for additional glider-specific instruments
- Improved handling of edge cases in IGC files
- GUI for easier configuration and file selection
- Additional output formats (KML, GPX, etc.)

## Troubleshooting

### Common Issues

**Problem: "No module named 'igc_config'"**
- **Solution**: Make sure you're running the script from the project directory, or add the project directory to your Python path.

**Problem: Generated FDR file has discontinuities or jumps**
- **Solution**: Use the FDR analyzer tool to identify issues:
  ```bash
  python tools/fdr_analyzer.py your_flight.fdr
  ```
- **Tip**: Adjust `RollFactor` and `PitchFactor` in the config file to smooth attitude changes.

**Problem: X-Plane doesn't show the FDR file**
- **Solution**: Ensure the file is in `X-Plane/Output/FDR/` folder
- **Check**: File has `.fdr` extension (lowercase)
- **Verify**: File is not corrupted (should start with `A\n4\n`)

**Problem: Heading shows sudden jumps**
- **Solution**: This was fixed in recent updates. Make sure you're using the latest version with heading interpolation fixes.

**Problem: Flight plays back at wrong time in X-Plane**
- **Solution**: Use the `-t` option to adjust timezone:
  ```bash
  python igc2fdr.py -t "+2" my_flight.igc  # Add 2 hours
  ```

### Getting Help

- Check the [Issues](https://github.com/jlgabriel/IGC2FDR/issues) page for known problems
- Review test examples in `tests/` for usage patterns
- Run tests to verify your installation: `pytest`

## License

This project is licensed under the [MIT License](LICENSE) - see the LICENSE file for details.
