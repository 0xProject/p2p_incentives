"""
We put a helper function in this __init__.py.
"""

from typing import Tuple, List
from scenario import Scenario
from engine import Engine
from node import Peer, Neighbor
from ..__init__ import create_a_test_peer, create_test_peers


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
