"""
This module contains unit tests of peer_arrival().
"""

import pytest

from scenario import Scenario
from engine import Engine
from performance import Performance
from node import Peer

from single_run import SingleRun
from ..__init__ import SCENARIO_SAMPLE, ENGINE_SAMPLE, PERFORMANCE_SAMPLE


@pytest.mark.parametrize(
    "scenario, engine, performance",
    [(SCENARIO_SAMPLE, ENGINE_SAMPLE, PERFORMANCE_SAMPLE)],
)
def test_peer_arrival__normal(
    scenario: Scenario, engine: Engine, performance: Performance
) -> None:
    """
    This function tests peer_arrival() for a normal peer.
    """

    # Arrange.
    single_run_instance = SingleRun(scenario, engine, performance)

    # Act.
    order_number = 20
    single_run_instance.peer_arrival("normal", {"default": order_number})

    # Assert.

    # Only one peer is added
    assert len(single_run_instance.peer_full_set) == 1
    assert len(single_run_instance.peer_type_set_mapping["normal"]) == 1
    peer: Peer = single_run_instance.peer_full_set.pop()

    # Assert the peer properties
    assert peer.peer_type == "normal"
    assert len(peer.order_orderinfo_mapping) == order_number
    for order in peer.order_orderinfo_mapping:
        assert order.creator == peer

    # Assert the sequence numbers.
    assert single_run_instance.latest_peer_seq == 1
    assert single_run_instance.latest_order_seq == order_number


@pytest.mark.parametrize(
    "scenario, engine, performance",
    [(SCENARIO_SAMPLE, ENGINE_SAMPLE, PERFORMANCE_SAMPLE)],
)
def test_peer_arrival__free_rider(
    scenario: Scenario, engine: Engine, performance: Performance
) -> None:
    """
    This function tests peer_arrival() for a free rider.
    """

    # Arrange.
    single_run_instance = SingleRun(scenario, engine, performance)

    # Act.
    single_run_instance.peer_arrival("free_rider", {})

    # Assert.

    # Only one peer is added
    assert len(single_run_instance.peer_full_set) == 1
    assert len(single_run_instance.peer_type_set_mapping["free_rider"]) == 1
    peer: Peer = single_run_instance.peer_full_set.pop()

    # Assert the peer properties
    assert peer.peer_type == "free_rider"
    assert not peer.order_orderinfo_mapping

    # Assert the sequence numbers.
    assert single_run_instance.latest_peer_seq == 1
    assert single_run_instance.latest_order_seq == 0


@pytest.mark.parametrize(
    "scenario, engine, performance",
    [(SCENARIO_SAMPLE, ENGINE_SAMPLE, PERFORMANCE_SAMPLE)],
)
def test_peer_arrival__free_rider_error(
    scenario: Scenario, engine: Engine, performance: Performance
) -> None:
    """
    This function tests peer_arrival() for a free rider.
    """

    # Arrange.
    single_run_instance = SingleRun(scenario, engine, performance)

    # Act and Assert
    with pytest.raises(ValueError, match="Free riders do not have orders."):
        single_run_instance.peer_arrival("free_rider", {"default": 1})
