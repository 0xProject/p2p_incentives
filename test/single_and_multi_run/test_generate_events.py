"""
This module contains unit tests of generate_events_during_whole_process().
"""

from typing import List
import pytest

from single_run import SingleRun
from ..__init__ import SCENARIO_SAMPLE, ENGINE_SAMPLE, PERFORMANCE_SAMPLE


def generate_fake_events(rate: float, length: int) -> List[int]:
    """
    This is a fake function for generating events. Given a rate and a length, this function
    generate "rate" number of events for every time slot, and the number of time slots is "length".
    """
    return [int(rate)] * length


@pytest.mark.parametrize(
    "scenario, engine, performance",
    [(SCENARIO_SAMPLE, ENGINE_SAMPLE, PERFORMANCE_SAMPLE)],
)
def test_generate_events_during_whole_process(
    scenario, engine, performance, monkeypatch
):
    """
    This tests generate_events_during_whole_process().
    """

    # Arrange.

    # Mocking generate_event_counts_over_time()
    monkeypatch.setattr(
        scenario, "generate_event_counts_over_time", generate_fake_events
    )

    single_run_instance = SingleRun(scenario, engine, performance)

    # Act.
    actual_counts = list(single_run_instance.generate_events_during_whole_process())

    # Assert.
    parameter_number = 3
    expected_counts = [[] for _ in range(parameter_number)]
    for i in range(parameter_number):
        expected_counts[i] = [scenario.growth_rates[i]] * scenario.growth_rounds + [
            scenario.stable_rates[i]
        ] * scenario.stable_rounds

    for i in range(parameter_number):
        assert expected_counts[i] == actual_counts[i]
