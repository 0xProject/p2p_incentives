"""
This module contains test functions for functions in engine_candiates.py
"""

# pylint: disable=redefined-outer-name
# We use a lot of fixtures in this test module, where the name of the fixture function must be
# the same as the input argument name of test functions that uses this fixture.
# Need to disable pylint from this warning.

# pylint: disable=no-self-use
# In this module we put functions under class merely for better readability. They are functions
# rather than methods; but it is still find to put them as methods and classify them according to
# the function they test for.

# pylint: disable=too-many-lines
# I know this module is very long but it contains all test cases for the functions in the
# corresponding module node.py. Putting them together in one module seems a good practice.

import collections
import random
from typing import List, Set, Tuple
import pytest

from message import Order, OrderInfo
from node import Peer, Neighbor
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


@pytest.fixture(scope="module", autouse=True)
def setup_scenario() -> Scenario:
    """
    This is a fixture function that sets up a scenario. It will serve like a setup function, and
    will be useful for initiating orders/nodes. Since nothing of scenario will be changed by any
    function that uses it, we don't need a teardown function so we don't use yield in the fixture.

    Note that settings are simply copied from example.py. Parameters are not important.
    Order/Node initialization simply needs a scenario.
    :return: A scenario instance.
    """

    # order property
    order_default_property = OrderProperty(
        ratio=1.0, expiration=Distribution(mean=500.0, var=0.0)
    )

    # order type and property dictionary. Only one type in this example.
    order_type_property_dict = OrderTypePropertyDict(default=order_default_property)

    # ratio and property of peers of each type.

    # peer property for type "normal"
    peer_normal_property = PeerProperty(
        ratio=0.9, initial_orderbook_size=Distribution(mean=6.0, var=0.0)
    )

    # peer property for type "free rider"
    peer_free_rider_property = PeerProperty(
        ratio=0.1, initial_orderbook_size=Distribution(0, 0)
    )

    # peer type and property dictionary. Now we have normal peers and free riders.
    peer_type_property_dict = PeerTypePropertyDict(
        normal=peer_normal_property, free_rider=peer_free_rider_property
    )

    # system's initial status.
    init_par = SystemInitialState(num_peers=10, birth_time_span=20)

    # system's growth period
    growth_par = SystemEvolution(
        rounds=30,
        peer_arrival=3.0,
        peer_dept=0.0,
        order_arrival=15.0,
        order_cancel=15.0,
    )

    # system's stable period
    stable_par = SystemEvolution(
        rounds=50,
        peer_arrival=2.0,
        peer_dept=2.0,
        order_arrival=15.0,
        order_cancel=15.0,
    )

    # Create scenario parameters
    s_parameters = ScenarioParameters(
        order_type_property=order_type_property_dict,
        peer_type_property=peer_type_property_dict,
        init_state=init_par,
        growth_period=growth_par,
        stable_period=stable_par,
    )

    # options.

    # event arrival pattern.
    event_arrival = EventOption(method="Poisson")
    # how an order's is_settled status is changed
    change_settle_status = SettleOption(method="Never")

    # creating scenario options
    s_options = ScenarioOptions(event_arrival, change_settle_status)

    # return scenario instance
    return Scenario(s_parameters, s_options)


@pytest.fixture(scope="module")
def setup_engine() -> Engine:
    """
    This is a fixture function that sets up an engine. This will be useful for initiating
    orders/nodes. Same reason that we don't need a yield statement for teardown.
    Note that most settings are simply copied from example.py. Most parameters are not important.
    Order/Node initialization simply needs an engine.
    :return: An engine instance.
    """

    batch: int = 10  # length of a batch period

    topology = Topology(
        max_neighbor_size=30, min_neighbor_size=20
    )  # neighborhood sizes

    # The following are incentive parameters. In order to check if rewards/penalties are properly
    # added, we carefully choose (mutually prime) parameters below so that we can make sure the
    # final sum is correct in test functions.

    incentive = Incentive(
        score_sheet_length=3,
        reward_a=2,
        reward_b=3,
        reward_c=5,
        reward_d=7,
        reward_e=11,
        penalty_a=-13,
        penalty_b=-17,
    )

    # creating engine parameters, in type of a namedtuple.
    e_parameters = EngineParameters(batch, topology, incentive)

    # options. Just copied from example.py. No need to make clear their meaning for here.
    # Only need a valid one to run.
    preference = PreferenceOption(method="Passive")
    priority = PriorityOption(method="Passive")
    external = ExternalOption(method="Always")
    internal = InternalOption(method="Always")
    store = StoreOption(method="First")
    share = AllNewSelectedOld(
        method="AllNewSelectedOld", max_to_share=5000, old_share_prob=0.5
    )
    score = Weighted(
        method="Weighted",
        lazy_length_threshold=6,
        lazy_contribution_threshold=2,
        weights=[1.0, 1.0, 1.0],
    )
    beneficiary = TitForTat(
        method="TitForTat", baby_ending_age=0, mutual_helpers=3, optimistic_choices=1
    )
    rec = RecommendationOption(method="Random")

    # creating engine option, in type of a namedtuple
    e_options = EngineOptions(
        preference, priority, external, internal, store, share, score, beneficiary, rec
    )

    # return engine instance.
    return Engine(e_parameters, e_options)


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


