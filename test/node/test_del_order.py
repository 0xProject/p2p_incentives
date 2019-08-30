"""
This module contains functions to test del_order().
"""
from typing import List
import pytest

from node import Peer
from message import Order

from .__init__ import (
    SCENARIO_SAMPLE,
    ENGINE_SAMPLE,
    create_test_peers,
    create_test_orders,
    create_a_test_peer,
    create_a_test_order,
)


@pytest.mark.parametrize("scenario,engine", [(SCENARIO_SAMPLE, ENGINE_SAMPLE)])
def test_del_order__in_storage(scenario, engine) -> None:
    """
    This function tests del_orders() when order is in local storage.
    """

    # Arrange.

    # create peer
    my_peer: Peer = create_a_test_peer(scenario, engine)[0]
    # create new orders
    new_order: Order = create_a_test_order(scenario)

    # my_peer receives an external order and stores it.
    my_peer.receive_order_external(new_order)
    my_peer.store_orders()

    # Act.
    my_peer.del_order(new_order)

    # Assert.
    assert new_order not in my_peer.order_orderinfo_mapping


@pytest.mark.parametrize("scenario,engine", [(SCENARIO_SAMPLE, ENGINE_SAMPLE)])
def test_del_order__in_pending_table(scenario, engine) -> None:
    """
    This function tests del_orders() when orders are in pending table.
    """

    # Arrange.

    # create peers.
    peer_list: List[Peer] = create_test_peers(scenario, engine, 3)
    my_peer: Peer = peer_list[0]
    neighbor_one: Peer = peer_list[1]
    neighbor_two: Peer = peer_list[2]

    # create new orders
    new_order_list: List[Order] = create_test_orders(scenario, 2)

    # add neighbors
    my_peer.add_neighbor(neighbor_one)
    my_peer.add_neighbor(neighbor_two)
    neighbor_one.add_neighbor(my_peer)
    neighbor_two.add_neighbor(my_peer)

    # both new_order_list[0] and new_order_list[1] will be put into both neighbor's local
    # storage, for new_order_list[0], my_peer will receive from both neighbors,
    # but for new_order_list[1], it will only receive from neighbor_one

    for neighbor in [neighbor_one, neighbor_two]:
        for new_order in (new_order_list[0], new_order_list[1]):
            neighbor.receive_order_external(new_order)
            neighbor.store_orders()

    my_peer.receive_order_internal(neighbor_one, new_order_list[0])
    my_peer.receive_order_internal(neighbor_two, new_order_list[0])
    my_peer.receive_order_internal(neighbor_one, new_order_list[1])

    # Now, my_peer's pending table should look like
    # {new_order_list[0]: [orderinfo_from_neighbor_1, orderinfo_from_neighbor_2],
    #  new_order_list[1]: [orderinfo_from_neighbor_1]}

    # Act.
    # delete all new orders
    my_peer.del_order(new_order_list[0])
    my_peer.del_order(new_order_list[1])

    # Assert.
    assert new_order_list[0] not in my_peer.order_pending_orderinfo_mapping
    assert new_order_list[1] not in my_peer.order_pending_orderinfo_mapping


@pytest.mark.parametrize("scenario,engine", [(SCENARIO_SAMPLE, ENGINE_SAMPLE)])
def test_del_order__not_existing(scenario, engine) -> None:
    """
    This function tests del_orders() when the peer does not have this order.
    According to our design, nothing will happen under this case.
    """

    # Arrange.
    # create peers.
    my_peer: Peer = create_a_test_peer(scenario, engine)[0]
    # create an order
    new_order: Order = create_a_test_order(scenario)

    # Act.
    # Delete the new order
    my_peer.del_order(new_order)

    # Assert.
    # No error should be raised.
    assert new_order not in my_peer.order_pending_orderinfo_mapping
    assert new_order not in my_peer.order_orderinfo_mapping
