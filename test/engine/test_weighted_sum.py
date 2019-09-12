"""
This module contains unit tests of weighted_sum().
"""

from typing import List, Tuple
from collections import deque
import pytest
from node import Peer, Neighbor
import engine_candidates
from scenario import Scenario
from engine import Engine


from ..__init__ import (
    create_a_test_peer,
    create_test_peers,
    ENGINE_SAMPLE,
    SCENARIO_SAMPLE,
)


def create_a_peer_and_two_neighbors_helper(
    scenario: Scenario, engine: Engine
) -> Tuple[Peer, List[Peer], List[Neighbor]]:
    """
    This is a helper function to create a peer and two neighbors.
    :return: A tuple: this peer, list of two neighbors (as peer instances),
    list of two neighbors (as neighbor instances)
    """
    peer: Peer = create_a_test_peer(scenario, engine)[0]
    neighbor_list: List[Peer] = create_test_peers(scenario, engine, 2)
    neighbor_instance_list: List[Neighbor] = list()
    for neighbor_peer in neighbor_list:
        peer.add_neighbor(neighbor_peer)
        neighbor_peer.add_neighbor(peer)
        neighbor_instance_list.append(peer.peer_neighbor_mapping[neighbor_peer])

    return peer, neighbor_list, neighbor_instance_list


@pytest.mark.parametrize("scenario,engine", [(SCENARIO_SAMPLE, ENGINE_SAMPLE)])
def test_weighted_sum(scenario: Scenario, engine: Engine):
    """
    Unit test of weighted_sum().
    In here we test everything for the current weighted_sum(): calculating scores and deleting
    neighbors.
    """

    # Arrange.

    peer, _, neighbor_instance_list = create_a_peer_and_two_neighbors_helper(
        scenario, engine
    )

    neighbor_instance_list[0].share_contribution = deque([0, 0, 7])
    neighbor_instance_list[1].share_contribution = deque([1, 2, 0])

    weights: List[float] = [1.0, 0.5, 0.25]

    # Act.
    engine_candidates.weighted_sum(discount=weights, peer=peer)

    # Assert.
    assert neighbor_instance_list[0].score == pytest.approx(7 / 4)
    assert neighbor_instance_list[1].score == pytest.approx(2)
