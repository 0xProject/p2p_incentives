"""
This module contains test functions for share_order() function.
"""

import random
from typing import List
import pytest

from node import Peer
from .__init__ import (
    create_test_peers,
    create_a_test_peer,
    SCENARIO_SAMPLE,
    ENGINE_SAMPLE,
)


@pytest.mark.parametrize("scenario,engine", [(SCENARIO_SAMPLE, ENGINE_SAMPLE)])
def test_share_orders__normal(scenario, engine, monkeypatch) -> None:
    """
    This function tests share_orders(). It mocks find_orders_to_share() and
    find_neighbors_to_share() function by only selecting orders/peers with sequence number less
    than 100.
    """

    # Arrange.

    # mock the method of find orders/peers to share

    def mock_find_orders_to_share(peer):
        return set(
            any_order
            for any_order in peer.order_orderinfo_mapping
            if any_order.seq < 100
        )

    def mock_find_neighbors_to_share(_time_now, peer):
        return set(
            any_peer for any_peer in peer.peer_neighbor_mapping if any_peer.seq < 100
        )

    monkeypatch.setattr(engine, "find_orders_to_share", mock_find_orders_to_share)
    monkeypatch.setattr(engine, "find_neighbors_to_share", mock_find_neighbors_to_share)

    # peer is a normal peer. We will add three neighbors for it.
    # We will change the sequence number of neighbor 2 and one of the initial orders of the peer

    peer, order_set = create_a_test_peer(scenario, engine)

    neighbor_list = create_test_peers(scenario, engine, 3)
    neighbor_list[2].seq = 101

    unlucky_order = random.sample(order_set, 1)[0]
    unlucky_order.seq = 280

    for neighbor in neighbor_list:
        peer.add_neighbor(neighbor)
        neighbor.add_neighbor(peer)

    # Act.

    order_sharing_set, beneficiary_set = peer.share_orders()

    # Assert.
    assert len(beneficiary_set) == 2 and neighbor_list[2] not in beneficiary_set
    assert len(order_sharing_set) == 4 and unlucky_order not in order_sharing_set
    assert peer.new_order_set == set()


@pytest.mark.parametrize("scenario,engine", [(SCENARIO_SAMPLE, ENGINE_SAMPLE)])
def test_share_orders__free_rider(scenario, engine) -> None:
    """
    Test sharing behavior of a free rider. Should not share anything.
    """

    # Arrange.
    free_rider: Peer = create_a_test_peer(scenario, engine)[0]
    free_rider.is_free_rider = True

    # Give the free rider three neighbors
    neighbor_list: List[Peer] = create_test_peers(scenario, engine, 3)
    for neighbor in neighbor_list:
        free_rider.add_neighbor(neighbor)
        neighbor.add_neighbor(free_rider)

    # Act and Assert.
    assert free_rider.share_orders() == (set(), set())
