"""
Pytest configuration and shared fixtures for IGC2FDR tests
"""
import pytest
import tempfile
import os
from datetime import datetime, date
from pathlib import Path


@pytest.fixture
def sample_igc_content():
    """Sample IGC file content for testing"""
    return """AXCS001
HFDTE090525
HFPLTPILOT:Juan Gabriel
HFGTYGLIDERTYPE:JS3-15
HFGIDGLIDERID:CC-JUGA
HFSITEFREEFLY:Test Site
B1214288099883N00805990EA0090200902
B1214298099883N00805990EA0090200902
B1214308099900N00806000EA0090500905
B1214318099917N00806017EA0091000910
B1214328099933N00806033EA0091500915
"""


@pytest.fixture
def sample_igc_file(tmp_path, sample_igc_content):
    """Create a temporary IGC file for testing"""
    igc_file = tmp_path / "test_flight.igc"
    igc_file.write_text(sample_igc_content)
    return igc_file


@pytest.fixture
def sample_config_content():
    """Sample configuration file content"""
    return """[Defaults]
Aircraft = Aircraft/Laminar Research/Schleicher ASK 21/ASK21.acf
Timezone = 0
OutPath = .
RollFactor = 0.6
PitchFactor = 0.8

DREF sim/cockpit2/gauges/indicators/airspeed_kts_pilot = round({Speed}, 4), 1.0, IAS
DREF sim/cockpit2/gauges/indicators/altitude_ft_pilot = round({ALTMSL}, 4), 1.0, Altimeter

[Aircraft/Laminar Research/Schleicher ASK 21/ASK21.acf]
Tails = TEST-TAIL, CC-JUGA
StripPrefixes = GLIDERID:, PILOT:, GLIDERTYPE:

[TEST-TAIL]
headingTrim = 1.5
pitchTrim = 0.5
rollTrim = -0.5
"""


@pytest.fixture
def sample_config_file(tmp_path, sample_config_content):
    """Create a temporary config file for testing"""
    config_file = tmp_path / "test_config.conf"
    config_file.write_text(sample_config_content)
    return config_file


@pytest.fixture
def temp_output_dir(tmp_path):
    """Create a temporary output directory"""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return output_dir


@pytest.fixture
def mock_cli_args(sample_config_file, temp_output_dir):
    """Mock command-line arguments for testing"""
    class MockArgs:
        def __init__(self):
            self.config = str(sample_config_file)
            self.aircraft = None
            self.timezone = None
            self.output = str(temp_output_dir)
            self.files = []

    return MockArgs()
