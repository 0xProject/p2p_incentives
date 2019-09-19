"""
This module contains unit tests of add_new_links_helper().
"""

from typing import List, Tuple
import pytest

from single_run import SingleRun
from node import Peer
from scenario import Scenario
from engine import Engine
from performance import Performance
from ..__init__ import SCENARIO_SAMPLE, ENGINE_SAMPLE, PERFORMANCE_SAMPLE


@pytest.fixture(autouse=True)
def temporary_change_of_neighbor_size(engine):
    """
    This function is to temporarily change the expected neighborhood size for the test functions
    to use in this module.
    It is set to autouse so all functions in this module will call it.
    """

    # Setup
    original_neighbor_max = engine.neighbor_max
    original_neighbor_min = engine.neighbor_min
    engine.neighbor_max = 6
    engine.neighbor_min = 3

    yield

    # Tear down
    engine.neighbor_max = original_neighbor_max
    engine.neighbor_min = original_neighbor_min


# Define some constants for use in this module.

NUM_FULLY_CONNECTED_PEERS = 7  # 7 peers are fully connected
TOTAL_NUM_OF_PEERS = 12  # total number of peers is 12


def create_single_run_instance_and_peers(
    scenario: Scenario, engine: Engine, performance: Performance
) -> Tuple[SingleRun, List[Peer]]:
    """
    This helper function sets up a single_run instance with 12 peers, among which the first 7
    peers are connected with each other. It returns the single_run instance and the 12 peers.
    """

    # Create the single_run instance
    this_instance = SingleRun(scenario, engine, performance)

    # Create 12 peers in this single_run
    for _ in range(TOTAL_NUM_OF_PEERS):
        this_instance.peer_arrival("normal", {})

    # Record these peers
    the_peer_list: List[Peer] = list()
    iterator = iter(this_instance.peer_full_set)
    for _ in range(TOTAL_NUM_OF_PEERS):
        the_peer_list.append(next(iterator))

    # For the first 7 peers, they form a full mesh.
    for any_peer in the_peer_list[0:NUM_FULLY_CONNECTED_PEERS]:
        for other_peer in the_peer_list[0:NUM_FULLY_CONNECTED_PEERS]:
            if (
                any_peer is not other_peer
                and any_peer not in other_peer.peer_neighbor_mapping
            ):
                any_peer.add_neighbor(other_peer)
                other_peer.add_neighbor(any_peer)

    return this_instance, the_peer_list


@pytest.mark.parametrize(
    "scenario, engine, performance",
    [(SCENARIO_SAMPLE, ENGINE_SAMPLE, PERFORMANCE_SAMPLE)],
)
def test_add_new_links_helper__normal(
    scenario: Scenario, engine: Engine, performance: Performance
) -> None:
    """
    This function tests add_new_links_helper() in a normal case.
    """

    # Arrange

    # Create the single_run instance and peers
    single_run_instance, peer_list = create_single_run_instance_and_peers(
        scenario, engine, performance
    )

    # Act.

    # Now, let peer_list[7] try to add 3 neighbors, or at least 1.
    min_neighbor = 1
    max_neighbor = 3
    single_run_instance.add_new_links_helper(
        peer_list[NUM_FULLY_CONNECTED_PEERS], max_neighbor, min_neighbor
    )

    # Assert.

    assert (
        min_neighbor
        <= len(peer_list[NUM_FULLY_CONNECTED_PEERS].peer_neighbor_mapping)
        <= max_neighbor
    )
    for any_peer in peer_list[0:NUM_FULLY_CONNECTED_PEERS]:
        assert (
            any_peer not in peer_list[NUM_FULLY_CONNECTED_PEERS].peer_neighbor_mapping
        )


@pytest.mark.parametrize(
    "scenario, engine, performance",
    [(SCENARIO_SAMPLE, ENGINE_SAMPLE, PERFORMANCE_SAMPLE)],
)
def test_add_new_links_helper__all_to_add(
    scenario: Scenario, engine: Engine, performance: Performance
) -> None:
    """
    This function tests add_new_links_helper() where the number of possible neighbors to add is
    4, and the minimum requirement is also 4. So all possibilities are tried and added.
    """

    # Arrange

    # Create the single_run instance and peers
    single_run_instance, peer_list = create_single_run_instance_and_peers(
        scenario, engine, performance
    )

    # Act.

    # Now, let peer_list[7] try to add 4 neighbors, and at least 4.
    neighbor_size = 4
    single_run_instance.add_new_links_helper(
        peer_list[NUM_FULLY_CONNECTED_PEERS], neighbor_size, neighbor_size
    )

    # Assert.

    assert (
        len(peer_list[NUM_FULLY_CONNECTED_PEERS].peer_neighbor_mapping) == neighbor_size
    )
    for any_peer in peer_list[0:NUM_FULLY_CONNECTED_PEERS]:
        assert (
            any_peer not in peer_list[NUM_FULLY_CONNECTED_PEERS].peer_neighbor_mapping
        )
    for any_peer in peer_list[NUM_FULLY_CONNECTED_PEERS + 1 :]:
        assert any_peer in peer_list[NUM_FULLY_CONNECTED_PEERS].peer_neighbor_mapping


@pytest.mark.parametrize(
    "scenario, engine, performance",
    [(SCENARIO_SAMPLE, ENGINE_SAMPLE, PERFORMANCE_SAMPLE)],
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

    # Create the single_run instance and peers
    single_run_instance, peer_list = create_single_run_instance_and_peers(
        scenario, engine, performance
    )

    # Act.

    # Now, let peer_list[7] try to add 8 neighbors, and at least 6.
    min_neighbor = 6
    max_neighbor = 8
    single_run_instance.add_new_links_helper(
        peer_list[NUM_FULLY_CONNECTED_PEERS], max_neighbor, min_neighbor
    )

    # Assert.

    assert (
        len(peer_list[NUM_FULLY_CONNECTED_PEERS].peer_neighbor_mapping)
        == TOTAL_NUM_OF_PEERS - NUM_FULLY_CONNECTED_PEERS - 1
    )
    for peer in peer_list[0:NUM_FULLY_CONNECTED_PEERS]:
        assert peer not in peer_list[NUM_FULLY_CONNECTED_PEERS].peer_neighbor_mapping
    for peer in peer_list[NUM_FULLY_CONNECTED_PEERS + 1 :]:
        assert peer in peer_list[NUM_FULLY_CONNECTED_PEERS].peer_neighbor_mapping


@pytest.mark.parametrize(
    "scenario, engine, performance",
    [(SCENARIO_SAMPLE, ENGINE_SAMPLE, PERFORMANCE_SAMPLE)],
)
def test_add_new_links_helper__error_input(
    scenario: Scenario, engine: Engine, performance: Performance
) -> None:
    """
    This function tests add_new_links_helper() where input values are wrong.
    """

    # Arrange

    # Create the single_run instance and peers
    single_run_instance, peer_list = create_single_run_instance_and_peers(
        scenario, engine, performance
    )

    # Act and Assert.

    with pytest.raises(ValueError, match="Input value is invalid."):
        single_run_instance.add_new_links_helper(peer_list[7], 4, 6)

    with pytest.raises(ValueError, match="Input value is invalid."):
        single_run_instance.add_new_links_helper(peer_list[7], 0, 0)

    with pytest.raises(ValueError, match="Input value is invalid."):
        single_run_instance.add_new_links_helper(peer_list[7], 6, -1)
