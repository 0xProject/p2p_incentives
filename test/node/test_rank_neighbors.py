"""
This module contains unit test of rank_neighbors().
"""

from typing import List
import pytest

from node import Peer
from ..__init__ import SCENARIO_SAMPLE, ENGINE_SAMPLE, create_test_peers


@pytest.mark.parametrize("scenario,engine", [(SCENARIO_SAMPLE, ENGINE_SAMPLE)])
def test_rank_neighbors(scenario, engine) -> None:
    """
    This function tests rank_neighbors().
    """

    # Arrange.

    # create peer list
    peer_list: List[Peer] = create_test_peers(scenario, engine, 4)

    peer_list[0].add_neighbor(peer_list[1])
    peer_list[0].add_neighbor(peer_list[2])
    peer_list[0].add_neighbor(peer_list[3])

    # manually set their scores

    peer_list[0].peer_neighbor_mapping[peer_list[1]].score = 50
    peer_list[0].peer_neighbor_mapping[peer_list[2]].score = 10
    peer_list[0].peer_neighbor_mapping[peer_list[3]].score = 80

    # Act and Assert.

    # assert the return value of rank_neighbors(). Should be a list of peer instances ranked by
    # the score of their corresponding neighbor instances at peer_list[0], from highest to
    # lowest.
    assert peer_list[0].rank_neighbors() == [peer_list[3], peer_list[1], peer_list[2]]
