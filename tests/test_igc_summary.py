"""
Tests for igc_summary.py flight summary generation
"""
import pytest
from datetime import datetime, timedelta
from igc_summary import flightSummary
from igc_model import FlightMeta


class TestFlightSummary:
    """Tests for flightSummary function"""

    def test_basic_summary(self):
        """Test basic summary generation with minimal data"""
        meta = FlightMeta()
        meta.TailNumber = 'TEST-123'
        meta.StartTime = datetime(2025, 5, 23, 12, 0, 0)
        meta.EndTime = datetime(2025, 5, 23, 13, 30, 0)
        meta.TotalDuration = meta.EndTime - meta.StartTime
        meta.TotalDistance = 125.5
        meta.StartLatitude = 45.5
        meta.StartLongitude = 8.1
        meta.EndLatitude = 45.6
        meta.EndLongitude = 8.2

        summary = flightSummary(meta)

        assert 'TEST-123' in summary
        assert '2025/05/23' in summary
        assert '125.5' in summary
        assert '1 hours and 30 minutes' in summary
        assert '45.5' in summary
        assert '8.1' in summary

    def test_summary_with_pilot(self):
        """Test summary with pilot information"""
        meta = FlightMeta()
        meta.Pilot = 'John Doe'
        meta.TailNumber = 'TEST-123'
        meta.StartTime = datetime(2025, 5, 23, 12, 0, 0)
        meta.TotalDuration = timedelta(hours=2, minutes=15)

        summary = flightSummary(meta)

        assert 'John Doe' in summary
        assert 'by John Doe' in summary

    def test_summary_without_pilot(self):
        """Test summary without pilot information"""
        meta = FlightMeta()
        meta.TailNumber = 'TEST-123'
        meta.StartTime = datetime(2025, 5, 23, 12, 0, 0)
        meta.TotalDuration = timedelta(hours=1)

        summary = flightSummary(meta)

        # Should not have 'by' clause
        assert 'by' not in summary.split('\n')[0]

    def test_summary_with_origin_destination(self):
        """Test summary with origin and destination"""
        meta = FlightMeta()
        meta.TailNumber = 'TEST-123'
        meta.DerivedOrigin = 'Airport A'
        meta.DerivedDestination = 'Airport B'
        meta.StartTime = datetime(2025, 5, 23, 12, 0, 0)
        meta.EndTime = datetime(2025, 5, 23, 13, 0, 0)
        meta.TotalDuration = timedelta(hours=1)
        meta.StartLatitude = 45.5
        meta.StartLongitude = 8.1
        meta.EndLatitude = 45.6
        meta.EndLongitude = 8.2

        summary = flightSummary(meta)

        assert 'Airport A' in summary
        assert 'Airport B' in summary
        assert 'From:' in summary
        assert 'To:' in summary

    def test_summary_without_origin_destination(self):
        """Test summary with N/A for missing origin/destination"""
        meta = FlightMeta()
        meta.TailNumber = 'TEST-123'
        meta.StartTime = datetime(2025, 5, 23, 12, 0, 0)
        meta.TotalDuration = timedelta(hours=1)
        meta.StartLatitude = 45.5
        meta.StartLongitude = 8.1

        summary = flightSummary(meta)

        assert 'N/A' in summary

    def test_summary_with_device_info(self):
        """Test summary with device information"""
        meta = FlightMeta()
        meta.TailNumber = 'TEST-123'
        meta.DeviceModel = 'FlightLogger Pro'
        meta.DeviceVersion = '2.5.1'
        meta.StartTime = datetime(2025, 5, 23, 12, 0, 0)
        meta.TotalDuration = timedelta(hours=1)

        summary = flightSummary(meta)

        assert 'FlightLogger Pro' in summary
        assert '2.5.1' in summary
        assert 'Client:' in summary

    def test_summary_with_gps_source(self):
        """Test summary with GPS source information"""
        meta = FlightMeta()
        meta.TailNumber = 'TEST-123'
        meta.GPSSource = 'Internal GPS (DOP 1.5)'
        meta.StartTime = datetime(2025, 5, 23, 12, 0, 0)
        meta.TotalDuration = timedelta(hours=1)

        summary = flightSummary(meta)

        assert 'Internal GPS' in summary
        assert 'GPS/AHRS:' in summary

    def test_summary_with_waypoints(self):
        """Test summary with waypoint information"""
        meta = FlightMeta()
        meta.TailNumber = 'TEST-123'
        meta.RouteWaypoints = 'WP1, WP2, WP3'
        meta.StartTime = datetime(2025, 5, 23, 12, 0, 0)
        meta.TotalDuration = timedelta(hours=1)

        summary = flightSummary(meta)

        assert 'WP1, WP2, WP3' in summary
        assert 'Planned:' in summary

    def test_summary_with_imported_from(self):
        """Test summary with import source"""
        meta = FlightMeta()
        meta.TailNumber = 'TEST-123'
        meta.ImportedFrom = 'IGC Flight Logger'
        meta.StartTime = datetime(2025, 5, 23, 12, 0, 0)
        meta.TotalDuration = timedelta(hours=1)

        summary = flightSummary(meta)

        assert 'IGC Flight Logger' in summary
        assert 'Imported:' in summary

    def test_summary_duration_formatting(self):
        """Test different duration formats"""
        meta = FlightMeta()
        meta.TailNumber = 'TEST-123'
        meta.StartTime = datetime(2025, 5, 23, 12, 0, 0)

        # Test 1 hour exactly
        meta.TotalDuration = timedelta(hours=1)
        summary = flightSummary(meta)
        assert '1 hours and 0 minutes' in summary

        # Test multiple hours and minutes
        meta.TotalDuration = timedelta(hours=3, minutes=45)
        summary = flightSummary(meta)
        assert '3 hours and 45 minutes' in summary

        # Test less than 1 hour
        meta.TotalDuration = timedelta(minutes=30)
        summary = flightSummary(meta)
        assert '0 hours and 30 minutes' in summary

    def test_summary_coordinate_precision(self):
        """Test that coordinates are formatted with proper precision"""
        meta = FlightMeta()
        meta.TailNumber = 'TEST-123'
        meta.StartLatitude = 45.123456789
        meta.StartLongitude = 8.987654321
        meta.EndLatitude = 46.111111111
        meta.EndLongitude = 9.222222222
        meta.StartTime = datetime(2025, 5, 23, 12, 0, 0)
        meta.TotalDuration = timedelta(hours=1)

        summary = flightSummary(meta)

        # Should show 6 decimal places
        assert '45.123457' in summary
        assert '8.987654' in summary
        assert '46.111111' in summary
        assert '9.222222' in summary

    def test_summary_time_in_zulu(self):
        """Test that times are shown in Zulu (UTC)"""
        meta = FlightMeta()
        meta.TailNumber = 'TEST-123'
        meta.StartTime = datetime(2025, 5, 23, 12, 30, 0)
        meta.EndTime = datetime(2025, 5, 23, 14, 45, 0)
        meta.TotalDuration = meta.EndTime - meta.StartTime

        summary = flightSummary(meta)

        # Should have Z suffix for UTC times
        assert '12:30Z' in summary
        assert '14:45Z' in summary

    def test_summary_with_complete_data(self):
        """Test summary with all fields populated"""
        meta = FlightMeta()
        meta.Pilot = 'John Doe'
        meta.TailNumber = 'CC-JUGA'
        meta.DerivedOrigin = 'Airport A'
        meta.DerivedDestination = 'Airport B'
        meta.StartTime = datetime(2025, 5, 23, 12, 0, 0)
        meta.EndTime = datetime(2025, 5, 23, 14, 30, 0)
        meta.TotalDuration = meta.EndTime - meta.StartTime
        meta.TotalDistance = 250.75
        meta.StartLatitude = 45.5
        meta.StartLongitude = 8.1
        meta.EndLatitude = 46.2
        meta.EndLongitude = 8.8
        meta.DeviceModel = 'IGC Logger Pro'
        meta.DeviceVersion = '1.2.3'
        meta.GPSSource = 'Internal GPS'
        meta.RouteWaypoints = 'WP1, WP2, WP3'
        meta.ImportedFrom = 'IGC File'

        summary = flightSummary(meta)

        # Verify all elements are present
        assert 'John Doe' in summary
        assert 'CC-JUGA' in summary
        assert 'Airport A' in summary
        assert 'Airport B' in summary
        assert '250.75' in summary
        assert '2 hours and 30 minutes' in summary
        assert 'IGC Logger Pro' in summary
        assert '1.2.3' in summary
        assert 'Internal GPS' in summary
        assert 'WP1, WP2, WP3' in summary
        assert 'IGC File' in summary

    def test_summary_structure(self):
        """Test that summary has proper structure"""
        meta = FlightMeta()
        meta.TailNumber = 'TEST-123'
        meta.StartTime = datetime(2025, 5, 23, 12, 0, 0)
        meta.EndTime = datetime(2025, 5, 23, 13, 0, 0)
        meta.TotalDuration = timedelta(hours=1)
        meta.TotalDistance = 100.0
        meta.StartLatitude = 45.5
        meta.StartLongitude = 8.1
        meta.EndLatitude = 45.6
        meta.EndLongitude = 8.2

        summary = flightSummary(meta)
        lines = summary.split('\n')

        # Should have multiple lines
        assert len(lines) >= 5

        # First line should be the heading
        assert 'TEST-123' in lines[0]

        # Should have dashed separator
        assert any('-' * 10 in line for line in lines)

        # Should have 'From:' and 'To:' lines
        from_lines = [line for line in lines if 'From:' in line]
        to_lines = [line for line in lines if 'To:' in line]
        assert len(from_lines) == 1
        assert len(to_lines) == 1

    def test_summary_handles_none_values(self):
        """Test that summary handles None values gracefully"""
        meta = FlightMeta()
        meta.TailNumber = None
        meta.StartTime = None
        meta.TotalDuration = None
        meta.TotalDistance = None

        summary = flightSummary(meta)

        # Should handle None gracefully with 'Unknown' or 'N/A'
        assert 'Unknown' in summary or 'N/A' in summary
