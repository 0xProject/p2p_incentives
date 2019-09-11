"""
This module contains test functions for should_accept_neighbor_request().
"""

from typing import List
import pytest

from node import Peer
from ..__init__ import (
    SCENARIO_SAMPLE,
    ENGINE_SAMPLE,
    create_a_test_peer,
    create_test_peers,
)


@pytest.mark.parametrize("scenario,engine", [(SCENARIO_SAMPLE, ENGINE_SAMPLE)])
def test_should_accept_neighbor_request__true(scenario, engine) -> None:
    """
    Test when it should return True.
    """

    # Arrange. Create two peers
    peer_list: List[Peer] = create_test_peers(scenario, engine, 2)

    # Act and Assert.
    # Should accept invitation
    assert peer_list[0].should_accept_neighbor_request(peer_list[1]) is True


@pytest.mark.parametrize("scenario,engine", [(SCENARIO_SAMPLE, ENGINE_SAMPLE)])
def test_should_accept_neighbor_request__false(scenario, engine, monkeypatch) -> None:
    """
    Test when it should return False.
    """
    # Arrange.
    # Create three peers. First two are neighbors.
    peer_list: List[Peer] = create_test_peers(scenario, engine, 3)
    peer_list[0].add_neighbor(peer_list[1])
    peer_list[1].add_neighbor(peer_list[0])

    # Fake max neighbor size to 1.
    monkeypatch.setattr(engine, "neighbor_max", 1)

    # Action and Assert.
    # Peer 2 wants to be Peer 0's neighbor. Should reject.
    assert peer_list[0].should_accept_neighbor_request(peer_list[2]) is False


@pytest.mark.parametrize("scenario,engine", [(SCENARIO_SAMPLE, ENGINE_SAMPLE)])
def test_should_accept_neighbor__existing_neighbor(scenario, engine) -> None:
    """
    Requested by an existing neighbor.
    """
    # Arrange.
    # Create three peers. First two are neighbors.
    peer_list: List[Peer] = create_test_peers(scenario, engine, 3)
    peer_list[0].add_neighbor(peer_list[1])
    peer_list[1].add_neighbor(peer_list[0])

    # Act and Assert.
    # when they're already neighbors and a peer still requests, an error should be raised.
    with pytest.raises(ValueError, match="Called by a wrong peer."):
        peer_list[0].should_accept_neighbor_request(peer_list[1])


@pytest.mark.parametrize("scenario,engine", [(SCENARIO_SAMPLE, ENGINE_SAMPLE)])
def test_should_accept_neighbor__self_request(scenario, engine) -> None:
    """
    Requested by itself.
    """

    # Arrange.
    # Create three peers. First two are neighbors.
    peer = create_a_test_peer(scenario, engine)[0]

    # Act and Assert.
    # An error should be raised when receiving a request from self.
    with pytest.raises(ValueError, match="Called by a wrong peer."):
        peer.should_accept_neighbor_request(peer)
