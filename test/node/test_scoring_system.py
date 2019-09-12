"""
This module tests the scoring system for neighbors to contribute. Score changes happen in
receive_order_internal() and store_orders(), but it is difficult to cover all cases when
tests of these two functions are focused on other perspectives.
So we decided to have an individual test function for the score updates.
"""

import pytest

from message import Order
from node import Peer
from ..__init__ import (
    SCENARIO_SAMPLE,
    ENGINE_SAMPLE,
    create_a_test_order,
    create_a_test_peer,
)


def always_store_orders(peer):
    """
    This is a fake function for store_or_discard_orders(), and it always store orders.
    """
    for orderinfo_list in peer.order_pending_orderinfo_mapping.values():
        for orderinfo in orderinfo_list:
            orderinfo.storage_decision = True


@pytest.mark.parametrize("scenario,engine", [(SCENARIO_SAMPLE, ENGINE_SAMPLE)])
def test_scoring_system_penalty_a(scenario, engine, monkeypatch) -> None:
    """
    This function tests the case for penalty_a
    """
    # Setting for this case:
    # Order does not pass should_accept_internal_order()
    # Order rejected since it doesn't pass should_accept_internal_order() (penalty_a).

    # Arrange.

    my_peer: Peer = create_a_test_peer(scenario, engine)[0]
    neighbor: Peer = create_a_test_peer(scenario, engine)[0]
    order: Order = create_a_test_order(scenario)

    # establish neighborhood
    my_peer.add_neighbor(neighbor)
    neighbor.add_neighbor(my_peer)

    # let neighbor own the order that it should have
    neighbor.receive_order_external(order)
    neighbor.store_orders()

    # clear score sheet for neighbors
    my_peer.peer_neighbor_mapping[neighbor].share_contribution[-1] = 0

    # define fake functions.
    # always store orders
    monkeypatch.setattr(engine, "store_or_discard_orders", always_store_orders)

    # Order cannot be accepted to the pending list
    def never_accept_internal_order(_receiver, _sender, _order):
        return False

    monkeypatch.setattr(
        engine, "should_accept_internal_order", never_accept_internal_order
    )

    # Act.

    # neighbor sends the order to my_peer
    my_peer.receive_order_internal(neighbor, order)
    # store orders
    my_peer.store_orders()
    # calculate scores. The value equals to the last entry of the score sheet.
    my_peer.rank_neighbors()

    # Assert.
    assert my_peer.peer_neighbor_mapping[neighbor].score == -13


@pytest.mark.parametrize("scenario,engine", [(SCENARIO_SAMPLE, ENGINE_SAMPLE)])
def test_scoring_system_reward_a(scenario, engine, monkeypatch) -> None:
    """
    This function tests the case for reward_a
    """

    # Setting for this case:
    # my_peer's initial status:
    # Local storage: there is an Order instance from the same neighbor
    # Behavior: neighbor sends order to my_peer
    # Result: Order rejected since there's a duplicate in local storage from the same neighbor (
    # reward_a).

    # Arrange.

    my_peer: Peer = create_a_test_peer(scenario, engine)[0]
    neighbor: Peer = create_a_test_peer(scenario, engine)[0]
    order: Order = create_a_test_order(scenario)

    # establish neighborhood
    my_peer.add_neighbor(neighbor)
    neighbor.add_neighbor(my_peer)

    # let neighbor own the order that it should have
    neighbor.receive_order_external(order)
    neighbor.store_orders()

    # setup the initial status for my_peer
    my_peer.receive_order_internal(neighbor, order)
    my_peer.store_orders()

    # clear score sheet for neighbor
    my_peer.peer_neighbor_mapping[neighbor].share_contribution[-1] = 0

    # always store orders
    monkeypatch.setattr(engine, "store_or_discard_orders", always_store_orders)

    # Act.

    # neighbor sends the order to my_peer
    my_peer.receive_order_internal(neighbor, order)
    # store orders
    my_peer.store_orders()
    # calculate scores. The value equals to the last entry of the score sheet.
    my_peer.rank_neighbors()

    # Assert.
    assert my_peer.peer_neighbor_mapping[neighbor].score == 2


