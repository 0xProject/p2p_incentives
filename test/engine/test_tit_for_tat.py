"""
This module contains all test functions for tit_for_tat()
"""
import random
from typing import NamedTuple, Tuple, List
import pytest

import engine_candidates
from scenario import Scenario
from engine import Engine
from node import Peer

from .__init__ import (
    SCENARIO_SAMPLE,
    ENGINE_SAMPLE,
    create_test_peers,
    create_a_test_peer,
)


def mock_random_sample(peers: List[Peer], number: int) -> List[Peer]:
    """
    This is a mock function for random.sample(). In this module it is particularly used to select
    some peer from a list of peers. In order to make it deterministic, in this mock
    function we always return a list of peers with the smallest sequence numbers, and that the
    size of the list equals "number".
    """
    if number > len(peers):
        raise ValueError("Not enough peers to choose from.")
    list_of_peers = list(peers)
    list_of_peers.sort(key=lambda x: x.seq)
    return list_of_peers[:number]


def fake_score_neighbors(_peer):
    """
    This is a fake function to disable engine.score_neighbors(). In our current design
    engine.score_neighbors() is called by peer.rank_neighbors(). In our unit tests here we will
    need to call peer.rank_neighbors() but we have manually set scores for neighbors; we don't
    want the function engine.score_neighbors() to change the scores again when it is called by
    peer.rank_neighbors() so we use the fake function to disable the scores from being calculated
    and updated again.
    """
    # HACK (weijiewu8): This is a temporary treatment. Consider changing engine.score_neighbors()
    # to be moved out of peer.rank_neighbors() so they become independent of each other.
    # If we do it, all fake_score_neighbors() can be deleted.


class CaseType(NamedTuple):
    """
    This is a date type defined for the test cases in this module.
    The first six attributes are inputs to the test function, and the last two are expected outputs.

    """

    scenario: Scenario  # a scenario instance to create peers/orders
    engine: Engine  # an engine instance to create peers/orders
    num_neighbors: int  # number of neighbors that a peer has
    mutual: int  # mutual in tit-for-tat
    optimistic: int  # optimistic in tit-for-tat
    time_now: int  # time now
    expected_length: int  # expected number of neighbors selected as beneficiaries, by tit-for-tat
    expected_seqs: Tuple[
        int, ...
    ]  # tuple containing sequence numbers of neighbor selected


# Case 1 represents that a peer is still a baby (age < baby_ending, in all tests we fix
# baby_ending = 10 and peer.birthtime = 0) so it will randomly choose (mutual + optimistic)
# neighbors from the set.
# Since we mocked the random.sample() function it will always choose the ones with the smallest
# sequence numbers.

CASE_1 = CaseType(
    scenario=SCENARIO_SAMPLE,
    engine=ENGINE_SAMPLE,
    num_neighbors=10,
    mutual=3,
    optimistic=1,
    time_now=0,
    expected_length=4,
    expected_seqs=(0, 1, 2, 3),
)

# In all following cases, peers are not babies any more (time_now = 100).
# In case 2, the total number of neighbors is so small (< mutual) so all neighbors will be selected.

CASE_2 = CaseType(
    scenario=SCENARIO_SAMPLE,
    engine=ENGINE_SAMPLE,
    num_neighbors=3,
    mutual=8,
    optimistic=1,
    time_now=100,
    expected_length=3,
    expected_seqs=(0, 1, 2),
)

# In case 3, the total number of neighbors is still small (> mutual but < mutual + optimistic),
# so all neighbors will be selected.

CASE_3 = CaseType(
    scenario=SCENARIO_SAMPLE,
    engine=ENGINE_SAMPLE,
    num_neighbors=5,
    mutual=3,
    optimistic=5,
    time_now=100,
    expected_length=5,
    expected_seqs=(0, 1, 2, 3, 4),
)

# Case 4 is a typical one. The total number of neighbors is large, so "mutual" number of highly
# scored peers will be selected (in this case, they are peer 497-499) and "optimistic" number of
# the rest will be randomly selected (in this case, they are peers 0-4).

CASE_4 = CaseType(
    scenario=SCENARIO_SAMPLE,
    engine=ENGINE_SAMPLE,
    num_neighbors=500,
    mutual=3,
    optimistic=5,
    time_now=100,
    expected_length=8,
    expected_seqs=(497, 498, 499, 0, 1, 2, 3, 4),
)


