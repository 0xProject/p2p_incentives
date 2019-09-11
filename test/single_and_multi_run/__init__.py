"""
Tests for single_run.py
It contains specific constants for this sub-module.
"""

from typing import List, Set, Tuple

from message import Order
from node import Peer
from data_types import (
    OrderProperty,
    Distribution,
    OrderTypePropertyDict,
    PeerProperty,
    PeerTypePropertyDict,
    SystemInitialState,
    ScenarioParameters,
    SystemEvolution,
    ScenarioOptions,
    EventOption,
    SettleOption,
    Incentive,
    Topology,
    EngineParameters,
    PriorityOption,
    InternalOption,
    PreferenceOption,
    ExternalOption,
    StoreOption,
    Weighted,
    TitForTat,
    AllNewSelectedOld,
    RecommendationOption,
    EngineOptions,
    PerformanceParameters,
    SpreadingOption,
    SatisfactionOption,
    FairnessOption,
    PerformanceOptions,
    PerformanceExecutions,
)

from scenario import Scenario
from engine import Engine
from performance import Performance

# This is another scenario example, where init_state.num_peers * peer_ratio are NOT integers.

SCENARIO_SAMPLE_NON_INT = Scenario(
    ScenarioParameters(
        order_type_property=OrderTypePropertyDict(
            default=OrderProperty(
                ratio=1.0, expiration=Distribution(mean=500.0, var=0.0)
            )
        ),
        peer_type_property=PeerTypePropertyDict(
            normal=PeerProperty(
                ratio=0.52, initial_orderbook_size=Distribution(mean=7.5, var=4.0)
            ),
            free_rider=PeerProperty(
                ratio=0.48, initial_orderbook_size=Distribution(0, 0)
            ),
        ),
        init_state=SystemInitialState(num_peers=29, birth_time_span=20),
        growth_period=SystemEvolution(
            rounds=30,
            peer_arrival=3.0,
            peer_dept=0.0,
            order_arrival=15.0,
            order_cancel=15.0,
        ),
        stable_period=SystemEvolution(
            rounds=50,
            peer_arrival=2.0,
            peer_dept=2.0,
            order_arrival=15.0,
            order_cancel=15.0,
        ),
    ),
    ScenarioOptions(
        event=EventOption(method="Poisson"), settle=SettleOption(method="Never")
    ),
)

# This is an engine example where we set batch_length = 1 so peer operations (store and share
# orders) will happen in every time slot.

ENGINE_SAMPLE_STORE_SHARE_MUST_HAPPEN = Engine(
    EngineParameters(
        batch_length=1,
        topology=Topology(max_neighbor_size=30, min_neighbor_size=20),
        incentive=Incentive(
            score_sheet_length=3,
            reward_a=2,
            reward_b=3,
            reward_c=5,
            reward_d=7,
            reward_e=11,
            penalty_a=-13,
            penalty_b=-17,
        ),
    ),
    EngineOptions(
        preference=PreferenceOption(method="Passive"),
        priority=PriorityOption(method="Passive"),
        external=ExternalOption(method="Always"),
        internal=InternalOption(method="Always"),
        store=StoreOption(method="First"),
        share=AllNewSelectedOld(
            method="AllNewSelectedOld", max_to_share=5000, old_share_prob=0.5
        ),
        score=Weighted(
            method="Weighted",
            lazy_length_threshold=6,
            lazy_contribution_threshold=2,
            weights=[1.0, 1.0, 1.0],
        ),
        beneficiary=TitForTat(
            method="TitForTat",
            baby_ending_age=100,
            mutual_helpers=30,
            optimistic_choices=10,
        ),
        rec=RecommendationOption(method="Random"),
    ),
)

# This is an example for performance instance.

PERFORMANCE_SAMPLE = Performance(
    PerformanceParameters(max_age_to_track=50, adult_age=30, statistical_window=5),
    PerformanceOptions(
        spreading_option=SpreadingOption(method="Ratio"),
        satisfaction_option=SatisfactionOption(method="Neutral"),
        fairness_option=FairnessOption(method="Dummy"),
    ),
    PerformanceExecutions(
        order_spreading=True,
        normal_peer_satisfaction=True,
        free_rider_satisfaction=True,
        system_fairness=False,
    ),
)


def mock_random_choice(candidates: List, weights: List[float], *, k: int) -> List:
    """
    This is a mock function for random.choice(). It generates a deterministic sequence of the
    candidates, each one with frequency weights[i] (count: int(len(candidates) * k). If the
    sum of total count is less than number, then the deficiency is given to the candidates
    with the highest weight.
    :param candidates: candidates to choose from.
    :param weights: frequency of each candidate to be chosen.
    :param k: total number of output list.
    :return: a list of items in the candidates.
    """

    # normalization

    sum_of_weights = sum(weights)
    weights = [weight / sum_of_weights for weight in weights]

    counts: List[int] = [int(k * weights[i]) for i in range(len(weights))]

    if sum(counts) < k:
        max_idx: int = weights.index(max(weights))
        counts[max_idx] += k - sum(counts)

    result: List = list()
    for i in range(len(counts)):
        result += [candidates[i] for _ in range(counts[i])]
    return result


def test_mock_random_choice__no_remains() -> None:
    """
    This is to make sure mock_random_choice() works correct.
    """
    actual_result: List = mock_random_choice(
        candidates=["a", "b", "c"], weights=[0.1, 0.3, 0.6], k=10
    )
    expected_result: List = ["a", "b", "b", "b", "c", "c", "c", "c", "c", "c"]
    assert actual_result == expected_result


def test_mock_random_choice__with_remains() -> None:
    """
    This is to make sure mock_random_choice() works correct.
    """
    actual_result: List = mock_random_choice(
        candidates=["a", "b", "c"], weights=[0.1, 0.6, 0.3], k=11
    )
    expected_result: List = ["a", "b", "b", "b", "b", "b", "b", "b", "c", "c", "c"]
    assert actual_result == expected_result


def fake_gauss(mean: float, _var: float) -> int:
    """
    This is a fake function for Gaussian variable. It simply convert mean to integer and return it.
    """
    return int(mean)