@pytest.mark.parametrize("scenario,engine", [(SCENARIO_SAMPLE, ENGINE_SAMPLE)])
def test_scoring_system_reward_b(scenario, engine, monkeypatch) -> None:
    """
    This function tests the case for reward_b
    """

    # Setting for this case:
    # my_peer's initial status:
    # Local storage: there is an Order instance from the competitor.
    # Behavior: neighbor sends order to my_peer
    # Result: Order rejected since there's a duplicate in local storage from competitor \(
    # reward_b).

    # Arrange.

    my_peer: Peer = create_a_test_peer(scenario, engine)[0]
    neighbor: Peer = create_a_test_peer(scenario, engine)[0]
    competitor: Peer = create_a_test_peer(scenario, engine)[0]
    order: Order = create_a_test_order(scenario)

    # establish neighborhood
    for anyone in (neighbor, competitor):
        my_peer.add_neighbor(anyone)
        anyone.add_neighbor(my_peer)

    # let neighbor and competitor own the order that it should have
    for anyone in (neighbor, competitor):
        anyone.receive_order_external(order)
        anyone.store_orders()

    # setup the initial status for my_peer
    my_peer.receive_order_internal(competitor, order)
    my_peer.store_orders()

    # clear score sheet for neighbor
    my_peer.peer_neighbor_mapping[neighbor].share_contribution[-1] = 0

    # Always store orders
    monkeypatch.setattr(engine, "store_or_discard_orders", always_store_orders)

    # Act.

    # neighbor sends the order to my_peer
    my_peer.receive_order_internal(neighbor, order)
    # store orders
    my_peer.store_orders()
    # calculate scores. The value equals to the last entry of the score sheet.
    my_peer.rank_neighbors()

    # Assert.
    assert my_peer.peer_neighbor_mapping[neighbor].score == 3


@pytest.mark.parametrize("scenario,engine", [(SCENARIO_SAMPLE, ENGINE_SAMPLE)])
def test_scoring_system_penalty_b(scenario, engine, monkeypatch) -> None:
    """
    This function tests the case for penalty_b
    """

    # Setting for this case:
    # my_peer's initial status:
    # Pending table: there is an Order instance from the same neighbor
    # Behavior: neighbor sends order to my_peer
    # Result: The second copy rejected since there's a duplicate in pending table from the same
    # neighbor (penalty_b); however, the first version will be stored finally (reward_d)

    # Arrange.

    my_peer: Peer = create_a_test_peer(scenario, engine)[0]
    neighbor: Peer = create_a_test_peer(scenario, engine)[0]
    order: Order = create_a_test_order(scenario)

    # establish neighborhood
    my_peer.add_neighbor(neighbor)
    neighbor.add_neighbor(my_peer)

    # let neighbor own the order that it should have
    neighbor.receive_order_external(order)
    neighbor.store_orders()

    # setup the initial status for my_peer
    my_peer.receive_order_internal(neighbor, order)

    # clear score sheet for neighbor
    my_peer.peer_neighbor_mapping[neighbor].share_contribution[-1] = 0

    # Always store orders
    monkeypatch.setattr(engine, "store_or_discard_orders", always_store_orders)

    # Act.

    # neighbor sends the order to my_peer
    my_peer.receive_order_internal(neighbor, order)
    # store orders
    my_peer.store_orders()
    # calculate scores. The value equals to the last entry of the score sheet.
    my_peer.rank_neighbors()

    # Assert.

    assert my_peer.peer_neighbor_mapping[neighbor].score == -10


@pytest.mark.parametrize("scenario,engine", [(SCENARIO_SAMPLE, ENGINE_SAMPLE)])
def test_scoring_system_reward_c(scenario, engine, monkeypatch) -> None:
    """
    This function tests the case for reward_c
    """
    # Setting for this case:
    # Order passes should_accept_internal_order() but storage_decision is False
    # Order accepted to pending table, rejected to storage, and gets reward_c

    # Arrange.

    my_peer: Peer = create_a_test_peer(scenario, engine)[0]
    neighbor: Peer = create_a_test_peer(scenario, engine)[0]
    order: Order = create_a_test_order(scenario)

    # establish neighborhood
    my_peer.add_neighbor(neighbor)
    neighbor.add_neighbor(my_peer)

    # let neighbor own the order that it should have
    neighbor.receive_order_external(order)
    neighbor.store_orders()

    # clear score sheet for neighbors
    my_peer.peer_neighbor_mapping[neighbor].share_contribution[-1] = 0

    # define fake functions.

    # This fake function sets storage_decision as False for any orderinfo.
    def never_store_orders(peer):
        for orderinfo_list in peer.order_pending_orderinfo_mapping.values():
            for orderinfo in orderinfo_list:
                orderinfo.storage_decision = False

    monkeypatch.setattr(engine, "store_or_discard_orders", never_store_orders)

    # Act.

    # neighbor sends the order to my_peer
    my_peer.receive_order_internal(neighbor, order)
    # store orders
    my_peer.store_orders()
    # calculate scores. The value equals to the last entry of the score sheet.
    my_peer.rank_neighbors()

    # Assert.

    assert my_peer.peer_neighbor_mapping[neighbor].score == 5


