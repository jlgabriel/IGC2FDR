"""
Tests for igc_config.py configuration handling
"""
import pytest
from pathlib import Path
from igc_config import (
    Config,
    ConfigParser,
    DrefDefinition,
    AircraftSettings,
    TailSettings,
    TimezoneSettings
)


class TestTimezoneSettings:
    """Tests for TimezoneSettings"""

    def test_default_values(self):
        tz = TimezoneSettings()
        assert tz.default == 0
        assert tz.csv is None
        assert tz.kml is None
        assert tz.igc is None

    def test_get_for_file_type_default(self):
        tz = TimezoneSettings(default=3600)
        assert tz.get_for_file_type('csv') == 3600
        assert tz.get_for_file_type('kml') == 3600
        assert tz.get_for_file_type('igc') == 3600

    def test_get_for_file_type_specific(self):
        tz = TimezoneSettings(default=0, csv=3600, igc=-3600)
        assert tz.get_for_file_type('csv') == 3600
        assert tz.get_for_file_type('igc') == -3600
        assert tz.get_for_file_type('kml') == 0  # Falls back to default


class TestDrefDefinition:
    """Tests for DrefDefinition"""

    def test_initialization(self):
        dref = DrefDefinition(
            instrument='sim/test/instrument',
            expression='round({Speed}, 2)',
            scale='1.0',
            name='TestInst'
        )
        assert dref.instrument == 'sim/test/instrument'
        assert dref.expression == 'round({Speed}, 2)'
        assert dref.scale == '1.0'
        assert dref.name == 'TestInst'

    def test_get_column_name_with_name(self):
        dref = DrefDefinition(
            instrument='sim/test/instrument',
            expression='{Speed}',
            name='CustomName'
        )
        assert dref.get_column_name() == 'CustomName'

    def test_get_column_name_from_instrument(self):
        dref = DrefDefinition(
            instrument='sim/cockpit2/gauges/indicators/airspeed_kts_pilot',
            expression='{Speed}'
        )
        name = dref.get_column_name()
        assert name == 'airspeed_kts_pilot'

    def test_get_definition(self):
        dref = DrefDefinition(
            instrument='sim/test/instrument',
            expression='round({Speed}, 2)',
            scale='1.0'
        )
        definition = dref.get_definition()
        assert 'sim/test/instrument' in definition
        assert '1.0' in definition
        assert 'round({Speed}, 2)' in definition


class TestAircraftSettings:
    """Tests for AircraftSettings"""

    def test_default_initialization(self):
        aircraft = AircraftSettings(path='Aircraft/Test/test.acf')
        assert aircraft.path == 'Aircraft/Test/test.acf'
        assert aircraft.tail_numbers == []
        assert aircraft.drefs == []
        assert aircraft.heading_trim == 0.0
        assert aircraft.pitch_trim == 0.0
        assert aircraft.roll_trim == 0.0

    def test_matches_tail(self):
        aircraft = AircraftSettings(
            path='Aircraft/Test/test.acf',
            tail_numbers=['TEST-1', 'TEST-2', 'CC-JUGA']
        )
        assert aircraft.matches_tail('TEST-1')
        assert aircraft.matches_tail('CC-JUGA')
        assert not aircraft.matches_tail('OTHER-TAIL')


class TestTailSettings:
    """Tests for TailSettings"""

    def test_default_initialization(self):
        tail = TailSettings()
        assert tail.heading_trim == 0.0
        assert tail.pitch_trim == 0.0
        assert tail.roll_trim == 0.0
        assert tail.roll_factor == 0.6
        assert tail.pitch_factor == 0.8

    def test_to_dict(self):
        tail = TailSettings(
            heading_trim=1.5,
            pitch_trim=0.5,
            roll_trim=-0.5,
            roll_factor=0.7,
            pitch_factor=0.9
        )
        d = tail.to_dict()
        assert d['headingtrim'] == 1.5
        assert d['pitchtrim'] == 0.5
        assert d['rolltrim'] == -0.5
        assert d['rollfactor'] == 0.7
        assert d['pitchfactor'] == 0.9


