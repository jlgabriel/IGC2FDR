"""
Tests for igc_writer.py FDR file writing
"""
import pytest
from io import StringIO
from datetime import datetime, date
from igc_writer import FdrWriter, writeOutputFile
from igc_model import FdrFlight, FdrTrackPoint
from igc_config import Config


class TestFdrWriter:
    """Tests for FdrWriter class"""

    def test_format_comment(self):
        comment = "This is a test\nwith multiple lines"
        formatted = FdrWriter.format_comment(comment)
        assert 'COMM,' in formatted
        assert 'This is a test' in formatted
        assert 'with multiple lines' in formatted

    def test_format_drefs(self):
        drefs = [
            'sim/test/instrument\t1.0\t\t// source: {Speed}',
            'sim/test/altitude\t1.0\t\t// source: {ALTMSL}'
        ]
        formatted = FdrWriter.format_drefs(drefs)
        assert 'DREF,' in formatted
        assert 'sim/test/instrument' in formatted
        assert 'sim/test/altitude' in formatted

    def test_format_drefs_empty(self):
        formatted = FdrWriter.format_drefs([])
        assert formatted == ""

    def test_format_column_names(self):
        dref_names = {'IAS', 'Altimeter', 'VSI'}
        formatted = FdrWriter.format_column_names(dref_names)
        assert 'Longitude' in formatted
        assert 'Latitude' in formatted
        assert 'IAS' in formatted
        assert 'Altimeter' in formatted
        assert 'VSI' in formatted

    def test_get_timezone_explanation_zero(self, mock_cli_args):
        from igc_config import Config
        config = Config(mock_cli_args)
        writer = FdrWriter(config)
        explanation = writer.get_timezone_explanation(0)
        assert 'same timezone' in explanation.lower()

    def test_get_timezone_explanation_positive(self, mock_cli_args):
        from igc_config import Config
        config = Config(mock_cli_args)
        writer = FdrWriter(config)
        explanation = writer.get_timezone_explanation(7200)  # +2 hours
        assert '2 hour' in explanation
        assert 'added' in explanation

    def test_get_timezone_explanation_negative(self, mock_cli_args):
        from igc_config import Config
        config = Config(mock_cli_args)
        writer = FdrWriter(config)
        explanation = writer.get_timezone_explanation(-5400)  # -1.5 hours
        assert '1 hour' in explanation
        assert '30 minute' in explanation
        assert 'subtracted' in explanation


class TestFdrWriting:
    """Tests for FDR file writing operations"""

    def test_write_header(self, mock_cli_args):
        from igc_config import Config
        config = Config(mock_cli_args)
        writer = FdrWriter(config)

        # Create a simple flight
        flight = FdrFlight(
            ACFT='Aircraft/Test/test.acf',
            TAIL='TEST-123',
            DATE=date(2025, 5, 23),
            summary='Test flight summary'
        )

        dref_sources = {'IAS': 'round({Speed}, 4)'}
        dref_defines = ['sim/test/ias\t1.0\t\t// source: round({Speed}, 4)']

        output = StringIO()
        writer.write_header(output, flight, dref_sources, dref_defines)
        content = output.getvalue()

        # Check header elements
        assert 'A\n4\n' in content  # FDR header
        assert 'COMM,' in content
        assert 'ACFT,' in content
        assert 'TAIL,' in content
        assert 'DATE,' in content
        assert 'TEST-123' in content
        assert '05/23/2025' in content

    def test_write_track_points(self, mock_cli_args):
        from igc_config import Config
        config = Config(mock_cli_args)
        writer = FdrWriter(config)

        # Create track points
        points = [
            FdrTrackPoint(
                TIME=datetime(2025, 5, 23, 12, 30, 0),
                LONG=8.123456,
                LAT=45.678901,
                ALTMSL=1500.5,
                HEADING=270.5,
                PITCH=5.2,
                ROLL=-3.1
            ),
            FdrTrackPoint(
                TIME=datetime(2025, 5, 23, 12, 30, 1),
                LONG=8.123457,
                LAT=45.678902,
                ALTMSL=1501.0,
                HEADING=271.0,
                PITCH=5.3,
                ROLL=-3.2
            )
        ]

        # Add drefs
        for point in points:
            point.drefs['IAS'] = 75.5
            point.drefs['VSI'] = 150.0

        dref_sources = {'IAS': 'round({Speed}, 4)', 'VSI': '{VerticalSpeed}'}

        output = StringIO()
        writer.write_track_points(output, points, dref_sources)
        content = output.getvalue()

        # Check track data is present
        assert '12:30:00' in content
        assert '8.123456' in content
        assert '45.678901' in content
        assert '1500.5' in content
        assert '270.5' in content

    def test_write_complete_file(self, mock_cli_args):
        from igc_config import Config
        config = Config(mock_cli_args)
        writer = FdrWriter(config)

        # Create a complete flight
        flight = FdrFlight(
            ACFT='Aircraft/Test/test.acf',
            TAIL='CC-JUGA',
            DATE=date(2025, 5, 23),
            summary='Test flight from A to B'
        )

        # Get the DREFs for this tail to initialize them correctly
        dref_sources, _ = config.drefsByTail(flight.TAIL)

        # Add track points with proper DREF initialization
        for i in range(5):
            point = FdrTrackPoint(
                TIME=datetime(2025, 5, 23, 12, 30, i),
                LONG=8.1 + i * 0.001,
                LAT=45.5 + i * 0.001,
                ALTMSL=1000 + i * 10,
                HEADING=90.0,
                PITCH=2.0,
                ROLL=0.0
            )
            # Initialize all DREFs with dummy values
            point.drefs = {name: 0.0 for name in dref_sources.keys()}
            flight.track.append(point)

        output = StringIO()
        writer.write_file(output, flight)
        content = output.getvalue()

        # Verify complete FDR structure
        assert 'A\n4\n' in content  # Header
        assert 'ACFT,' in content
        assert 'TAIL,' in content
        assert 'CC-JUGA' in content
        assert 'DREF,' in content
        assert 'Longitude' in content
        assert 'Latitude' in content
        assert len(flight.track) == 5

        # Count data lines (should have 5 track points)
        data_lines = [line for line in content.split('\n')
                     if line.strip() and not line.startswith(('A', 'COMM,', 'ACFT,', 'TAIL,', 'DATE,', 'DREF,'))]
        # Should have at least the track points
        assert len(data_lines) >= 5


