"""
Tests for igc_utils.py utility functions
"""
import pytest
import math
from datetime import datetime, date
from igc_utils import (
    secondsFromString,
    numberOrString,
    wrapHeading,
    wrapAttitude,
    calculateDistance,
    calculateHeading,
    toMDY,
    toYMD,
    toHM
)


class TestTimezoneConversion:
    """Tests for secondsFromString timezone conversion"""

    def test_hours_as_integer(self):
        assert secondsFromString("5") == 18000  # 5 hours * 3600
        assert secondsFromString("-3") == -10800  # -3 hours * 3600

    def test_hours_as_float(self):
        assert secondsFromString("2.5") == 9000  # 2.5 hours * 3600

    def test_hms_format(self):
        assert secondsFromString("+05:30:00") == 19800  # 5.5 hours
        assert secondsFromString("-02:15:00") == -8100  # -2.25 hours

    def test_hm_format(self):
        assert secondsFromString("+05:30") == 19800  # 5.5 hours
        assert secondsFromString("-02:15") == -8100  # -2.25 hours

    def test_zero_offset(self):
        assert secondsFromString("0") == 0
        assert secondsFromString("+00:00:00") == 0


class TestNumberOrString:
    """Tests for numberOrString type conversion"""

    def test_integer_string(self):
        assert numberOrString("42") == 42.0
        assert isinstance(numberOrString("42"), float)

    def test_float_string(self):
        assert numberOrString("3.14") == 3.14
        assert numberOrString("-2.5") == -2.5

    def test_signed_numbers(self):
        assert numberOrString("+10") == 10.0
        assert numberOrString("-10") == -10.0

    def test_non_numeric_string(self):
        assert numberOrString("hello") == "hello"
        assert numberOrString("123abc") == "123abc"


class TestHeadingWrapping:
    """Tests for wrapHeading angle normalization"""

    def test_normal_headings(self):
        assert wrapHeading(45) == 45
        assert wrapHeading(180) == 180
        assert wrapHeading(359) == 359

    def test_wrap_positive_overflow(self):
        assert wrapHeading(360) == 0
        assert wrapHeading(370) == 10
        assert wrapHeading(720) == 0

    def test_wrap_negative(self):
        assert wrapHeading(-10) == 350
        assert wrapHeading(-90) == 270
        assert wrapHeading(-360) == 0

    def test_zero_heading(self):
        assert wrapHeading(0) == 0


class TestAttitudeWrapping:
    """Tests for wrapAttitude angle normalization"""

    def test_normal_attitudes(self):
        assert wrapAttitude(45) == 45
        assert wrapAttitude(-45) == -45
        assert wrapAttitude(180) == 180
        assert wrapAttitude(-180) == -180

    def test_wrap_positive_overflow(self):
        assert wrapAttitude(190) == -170
        assert wrapAttitude(270) == -90

    def test_wrap_negative_overflow(self):
        assert wrapAttitude(-190) == 170
        assert wrapAttitude(-270) == 90

    def test_boundary_values(self):
        assert abs(wrapAttitude(180) - 180) < 0.001
        assert abs(wrapAttitude(-180) - (-180)) < 0.001


class TestDistanceCalculation:
    """Tests for calculateDistance haversine formula"""

    def test_same_point(self):
        dist = calculateDistance(45.0, 8.0, 45.0, 8.0)
        assert dist == 0

    def test_known_distance(self):
        # London to Paris (approximately 340 km)
        london_lat, london_lon = 51.5074, -0.1278
        paris_lat, paris_lon = 48.8566, 2.3522
        dist = calculateDistance(london_lat, london_lon, paris_lat, paris_lon)
        # Should be around 340,000 meters (±10%)
        assert 300000 < dist < 380000

    def test_short_distance(self):
        # Two close points (should be ~111 meters for 0.001 deg latitude)
        dist = calculateDistance(45.0, 8.0, 45.001, 8.0)
        assert 100 < dist < 120

    def test_equator_vs_poles(self):
        # Same longitude difference at equator vs near pole
        equator_dist = calculateDistance(0, 0, 0, 1)
        pole_dist = calculateDistance(80, 0, 80, 1)
        # Distance should be less near poles
        assert pole_dist < equator_dist


class TestHeadingCalculation:
    """Tests for calculateHeading bearing calculation"""

    def test_north_heading(self):
        # Moving north
        heading = calculateHeading(45.0, 8.0, 45.001, 8.0)
        assert 355 < heading or heading < 5  # Close to 0° (north)

    def test_east_heading(self):
        # Moving east
        heading = calculateHeading(45.0, 8.0, 45.0, 8.001)
        assert 85 < heading < 95  # Close to 90° (east)

    def test_south_heading(self):
        # Moving south
        heading = calculateHeading(45.001, 8.0, 45.0, 8.0)
        assert 175 < heading < 185  # Close to 180° (south)

    def test_west_heading(self):
        # Moving west
        heading = calculateHeading(45.0, 8.001, 45.0, 8.0)
        assert 265 < heading < 275  # Close to 270° (west)

    def test_same_point_with_fallback(self):
        # Same point should use fallback
        heading = calculateHeading(45.0, 8.0, 45.0, 8.0, fallback_heading=123.0)
        assert heading == 123.0

    def test_same_point_without_fallback(self):
        # Same point without fallback should return 360
        heading = calculateHeading(45.0, 8.0, 45.0, 8.0)
        assert heading == 360.0


class TestDateFormatting:
    """Tests for date/time formatting functions"""

    def test_toMDY_from_datetime(self):
        dt = datetime(2025, 5, 23, 12, 30, 45)
        assert toMDY(dt) == "05/23/2025"

    def test_toMDY_from_date(self):
        d = date(2025, 5, 23)
        assert toMDY(d) == "05/23/2025"

    def test_toYMD_from_datetime(self):
        dt = datetime(2025, 5, 23, 12, 30, 45)
        assert toYMD(dt) == "2025/05/23"

    def test_toYMD_from_date(self):
        d = date(2025, 5, 23)
        assert toYMD(d) == "2025/05/23"

    def test_toHM_from_datetime(self):
        dt = datetime(2025, 5, 23, 12, 30, 45)
        assert toHM(dt) == "12:30"

    def test_toHM_edge_cases(self):
        dt_midnight = datetime(2025, 5, 23, 0, 0, 0)
        assert toHM(dt_midnight) == "00:00"

        dt_noon = datetime(2025, 5, 23, 12, 0, 0)
        assert toHM(dt_noon) == "12:00"


class TestEdgeCases:
    """Test edge cases and error conditions"""

    def test_distance_antipodal_points(self):
        # Opposite sides of Earth (should be ~20,000 km)
        dist = calculateDistance(0, 0, 0, 180)
        assert 19000000 < dist < 21000000

    def test_heading_wrap_around(self):
        # Test near 0/360 boundary
        heading1 = calculateHeading(45.0, 8.0, 45.0001, 8.00001)
        heading2 = calculateHeading(45.0, 8.0, 45.0001, 7.99999)
        # Both should be valid headings
        assert 0 <= heading1 <= 360
        assert 0 <= heading2 <= 360

    def test_attitude_large_values(self):
        # Test with very large angles
        assert -180 <= wrapAttitude(1000) <= 180
        assert -180 <= wrapAttitude(-1000) <= 180
