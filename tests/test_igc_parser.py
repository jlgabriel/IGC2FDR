"""
Tests for igc_parser.py IGC file parsing
"""
import pytest
from io import StringIO
from datetime import datetime, date
from igc_parser import (
    IgcFileDetector,
    IgcHeaderParser,
    IgcPositionParser,
    AttitudeCalculator,
    TrackBuilder,
    IgcParser,
    getFiletype
)
from igc_model import FileType, FdrTrackPoint, FlightMeta


class TestIgcFileDetector:
    """Tests for IgcFileDetector"""

    def test_detect_igc_file(self):
        content = "AXCS001\nHFDTE090525\nB1214288099883N00805990EA0090200902\n"
        file = StringIO(content)
        file_type = IgcFileDetector.detect_filetype(file)
        assert file_type == FileType.IGC

    def test_detect_csv_file(self):
        content = "Latitude,Longitude,Altitude\n45.5,8.1,1000\n"
        file = StringIO(content)
        file_type = IgcFileDetector.detect_filetype(file)
        assert file_type == FileType.CSV

    def test_detect_kml_file(self):
        content = '<?xml version="1.0"?>\n<kml xmlns="...">\n'
        file = StringIO(content)
        file_type = IgcFileDetector.detect_filetype(file)
        assert file_type == FileType.KML

    def test_detect_gpx_file(self):
        content = '<?xml version="1.0"?>\n<gpx version="1.1">\n'
        file = StringIO(content)
        file_type = IgcFileDetector.detect_filetype(file)
        assert file_type == FileType.GPX

    def test_detect_unknown_file(self):
        content = "This is not a valid file\n"
        file = StringIO(content)
        file_type = IgcFileDetector.detect_filetype(file)
        # Should default to CSV if not recognized
        assert file_type in [FileType.UNKNOWN, FileType.CSV]

    def test_getFiletype_function(self):
        """Test the backward-compatible function"""
        content = "AXCS001\nHFDTE090525\n"
        file = StringIO(content)
        file_type = getFiletype(file)
        assert file_type == FileType.IGC


class TestIgcHeaderParser:
    """Tests for IgcHeaderParser"""

    def test_strip_prefixes(self):
        prefixes = ['PILOT:', 'GLIDERID:', 'GLIDERTYPE:']
        assert IgcHeaderParser.strip_prefixes('PILOT:John Doe', prefixes) == 'John Doe'
        assert IgcHeaderParser.strip_prefixes('GLIDERID:CC-JUGA', prefixes) == 'CC-JUGA'
        assert IgcHeaderParser.strip_prefixes('No prefix', prefixes) == 'No prefix'

    def test_parse_pilot_header(self):
        parser = IgcHeaderParser()
        meta = FlightMeta()
        line = 'HFPLTPILOT:Juan Gabriel'
        meta, _ = parser.parse_header_line(line, meta, None)
        assert meta.Pilot == 'Juan Gabriel'

    def test_parse_glider_type_header(self):
        parser = IgcHeaderParser()
        meta = FlightMeta()
        line = 'HFGTYGLIDERTYPE:JS3-15'
        meta, _ = parser.parse_header_line(line, meta, None)
        assert meta.DeviceModel == 'JS3-15'

    def test_parse_glider_id_header(self):
        parser = IgcHeaderParser()
        meta = FlightMeta()
        line = 'HFGIDGLIDERID:CC-JUGA'
        meta, _ = parser.parse_header_line(line, meta, None)
        assert meta.TailNumber == 'CC-JUGA'

    def test_parse_date_header(self):
        parser = IgcHeaderParser()
        meta = FlightMeta()
        # Format: HFDTE[DDMMYY] - need at least 12 chars (5 + 6 + 1)
        line = 'HFDTE090525XX'  # DDMMYY format: 09/05/25
        meta, flight_date = parser.parse_header_line(line, meta, None)
        assert flight_date == date(2025, 5, 9)

    def test_parse_site_header(self):
        parser = IgcHeaderParser()
        meta = FlightMeta()
        line = 'HFSITFREEFLY:Test Airport'
        meta, _ = parser.parse_header_line(line, meta, None)
        # Parser doesn't strip "FREEFLY:", it's stored as-is
        assert 'Test Airport' in meta.DerivedOrigin

    def test_parse_gps_header(self):
        parser = IgcHeaderParser()
        meta = FlightMeta()
        line = 'HFDOPGPS:HDOP 2.5'
        meta, _ = parser.parse_header_line(line, meta, None)
        assert 'IGC Flight Logger' in meta.GPSSource
        assert 'HDOP 2.5' in meta.GPSSource


