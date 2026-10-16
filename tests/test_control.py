from src.control import PID


def test_output_stays_between_0_and_100():
    pid = PID(kp=10.0, ki=1.0, kd=0.0, output=50.0)
    assert pid.update(100.0, 0.0, 1.0) == 100.0
    assert pid.update(0.0, 100.0, 1.0) == 0.0


def test_starts_from_the_current_output():
    pid = PID(kp=1.0, ki=0.03, kd=0.0, output=40.0)
    assert pid.update(60.0, 60.0, 1.0) == 40.0


def test_no_windup_after_saturation():
    pid = PID(kp=1.0, ki=0.1, kd=0.0, output=50.0)
    for i in range(100):
        pid.update(100.0, 0.0, 1.0)
    # Once the measurement overshoots, the output must come off 100 straight away.
    assert pid.update(50.0, 51.0, 1.0) < 100.0


def test_no_derivative_kick_on_first_update():
    with_d = PID(kp=1.0, ki=0.0, kd=100.0, output=0.0)
    without_d = PID(kp=1.0, ki=0.0, kd=0.0, output=0.0)
    assert with_d.update(60.0, 40.0, 1.0) == without_d.update(60.0, 40.0, 1.0)


def test_settles_on_a_simple_humidifier():
    # RH follows the humid share of the flow with a lag, like a saturating bubbler.
    pid = PID(kp=1.0, ki=0.03, kd=0.0, output=0.0)
    rh = 20.0
    for i in range(1000):
        share = pid.update(60.0, rh, 1.0)
        rh += (share - rh) * 0.1
    assert abs(rh - 60.0) < 0.5
