"""
This module contains unit tests for peer_departure().
"""

from typing import Iterator
import pytest

from single_run import SingleRun
from node import Peer
from message import Order
from scenario import Scenario
from engine import Engine
from performance import Performance
from .__init__ import (
    SCENARIO_SAMPLE_1,
    ENGINE_SAMPLE,
    PERFORMANCE_SAMPLE,
    create_a_test_order,
    create_a_test_peer,
)


@pytest.mark.parametrize(
    "scenario, engine, performance",
    [(SCENARIO_SAMPLE_1, ENGINE_SAMPLE, PERFORMANCE_SAMPLE)],
)
def test_peer_departure__normal(
    scenario: Scenario, engine: Engine, performance: Performance
) -> None:
    """
    This is to test peer_departure() in normal case.
    """

    # Arrange.

    # create a single_run instance.
    single_run_instance = SingleRun(scenario, engine, performance)

    # create two peers. One is the peer that will depart, the other is its neighbor.
    single_run_instance.peer_arrival("normal", 0)
    single_run_instance.peer_arrival("normal", 0)

    iterator: Iterator[Peer] = iter(single_run_instance.peer_full_set)
    peer: Peer = next(iterator)
    neighbor: Peer = next(iterator)

    peer.add_neighbor(neighbor)
    neighbor.add_neighbor(peer)

    # Let the peer have one order in pending table and one in storage.
    order_store: Order = create_a_test_order(scenario)
    peer.receive_order_external(order_store)
    peer.store_orders()

    order_pending: Order = create_a_test_order(scenario)
    peer.receive_order_external(order_pending)

    # Act.
    single_run_instance.peer_departure(peer)

    # Assert.
    assert peer not in single_run_instance.peer_full_set
    assert peer not in single_run_instance.peer_type_set_mapping["normal"]
    assert peer not in order_store.holders
    assert peer not in order_pending.hesitators
    assert peer not in neighbor.peer_neighbor_mapping


@pytest.mark.parametrize(
    "scenario, engine, performance",
    [(SCENARIO_SAMPLE_1, ENGINE_SAMPLE, PERFORMANCE_SAMPLE)],
)
def test_peer_departure__error(
    scenario: Scenario, engine: Engine, performance: Performance
) -> None:
    """
    This is to test peer_departure() when the peer does not exist.
    """

    # Arrange.
    # create a single_run instance.
    single_run_instance = SingleRun(scenario, engine, performance)
    # create a peer
    peer: Peer = create_a_test_peer(scenario, engine)[0]

    # Act and Assert.
    with pytest.raises(ValueError, match="No such peer to depart."):
        single_run_instance.peer_departure(peer)