@pytest.mark.parametrize(
    "scenario, engine, num_neighbors, mutual, optimistic, time_now, expected_length, expected_seqs",
    [CASE_1, CASE_2, CASE_3, CASE_4],
)
def test_tit_for_tat__no_zero_contributors(
    scenario: Scenario,
    engine: Engine,
    num_neighbors: int,
    mutual: int,
    optimistic: int,
    time_now: int,
    expected_length: int,
    expected_seqs: Tuple[int, ...],
    monkeypatch,
):
    """
    Parameter explanation: please refer to CaseType data type definition.
    This is to test tit_for_tat() when all neighbors have a positive score.
    """
    # Arrange
    peer = create_a_test_peer(scenario, engine)[0]
    peer.birth_time = 0

    neighbor_peers = create_test_peers(scenario, engine, num_neighbors)
    for i in range(num_neighbors):
        neighbor_peers[i].seq = i
        # HACK (weijiewu8): need to change when the old PR is merged.
        peer.should_add_neighbor(neighbor_peers[i])
        neighbor_peers[i].should_add_neighbor(peer)
        # make sure no one is having a score of zero
        peer.peer_neighbor_mapping[neighbor_peers[i]].score = i + 300

    monkeypatch.setattr(random, "sample", mock_random_sample)
    monkeypatch.setattr(engine, "score_neighbors", fake_score_neighbors)

    # Act
    selected_peer_set = engine_candidates.tit_for_tat(
        baby_ending=10,
        mutual=mutual,
        optimistic=optimistic,
        time_now=time_now,
        peer=peer,
    )

    # Assert
    assert len(selected_peer_set) == expected_length
    for peer in selected_peer_set:
        assert peer.seq in expected_seqs


# The last test case is a bit different and we leave it alone.
# We would like to test of some peers have zero-contribution (score = 0).
# According to the implementation of tit-for-tat, only non-zero scored peers can be selected to
# the mutually-helping group (total number is "mutual"), but if there are not enough such peers,
# then this group of choice will only cover the qualified peers (score > 0) and we don't
# necessarily choose exactly "mutual" number of such peers, but we select up to all
# non-zero-scored peers. The quota in the "mutual" group can be wasted.
# For any peer which is not selected in the first group, they are put into the random choice
# group (will choose up to "optimistic" ones).
# In the following example, we have 5 peers whose score = 0, and 5 peers score > 0. Mutual = 7
# and optimistic = 3. However, we will only choose 5 mutually helping peers, and still select 3
# optimistic ones.


@pytest.mark.parametrize("scenario,engine", [(SCENARIO_SAMPLE, ENGINE_SAMPLE)])
def test_tit_for_tat__zero_contributors(scenario, engine, monkeypatch):
    """
    Test the most general case with a number of zero-contributors.
    Zero-contributor can never be put into mutual helpers. But they can still be optimistically
    chosen.
    """
    peer = create_a_test_peer(scenario, engine)[0]
    peer.birth_time = 0

    neighbor_peers = create_test_peers(scenario, engine, 10)
    for i in range(5):
        neighbor_peers[i].seq = i
        # HACK (weijiewu8): need to change when the old PR is merged.
        peer.should_add_neighbor(neighbor_peers[i])
        neighbor_peers[i].should_add_neighbor(peer)
        # making sure everyone is having a score of zero
        peer.peer_neighbor_mapping[neighbor_peers[i]].score = 0

    for i in range(5, 10):
        neighbor_peers[i].seq = i
        # HACK (weijiewu8): need to change when the old PR is merged.
        peer.should_add_neighbor(neighbor_peers[i])
        neighbor_peers[i].should_add_neighbor(peer)
        # making sure no one is having a score of zero
        peer.peer_neighbor_mapping[neighbor_peers[i]].score = i + 300

    monkeypatch.setattr(random, "sample", mock_random_sample)
    monkeypatch.setattr(engine, "score_neighbors", fake_score_neighbors)

    # Act
    selected_peer_set = engine_candidates.tit_for_tat(
        baby_ending=10, mutual=7, optimistic=3, time_now=100, peer=peer
    )

    # Assert
    assert len(selected_peer_set) == 8
    for peer in selected_peer_set:
        assert peer.seq in (5, 6, 7, 8, 9, 0, 1, 2)
