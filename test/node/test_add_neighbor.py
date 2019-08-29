"""
This module contains test functions for add_neighbor()
"""

import collections
from typing import List, Deque
import pytest

from node import Peer, Neighbor

from .__init__ import (
    ENGINE_SAMPLE,
    SCENARIO_SAMPLE,
    create_a_test_peer,
    create_test_peers,
)


# Please refer to __init__.py to see the reason of using parametrization.


@pytest.mark.parametrize("scenario,engine", [(SCENARIO_SAMPLE, ENGINE_SAMPLE)])
def test_add_neighbor__normal(scenario, engine) -> None:
    """
    normal cases.
    """

    # Arrange.
    # We have three peers.
    peer_list: List[Peer] = create_test_peers(scenario, engine, 3)

    # Act.

    # add peer_list[1] and peer_list[2] into peer_list[0]'s neighbor.
    peer_list[0].add_neighbor(peer_list[1])
    peer_list[0].add_neighbor(peer_list[2])

    # Assert.

    # assert if the neighbor can be found and if neighbor size is correct.
    assert peer_list[1] in peer_list[0].peer_neighbor_mapping
    assert peer_list[2] in peer_list[0].peer_neighbor_mapping
    assert len(peer_list[0].peer_neighbor_mapping) == 2

    # assert neighbor instance setting
    neighbor: Neighbor = peer_list[0].peer_neighbor_mapping[peer_list[1]]
    assert neighbor.engine == engine
    assert neighbor.est_time == peer_list[0].birth_time
    assert neighbor.preference is None
    expected_score_sheet: Deque = collections.deque()
    for _ in range(engine.score_length):
        expected_score_sheet.append(0.0)
    assert neighbor.share_contribution == expected_score_sheet
    assert neighbor.score == pytest.approx(0.0)
    assert neighbor.lazy_round == 0


@pytest.mark.parametrize("scenario,engine", [(SCENARIO_SAMPLE, ENGINE_SAMPLE)])
def test_add_neighbor__add_an_existing_neighbor(scenario, engine):
    """
    Test if one tries to add an existing neighbor
    """

    # Arrange.
    # We have two peers. Peer 1 is in Peer 0's neighbor.
    peer_list: List[Peer] = create_test_peers(scenario, engine, 2)
    peer_list[0].add_neighbor(peer_list[1])

    # Action and Assert.
    # Should raise an error when adding an existing neighbor.

    with pytest.raises(ValueError, match="Function called by a wrong peer."):
        peer_list[0].add_neighbor(peer_list[1])


@pytest.mark.parametrize("scenario,engine", [(SCENARIO_SAMPLE, ENGINE_SAMPLE)])
def test_add_neighbor__add_self(scenario, engine):
    """
    Test if one tries to add itself as a neighbor
    """
    # Arrange.
    peer: Peer = create_a_test_peer(scenario, engine)[0]

    # Act and Assert.
    # Add self. Should raise an error
    with pytest.raises(ValueError, match="Function called by a wrong peer."):
        peer.add_neighbor(peer)
