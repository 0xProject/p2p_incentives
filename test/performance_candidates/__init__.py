"""
This module contains test functions for performance_candidates.py

This init file contains exactly the same content as other modules (e.g., node.py).
Later we will need to find a better place to place it.

# HACK(weijiewu8): Re-organize __init__.py files.

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
)

from scenario import Scenario
from engine import Engine


SCENARIO_SAMPLE = Scenario(
    ScenarioParameters(
        order_type_property=OrderTypePropertyDict(
            default=OrderProperty(
                ratio=1.0, expiration=Distribution(mean=500.0, var=0.0)
            )
        ),
        peer_type_property=PeerTypePropertyDict(
            normal=PeerProperty(
                ratio=0.9, initial_orderbook_size=Distribution(mean=6.0, var=0.0)
            ),
            free_rider=PeerProperty(
                ratio=0.1, initial_orderbook_size=Distribution(0, 0)
            ),
        ),
        init_state=SystemInitialState(num_peers=10, birth_time_span=20),
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

ENGINE_SAMPLE = Engine(
    EngineParameters(
        batch_length=10,
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
            baby_ending_age=0,
            mutual_helpers=3,
            optimistic_choices=1,
        ),
        rec=RecommendationOption(method="Random"),
    ),
)


def create_a_test_order(scenario: Scenario) -> Order:
    """
    This is a helper function to create an order.
    :param scenario: the scenario for the order.
    :return: the order instance.
    Note: parameters are arbitrarily set and not important.
    Note that though the parameters are fixed, calling this function multiple times will create
    multiple distinct instances.
    """
    return Order(scenario=scenario, seq=5, birth_time=12, creator=None)


def create_test_orders(scenario: Scenario, num: int) -> List[Order]:
    """
    This function creates multiple order instances, each created by create_a_test_order().
    :param scenario: scenario to pass to init()
    :param num: number of order instances.
    :return: a set of order instances.
    """
    order_list: List[Order] = list()
    for _ in range(num):
        order_list.append(create_a_test_order(scenario))
    return order_list


def create_a_test_peer(scenario: Scenario, engine: Engine) -> Tuple[Peer, Set[Order]]:
    """
    This function creates a peer constant. Parameters are hard coded (e.g., it has five initial
    orders). It does not pursue any generality, but merely for use of following test functions.
    :param scenario: scenario to pass to order init.
    :param engine: engine to pass to peer init.
    :return: a peer instance, and the set (5) of initial order instances.
    Parameters are arbitrarily set and they are not important.
    Note that though the parameters are fixed, calling this function multiple times will create
    multiple distinct instances.
    """

    # manually create 5 orders for this peer.
    order_set: Set[Order] = set(create_test_orders(scenario, 5))

    # create the peer instance
    my_peer = Peer(
        engine=engine,
        seq=1,
        birth_time=7,
        init_orders=order_set,
        namespacing=None,
        peer_type="normal",
    )

    return my_peer, order_set


def create_test_peers(scenario: Scenario, engine: Engine, nums: int) -> List[Peer]:
    """
    This function creates a number of peers and return a list of them.
    Each peer is created using create_a_test_peer() function.
    :param scenario: scenario to pass to create_a_test_peer()
    :param engine: engine to pass to create_a_test_peer()
    :param nums: number of peers.
    :return: a list of peer instances.
    """
    peer_list: List[Peer] = list()

    for _ in range(nums):
        peer_list.append(create_a_test_peer(scenario, engine)[0])

    return peer_list
