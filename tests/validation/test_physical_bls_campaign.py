"""New production must pass the frozen campaign; legacy xfails are historical only."""

import socket

import pytest

from validation.physical_bls_campaign import run


@pytest.fixture(scope="module")
def record():
    with pytest.MonkeyPatch.context() as m:

        def deny(*args, **kwargs):
            raise AssertionError("Network forbidden")

        m.setattr(socket.socket, "connect", deny)
        return run()


@pytest.mark.parametrize("index", range(252))
def test_frozen_scientific_acceptance(index, record):
    assert record["results"][index]["passed"], record["results"][index]


def test_no_production_expected_failures_or_qualification_inflation(record):
    assert record["overall_passed"] and record["failed_trials"] == 0
    assert record["required_recovery_count"] == record["required_recovery_successes"] == 10
    assert record["all_nine_previous_failures_pass"]
    assert (
        record["mission"] == 58
        and record["execution_target"] == "current production physical-window search"
    )
    assert not record["physical_arrival_qualification_changed"]
    assert not record["universal_fap_calibration_established"]