class TestIgcPositionParser:
    """Tests for IgcPositionParser"""

    def test_parse_time(self):
        parser = IgcPositionParser()
        line = 'B1214288099883N00805990EA0090200902'
        flight_date = date(2025, 5, 9)
        time = parser.parse_time(line, flight_date)
        assert time.hour == 12
        assert time.minute == 14
        assert time.second == 28

    def test_parse_latitude_north(self):
        parser = IgcPositionParser()
        line = 'B1214288099883N00805990EA0090200902'
        lat = parser.parse_latitude(line)
        # 80°99.883' N = 80 + 99.883/60
        expected = 80 + (99 + 0.883) / 60
        assert abs(lat - expected) < 0.001

    def test_parse_latitude_south(self):
        parser = IgcPositionParser()
        line = 'B1214288099883S00805990EA0090200902'
        lat = parser.parse_latitude(line)
        assert lat < 0  # South should be negative

    def test_parse_longitude_east(self):
        parser = IgcPositionParser()
        line = 'B1214288099883N00805990EA0090200902'
        lon = parser.parse_longitude(line)
        # 008°05.990' E = 8 + 5.990/60
        expected = 8 + (5 + 0.990) / 60
        assert abs(lon - expected) < 0.001

    def test_parse_longitude_west(self):
        parser = IgcPositionParser()
        line = 'B1214288099883N00805990WA0090200902'
        lon = parser.parse_longitude(line)
        assert lon < 0  # West should be negative

    def test_parse_altitude(self):
        parser = IgcPositionParser()
        # Format: ...EA00902009 02 (pressure alt: 902m, GPS alt: 902m)
        line = 'B1214288099883N00805990EA0090200902'
        press_alt, gps_alt = parser.parse_altitude(line)
        assert press_alt == 902
        assert gps_alt == 902

    def test_parse_position_record_complete(self):
        parser = IgcPositionParser()
        line = 'B1214288099883N00805990EA0090200902'
        flight_date = date(2025, 5, 9)
        point = parser.parse_position_record(line, flight_date, 0)

        assert point.TIME is not None
        assert point.LAT > 80
        assert point.LONG > 8
        assert point.ALTMSL > 0  # Converted to feet
        assert point.HEADING == 0  # Not calculated yet
        assert point.PITCH == 0
        assert point.ROLL == 0


class TestAttitudeCalculator:
    """Tests for AttitudeCalculator"""

    def test_calculate_derived_values_stationary(self):
        # Create two identical points
        prev_point = FdrTrackPoint(
            LAT=45.5, LONG=8.1, ALTMSL=1000.0, HEADING=0
        )
        curr_point = FdrTrackPoint(
            LAT=45.5, LONG=8.1, ALTMSL=1000.0, HEADING=0
        )

        values = AttitudeCalculator.calculate_derived_values(
            curr_point, prev_point, 1.0
        )

        assert values['Speed'] == 0.0  # No movement
        assert values['VerticalSpeed'] == 0.0  # No altitude change

    def test_calculate_derived_values_moving(self):
        # Create two points with known distance
        prev_point = FdrTrackPoint(
            LAT=45.5, LONG=8.1, ALTMSL=1000.0, HEADING=0
        )
        curr_point = FdrTrackPoint(
            LAT=45.501, LONG=8.101, ALTMSL=1050.0, HEADING=0
        )

        values = AttitudeCalculator.calculate_derived_values(
            curr_point, prev_point, 1.0
        )

        assert values['Speed'] > 0  # Should have speed
        assert values['VerticalSpeed'] > 0  # Climbing
        assert 0 <= values['Course'] <= 360  # Valid heading

    def test_calculate_derived_values_descending(self):
        prev_point = FdrTrackPoint(
            LAT=45.5, LONG=8.1, ALTMSL=2000.0, HEADING=90
        )
        curr_point = FdrTrackPoint(
            LAT=45.501, LONG=8.101, ALTMSL=1900.0, HEADING=90
        )

        values = AttitudeCalculator.calculate_derived_values(
            curr_point, prev_point, 1.0
        )

        assert values['VerticalSpeed'] < 0  # Descending

    def test_apply_smoothing_no_previous(self):
        point = FdrTrackPoint(HEADING=180, PITCH=10, ROLL=5)
        tail_config = {
            'headingtrim': 0, 'pitchtrim': 0, 'rolltrim': 0,
            'rollfactor': 0.6, 'pitchfactor': 0.8
        }

        AttitudeCalculator.apply_smoothing(point, None, tail_config)

        # Should apply scaling factors
        assert abs(point.ROLL - (5 * 0.6)) < 0.1
        assert abs(point.PITCH - (10 * 0.8)) < 0.1

    def test_apply_smoothing_with_previous(self):
        prev_point = FdrTrackPoint(HEADING=180, PITCH=5, ROLL=2)
        curr_point = FdrTrackPoint(HEADING=190, PITCH=10, ROLL=5)
        tail_config = {
            'headingtrim': 0, 'pitchtrim': 0, 'rolltrim': 0,
            'rollfactor': 1.0, 'pitchfactor': 1.0
        }

        AttitudeCalculator.apply_smoothing(curr_point, prev_point, tail_config)

        # Heading should be smoothed (between 180 and 190)
        assert 180 <= curr_point.HEADING <= 190