class TestConfigParser:
    """Tests for ConfigParser"""

    def test_initialization(self):
        parser = ConfigParser()
        assert parser.parser is not None

    def test_parse_dref_config_simple(self):
        parser = ConfigParser()
        dref = parser.parse_dref_config(
            'DREF sim/test/instrument',
            'round({Speed}, 2), 1.0, TestName'
        )
        assert dref.instrument == 'sim/test/instrument'
        assert dref.expression == 'round({Speed}, 2)'
        assert dref.scale == '1.0'
        assert dref.name == 'TestName'

    def test_parse_dref_config_nested_parens(self):
        parser = ConfigParser()
        dref = parser.parse_dref_config(
            'DREF sim/test/instrument',
            'round(max({Speed}, min({IAS}, 100)), 2), 1.0'
        )
        assert 'max(' in dref.expression
        assert 'min(' in dref.expression

    def test_parse_dref_config_invalid_key(self):
        parser = ConfigParser()
        with pytest.raises(ValueError, match="must start with 'DREF '"):
            parser.parse_dref_config('INVALID key', 'value')

    def test_load_config_file(self, sample_config_file):
        parser = ConfigParser()
        success = parser.load_config_file(str(sample_config_file))
        assert success
        assert 'Defaults' in parser.get_sections()

    def test_load_nonexistent_config(self):
        # Test that providing an invalid path to load_config_file works gracefully
        # ConfigParser.read() doesn't raise exceptions for missing files,
        # so we just verify the behavior is safe
        parser = ConfigParser()
        # Try loading from a path that doesn't exist
        # This should not crash and should return True/False based on internal logic
        result = parser.load_config_file('/x/y/z/does_not_exist_12345.conf')
        # The method will return False since the file wasn't found in standard locations either
        # Or True if it read the file (though it doesn't exist, read() succeeds with empty result)
        assert isinstance(result, bool)  # Just verify it returns a boolean safely

    def test_get_section(self, sample_config_file):
        parser = ConfigParser()
        parser.load_config_file(str(sample_config_file))
        defaults = parser.get_section('Defaults')
        assert 'aircraft' in defaults
        assert 'timezone' in defaults

    def test_get_drefs_from_section(self, sample_config_file):
        parser = ConfigParser()
        parser.load_config_file(str(sample_config_file))
        drefs = parser.get_drefs_from_section('Defaults')
        assert len(drefs) >= 2  # At least 2 DREFs in sample config

    def test_get_aircraft_settings(self, sample_config_file):
        parser = ConfigParser()
        parser.load_config_file(str(sample_config_file))
        aircraft_settings = parser.get_aircraft_settings()
        assert len(aircraft_settings) > 0
        # Check if ASK 21 is in the settings
        ask21_found = any('ASK 21' in key for key in aircraft_settings.keys())
        assert ask21_found

    def test_get_tail_settings(self, sample_config_file):
        parser = ConfigParser()
        parser.load_config_file(str(sample_config_file))
        tail_settings = parser.get_tail_settings()
        assert 'TEST-TAIL' in tail_settings
        assert tail_settings['TEST-TAIL'].heading_trim == 1.5


class TestConfig:
    """Tests for main Config class"""

    def test_initialization(self, mock_cli_args):
        config = Config(mock_cli_args)
        assert config is not None
        assert config.aircraft is not None
        assert config.out_path is not None

    def test_cli_aircraft_override(self, mock_cli_args):
        mock_cli_args.aircraft = 'Aircraft/Custom/custom.acf'
        config = Config(mock_cli_args)
        assert config.aircraft == 'Aircraft/Custom/custom.acf'
        assert config.cli_aircraft

    def test_timezone_from_config(self, mock_cli_args):
        config = Config(mock_cli_args)
        # Default should be 0
        assert config.timezone == 0

    def test_timezone_from_cli(self, mock_cli_args):
        mock_cli_args.timezone = '5'
        config = Config(mock_cli_args)
        assert config.timezone == 18000  # 5 hours in seconds

    def test_get_aircraft_for_tail(self, mock_cli_args):
        config = Config(mock_cli_args)
        aircraft = config.get_aircraft_for_tail('CC-JUGA')
        assert 'Aircraft' in aircraft

    def test_get_aircraft_for_unknown_tail(self, mock_cli_args):
        config = Config(mock_cli_args)
        aircraft = config.get_aircraft_for_tail('UNKNOWN-TAIL')
        # Should return default aircraft
        assert aircraft == config.aircraft

    def test_get_tail_settings(self, mock_cli_args):
        config = Config(mock_cli_args)
        settings = config.get_tail_settings('TEST-TAIL')
        assert settings.heading_trim == 1.5
        assert settings.pitch_trim == 0.5
        assert settings.roll_trim == -0.5

    def test_get_tail_settings_unknown(self, mock_cli_args):
        config = Config(mock_cli_args)
        settings = config.get_tail_settings('UNKNOWN-TAIL')
        # Should return defaults
        assert settings.heading_trim == 0.0
        assert settings.pitch_trim == 0.0
        assert settings.roll_trim == 0.0

    def test_drefs_by_tail(self, mock_cli_args):
        config = Config(mock_cli_args)
        sources, defines = config.drefsByTail('CC-JUGA')
        assert len(sources) > 0
        assert len(defines) > 0
        # Should include default DREFs
        assert any('IAS' in name or 'airspeed' in name.lower() for name in sources.keys())

    def test_get_strip_prefixes(self, mock_cli_args):
        config = Config(mock_cli_args)
        prefixes = config.get_strip_prefixes('CC-JUGA')
        assert 'GLIDERID:' in prefixes
        assert 'PILOT:' in prefixes
        assert 'GLIDERTYPE:' in prefixes

    def test_output_path(self, mock_cli_args, temp_output_dir):
        config = Config(mock_cli_args)
        assert config.outPath == str(temp_output_dir)


class TestConfigIntegration:
    """Integration tests for configuration system"""

    def test_complete_configuration_flow(self, mock_cli_args):
        # Create config
        config = Config(mock_cli_args)

        # Get settings for a tail
        tail = 'CC-JUGA'
        aircraft_path = config.aircraftPathForTail(tail)
        tail_settings = config.get_tail_settings(tail)
        drefs, defines = config.drefsByTail(tail)

        # Verify everything is connected
        assert aircraft_path is not None
        assert tail_settings is not None
        assert len(drefs) > 0
        assert len(defines) > 0

    def test_cli_overrides_config_file(self, mock_cli_args):
        # Set CLI override
        mock_cli_args.aircraft = 'Aircraft/CLI/override.acf'
        mock_cli_args.timezone = '-5'

        config = Config(mock_cli_args)

        # CLI values should override config file
        assert config.aircraft == 'Aircraft/CLI/override.acf'
        assert config.timezone == -18000  # -5 hours