@pytest.mark.parametrize("scenario,engine", [(SCENARIO_SAMPLE, ENGINE_SAMPLE)])
def test_scoring_system_reward_d(scenario, engine, monkeypatch) -> None:
    """
    This function tests the case for reward_d
    """

    # Setting for this case:
    # my_peer's initial status:
    # Pending table: there is a pending orderinfo instance from the competitor.
    # Behavior: neighbor sends order to my_peer
    # Result: Order from neighbor stored since neighbor won over competitor (reward_d).

    # Arrange.

    my_peer: Peer = create_a_test_peer(scenario, engine)[0]
    neighbor: Peer = create_a_test_peer(scenario, engine)[0]
    competitor: Peer = create_a_test_peer(scenario, engine)[0]
    order: Order = create_a_test_order(scenario)

    # establish neighborhood
    for anyone in (neighbor, competitor):
        my_peer.add_neighbor(anyone)
        anyone.add_neighbor(my_peer)

    # let neighbor and competitor own the order that it should have
    for anyone in (neighbor, competitor):
        anyone.receive_order_external(order)
        anyone.store_orders()

    # setup the initial status for my_peer
    my_peer.receive_order_internal(competitor, order)

    # clear score sheet for neighbor
    my_peer.peer_neighbor_mapping[neighbor].share_contribution[-1] = 0

    # define fake functions.

    # This fake function sets storage_decision as True for orderinfo from neighbor and False
    # from competitor.
    def fake_store_or_discard_orders(peer):
        for orderinfo_list in peer.order_pending_orderinfo_mapping.values():
            for orderinfo in orderinfo_list:
                if orderinfo.prev_owner == neighbor:
                    orderinfo.storage_decision = True
                else:
                    orderinfo.storage_decision = False

    monkeypatch.setattr(engine, "store_or_discard_orders", fake_store_or_discard_orders)

    # Act.

    # neighbor sends the order to my_peer
    my_peer.receive_order_internal(neighbor, order)
    # store orders
    my_peer.store_orders()
    # calculate scores. The value equals to the last entry of the score sheet.
    my_peer.rank_neighbors()

    # Assert.
    assert my_peer.peer_neighbor_mapping[neighbor].score == 7


@pytest.mark.parametrize("scenario,engine", [(SCENARIO_SAMPLE, ENGINE_SAMPLE)])
def test_scoring_system_reward_e(scenario, engine, monkeypatch) -> None:
    """
    This function tests the case for reward_d
    """

    # Setting for this case:
    # my_peer's initial status:
    # Pending table: there is a pending orderinfo instance from the competitor.
    # Behavior: neighbor sends order to my_peer
    # Result: Order from neighbor not stored since competitor won over neighbor (reward_e).

    # Arrange.

    my_peer: Peer = create_a_test_peer(scenario, engine)[0]
    neighbor: Peer = create_a_test_peer(scenario, engine)[0]
    competitor: Peer = create_a_test_peer(scenario, engine)[0]
    order: Order = create_a_test_order(scenario)

    # establish neighborhood
    for anyone in (neighbor, competitor):
        my_peer.add_neighbor(anyone)
        anyone.add_neighbor(my_peer)

    # let neighbor and competitor own the order that it should have
    for anyone in (neighbor, competitor):
        anyone.receive_order_external(order)
        anyone.store_orders()

    # setup the initial status for my_peer
    my_peer.receive_order_internal(competitor, order)

    # clear score sheet for neighbor
    my_peer.peer_neighbor_mapping[neighbor].share_contribution[-1] = 0

    # define fake functions.

    # This fake function sets storage_decision as True for orderinfo from competitor and
    # False from neighbor.
    def fake_store_or_discard_orders(peer):
        for orderinfo_list in peer.order_pending_orderinfo_mapping.values():
            for orderinfo in orderinfo_list:
                if orderinfo.prev_owner == neighbor:
                    orderinfo.storage_decision = False
                else:
                    orderinfo.storage_decision = True

    monkeypatch.setattr(engine, "store_or_discard_orders", fake_store_or_discard_orders)

    # Act.

    # neighbor sends the order to my_peer
    my_peer.receive_order_internal(neighbor, order)
    # store orders
    my_peer.store_orders()
    # calculate scores. The value equals to the last entry of the score sheet.
    my_peer.rank_neighbors()

    # Assert.

    assert my_peer.peer_neighbor_mapping[neighbor].score == 11
