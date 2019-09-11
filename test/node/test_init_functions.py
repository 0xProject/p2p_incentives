"""
This module contains test functions for peer and order initialization functions.
"""

from typing import Set
import pytest

from message import Order
from node import Peer

from ..__init__ import (
    create_a_test_order,
    create_test_orders,
    create_a_test_peer,
    SCENARIO_SAMPLE,
    ENGINE_SAMPLE,
)


@pytest.mark.parametrize("scenario", [(SCENARIO_SAMPLE)])
def test_order(scenario) -> None:
    """
    This function tests order initialization.
    """
    my_order: Order = create_a_test_order(scenario)
    assert my_order.seq == 5
    assert my_order.birth_time == 12
    assert my_order.scenario.peer_type_property["normal"].ratio == pytest.approx(0.9)
    assert my_order.scenario.peer_type_property["free_rider"].ratio == pytest.approx(
        0.1
    )


@pytest.mark.parametrize("scenario,engine", [(SCENARIO_SAMPLE, ENGINE_SAMPLE)])
def test_peer(scenario, engine) -> None:
    """
    This function tests peer initialization.
    """

    # Arrange and Act.
    my_peer, order_set = create_a_test_peer(scenario, engine)

    # Assert.

    # assert my_peer's attributes.

    assert my_peer.engine == engine
    assert my_peer.seq == 1
    assert my_peer.birth_time == 7
    assert my_peer.init_orderbook_size == 5
    assert my_peer.namespacing is None
    assert my_peer.peer_type == "normal"
    assert my_peer.is_free_rider is False

    # assert of my_peer has changed the creator of initial orders.
    for order in order_set:
        assert order.creator == my_peer

    # assert my_peer's storage for order and orderinfo
    assert my_peer.new_order_set == order_set

    assert len(my_peer.order_orderinfo_mapping) == 5
    for order in order_set:
        orderinfo = my_peer.order_orderinfo_mapping[order]
        assert orderinfo.engine == engine
        assert orderinfo.arrival_time == my_peer.birth_time
        assert orderinfo.prev_owner is None
        assert orderinfo.novelty == 0
        assert orderinfo.priority is None
        assert orderinfo.storage_decision is True

    assert my_peer.peer_neighbor_mapping == {}
    assert my_peer.order_pending_orderinfo_mapping == {}

    # assert order instance's record

    for order in order_set:
        assert order.holders == {my_peer}


@pytest.mark.parametrize("scenario,engine", [(SCENARIO_SAMPLE, ENGINE_SAMPLE)])
def test_peer__free_rider_with_orders(scenario, engine) -> None:
    """
    This function tests creating a free rider with its own orders.
    Should raise an error.
    """
    # manually create 5 orders for this peer.
    order_set: Set[Order] = set(create_test_orders(scenario, 5))

    # create the peer instance
    with pytest.raises(
        ValueError, match="Free riders should not have their own orders."
    ):
        Peer(
            engine=engine,
            seq=0,
            birth_time=6,
            init_orders=order_set,
            namespacing=None,
            peer_type="free_rider",
        )