class TestWriteOutputFile:
    """Tests for writeOutputFile backward-compatible function"""

    def test_write_output_file(self, mock_cli_args):
        from igc_config import Config
        config = Config(mock_cli_args)

        # Create a flight
        flight = FdrFlight(
            TAIL='TEST-TAIL',
            DATE=date(2025, 5, 23)
        )

        # Get the DREFs for this tail
        dref_sources, _ = config.drefsByTail(flight.TAIL)

        # Add a track point with proper DREF initialization
        point = FdrTrackPoint(
            TIME=datetime(2025, 5, 23, 12, 30, 0),
            LONG=8.1,
            LAT=45.5,
            ALTMSL=1000.0,
            HEADING=90.0,
            PITCH=0.0,
            ROLL=0.0
        )
        # Initialize all DREFs
        point.drefs = {name: 0.0 for name in dref_sources.keys()}
        flight.track.append(point)

        output = StringIO()
        writeOutputFile(config, output, flight)
        content = output.getvalue()

        # Should produce valid FDR output
        assert 'A\n4\n' in content
        assert 'TEST-TAIL' in content


class TestFdrFormatting:
    """Tests for FDR format compliance"""

    def test_time_format(self, mock_cli_args):
        """Test that time is formatted correctly"""
        from igc_config import Config
        config = Config(mock_cli_args)
        writer = FdrWriter(config)

        point = FdrTrackPoint(
            TIME=datetime(2025, 5, 23, 12, 30, 45, 123456),
            LONG=8.1,
            LAT=45.5,
            ALTMSL=1000.0,
            HEADING=90.0,
            PITCH=0.0,
            ROLL=0.0
        )
        point.drefs = {}

        output = StringIO()
        writer.write_track_points(output, [point], {})
        content = output.getvalue()

        # Time should include microseconds
        assert '12:30:45' in content

    def test_coordinate_precision(self, mock_cli_args):
        """Test that coordinates maintain precision"""
        from igc_config import Config
        config = Config(mock_cli_args)
        writer = FdrWriter(config)

        point = FdrTrackPoint(
            TIME=datetime(2025, 5, 23, 12, 30, 0),
            LONG=8.123456789,  # High precision
            LAT=45.987654321,
            ALTMSL=1234.5678,
            HEADING=270.123,
            PITCH=5.678,
            ROLL=-3.456
        )
        point.drefs = {}

        output = StringIO()
        writer.write_track_points(output, [point], {})
        content = output.getvalue()

        # Should preserve significant digits
        assert '8.123456789' in content
        assert '45.987654321' in content

    def test_column_alignment(self, mock_cli_args):
        """Test that columns are properly aligned"""
        from igc_config import Config
        config = Config(mock_cli_args)
        writer = FdrWriter(config)

        points = [
            FdrTrackPoint(TIME=datetime(2025, 5, 23, 12, 30, 0),
                         LONG=8.1, LAT=45.5, ALTMSL=1000.0,
                         HEADING=90.0, PITCH=0.0, ROLL=0.0),
            FdrTrackPoint(TIME=datetime(2025, 5, 23, 12, 30, 1),
                         LONG=8.123456789, LAT=45.987654321, ALTMSL=1234.5678,
                         HEADING=270.123, PITCH=5.678, ROLL=-3.456)
        ]

        for point in points:
            point.drefs = {}

        output = StringIO()
        writer.write_track_points(output, points, {})
        lines = output.getvalue().strip().split('\n')

        # All lines should have commas at consistent positions
        assert len(lines) == 2
        comma_count_1 = lines[0].count(',')
        comma_count_2 = lines[1].count(',')
        assert comma_count_1 == comma_count_2


class TestFdrWriterEdgeCases:
    """Test edge cases and error conditions"""

    def test_write_empty_track(self, mock_cli_args):
        """Test writing a flight with no track points"""
        from igc_config import Config
        config = Config(mock_cli_args)
        writer = FdrWriter(config)

        flight = FdrFlight(
            TAIL='EMPTY',
            DATE=date(2025, 5, 23),
            track=[]
        )

        output = StringIO()
        writer.write_file(output, flight)
        content = output.getvalue()

        # Should still produce valid header
        assert 'A\n4\n' in content
        assert 'EMPTY' in content

    def test_write_with_special_characters(self, mock_cli_args):
        """Test handling of special characters in summary"""
        from igc_config import Config
        config = Config(mock_cli_args)
        writer = FdrWriter(config)

        flight = FdrFlight(
            TAIL='TEST-123',
            DATE=date(2025, 5, 23),
            summary='Flight with "quotes" and\nline breaks'
        )

        output = StringIO()
        writer.write_file(output, flight)
        content = output.getvalue()

        # Should handle special characters
        assert 'quotes' in content
        assert 'line breaks' in content