class TestStorageFirst:
    """
    this class contains all test functions for store_first()
    """

    def test_store_first__multi_orderinfo(self, setup_scenario, setup_engine):
        """
        This test is for multiple orderinfo isntances from different neighbors, in the pending table
        :param setup_scenario: fixture
        :param setup_engine: fixture
        :return: None
        """
        peer = create_a_test_peer(setup_scenario, setup_engine)[0]
        order = create_a_test_order(setup_scenario)
        neighbor_list = create_test_peers(setup_scenario, setup_engine, 2)

        for neighbor in neighbor_list:
            neighbor.receive_order_external(order)
            neighbor.store_orders()

            # HACK(weijiewu8): this one should change after the previous PR is merged.
            peer.should_add_neighbor(neighbor)
            neighbor.should_add_neighbor(peer)

            peer.receive_order_internal(neighbor, order)

        peer.store_orders()
        assert peer.order_orderinfo_mapping[order].prev_owner == neighbor_list[0]

    def test_store_first__single_orderinfo(self, setup_scenario, setup_engine):
        """
        This test is for multiple orderinfo isntances from different neighbors, in the pending table
        :param setup_scenario: fixture
        :param setup_engine: fixture
        :return: None
        """
        peer = create_a_test_peer(setup_scenario, setup_engine)[0]
        order = create_a_test_order(setup_scenario)
        peer.receive_order_external(order)
        peer.store_orders()
        assert peer.order_orderinfo_mapping[order].prev_owner is None


class TestAllNewSelectedOld:
    """
    This class contains all test functions for all_new_selected_old()
    """

    def test_all_new_selected_old__many_new(self, setup_scenario, setup_engine, monkeypatch):
        """
        there are many new orders (> max_to_share) so only a subset of new orders are
        selected; no old one is selected.
        :param setup_scenario: fixture
        :param setup_engine: fixture
        :param monkeypatch: mocking tool
        :return: None
        """
        # need to change max_to_share first
        def fake_share_option():
            return {'method': "AllNewSelectedOld",
                    'max_to_share': 5,
                    'old_share_prob': 0.5}

        monkeypatch.setattr(setup_engine, "share_option", fake_share_option())

        pass

    def test_all_new_selected_old__limited_new_many_old(self, setup_scenario, setup_engine, monkeypatch):
        """
        there are limited new orders (< max_to_share, all can be selected) and many old ones (
        actual selection probability less than planned).
        :param setup_scenario: fixture.
        :param setup_engine: fixture.
        :param monkeypatch: mocking tool
        :return: None
        """
        # need to change max_to_share first
        pass

    def test_all_new_selected_old__limited_total(self, setup_scenario, setup_engine):
        """
        there are limited new and old orders so everything is as planned.
        :param setup_scenario: fixture
        :param setup_engine: fixture
        :return: None
        """
        pass


# I think I'll need to re-write weighted_sum() by splitting the operations on calculating the
# sore and neighbor deletion.

class TestTitForTat:
    """
    This class contains all test functions for tit_for_tat()
    """

    def test_tit_for_tat__new_peer(self):
        pass

    def test_tit_for_tat__very_few_neighbors(self):
        pass

    def test_tit_for_tat__few_neighbors(self):
        pass

    def test_tit_for_tat__zero_contributors(self):
        pass

