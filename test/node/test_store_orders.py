"""
This module contains tests to function store_orders(). We should have these tests before testing
receive_order_internal() because store_order() will be used during the test of
receive_order_internal().
"""

from typing import List
import pytest

from node import Peer
from message import Order, OrderInfo
from ..__init__ import (
    create_a_test_order,
    create_a_test_peer,
    create_test_peers,
    SCENARIO_SAMPLE,
    ENGINE_SAMPLE,
)


@pytest.mark.parametrize("scenario,engine", [(SCENARIO_SAMPLE, ENGINE_SAMPLE)])
def test_store_orders__single_orderinfo(scenario, engine) -> None:
    """
    This one tests the case where an order has a single orderinfo instance in the pending table
    and later, it is put into local storage.
    """
    # Arrange.
    peer: Peer = create_a_test_peer(scenario, engine)[0]
    order: Order = create_a_test_order(scenario)
    peer.receive_order_external(order)

    # Act.
    peer.store_orders()

    # Assert.
    assert order in peer.order_orderinfo_mapping


@pytest.mark.parametrize("scenario,engine", [(SCENARIO_SAMPLE, ENGINE_SAMPLE)])
def test_store_orders__multi_orderinfo(scenario, engine, monkeypatch) -> None:
    """
    This one tests the case where an order has multiple orderinfo instances in the pending table
    and later, one of them is put into local storage.
    """
    # Arrange.

    # Create a peer and a neighbors for this peer. They will be connected.
    peer: Peer = create_a_test_peer(scenario, engine)[0]
    neighbor_list: List[Peer] = create_test_peers(scenario, engine, 2)

    # create an order
    order: Order = create_a_test_order(scenario)

    # neighbors store this order and are connected to peer.
    for neighbor in neighbor_list:
        neighbor.add_neighbor(peer)
        peer.add_neighbor(neighbor)
        neighbor.receive_order_external(order)
        neighbor.store_orders()

    # since receive_order_internal() function has not been tested, we manually put the order
    # into peer's pending table

    for neighbor in neighbor_list:
        orderinfo = OrderInfo(
            engine=engine,
            order=order,
            master=neighbor,
            arrival_time=peer.birth_time,
            priority=None,
            prev_owner=neighbor,
            novelty=0,
        )
        if order not in peer.order_pending_orderinfo_mapping:
            peer.order_pending_orderinfo_mapping[order] = [orderinfo]
        else:
            peer.order_pending_orderinfo_mapping[order].append(orderinfo)
    order.hesitators.add(peer)

    # manually set storage_decisions for the order.
    # Store neighbor_0's orderinfo instance for the order.

    for orderinfo in peer.order_pending_orderinfo_mapping[order]:
        if orderinfo.prev_owner == neighbor_list[0]:
            orderinfo.storage_decision = True
        else:
            orderinfo.storage_decision = False

    # Disable engine.store_or_discard_orders which will otherwise
    # change the values for orderinfo.storage_decision
    def fake_storage_decision(_node):
        pass

    monkeypatch.setattr(engine, "store_or_discard_orders", fake_storage_decision)

    # Act.
    peer.store_orders()

    # Assert.

    # order should have been stored and it is the right version.
    assert peer.order_orderinfo_mapping[order].prev_owner == neighbor_list[0]
    # peer's pending table should have been cleared.
    assert peer.order_pending_orderinfo_mapping == {}


@pytest.mark.parametrize("scenario,engine", [(SCENARIO_SAMPLE, ENGINE_SAMPLE)])
def test_store_orders__do_not_store(scenario, engine, monkeypatch) -> None:
    """
    This one tests the case where an order has orderinfo instance(s) in the pending
    table but later, it is not stored since labeled as not to store.
    """
    # Arrange.

    # Create a peer and a neighbors for this peer. They will be connected.
    peer: Peer = create_a_test_peer(scenario, engine)[0]
    neighbor_list: List[Peer] = create_test_peers(scenario, engine, 2)

    # create an order
    order: Order = create_a_test_order(scenario)

    # neighbors store this order and are connected to peer.
    for neighbor in neighbor_list:
        neighbor.add_neighbor(peer)
        peer.add_neighbor(neighbor)
        neighbor.receive_order_external(order)
        neighbor.store_orders()

    # since receive_order_internal() function has not been tested, we manually put the order
    # into peer's pending table

    for neighbor in neighbor_list:
        orderinfo = OrderInfo(
            engine=engine,
            order=order,
            master=neighbor,
            arrival_time=peer.birth_time,
            priority=None,
            prev_owner=neighbor,
            novelty=0,
        )
        if order not in peer.order_pending_orderinfo_mapping:
            peer.order_pending_orderinfo_mapping[order] = [orderinfo]
        else:
            peer.order_pending_orderinfo_mapping[order].append(orderinfo)
    order.hesitators.add(peer)

    # manually set storage_decisions for the order. All are False.

    for orderinfo in peer.order_pending_orderinfo_mapping[order]:
        orderinfo.storage_decision = False

    # Disable engine.store_or_discard_orders which will otherwise
    # change the values for orderinfo.storage_decision
    def fake_storage_decision(_node):
        pass

    monkeypatch.setattr(engine, "store_or_discard_orders", fake_storage_decision)

    # Act.
    peer.store_orders()

    # Assert.

    # order should have been stored and it is the right version.
    assert order not in peer.order_orderinfo_mapping
    # peer's pending table should have been cleared.
    assert peer.order_pending_orderinfo_mapping == {}


