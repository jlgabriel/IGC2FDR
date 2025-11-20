"""
Tests for igc_model.py data models
"""
import pytest
from datetime import datetime, date, timedelta
from igc_model import (
    FileType,
    FdrTrackPoint,
    FdrFlight,
    FlightMeta
)


class TestFileType:
    """Tests for FileType enum"""

    def test_file_type_values(self):
        assert FileType.UNKNOWN.value == 0
        assert FileType.CSV.value == 1
        assert FileType.KML.value == 2
        assert FileType.GPX.value == 3
        assert FileType.IGC.value == 4

    def test_file_type_comparison(self):
        assert FileType.IGC != FileType.CSV
        assert FileType.UNKNOWN == FileType.UNKNOWN


class TestFdrTrackPoint:
    """Tests for FdrTrackPoint data model"""

    def test_default_initialization(self):
        point = FdrTrackPoint()
        assert point.TIME is None
        assert point.LONG == 0.0
        assert point.LAT == 0.0
        assert point.ALTMSL == 0.0
        assert point.HEADING == 0.0
        assert point.PITCH == 0.0
        assert point.ROLL == 0.0
        assert point.drefs == {}

    def test_initialization_with_values(self):
        test_time = datetime(2025, 5, 23, 12, 30, 45)
        point = FdrTrackPoint(
            TIME=test_time,
            LONG=8.123456,
            LAT=45.678901,
            ALTMSL=1500.5,
            HEADING=270.5,
            PITCH=5.2,
            ROLL=-3.1
        )
        assert point.TIME == test_time
        assert point.LONG == 8.123456
        assert point.LAT == 45.678901
        assert point.ALTMSL == 1500.5
        assert point.HEADING == 270.5
        assert point.PITCH == 5.2
        assert point.ROLL == -3.1

    def test_drefs_dictionary(self):
        point = FdrTrackPoint()
        point.drefs['IAS'] = 75.5
        point.drefs['VSI'] = 150.2
        assert point.drefs['IAS'] == 75.5
        assert point.drefs['VSI'] == 150.2
        assert len(point.drefs) == 2

    def test_track_point_modification(self):
        point = FdrTrackPoint()
        point.HEADING = 180.0
        point.PITCH = 10.0
        assert point.HEADING == 180.0
        assert point.PITCH == 10.0


class TestFdrFlight:
    """Tests for FdrFlight data model"""

    def test_default_initialization(self):
        flight = FdrFlight()
        assert flight.ACFT == ''
        assert flight.TAIL == ''
        assert isinstance(flight.DATE, date)
        assert flight.PRES == 0.0
        assert flight.DISA == 0
        assert flight.WIND == (0, 0)
        assert flight.timezone == 0
        assert flight.track == []
        assert flight.summary == ''

    def test_initialization_with_values(self):
        test_date = date(2025, 5, 23)
        test_track = [FdrTrackPoint(), FdrTrackPoint()]

        flight = FdrFlight(
            ACFT='Aircraft/Test/test.acf',
            TAIL='CC-JUGA',
            DATE=test_date,
            PRES=29.92,
            DISA=0,
            WIND=(10, 270),
            timezone=3600,
            track=test_track,
            summary='Test flight'
        )

        assert flight.ACFT == 'Aircraft/Test/test.acf'
        assert flight.TAIL == 'CC-JUGA'
        assert flight.DATE == test_date
        assert flight.PRES == 29.92
        assert flight.WIND == (10, 270)
        assert flight.timezone == 3600
        assert len(flight.track) == 2
        assert flight.summary == 'Test flight'

    def test_track_modification(self):
        flight = FdrFlight()
        assert len(flight.track) == 0

        point1 = FdrTrackPoint(HEADING=90.0)
        point2 = FdrTrackPoint(HEADING=180.0)

        flight.track.append(point1)
        flight.track.append(point2)

        assert len(flight.track) == 2
        assert flight.track[0].HEADING == 90.0
        assert flight.track[1].HEADING == 180.0


