"""
This module contains unit tests of del_neighbor().

Note: we also need to test the "remove_order" option here. However, in order to test it we
will need to use functions receive_order_internal() and store_orders().
Thus, the test cases with "remove_oder" option turned on depends on the correctness of
receive_order_internal() and store_orders() functions, which we test in separate cases.
"""

from typing import List
import pytest

from message import Order
from node import Peer

from ..__init__ import (
    create_a_test_peer,
    SCENARIO_SAMPLE,
    ENGINE_SAMPLE,
    create_a_test_order,
    create_test_peers,
)


@pytest.mark.parametrize("scenario,engine", [(SCENARIO_SAMPLE, ENGINE_SAMPLE)])
def test_del_neighbor_normal(scenario, engine) -> None:
    """
    normal case.
    """

    # Arrange.
    peer_list: List[Peer] = create_test_peers(scenario, engine, 2)
    peer_list[0].add_neighbor(peer_list[1])
    peer_list[1].add_neighbor(peer_list[0])

    # Act.
    peer_list[0].del_neighbor(peer_list[1])

    # Assert.
    # The deletion should be normal. Both sides should delete the other one.
    assert (
        not peer_list[0].peer_neighbor_mapping
        and not peer_list[1].peer_neighbor_mapping
    )


@pytest.mark.parametrize("scenario,engine", [(SCENARIO_SAMPLE, ENGINE_SAMPLE)])
def test_del_neighbor__non_existing(scenario, engine) -> None:
    """
    Delete non existing neighbor.
    """

    # Arrange.
    peer_list: List[Peer] = create_test_peers(scenario, engine, 2)

    # Act and Assert.
    # Delete an non-existing neighbor
    with pytest.raises(
        ValueError, match="This peer is not my neighbor. Unable to delete."
    ):
        peer_list[0].del_neighbor(peer_list[1])


@pytest.mark.parametrize("scenario,engine", [(SCENARIO_SAMPLE, ENGINE_SAMPLE)])
def test_del_neighbor__self(scenario, engine) -> None:
    """
    Delete itself from neighbor set.
    """

    # Arrange
    peer: Peer = create_a_test_peer(scenario, engine)[0]

    # Act and Assert. Delete self.
    with pytest.raises(
        ValueError, match="This peer is not my neighbor. Unable to delete."
    ):
        peer.del_neighbor(peer)


@pytest.mark.parametrize("scenario,engine", [(SCENARIO_SAMPLE, ENGINE_SAMPLE)])
def test_del_neighbor_with_remove_order__in_storage(scenario, engine) -> None:
    """
    This tests when there is an order from the deleted neighbor in the local storage.
    """

    # Arrange.

    # create my_peer and a neighbor. Later, the neighbor will be deleted.
    my_peer: Peer = create_a_test_peer(scenario, engine)[0]
    neighbor: Peer = create_a_test_peer(scenario, engine)[0]
    my_peer.add_neighbor(neighbor)
    neighbor.add_neighbor(my_peer)

    # we have a new order. Neighbor has it.
    order: Order = create_a_test_order(scenario)
    neighbor.receive_order_external(order)
    # Manually set verification done
    neighbor.send_orders_to_on_chain_check(neighbor.local_clock)
    neighbor.store_orders()

    # my_peer will have the order in local storage, from the neighbor
    my_peer.receive_order_internal(neighbor, order)
    # Manually set verification done
    my_peer.send_orders_to_on_chain_check(my_peer.local_clock)
    my_peer.store_orders()

    # Act.

    # my_peer deletes neighbor and cancels orders from it.
    my_peer.del_neighbor(neighbor, remove_order=True)

    # Assert.

    # Now order should have been deleted from local storage.
    assert order not in my_peer.order_orderinfo_mapping


@pytest.mark.parametrize("scenario,engine", [(SCENARIO_SAMPLE, ENGINE_SAMPLE)])
def test_del_neighbor_with_remove_order__single_pending_orderinfo(
    scenario, engine
) -> None:
    """
    This tests if there is a single orderinfo from the deleted neighbor in the pending table.
    """

    # Arrange.

    # create my_peer and a neighbor. Later, the neighbor will be deleted.
    my_peer: Peer = create_a_test_peer(scenario, engine)[0]
    neighbor: Peer = create_a_test_peer(scenario, engine)[0]
    my_peer.add_neighbor(neighbor)
    neighbor.add_neighbor(my_peer)

    # we have a new order. Neighbor has it.
    order: Order = create_a_test_order(scenario)
    neighbor.receive_order_external(order)
    # Manually set verification done
    neighbor.send_orders_to_on_chain_check(neighbor.local_clock)
    neighbor.store_orders()

    # my_peer will have the order in the pending table, from the neighbor
    my_peer.receive_order_internal(neighbor, order)

    # Act.

    # my_peer deletes neighbor and cancels orders from it.
    my_peer.del_neighbor(neighbor, remove_order=True)

    # Assert.

    # Now order should have been deleted from local storage.
    assert order not in my_peer.order_pending_orderinfo_mapping


@pytest.mark.parametrize("scenario,engine", [(SCENARIO_SAMPLE, ENGINE_SAMPLE)])
def test_del_neighbor_with_remove_order__multi_pending_orderinfo(
    scenario, engine
) -> None:
    """
    Test if there are multiple orderinfos, one from the deleted neighbor, in the pending table.
    """

    # Arrange.

    # create my_peer and neighbors. Later, neighbor_list[0] will be deleted.
    my_peer: Peer = create_a_test_peer(scenario, engine)[0]
    neighbor_list: List[Peer] = create_test_peers(scenario, engine, 2)
    for neighbor in neighbor_list:
        my_peer.add_neighbor(neighbor)
        neighbor.add_neighbor(my_peer)

    # new order.
    order: Order = create_a_test_order(scenario)
    for neighbor in neighbor_list:
        neighbor.receive_order_external(order)
        # Manually set verification done
        neighbor.send_orders_to_on_chain_check(neighbor.local_clock)
        neighbor.store_orders()

    # my_peer also has order in pending table. It has versions from both neighbors.
    for neighbor in neighbor_list:
        my_peer.receive_order_internal(neighbor, order)

    # Act.

    # my_peer deletes neighbor 0 and cancels orders from it.
    my_peer.del_neighbor(neighbor_list[0], remove_order=True)

    # Assert.

    # Now order should still be in the pending table, but the copy is not from neighbor[0]
    assert len(my_peer.order_pending_orderinfo_mapping[order]) == 1
    assert (
        my_peer.order_pending_orderinfo_mapping[order][0].prev_owner == neighbor_list[1]
    )
