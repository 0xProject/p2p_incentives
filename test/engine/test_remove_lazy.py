"""
This module contains unit tests of remove_lazy().
"""

from typing import List
from collections import deque
import pytest
from node import Peer
import engine_candidates
from scenario import Scenario
from engine import Engine

from ..__init__ import ENGINE_SAMPLE, SCENARIO_SAMPLE
from .__init__ import create_a_peer_and_two_neighbors_helper


@pytest.mark.parametrize("scenario,engine", [(SCENARIO_SAMPLE, ENGINE_SAMPLE)])
def test_remove_lazy(scenario: Scenario, engine: Engine):
    """
    Unit test of remove_lazy().
    """

    # Arrange.

    peer, neighbor_list, neighbor_instance_list = create_a_peer_and_two_neighbors_helper(
        scenario, engine
    )

    # Set neighbors lazy record. Neighbor 0's lazy_round will be reset to 0 after this round,
    # but neighbor 1's lazy_round will increase by 1, and reach 6.
    neighbor_instance_list[0].lazy_round = 4
    neighbor_instance_list[1].lazy_round = 5
    neighbor_instance_list[0].share_contribution = deque([0, 0, 7])
    neighbor_instance_list[1].share_contribution = deque([1, 2, 0])

    # Act.
    # Neighbor 1 will be deleted.
    lazy_list: List[Peer] = engine_candidates.remove_lazy_neighbors(
        lazy_contribution=2, lazy_length=6, peer=peer
    )

    # Assert.
    assert neighbor_list[0] not in lazy_list
    assert neighbor_instance_list[0].lazy_round == 0  # should have been reset
    assert neighbor_list[1] in lazy_list