class TestFlightMeta:
    """Tests for FlightMeta data model"""

    def test_default_initialization(self):
        meta = FlightMeta()
        assert meta.Pilot is None
        assert meta.TailNumber is None
        assert meta.DerivedOrigin is None
        assert meta.StartTime is None
        assert meta.EndTime is None
        assert meta.TotalDuration is None
        assert meta.TotalDistance is None
        assert meta.DeviceModel is None
        assert meta.GPSSource is None

    def test_initialization_with_values(self):
        start_time = datetime(2025, 5, 23, 12, 0, 0)
        end_time = datetime(2025, 5, 23, 13, 30, 0)
        duration = end_time - start_time

        meta = FlightMeta(
            Pilot='Juan Gabriel',
            TailNumber='CC-JUGA',
            DerivedOrigin='Test Airport',
            StartTime=start_time,
            EndTime=end_time,
            TotalDuration=duration,
            TotalDistance=150.5,
            DeviceModel='IGC Logger',
            GPSSource='Test GPS'
        )

        assert meta.Pilot == 'Juan Gabriel'
        assert meta.TailNumber == 'CC-JUGA'
        assert meta.DerivedOrigin == 'Test Airport'
        assert meta.StartTime == start_time
        assert meta.EndTime == end_time
        assert meta.TotalDuration == duration
        assert meta.TotalDistance == 150.5
        assert meta.DeviceModel == 'IGC Logger'
        assert meta.GPSSource == 'Test GPS'

    def test_optional_fields(self):
        meta = FlightMeta()
        meta.Pilot = 'Test Pilot'
        meta.BatteryLevel = 85.5
        meta.BatteryState = 'Charging'
        meta.RouteWaypoints = 'WP1, WP2, WP3'

        assert meta.Pilot == 'Test Pilot'
        assert meta.BatteryLevel == 85.5
        assert meta.BatteryState == 'Charging'
        assert meta.RouteWaypoints == 'WP1, WP2, WP3'

    def test_gps_error_fields(self):
        meta = FlightMeta()
        meta.MaximumHorizontalError = 10.5
        meta.MinimumHorizontalError = 2.3
        meta.AverageHorizontalError = 5.4
        meta.MaximumVerticalError = 15.0
        meta.MinimumVerticalError = 3.0
        meta.AverageVerticalError = 8.5

        assert meta.MaximumHorizontalError == 10.5
        assert meta.MinimumHorizontalError == 2.3
        assert meta.AverageHorizontalError == 5.4
        assert meta.MaximumVerticalError == 15.0
        assert meta.MinimumVerticalError == 3.0
        assert meta.AverageVerticalError == 8.5


class TestDataModelIntegration:
    """Integration tests for data models working together"""

    def test_complete_flight_structure(self):
        # Create a complete flight with metadata
        start_time = datetime(2025, 5, 23, 12, 0, 0)

        # Create track points
        track = []
        for i in range(5):
            point = FdrTrackPoint(
                TIME=start_time + timedelta(seconds=i),
                LAT=45.5 + i * 0.001,
                LONG=8.1 + i * 0.001,
                ALTMSL=1000 + i * 10,
                HEADING=90.0 + i * 5,
                PITCH=2.0,
                ROLL=0.0
            )
            point.drefs['IAS'] = 70.0 + i
            track.append(point)

        # Create flight
        flight = FdrFlight(
            ACFT='Aircraft/Test/test.acf',
            TAIL='TEST-123',
            DATE=date(2025, 5, 23),
            track=track
        )

        assert len(flight.track) == 5
        assert flight.track[0].HEADING == 90.0
        assert flight.track[4].HEADING == 110.0
        assert flight.track[0].drefs['IAS'] == 70.0
        assert flight.track[4].drefs['IAS'] == 74.0

    def test_flight_with_metadata(self):
        meta = FlightMeta(
            Pilot='Test Pilot',
            TailNumber='TEST-123',
            StartTime=datetime(2025, 5, 23, 12, 0, 0),
            EndTime=datetime(2025, 5, 23, 13, 30, 0)
        )

        # Calculate duration
        meta.TotalDuration = meta.EndTime - meta.StartTime
        meta.TotalDistance = 125.5

        assert meta.TotalDuration.total_seconds() == 5400  # 1.5 hours
        assert meta.TotalDistance == 125.5
