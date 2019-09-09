"""
This module contains functions to test generate_events_during_whole_process().
"""

from typing import List
import pytest

from simulator import SingleRun
from .__init__ import SCENARIO_SAMPLE_1, ENGINE_SAMPLE, PERFORMANCE_SAMPLE


def generate_fake_events(rate: float, length: int) -> List[int]:
    """
    This is a fake function for generating events. Given a rate and a length, this function
    generate "rate" number of events for every time slot, and the number of time slots is "length".
    """
    return [int(rate)] * length


@pytest.mark.parametrize(
    "scenario, engine, performance",
    [(SCENARIO_SAMPLE_1, ENGINE_SAMPLE, PERFORMANCE_SAMPLE)],
)
def test_generate_events_during_whole_process(
    scenario, engine, performance, monkeypatch
):
    """
    To test generate_events_during_whole_process()
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
    expected_counts = [[] for _ in range(4)]
    for i in range(4):
        expected_counts[i] = [scenario.growth_rates[i]] * scenario.growth_rounds + [
            scenario.stable_rates[i]
        ] * scenario.stable_rounds

    for i in range(4):
        assert expected_counts[i] == actual_counts[i]
