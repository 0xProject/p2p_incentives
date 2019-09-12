"""
This module contains unit tests of receive_order_internal().
"""

from typing import List
import pytest

from node import Peer
from message import Order
from ..__init__ import (
    create_test_peers,
    create_a_test_order,
    SCENARIO_SAMPLE,
    ENGINE_SAMPLE,
)


@pytest.mark.parametrize("scenario,engine", [(SCENARIO_SAMPLE, ENGINE_SAMPLE)])
def test_receive_order_internal__from_non_neighbor(scenario, engine):
    """
    This tests receiving an internal order from a non-neighbor. Error expeceted.
    """

    # Arrange.
    peer_list: List[Peer] = create_test_peers(scenario, engine, 2)
    order: Order = create_a_test_order(scenario)
    peer_list[1].receive_order_external(order)
    peer_list[1].store_orders()

    # Act and Assert.
    with pytest.raises(ValueError, match="Receiving order from non-neighbor."):
        peer_list[0].receive_order_internal(peer_list[1], order)


@pytest.mark.parametrize("scenario,engine", [(SCENARIO_SAMPLE, ENGINE_SAMPLE)])
def test_receive_order_internal__normal(scenario, engine):
    """
    This tests receiving an internal order normally.
    """

    # Arrange.
    peer_list: List[Peer] = create_test_peers(scenario, engine, 2)
    peer_list[0].add_neighbor(peer_list[1])
    peer_list[1].add_neighbor(peer_list[0])
    order: Order = create_a_test_order(scenario)
    peer_list[1].receive_order_external(order)
    peer_list[1].store_orders()

    # Act.
    peer_list[0].receive_order_internal(peer_list[1], order)

    # Assert.
    assert order in peer_list[0].order_pending_orderinfo_mapping


@pytest.mark.parametrize("scenario,engine", [(SCENARIO_SAMPLE, ENGINE_SAMPLE)])
def test_receive_order_internal_not_accepted(scenario, engine, monkeypatch):
    """
    This tests receiving an internal order labeled as not to accept by the receiver.
    """

    # Arrange.
    # Changes the decision of accepting an internal order from always yes to always no.
    def fake_should_accept_internal_order(_receiver, _sender, _order):
        return False

    monkeypatch.setattr(
        engine, "should_accept_internal_order", fake_should_accept_internal_order
    )

    # Same as the test above.
    peer_list: List[Peer] = create_test_peers(scenario, engine, 2)
    peer_list[0].add_neighbor(peer_list[1])
    peer_list[1].add_neighbor(peer_list[0])
    order: Order = create_a_test_order(scenario)
    peer_list[1].receive_order_external(order)
    peer_list[1].store_orders()

    # Act.
    peer_list[0].receive_order_internal(peer_list[1], order)

    # Assert. Now it should not be accepted.
    assert order not in peer_list[0].order_pending_orderinfo_mapping


@pytest.mark.parametrize("scenario,engine", [(SCENARIO_SAMPLE, ENGINE_SAMPLE)])
def test_receive_order_internal_duplicate_from_same_neighbor(scenario, engine):
    """
    This tests receiving the same internal order from the neighbor multiple times.
    """

    # Arrange.
    peer_list: List[Peer] = create_test_peers(scenario, engine, 2)
    peer_list[0].add_neighbor(peer_list[1])
    peer_list[1].add_neighbor(peer_list[0])
    order: Order = create_a_test_order(scenario)
    peer_list[1].receive_order_external(order)
    peer_list[1].store_orders()

    # Act.
    peer_list[0].receive_order_internal(peer_list[1], order)
    peer_list[0].receive_order_internal(peer_list[1], order)

    # Assert.
    assert len(peer_list[0].order_pending_orderinfo_mapping[order]) == 1


@pytest.mark.parametrize("scenario,engine", [(SCENARIO_SAMPLE, ENGINE_SAMPLE)])
def test_receive_order_internal_duplicate_from_others(scenario, engine):
    """
    This tests receiving the same internal order from different neighbors for multiple times.
    """

    # Arrange.
    peer_list: List[Peer] = create_test_peers(scenario, engine, 3)
    order: Order = create_a_test_order(scenario)
    for neighbor in peer_list[1:3]:
        peer_list[0].add_neighbor(neighbor)
        neighbor.add_neighbor(peer_list[0])
        neighbor.receive_order_external(order)
        neighbor.store_orders()

    # Act.
    for neighbor in peer_list[1:3]:
        peer_list[0].receive_order_internal(neighbor, order)

    # Assert. Both copies should be in the pending table.
    assert len(peer_list[0].order_pending_orderinfo_mapping[order]) == 2
