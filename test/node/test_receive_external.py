"""
This module contains unit tests of receive_order_external().
"""

import pytest
from node import Peer
from message import Order
from ..__init__ import (
    SCENARIO_SAMPLE,
    ENGINE_SAMPLE,
    create_a_test_peer,
    create_a_test_order,
)


@pytest.mark.parametrize("scenario,engine", [(SCENARIO_SAMPLE, ENGINE_SAMPLE)])
def test_receive_order_external__normal(scenario, engine) -> None:
    """
    normal case
    """

    # Arrange.
    peer: Peer = create_a_test_peer(scenario, engine)[0]
    order: Order = create_a_test_order(scenario)

    # Act.
    peer.receive_order_external(order)

    # Assert.
    assert order in peer.order_pending_orderinfo_mapping
    assert order not in peer.order_orderinfo_mapping
    assert peer in order.hesitators


@pytest.mark.parametrize("scenario,engine", [(SCENARIO_SAMPLE, ENGINE_SAMPLE)])
def test_receive_order_external__not_accepted(scenario, engine, monkeypatch) -> None:
    """
    The order is set to not be accepted.
    """

    # Arrange:

    # Change the should_accept_external_order() implementation to a fake one that
    # does not accept any external order.

    def fake_should_accept_external_order(_receiver, _order):
        return False

    monkeypatch.setattr(
        engine, "should_accept_external_order", fake_should_accept_external_order
    )

    peer: Peer = create_a_test_peer(scenario, engine)[0]
    order: Order = create_a_test_order(scenario)

    # Act: peer tries to receive order from external
    peer.receive_order_external(order)

    # Assert: should not accept the order.
    assert order not in peer.order_pending_orderinfo_mapping
    assert peer not in order.hesitators


@pytest.mark.parametrize("scenario,engine", [(SCENARIO_SAMPLE, ENGINE_SAMPLE)])
def test_receive_order_external__duplicate_pending(scenario, engine) -> None:
    """
    Test receiving duplicate external orders (already in pending table)
    """

    # Arrange

    peer: Peer = create_a_test_peer(scenario, engine)[0]
    order: Order = create_a_test_order(scenario)
    peer.receive_order_external(order)

    # Act and Assert.
    with pytest.raises(ValueError, match="Duplicated external order in pending table."):
        peer.receive_order_external(order)


@pytest.mark.parametrize("scenario,engine", [(SCENARIO_SAMPLE, ENGINE_SAMPLE)])
def test_receive_order_external__duplicate_storage(scenario, engine) -> None:
    """
    Test receiving duplicate external orders (already in storage)
    """

    # Arrange

    peer: Peer = create_a_test_peer(scenario, engine)[0]
    order: Order = create_a_test_order(scenario)
    peer.receive_order_external(order)
    peer.send_orders_to_on_chain_check(peer.local_clock)
    peer.store_orders()

    # Act and Assert.
    with pytest.raises(ValueError, match="Duplicated external order in local storage."):
        peer.receive_order_external(order)
