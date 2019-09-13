"""
This module contains unit tests of weighted_sum().
"""

from typing import List
from collections import deque
import pytest
import engine_candidates
from scenario import Scenario
from engine import Engine

from ..__init__ import ENGINE_SAMPLE, SCENARIO_SAMPLE
from .__init__ import create_a_peer_and_two_neighbors_helper


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
