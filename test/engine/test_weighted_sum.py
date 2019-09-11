"""
This module test weighted_sum().

In fact, I think I'll need to re-write weighted_sum() by splitting the operations on calculating the
scores and deleting inactive neighbors. However, revising it will lead to changes in node.py,
engine.py and single_run.py. I will do it in a future PR.
"""

# HACK (weijiewu8): Need to change this test when weighted_sum() is re-written

from typing import List
from collections import deque
import pytest
from node import Peer, Neighbor
import engine_candidates


from .__init__ import (
    create_a_test_peer,
    create_test_peers,
    ENGINE_SAMPLE,
    SCENARIO_SAMPLE,
)


@pytest.mark.parametrize("scenario,engine", [(SCENARIO_SAMPLE, ENGINE_SAMPLE)])
def test_weighted_sum(scenario, engine):
    """
    Test function for weighted_sum()
    In here we test everything for the current weighted_sum(): calculating scores and deleting
    neighbors.
    """

    # Arrange.

    # Create peers and neighbors
    peer: Peer = create_a_test_peer(scenario, engine)[0]
    neighbor_list: List[Peer] = create_test_peers(scenario, engine, 2)
    neighbor_instance_list: List[Neighbor] = list()
    for neighbor_peer in neighbor_list:
        peer.add_neighbor(neighbor_peer)
        neighbor_peer.add_neighbor(peer)
        neighbor_instance_list.append(peer.peer_neighbor_mapping[neighbor_peer])

    # Set neighbors lazy record. Neighbor 0's lazy_round will be reset to 0 after this round,
    # but neighbor 1's lazy_round will increase by 1, and reach 6.
    neighbor_instance_list[0].lazy_round = 4
    neighbor_instance_list[1].lazy_round = 5
    neighbor_instance_list[0].share_contribution = deque([0, 0, 7])
    neighbor_instance_list[1].share_contribution = deque([1, 2, 0])

    weights: List[float] = [1.0, 0.5, 0.25]

    # Act.
    # Scores will be calculated.
    # Neighbor 1 will be deleted.
    engine_candidates.weighted_sum(
        lazy_contribution=2, lazy_length=6, discount=weights, peer=peer
    )

    # Assert.
    # Neighbor 0 is still there and its score is the weighted sum.
    assert neighbor_instance_list[0] in peer.peer_neighbor_mapping.values()
    assert neighbor_instance_list[0].score == pytest.approx(7 / 4)
    # Neighbor 1 is deleted.
    assert neighbor_instance_list[1] not in peer.peer_neighbor_mapping.values()