@pytest.mark.parametrize("scenario,engine", [(SCENARIO_SAMPLE, ENGINE_SAMPLE)])
def test_store_orders__sender_disconnected(scenario, engine, monkeypatch) -> None:
    """
    This function tests the case of storing an order from some peer recently disconnected
    (it was a neighbor when sending this order to the peer).
    """

    # Arrange.

    # Create a peer and a neighbor for this peer.
    peer: Peer = create_a_test_peer(scenario, engine)[0]
    neighbor: Peer = create_a_test_peer(scenario, engine)[0]
    neighbor.add_neighbor(peer)
    peer.add_neighbor(neighbor)

    # create an order and the neighbor has this order.
    order: Order = create_a_test_order(scenario)
    neighbor.receive_order_external(order)
    neighbor.store_orders()

    # We manually put the order into peer's pending table

    orderinfo = OrderInfo(
        engine=engine,
        order=order,
        master=neighbor,
        arrival_time=peer.birth_time,
        priority=None,
        prev_owner=neighbor,
        novelty=0,
    )
    peer.order_pending_orderinfo_mapping[order] = [orderinfo]
    order.hesitators.add(peer)

    # manually set storage_decisions for the order.
    orderinfo.storage_decision = True

    # now let us disconnect neighbor_disconnect
    peer.del_neighbor(neighbor)

    # Disable engine.store_or_discard_orders which will otherwise
    # change the values for orderinfo.storage_decision
    def fake_storage_decision(_node):
        pass

    monkeypatch.setattr(engine, "store_or_discard_orders", fake_storage_decision)

    # Act.
    peer.store_orders()

    # Assert.

    # order should have been stored, though the neighbor left.
    assert peer.order_orderinfo_mapping[order].prev_owner == neighbor
    # check peer's pending table. It should have been cleared.
    assert peer.order_pending_orderinfo_mapping == {}


@pytest.mark.parametrize("scenario,engine", [(SCENARIO_SAMPLE, ENGINE_SAMPLE)])
def test_store_orders__multi_orderinfo_error(scenario, engine, monkeypatch) -> None:
    """
    This function tests if an order has multiple orderinfo instances and more than one is
    labeled as to store. In such case an error is expected.
    """

    # Arrange.

    # Create a peer and two neighbors for this peer.
    peer: Peer = create_a_test_peer(scenario, engine)[0]
    neighbor_list: List[Peer] = create_test_peers(scenario, engine, 2)

    # order will have multiple orderinfo instances to store and raise an error
    order: Order = create_a_test_order(scenario)

    for neighbor in neighbor_list:
        # each neighbor receives the orders and becomes the neighbor of the peer.
        neighbor.receive_order_external(order)
        neighbor.store_orders()
        neighbor.add_neighbor(peer)
        peer.add_neighbor(neighbor)

    # since receive_order_internal() function has not been tested, we manually put the order
    # into peer's pending table

    for neighbor in neighbor_list:
        orderinfo = OrderInfo(
            engine=engine,
            order=order,
            master=neighbor,
            arrival_time=peer.birth_time,
            priority=None,
            prev_owner=neighbor,
            novelty=0,
        )
        if order not in peer.order_pending_orderinfo_mapping:
            peer.order_pending_orderinfo_mapping[order] = [orderinfo]
        else:
            peer.order_pending_orderinfo_mapping[order].append(orderinfo)
        order.hesitators.add(peer)

    # manually set storage_decisions for each order as True
    for orderinfo in peer.order_pending_orderinfo_mapping[order]:
        orderinfo.storage_decision = True

    # Disable engine.store_or_discard_orders which will otherwise
    # change the values for orderinfo.storage_decision
    def fake_storage_decision(_node):
        pass

    monkeypatch.setattr(engine, "store_or_discard_orders", fake_storage_decision)

    # Act and Assert.
    with pytest.raises(
        ValueError, match="Should not store multiple copies of same order."
    ):
        peer.store_orders()
