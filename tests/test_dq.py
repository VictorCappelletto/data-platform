from dataplatform.dq.checks import null_rate, range_check, volume_vs_baseline
from dataplatform.dq.runner import DataQualityError, run_checks


def test_null_rate_pass():
    rows = [{"id": 1}, {"id": 2}]
    result = null_rate(rows, "id", max_rate=0.0)
    assert result.passed


def test_null_rate_fail():
    rows = [{"id": 1}, {"id": None}]
    result = null_rate(rows, "id", max_rate=0.0)
    assert not result.passed


def test_range_and_volume():
    rows = [{"amount": 10}, {"amount": 20}]
    assert range_check(rows, "amount", min_value=0, max_value=100).passed
    assert volume_vs_baseline(100, 100, max_variance_pct=5).passed


def test_run_checks_raises():
    bad = null_rate([{"id": None}], "id", max_rate=0.0)
    try:
        run_checks([bad])
        raised = False
    except DataQualityError:
        raised = True
    assert raised
