"""
This module contains unit tests for add_new_links_helper().
"""

from typing import List, Tuple
import pytest

from simulator import SingleRun
from node import Peer
from scenario import Scenario
from engine import Engine
from performance import Performance
from .__init__ import SCENARIO_SAMPLE_1, ENGINE_SAMPLE, PERFORMANCE_SAMPLE


def setup_help(
    scenario: Scenario, engine: Engine, performance: Performance
) -> Tuple[SingleRun, List[Peer]]:
    """
    This helper function sets up a single_run instance with 12 peers, among which the first 7
    peers are connected with each other. It returns the single_run instance and the 12 peers.
    """

    # Create the single_run instance
    this_instance = SingleRun(scenario, engine, performance)

    # Create 12 peers in this single_run
    for _ in range(12):
        this_instance.peer_arrival("normal", 0)

    # Record these peers
    the_peer_list: List[Peer] = list()
    iterator = iter(this_instance.peer_full_set)
    for _ in range(12):
        the_peer_list.append(next(iterator))

    # For the first 7 peers, they form a full mesh.
    for any_peer in the_peer_list[0:7]:
        for other_peer in the_peer_list[0:7]:
            if (
                any_peer is not other_peer
                and any_peer not in other_peer.peer_neighbor_mapping
            ):
                any_peer.add_neighbor(other_peer)
                other_peer.add_neighbor(any_peer)

    return this_instance, the_peer_list


@pytest.mark.parametrize(
    "scenario, engine, performance",
    [(SCENARIO_SAMPLE_1, ENGINE_SAMPLE, PERFORMANCE_SAMPLE)],
)
def test_add_new_links_helper__normal(
    scenario: Scenario, engine: Engine, performance: Performance
) -> None:
    """
    This function tests add_new_links_helper() in a normal case.
    """

    # Arrange

    # Change the minimum/maximal neighborhood size as 3 and 6
    engine.neighbor_max = 6
    engine.neighbor_min = 3

    # Create the single_run instance and peers
    single_run_instance, peer_list = setup_help(scenario, engine, performance)

    # Act.

    # Now, let peer_list[7] try to add 3 neighbors, or at least 1.
    single_run_instance.add_new_links_helper(peer_list[7], 3, 1)

    # Assert.

    assert 1 <= len(peer_list[7].peer_neighbor_mapping) <= 3
    for any_peer in peer_list[0:7]:
        assert any_peer not in peer_list[7].peer_neighbor_mapping


@pytest.mark.parametrize(
    "scenario, engine, performance",
    [(SCENARIO_SAMPLE_1, ENGINE_SAMPLE, PERFORMANCE_SAMPLE)],
)
def test_add_new_links_helper__all_to_add(
    scenario: Scenario, engine: Engine, performance: Performance
) -> None:
    """
    This function tests add_new_links_helper() where the number of possible neighbors to add is
    4, and the minimum requirement is also 4. So all possibilities are tried and added.
    """

    # Arrange

    # Change the minimum/maximal neighborhood size as 3 and 6
    engine.neighbor_max = 6
    engine.neighbor_min = 3

    # Create the single_run instance and peers
    single_run_instance, peer_list = setup_help(scenario, engine, performance)

    # Act.

    # Now, let peer_list[7] try to add 4 neighbors, and at least 4.
    single_run_instance.add_new_links_helper(peer_list[7], 4, 4)

    # Assert.

    assert len(peer_list[7].peer_neighbor_mapping) == 4
    for any_peer in peer_list[0:7]:
        assert any_peer not in peer_list[7].peer_neighbor_mapping
    for any_peer in peer_list[8:]:
        assert any_peer in peer_list[7].peer_neighbor_mapping


@pytest.mark.parametrize(
    "scenario, engine, performance",
    [(SCENARIO_SAMPLE_1, ENGINE_SAMPLE, PERFORMANCE_SAMPLE)],
)
def test_add_new_links_helper__tried_the_best(
    scenario: Scenario, engine: Engine, performance: Performance
) -> None:
    """
    This function tests add_new_links_helper() where the number of possible neighbors to add is
    4, and the minimum requirement is 6 (and tries at 8 maximal). So all possibilities are tried
    and added, and the process ends, although the added number does not reach 6.
    """

    # Arrange

    # Change the minimum/maximal neighborhood size as 3 and 6
    engine.neighbor_max = 6
    engine.neighbor_min = 3

    # Create the single_run instance and peers
    single_run_instance, peer_list = setup_help(scenario, engine, performance)

    # Act.

    # Now, let peer_list[7] try to add 8 neighbors, and at least 6.
    single_run_instance.add_new_links_helper(peer_list[7], 8, 6)

    # Assert.

    assert len(peer_list[7].peer_neighbor_mapping) == 4
    for peer in peer_list[0:7]:
        assert peer not in peer_list[7].peer_neighbor_mapping
    for peer in peer_list[8:]:
        assert peer in peer_list[7].peer_neighbor_mapping


@pytest.mark.parametrize(
    "scenario, engine, performance",
    [(SCENARIO_SAMPLE_1, ENGINE_SAMPLE, PERFORMANCE_SAMPLE)],
)
def test_add_new_links_helper__error_input(
    scenario: Scenario, engine: Engine, performance: Performance
) -> None:
    """
    This function tests add_new_links_helper() where input values are wrong.
    """

    # Arrange

    # Create the single_run instance and peers
    single_run_instance, peer_list = setup_help(scenario, engine, performance)

    # Act and Assert.

    with pytest.raises(ValueError, match="Input value is invalid."):
        single_run_instance.add_new_links_helper(peer_list[7], 4, 6)

    with pytest.raises(ValueError, match="Input value is invalid."):
        single_run_instance.add_new_links_helper(peer_list[7], 0, 0)

    with pytest.raises(ValueError, match="Input value is invalid."):
        single_run_instance.add_new_links_helper(peer_list[7], 6, -1)
