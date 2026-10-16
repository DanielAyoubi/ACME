import pytest

from src.humidity import calibrated_rh, rh_from_dewpoint


def test_saturated_air_is_100_percent():
    assert rh_from_dewpoint(20.0, 20.0) == 100.0
    assert rh_from_dewpoint(25.0, 20.0) == 100.0


def test_known_value():
    # Dew point 10 °C at 20 °C is about 52.5 % RH.
    assert rh_from_dewpoint(10.0, 20.0) == pytest.approx(52.5, abs=0.1)


def test_very_dry_air_stays_above_zero():
    assert 0.0 <= rh_from_dewpoint(-40.0, 40.0) < 1.0


def test_calibration_is_the_linear_fit():
    assert calibrated_rh(0.0) == pytest.approx(1.2871)
    assert calibrated_rh(100.0) == pytest.approx(97.6971)