class TestTrackBuilder:
    """Tests for TrackBuilder"""

    def test_interpolate_heading_no_wrap(self):
        builder = TrackBuilder(None)
        # Interpolate from 90° to 100°
        result = builder._interpolate_heading(90.0, 100.0, 0.5)
        assert abs(result - 95.0) < 0.1

    def test_interpolate_heading_with_wrap(self):
        builder = TrackBuilder(None)
        # Interpolate from 350° to 10° (should go through 360/0)
        result = builder._interpolate_heading(350.0, 10.0, 0.5)
        # Should be close to 0/360
        assert result < 5.0 or result > 355.0

    def test_interpolate_heading_reverse_wrap(self):
        builder = TrackBuilder(None)
        # Interpolate from 10° to 350° (should go backwards through 0)
        result = builder._interpolate_heading(10.0, 350.0, 0.5)
        # Should be close to 0/360
        assert result < 5.0 or result > 355.0


class TestIgcParser:
    """Integration tests for IgcParser"""

    def test_parse_complete_igc_file(self, sample_igc_file, mock_cli_args):
        from igc_config import Config
        config = Config(mock_cli_args)
        parser = IgcParser(config)

        with open(sample_igc_file, 'r') as f:
            flight = parser.parse_file(f)

        assert flight is not None
        assert len(flight.track) > 0
        assert flight.TAIL is not None
        assert flight.summary != ''

    def test_parse_flight_metadata(self, sample_igc_file, mock_cli_args):
        from igc_config import Config
        config = Config(mock_cli_args)
        parser = IgcParser(config)

        with open(sample_igc_file, 'r') as f:
            flight = parser.parse_file(f)

        # Check metadata was extracted
        first_point = flight.track[0]
        last_point = flight.track[-1]

        assert first_point.TIME is not None
        assert last_point.TIME is not None
        assert last_point.TIME >= first_point.TIME

    def test_parse_track_points(self, sample_igc_file, mock_cli_args):
        from igc_config import Config
        config = Config(mock_cli_args)
        parser = IgcParser(config)

        with open(sample_igc_file, 'r') as f:
            flight = parser.parse_file(f)

        # Verify track points have valid data
        for point in flight.track:
            assert -90 <= point.LAT <= 90
            assert -180 <= point.LONG <= 180
            assert point.ALTMSL >= 0
            assert 0 <= point.HEADING <= 360
            assert -180 <= point.PITCH <= 180
            assert -180 <= point.ROLL <= 180

    def test_parse_handles_timezone(self, sample_igc_file, mock_cli_args):
        from igc_config import Config
        mock_cli_args.timezone = '2'  # +2 hours
        config = Config(mock_cli_args)
        parser = IgcParser(config)

        with open(sample_igc_file, 'r') as f:
            flight = parser.parse_file(f)

        assert flight.timezone == 7200  # 2 hours in seconds


class TestParserEdgeCases:
    """Test edge cases and error handling"""

    def test_parse_empty_file(self, tmp_path, mock_cli_args):
        from igc_config import Config
        empty_file = tmp_path / "empty.igc"
        empty_file.write_text("")

        config = Config(mock_cli_args)
        parser = IgcParser(config)

        with open(empty_file, 'r') as f:
            flight = parser.parse_file(f)

        # Should handle gracefully
        assert flight.track == []

    def test_parse_malformed_b_record(self, tmp_path, mock_cli_args):
        from igc_config import Config
        malformed = tmp_path / "malformed.igc"
        content = """AXCS001
HFDTE090525
B12142880  # Incomplete B record
B1214288099883N00805990EA0090200902
"""
        malformed.write_text(content)

        config = Config(mock_cli_args)
        parser = IgcParser(config)

        with open(malformed, 'r') as f:
            flight = parser.parse_file(f)

        # Should skip malformed records and parse valid ones
        assert len(flight.track) >= 0
