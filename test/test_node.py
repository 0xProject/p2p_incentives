"""
This module contains test functions for instances of Peer and Neighbor.

Note that we will need to have instances of Order and OrderInfo first.

Also note that in order to create the instances, we will need an instance of Scenario and an
instance of Engine. We will simply set up a scenario instance and an engine instance for the test
functions to run, but we will not test Scenario or Engine in here. We will have extensive tests
over them separately.

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
# correponding module node.py. Putting them together in one module seems a good practice.

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


class TestOrderAndPeerInit:
    """
    This class contains test functions for peer and order initiliazation functions.
    """

    def test_order(self, setup_scenario) -> None:
        """
        This function tests order initialization.
        :param setup_scenario: the fixture function's return value
        :return: None
        """
        my_order: Order = create_a_test_order(setup_scenario)
        assert my_order.seq == 5
        assert my_order.birth_time == 12
        assert my_order.scenario.peer_type_property["normal"].ratio == pytest.approx(
            0.9
        )
        assert my_order.scenario.peer_type_property[
            "free_rider"
        ].ratio == pytest.approx(0.1)

    def test_peer(self, setup_scenario, setup_engine) -> None:
        """
        This function tests peer initialization.
        :param setup_scenario: fixture.
        :param setup_engine: fixture.
        :return: None.
        """

        # Arrange and Act.

        my_peer, order_set = create_a_test_peer(setup_scenario, setup_engine)

        # Assert.

        # assert my_peer's attributes.

        assert my_peer.engine == setup_engine
        assert my_peer.seq == 1
        assert my_peer.birth_time == 7
        assert my_peer.init_orderbook_size == 5
        assert my_peer.namespacing is None
        assert my_peer.peer_type == "normal"
        assert my_peer.is_free_rider is False

        # assert of my_peer has changed the creator of initial orders.
        for order in order_set:
            assert order.creator == my_peer

        # assert my_peer's storage for order and orderinfo
        assert my_peer.new_order_set == order_set

        assert len(my_peer.order_orderinfo_mapping) == 5
        for order in order_set:
            orderinfo = my_peer.order_orderinfo_mapping[order]
            assert orderinfo.engine == setup_engine
            assert orderinfo.arrival_time == my_peer.birth_time
            assert orderinfo.prev_owner is None
            assert orderinfo.novelty == 0
            assert orderinfo.priority is None
            assert orderinfo.storage_decision is True

        assert my_peer.peer_neighbor_mapping == {}
        assert my_peer.order_pending_orderinfo_mapping == {}

        # assert order instance's record

        for order in order_set:
            assert order.holders == {my_peer}


class TestAddNeighbor:
    """
    This class contains test functions for add_neighbor()
    """

    def test_add_neighbor__normal(self, setup_scenario, setup_engine) -> None:
        """
        normal cases.
        :param setup_scenario: fixture.
        :param setup_engine: fixture.
        :return: None
        """
        # Arrange.
        # We have three peers.
        peer_list: List[Peer] = create_test_peers(setup_scenario, setup_engine, 3)

        # Act.

        # add peer_list[1] and peer_list[2] into peer_list[0]'s neighbor.
        peer_list[0].add_neighbor(peer_list[1])
        peer_list[0].add_neighbor(peer_list[2])

        # Assert.

        # assert if the neighbor can be found and if neighbor size is correct.
        assert peer_list[1] in peer_list[0].peer_neighbor_mapping
        assert peer_list[2] in peer_list[0].peer_neighbor_mapping
        assert len(peer_list[0].peer_neighbor_mapping) == 2

        # assert neighbor instance setting
        neighbor: Neighbor = peer_list[0].peer_neighbor_mapping[peer_list[1]]
        assert neighbor.engine == setup_engine
        assert neighbor.est_time == peer_list[0].birth_time
        assert neighbor.preference is None
        expected_score_sheet = collections.deque()
        for _ in range(setup_engine.score_length):
            expected_score_sheet.append(0.0)
        assert neighbor.share_contribution == expected_score_sheet
        assert neighbor.score == pytest.approx(0.0)
        assert neighbor.lazy_round == 0

    def test_add_neighbor__add_an_existing_neighbor(self, setup_scenario, setup_engine):
        """
        Test if one tries to add an existing neighbor
        :param setup_scenario: fixture.
        :param setup_engine: fixture.
        :return: None.
        """

        # Arrange.
        # We have two peers. Peer 1 is in Peer 0's neighbor.
        peer_list: List[Peer] = create_test_peers(setup_scenario, setup_engine, 2)
        peer_list[0].add_neighbor(peer_list[1])

        # Action and Assert.
        # Should raise an error when adding an existing neighbor.

        with pytest.raises(ValueError):
            peer_list[0].add_neighbor(peer_list[1])

    def test_add_neighbor__add_self(self, setup_scenario, setup_engine):
        """
        Test if one tries to add itself as a neighbor
        :param setup_scenario: fixture.
        :param setup_engine: fixture.
        :return: None.
        """
        # Arrange.
        peer: Peer = create_a_test_peer(setup_scenario, setup_engine)[0]

        # Act and Assert.
        # Add self. Should raise an error
        with pytest.raises(ValueError):
            peer.add_neighbor(peer)


class TestShouldAcceptNeighborRequest:
    """
    This class contains test functions for should_accept_neighbor_request().
    """

    def test_should_accept_neighbor_request__true(
        self, setup_scenario, setup_engine
    ) -> None:
        """
        Test when it should return True.
        :param setup_scenario: fixture.
        :param setup_engine: fixture.
        :return: None
        """
        # Arrange. Create two peers
        peer_list: List[Peer] = create_test_peers(setup_scenario, setup_engine, 2)

        # Act and Assert.
        # Should accept invitation
        assert peer_list[0].should_accept_neighbor_request(peer_list[1]) is True

    def test_should_accept_neighbor_request__false(
        self, setup_scenario, setup_engine, monkeypatch
    ) -> None:
        """
        Test when it should return False.
        :param setup_scenario: fixture.
        :param setup_engine: fixture.
        :param monkeypatch: tool for fake attribute
        :return: None
        """
        # Arrange.
        # Create three peers. First two are neighbors.
        peer_list: List[Peer] = create_test_peers(setup_scenario, setup_engine, 3)
        peer_list[0].add_neighbor(peer_list[1])
        peer_list[1].add_neighbor(peer_list[0])

        # Fake max neighbor size to 1.
        monkeypatch.setattr(setup_engine, "neighbor_max", 1)

        # Action and Assert.
        # Peer 2 wants to be Peer 0's neighbor. Should reject.
        assert peer_list[0].should_accept_neighbor_request(peer_list[2]) is False

    def test_should_accept_neighbor__existing_neighbor(
        self, setup_scenario, setup_engine
    ) -> None:
        """
        Requested by an existing neighbor.
        :param setup_scenario: fixture.
        :param setup_engine: fixture.
        :return: None
        """
        # Arrange.
        # Create three peers. First two are neighbors.
        peer_list: List[Peer] = create_test_peers(setup_scenario, setup_engine, 3)
        peer_list[0].add_neighbor(peer_list[1])
        peer_list[1].add_neighbor(peer_list[0])

        # Act and Assert.
        # when they're already neighbors and a peer still requests, an error should be raised.
        with pytest.raises(ValueError):
            peer_list[0].should_accept_neighbor_request(peer_list[1])

    def test_should_accept_neighbor__self_request(
        self, setup_scenario, setup_engine
    ) -> None:
        """
        Requested by itself.
        :param setup_scenario: fixture.
        :param setup_engine: fixture.
        :return: None
        """
        # Arrange.
        # Create three peers. First two are neighbors.
        peer = create_a_test_peer(setup_scenario, setup_engine)[0]

        # Act and Assert.
        # An error should be raised when receiving a request from self.
        with pytest.raises(ValueError):
            peer.should_accept_neighbor_request(peer)


class TestDelNeighbor:
    """
    This class contains test functions for del_neighbor()
    Note: we have not tested the "remove_order" option here. However, in order to test it we
    will need to use functions receive_order_internal() and store_orders(). We will test them
    first and later, test this function.
    """

    def test_del_neighbor_normal(self, setup_scenario, setup_engine) -> None:
        """
        normal case.
        :param setup_scenario: fixture.
        :param setup_engine: fixture.
        :return: None
        """
        # Arrange.
        peer_list: List[Peer] = create_test_peers(setup_scenario, setup_engine, 2)
        peer_list[0].add_neighbor(peer_list[1])
        peer_list[1].add_neighbor(peer_list[0])

        # Act.
        peer_list[0].del_neighbor(peer_list[1])

        # Assert.
        # The deletion should be normal. Both sides should delete the other one.
        assert (
            not peer_list[0].peer_neighbor_mapping
            and not peer_list[1].peer_neighbor_mapping
        )

    def test_del_neighbor__non_existing(self, setup_scenario, setup_engine) -> None:
        """
        Delete non existing neighbor.
        :param setup_scenario: fixture.
        :param setup_engine: fixture.
        :return: None
        """
        # Arrange.
        peer_list: List[Peer] = create_test_peers(setup_scenario, setup_engine, 2)

        # Act and Assert.
        # Delete an non-existing neighbor
        with pytest.raises(ValueError):
            peer_list[0].del_neighbor(peer_list[1])

    def test_del_neighbor__self(self, setup_scenario, setup_engine) -> None:
        """
        Delete itself from neighbor set.
        :param setup_scenario: fixture.
        :param setup_engine: fixture.
        :return: None
        """

        # Arrange
        peer: Peer = create_a_test_peer(setup_scenario, setup_engine)[0]

        # Act and Assert. Delete self.
        with pytest.raises(ValueError):
            peer.del_neighbor(peer)


class TestReceiveExternal:
    """
    This class contains test functions for receive_order_external().
    """

    def test_receive_order_external__normal(self, setup_scenario, setup_engine) -> None:
        """
        normal case
        :param setup_scenario: fixture.
        :param setup_engine: fixture.
        :return: None
        """

        # Arrange.
        peer: Peer = create_a_test_peer(setup_scenario, setup_engine)[0]
        order: Order = create_a_test_order(setup_scenario)

        # Act.
        peer.receive_order_external(order)

        # Assert.
        assert order in peer.order_pending_orderinfo_mapping
        assert order not in peer.order_orderinfo_mapping
        assert peer in order.hesitators

    def test_receive_order_external__not_accepted(
        self, setup_scenario, setup_engine, monkeypatch
    ) -> None:
        """
        The order is set to not be accepted.
        :param setup_scenario: fixture.
        :param setup_engine: fixture.
        :param Monkeypatch:
        :return: None
        """

        # Arrange:

        # Change the should_accept_external_order() implementation to a fake one that
        # does not accept any external order.

        def fake_should_accept_external_order(_receiver, _order):
            return False

        monkeypatch.setattr(
            setup_engine,
            "should_accept_external_order",
            fake_should_accept_external_order,
        )

        peer: Peer = create_a_test_peer(setup_scenario, setup_engine)[0]
        order: Order = create_a_test_order(setup_scenario)

        # Act: peer tries to receive order from external
        peer.receive_order_external(order)

        # Assert: should not accept the order.
        assert order not in peer.order_pending_orderinfo_mapping
        assert peer not in order.hesitators


class TestStoreOrders:
    """
    This class contains tests to function store_orders(). We have these tests before testing
    receive_order_internal() because store_order() will be used during the test of
    receive_order_internal().
    """

    def test_store_orders__single_orderinfo(self, setup_scenario, setup_engine) -> None:
        """
        This one tests the case where an order has a single orderinfo instance in the pending table
        and later, it is put into local storage.
        :param setup_scenario: fixture.
        :param setup_engine: fixture.
        :return: None.
        """
        # Arrange.
        peer: Peer = create_a_test_peer(setup_scenario, setup_engine)[0]
        order: Order = create_a_test_order(setup_scenario)
        peer.receive_order_external(order)

        # Act.
        peer.store_orders()

        # Assert.
        assert order in peer.order_orderinfo_mapping

    def test_store_orders__multi_orderinfo(
        self, setup_scenario, setup_engine, monkeypatch
    ) -> None:
        """
        This one tests the case where an order has multiple orderinfo instances in the pending table
        and later, one of them is put into local storage.
        :param setup_scenario: fixture.
        :param setup_engine: fixture.
        :param monkeypatch: tool for fake function.
        :return: None.
        """
        # Arrange.

        # Create a peer and a neighbors for this peer. They will be connected.
        peer: Peer = create_a_test_peer(setup_scenario, setup_engine)[0]
        neighbor_list: List[Peer] = create_test_peers(setup_scenario, setup_engine, 2)

        # create an order
        order: Order = create_a_test_order(setup_scenario)

        # neighbors store this order and are connected to peer.
        for neighbor in neighbor_list:
            neighbor.add_neighbor(peer)
            peer.add_neighbor(neighbor)
            neighbor.receive_order_external(order)
            neighbor.store_orders()

        # since receive_order_internal() function has not been tested, we manually put the order
        # into peer's pending table

        for neighbor in neighbor_list:
            orderinfo = OrderInfo(
                engine=setup_engine,
                order=order,
                master=neighbor,
                arrival_time=peer.birth_time,
                priority=None,
                prev_owner=neighbor,
                novelty=0,
            )
            if order not in peer.order_pending_orderinfo_mapping:
                peer.order_pending_orderinfo_mapping[order] = [orderinfo]
            else:
                peer.order_pending_orderinfo_mapping[order].append(orderinfo)
        order.hesitators.add(peer)

        # manually set storage_decisions for the order.
        # Store neighbor_0's orderinfo instance for the order.

        for orderinfo in peer.order_pending_orderinfo_mapping[order]:
            if orderinfo.prev_owner == neighbor_list[0]:
                orderinfo.storage_decision = True
            else:
                orderinfo.storage_decision = False

        # Disable engine.store_or_discard_orders which will otherwise
        # change the values for orderinfo.storage_decision
        def fake_storage_decision(_node):
            pass

        monkeypatch.setattr(
            setup_engine, "store_or_discard_orders", fake_storage_decision
        )

        # Act.
        peer.store_orders()

        # Assert.

        # order should have been stored and it is the right version.
        assert peer.order_orderinfo_mapping[order].prev_owner == neighbor_list[0]
        # peer's pending table should have been cleared.
        assert peer.order_pending_orderinfo_mapping == {}

    def test_store_orders__do_not_store(
        self, setup_scenario, setup_engine, monkeypatch
    ) -> None:
        """
        This one tests the case where an order has orderinfo instance(s) in the pending
        table but later, it is not stored since labeled as not to store.
        :param setup_scenario: fixture.
        :param setup_engine: fixture.
        :param monkeypatch: tool for fake function.
        :return: None.
        """
        # Arrange.

        # Create a peer and a neighbors for this peer. They will be connected.
        peer: Peer = create_a_test_peer(setup_scenario, setup_engine)[0]
        neighbor_list: List[Peer] = create_test_peers(setup_scenario, setup_engine, 2)

        # create an order
        order: Order = create_a_test_order(setup_scenario)

        # neighbors store this order and are connected to peer.
        for neighbor in neighbor_list:
            neighbor.add_neighbor(peer)
            peer.add_neighbor(neighbor)
            neighbor.receive_order_external(order)
            neighbor.store_orders()

        # since receive_order_internal() function has not been tested, we manually put the order
        # into peer's pending table

        for neighbor in neighbor_list:
            orderinfo = OrderInfo(
                engine=setup_engine,
                order=order,
                master=neighbor,
                arrival_time=peer.birth_time,
                priority=None,
                prev_owner=neighbor,
                novelty=0,
            )
            if order not in peer.order_pending_orderinfo_mapping:
                peer.order_pending_orderinfo_mapping[order] = [orderinfo]
            else:
                peer.order_pending_orderinfo_mapping[order].append(orderinfo)
        order.hesitators.add(peer)

        # manually set storage_decisions for the order. All are False.

        for orderinfo in peer.order_pending_orderinfo_mapping[order]:
            orderinfo.storage_decision = False

        # Disable engine.store_or_discard_orders which will otherwise
        # change the values for orderinfo.storage_decision
        def fake_storage_decision(_node):
            pass

        monkeypatch.setattr(
            setup_engine, "store_or_discard_orders", fake_storage_decision
        )

        # Act.
        peer.store_orders()

        # Assert.

        # order should have been stored and it is the right version.
        assert order not in peer.order_orderinfo_mapping
        # peer's pending table should have been cleared.
        assert peer.order_pending_orderinfo_mapping == {}

    def test_store_orders__sender_disconnected(
        self, setup_scenario, setup_engine, monkeypatch
    ) -> None:
        """
        This function tests the case of storing an order from some peer recently disconnected
        (it was a neighbor when sending this order to the peer).
        :param setup_scenario: fixture.
        :param setup_engine: fixture.
        :param monkeypatch: tool for fake function.
        :return: None.
        """

        # Arrange.

        # Create a peer and a neighbor for this peer.
        peer: Peer = create_a_test_peer(setup_scenario, setup_engine)[0]
        neighbor: Peer = create_a_test_peer(setup_scenario, setup_engine)[0]
        neighbor.add_neighbor(peer)
        peer.add_neighbor(neighbor)

        # create an order and the neighbor has this order.
        order: Order = create_a_test_order(setup_scenario)
        neighbor.receive_order_external(order)
        neighbor.store_orders()

        # We manually put the order into peer's pending table

        orderinfo = OrderInfo(
            engine=setup_engine,
            order=order,
            master=neighbor,
            arrival_time=peer.birth_time,
            priority=None,
            prev_owner=neighbor,
            novelty=0,
        )
        peer.order_pending_orderinfo_mapping[order] = [orderinfo]
        order.hesitators.add(peer)

        # manually set storage_decisions for the order.
        orderinfo.storage_decision = True

        # now let us disconnect neighbor_disconnect
        peer.del_neighbor(neighbor)

        # Disable engine.store_or_discard_orders which will otherwise
        # change the values for orderinfo.storage_decision
        def fake_storage_decision(_node):
            pass

        monkeypatch.setattr(
            setup_engine, "store_or_discard_orders", fake_storage_decision
        )

        # Act.
        peer.store_orders()

        # Assert.

        # order should have been stored, though the neighbor left.
        assert peer.order_orderinfo_mapping[order].prev_owner == neighbor
        # check peer's pending table. It should have been cleared.
        assert peer.order_pending_orderinfo_mapping == {}

    def test_store_orders__multi_orderinfo_error(
        self, setup_scenario, setup_engine, monkeypatch
    ) -> None:
        """
        This function tests if an order has multiple orderinfo instances and more than one is
        labeled as to store. In such case an error is expected.
        :param setup_scenario: fixture.
        :param setup_engine: fixture.
        :param monkeypatch: tool for fake function.
        :return: None.
        """

        # Arrange.

        # Create a peer and two neighbors for this peer.
        peer: Peer = create_a_test_peer(setup_scenario, setup_engine)[0]
        neighbor_list: List[Peer] = create_test_peers(setup_scenario, setup_engine, 2)

        # order will have multiple orderinfo instances to store and raise an error
        order: Order = create_a_test_order(setup_scenario)

        for neighbor in neighbor_list:
            # each neighbor receives the orders and becomes the neighbor of the peer.
            neighbor.receive_order_external(order)
            neighbor.store_orders()
            neighbor.add_neighbor(peer)
            peer.add_neighbor(neighbor)

        # since receive_order_internal() function has not been tested, we manually put the order
        # into peer's pending table

        for neighbor in neighbor_list:
            orderinfo = OrderInfo(
                engine=setup_engine,
                order=order,
                master=neighbor,
                arrival_time=peer.birth_time,
                priority=None,
                prev_owner=neighbor,
                novelty=0,
            )
            if order not in peer.order_pending_orderinfo_mapping:
                peer.order_pending_orderinfo_mapping[order] = [orderinfo]
            else:
                peer.order_pending_orderinfo_mapping[order].append(orderinfo)
            order.hesitators.add(peer)

        # manually set storage_decisions for each order as True
        for orderinfo in peer.order_pending_orderinfo_mapping[order]:
            orderinfo.storage_decision = True

        # Disable engine.store_or_discard_orders which will otherwise
        # change the values for orderinfo.storage_decision
        def fake_storage_decision(_node):
            pass

        monkeypatch.setattr(
            setup_engine, "store_or_discard_orders", fake_storage_decision
        )

        # Act and Assert.
        with pytest.raises(ValueError):
            peer.store_orders()


class TestReceiveInternal:
    """
    This class contains test functions for receive_order_internal().
    """

    def test_receive_order_internal__from_non_neighbor(
        self, setup_scenario, setup_engine
    ):
        """
        Test receiving an internal order from a non-neighbor. Error expeceted.
        :param setup_scenario: fixture.
        :param setup_engine: fixture.
        :return: None.
        """

        # Arrange.
        peer_list: List[Peer] = create_test_peers(setup_scenario, setup_engine, 2)
        order: Order = create_a_test_order(setup_scenario)
        peer_list[1].receive_order_external(order)
        peer_list[1].store_orders()

        # Act and Assert.
        with pytest.raises(ValueError):
            peer_list[0].receive_order_internal(peer_list[1], order)

    def test_receive_order_internal__normal(self, setup_scenario, setup_engine):
        """
        Test receiving an internal order normally.
        :param setup_scenario: fixture.
        :param setup_engine: fixture.
        :return: None.
        """

        # Arrange.
        peer_list: List[Peer] = create_test_peers(setup_scenario, setup_engine, 2)
        peer_list[0].add_neighbor(peer_list[1])
        peer_list[1].add_neighbor(peer_list[0])
        order: Order = create_a_test_order(setup_scenario)
        peer_list[1].receive_order_external(order)
        peer_list[1].store_orders()

        # Act.
        peer_list[0].receive_order_internal(peer_list[1], order)

        # Assert.
        assert order in peer_list[0].order_pending_orderinfo_mapping

    def test_receive_order_internal_not_accepted(
        self, setup_scenario, setup_engine, monkeypatch
    ):
        """
        Test receiving an internal order labeled as not to accept by the receiver.
        :param setup_scenario: fixture.
        :param setup_engine: fixture.
        :return: None.
        """

        # Arrange.
        # Changes the decision of accepting an internal order from always yes to always no.
        def fake_should_accept_internal_order(_receiver, _sender, _order):
            return False

        monkeypatch.setattr(
            setup_engine,
            "should_accept_internal_order",
            fake_should_accept_internal_order,
        )

        # Same as the test above.
        peer_list: List[Peer] = create_test_peers(setup_scenario, setup_engine, 2)
        peer_list[0].add_neighbor(peer_list[1])
        peer_list[1].add_neighbor(peer_list[0])
        order: Order = create_a_test_order(setup_scenario)
        peer_list[1].receive_order_external(order)
        peer_list[1].store_orders()

        # Act.
        peer_list[0].receive_order_internal(peer_list[1], order)

        # Assert. Now it should not be accepted.
        assert order not in peer_list[0].order_pending_orderinfo_mapping

    def test_receive_order_internal_duplicate_from_same_neighbor(
        self, setup_scenario, setup_engine
    ):
        """
        Test receiving the same internal order from the neighbor multiple times.
        :param setup_scenario: fixture.
        :param setup_engine: fixture.
        :return: None.
        """

        # Arrange.
        peer_list: List[Peer] = create_test_peers(setup_scenario, setup_engine, 2)
        peer_list[0].add_neighbor(peer_list[1])
        peer_list[1].add_neighbor(peer_list[0])
        order: Order = create_a_test_order(setup_scenario)
        peer_list[1].receive_order_external(order)
        peer_list[1].store_orders()

        # Act.
        peer_list[0].receive_order_internal(peer_list[1], order)
        peer_list[0].receive_order_internal(peer_list[1], order)

        # Assert.
        assert len(peer_list[0].order_pending_orderinfo_mapping[order]) == 1

    def test_receive_order_internal_duplicate_from_others(
        self, setup_scenario, setup_engine
    ):
        """
        Test receiving the same internal order from different neighbors for multiple times.
        :param setup_scenario: fixture.
        :param setup_engine: fixture.
        :return: None.
        """

        # Arrange.
        peer_list: List[Peer] = create_test_peers(setup_scenario, setup_engine, 3)
        for neighbor in (peer_list[1], peer_list[2]):
            peer_list[0].add_neighbor(neighbor)
            neighbor.add_neighbor(peer_list[0])
        order: Order = create_a_test_order(setup_scenario)
        for neighbor in (peer_list[1], peer_list[2]):
            neighbor.receive_order_external(order)
            neighbor.store_orders()

        # Act.
        for neighbor in (peer_list[1], peer_list[2]):
            peer_list[0].receive_order_internal(neighbor, order)

        # Assert. Both copies should be in the pending table.
        assert len(peer_list[0].order_pending_orderinfo_mapping[order]) == 2


class TestShareOrders:
    """
    This class contains test functions for share_order() function.
    """

    def test_share_orders__normal(
        self, setup_scenario, setup_engine, monkeypatch
    ) -> None:
        """
        This function tests share_orders(). It mocks find_orders_to_share() and
        find_neighbors_to_share() function by only selecting orders/peers with sequence number less
        than 100.
        :param setup_scenario: fixture.
        :param setup_engine: fixture.
        :param monkeypatch: mocking tool.
        :return: None.
        """

        # Arrange.

        # mock the method of find orders/peers to share

        def mock_find_orders_to_share(peer):
            return set(
                any_order
                for any_order in peer.order_orderinfo_mapping
                if any_order.seq < 100
            )

        def mock_find_neighbors_to_share(_time_now, peer):
            return set(
                any_peer
                for any_peer in peer.peer_neighbor_mapping
                if any_peer.seq < 100
            )

        monkeypatch.setattr(
            setup_engine, "find_orders_to_share", mock_find_orders_to_share
        )
        monkeypatch.setattr(
            setup_engine, "find_neighbors_to_share", mock_find_neighbors_to_share
        )

        # peer is a normal peer. We will add three neighbors for it.
        # We will change the sequence number of neighbor 2 and one of the initial orders of the peer

        peer, order_set = create_a_test_peer(setup_scenario, setup_engine)

        neighbor_list = create_test_peers(setup_scenario, setup_engine, 3)
        neighbor_list[2].seq = 101

        unlucky_order = random.sample(order_set, 1)[0]
        unlucky_order.seq = 280

        for neighbor in neighbor_list:
            peer.add_neighbor(neighbor)
            neighbor.add_neighbor(peer)

        # Act.

        order_sharing_set, beneficiary_set = peer.share_orders()

        # Assert.
        assert len(beneficiary_set) == 2 and neighbor_list[2] not in beneficiary_set
        assert len(order_sharing_set) == 4 and unlucky_order not in order_sharing_set
        assert peer.new_order_set == set()

    def test_share_orders__free_rider(self, setup_scenario, setup_engine) -> None:
        """
        Test sharing behavior of a free rider. Should not share anything.
        :param setup_scenario: fixture.
        :param setup_engine: fixture.
        :return: None.
        """

        # Arrange.
        free_rider: Peer = create_a_test_peer(setup_scenario, setup_engine)[0]
        free_rider.is_free_rider = True

        # Give the free rider three neighbors
        neighbor_list: List[Peer] = create_test_peers(setup_scenario, setup_engine, 3)
        for neighbor in neighbor_list:
            free_rider.add_neighbor(neighbor)
            neighbor.add_neighbor(free_rider)

        # Act and Assert.
        assert free_rider.share_orders() == (set(), set())


class TestDelOrder:
    """
    This class contains functions to test del_order().
    """

    def test_del_order__in_storage(self, setup_scenario, setup_engine) -> None:
        """
        This function tests del_orders() when order is in local storage.
        :param setup_scenario: fixture.
        :param setup_engine: fixture.
        :return: None.
        """

        # Arrange.

        # create peer
        my_peer: Peer = create_a_test_peer(setup_scenario, setup_engine)[0]
        # create new orders
        new_order: Order = create_a_test_order(setup_scenario)

        # my_peer receives an external order and stores it.
        my_peer.receive_order_external(new_order)
        my_peer.store_orders()

        # Act.
        my_peer.del_order(new_order)

        # Assert.
        assert new_order not in my_peer.order_orderinfo_mapping

    def test_del_order__in_pending_table(self, setup_scenario, setup_engine) -> None:
        """
        This function tests del_orders() when orders are in pending table.
        :param setup_scenario: fixture.
        :param setup_engine: fixture.
        :return: None.
        """

        # Arrange.

        # create peers.
        peer_list: List[Peer] = create_test_peers(setup_scenario, setup_engine, 3)
        my_peer: Peer = peer_list[0]
        neighbor_one: Peer = peer_list[1]
        neighbor_two: Peer = peer_list[2]

        # create new orders
        new_order_list: List[Order] = create_test_orders(setup_scenario, 2)

        # add neighbors
        my_peer.add_neighbor(neighbor_one)
        my_peer.add_neighbor(neighbor_two)
        neighbor_one.add_neighbor(my_peer)
        neighbor_two.add_neighbor(my_peer)

        # both new_order_list[0] and new_order_list[1] will be put into both neighbor's local
        # storage, for new_order_list[0], my_peer will receive from both neighbors,
        # but for new_order_list[1], it will only receive from neighbor_one

        for neighbor in [neighbor_one, neighbor_two]:
            for new_order in (new_order_list[0], new_order_list[1]):
                neighbor.receive_order_external(new_order)
                neighbor.store_orders()

        my_peer.receive_order_internal(neighbor_one, new_order_list[0])
        my_peer.receive_order_internal(neighbor_two, new_order_list[0])
        my_peer.receive_order_internal(neighbor_one, new_order_list[1])

        # Now, my_peer's pending table should look like
        # {new_order_list[0]: [orderinfo_from_neighbor_1, orderinfo_from_neighbor_2],
        #  new_order_list[1]: [orderinfo_from_neighbor_1]}

        # Act.
        # delete all new orders
        my_peer.del_order(new_order_list[0])
        my_peer.del_order(new_order_list[1])

        # Assert.
        assert new_order_list[0] not in my_peer.order_pending_orderinfo_mapping
        assert new_order_list[1] not in my_peer.order_pending_orderinfo_mapping

    def test_del_order__not_existing(self, setup_scenario, setup_engine) -> None:
        """
        This function tests del_orders() when the peer does not have this order.
        According to our design, nothing will happen under this case.
        :param setup_scenario: fixture.
        :param setup_engine: fixture.
        :return: None.
        """

        # Arrange.
        # create peers.
        my_peer: Peer = create_a_test_peer(setup_scenario, setup_engine)[0]
        # create an order
        new_order: Order = create_a_test_order(setup_scenario)

        # Act.
        # Delete the new order
        my_peer.del_order(new_order)

        # Assert.
        # No error should be raised.
        assert new_order not in my_peer.order_pending_orderinfo_mapping
        assert new_order not in my_peer.order_orderinfo_mapping


class TestRankNeighbors:
    """
    This class contains a test function for rank_neighbors().
    """

    def test_rank_neighbors(self, setup_scenario, setup_engine, monkeypatch) -> None:
        """
        This function tests rank_neighbors(). We disable score_neighbors() function which will
        change the score of neighbors, and use a mocked one to replace it.
        :param setup_scenario: fixture.
        :param setup_engine: fixture.
        :param monkeypatch: tool for fake function.
        :return: None
        """

        # Arrange.

        # Disable score_neighbors() function. Otherwise rank_neighbors() will change the scores that
        # we have specifically set for this test.

        def fake_score_neighbors(_peer):
            pass

        monkeypatch.setattr(setup_engine, "score_neighbors", fake_score_neighbors)

        # create peer list
        peer_list: List[Peer] = create_test_peers(setup_scenario, setup_engine, 4)

        peer_list[0].add_neighbor(peer_list[1])
        peer_list[0].add_neighbor(peer_list[2])
        peer_list[0].add_neighbor(peer_list[3])

        # manually set their scores

        peer_list[0].peer_neighbor_mapping[peer_list[1]].score = 50
        peer_list[0].peer_neighbor_mapping[peer_list[2]].score = 10
        peer_list[0].peer_neighbor_mapping[peer_list[3]].score = 80

        # Act and Assert.

        # assert the return value of rank_neighbors(). Should be a list of peer instances ranked by
        # the score of their corresponding neighbor instances at peer_list[0], from highest to
        # lowest.
        assert peer_list[0].rank_neighbors() == [
            peer_list[3],
            peer_list[1],
            peer_list[2],
        ]


class TestScoringSystem:
    """
    This function tests the scoring system for neighbors to contribute. Score changes happen in
    receive_order_internal() and store_orders(), but it is difficult to cover all cases when
    tests of these two functions are focused on other perspectives.
    So we decided to have an individual test function for the score updates.
    """

    def test_scoring_system_penalty_a(
        self, setup_scenario, setup_engine, monkeypatch
    ) -> None:
        """
        This function tests the case for penalty_a
        :param setup_scenario: fixture
        :param setup_engine: fixture
        :param monkeypatch: tool for fake function.
        :return: None
        """
        # Setting for this case:
        # Order does not pass should_accept_internal_order()
        # Order rejected since it doesn't pass should_accept_internal_order() (penalty_a).

        # Arrange.

        my_peer: Peer = create_a_test_peer(setup_scenario, setup_engine)[0]
        neighbor: Peer = create_a_test_peer(setup_scenario, setup_engine)[0]
        order: Order = create_a_test_order(setup_scenario)

        # establish neighborhood
        my_peer.add_neighbor(neighbor)
        neighbor.add_neighbor(my_peer)

        # let neighbor own the order that it should have
        neighbor.receive_order_external(order)
        neighbor.store_orders()

        # clear score sheet for neighbors
        my_peer.peer_neighbor_mapping[neighbor].share_contribution[-1] = 0

        # define fake functions.
        # Order cannot be accepted to the pending list
        def fake_should_accept_internal_order(_receiver, _sender, _order):
            return False

        # This fake function sets storage_decision as True for any orderinfo.
        def fake_store_or_discard_orders(peer):
            for orderinfo_list in peer.order_pending_orderinfo_mapping.values():
                for orderinfo in orderinfo_list:
                    orderinfo.storage_decision = True

        monkeypatch.setattr(
            setup_engine, "store_or_discard_orders", fake_store_or_discard_orders
        )
        monkeypatch.setattr(
            setup_engine,
            "should_accept_internal_order",
            fake_should_accept_internal_order,
        )

        # Act.

        # neighbor sends the order to my_peer
        my_peer.receive_order_internal(neighbor, order)
        # store orders
        my_peer.store_orders()
        # calculate scores. The value equals to the last entry of the score sheet.
        my_peer.rank_neighbors()

        # Assert.
        assert my_peer.peer_neighbor_mapping[neighbor].score == pytest.approx(-13)

    def test_scoring_system_reward_a(
        self, setup_scenario, setup_engine, monkeypatch
    ) -> None:
        """
        This function tests the case for reward_a
        :param setup_scenario: fixture
        :param setup_engine: fixture
        :param monkeypatch: tool for fake function.
        :return: None
        """

        # Setting for this case:
        # my_peer's initial status:
        # Local storage: there is an Order instance from the same neighbor
        # Behavior: neighbor sends order to my_peer
        # Result: Order rejected since there's a duplicate in local storage from the same neighbor (
        # reward_a).

        # Arrange.

        my_peer: Peer = create_a_test_peer(setup_scenario, setup_engine)[0]
        neighbor: Peer = create_a_test_peer(setup_scenario, setup_engine)[0]
        order: Order = create_a_test_order(setup_scenario)

        # establish neighborhood
        my_peer.add_neighbor(neighbor)
        neighbor.add_neighbor(my_peer)

        # let neighbor own the order that it should have
        neighbor.receive_order_external(order)
        neighbor.store_orders()

        # setup the initial status for my_peer
        my_peer.receive_order_internal(neighbor, order)
        my_peer.store_orders()

        # clear score sheet for neighbor
        my_peer.peer_neighbor_mapping[neighbor].share_contribution[-1] = 0

        # define fake functions.

        # This fake function sets storage_decision as True for any orderinfo.
        def fake_store_or_discard_orders(peer):
            for orderinfo_list in peer.order_pending_orderinfo_mapping.values():
                for orderinfo in orderinfo_list:
                    orderinfo.storage_decision = True

        monkeypatch.setattr(
            setup_engine, "store_or_discard_orders", fake_store_or_discard_orders
        )

        # Act.

        # neighbor sends the order to my_peer
        my_peer.receive_order_internal(neighbor, order)
        # store orders
        my_peer.store_orders()
        # calculate scores. The value equals to the last entry of the score sheet.
        my_peer.rank_neighbors()

        # Assert.
        assert my_peer.peer_neighbor_mapping[neighbor].score == pytest.approx(2)

    def test_scoring_system_reward_b(
        self, setup_scenario, setup_engine, monkeypatch
    ) -> None:
        """
        This function tests the case for reward_b
        :param setup_scenario: fixture
        :param setup_engine: fixture
        :param monkeypatch: tool for fake function.
        :return: None
        """

        # Setting for this case:
        # my_peer's initial status:
        # Local storage: there is an Order instance from the competitor.
        # Behavior: neighbor sends order to my_peer
        # Result: Order rejected since there's a duplicate in local storage from competitor \(
        # reward_b).

        # Arrange.

        my_peer: Peer = create_a_test_peer(setup_scenario, setup_engine)[0]
        neighbor: Peer = create_a_test_peer(setup_scenario, setup_engine)[0]
        competitor: Peer = create_a_test_peer(setup_scenario, setup_engine)[0]
        order: Order = create_a_test_order(setup_scenario)

        # establish neighborhood
        for anyone in (neighbor, competitor):
            my_peer.add_neighbor(anyone)
            anyone.add_neighbor(my_peer)

        # let neighbor and competitor own the order that it should have
        for anyone in (neighbor, competitor):
            anyone.receive_order_external(order)
            anyone.store_orders()

        # setup the initial status for my_peer
        my_peer.receive_order_internal(competitor, order)
        my_peer.store_orders()

        # clear score sheet for neighbor
        my_peer.peer_neighbor_mapping[neighbor].share_contribution[-1] = 0

        # define fake functions.

        # This fake function sets storage_decision as True for any orderinfo.
        def fake_store_or_discard_orders(peer):
            for orderinfo_list in peer.order_pending_orderinfo_mapping.values():
                for orderinfo in orderinfo_list:
                    orderinfo.storage_decision = True

        monkeypatch.setattr(
            setup_engine, "store_or_discard_orders", fake_store_or_discard_orders
        )

        # Act.

        # neighbor sends the order to my_peer
        my_peer.receive_order_internal(neighbor, order)
        # store orders
        my_peer.store_orders()
        # calculate scores. The value equals to the last entry of the score sheet.
        my_peer.rank_neighbors()

        # Assert.
        assert my_peer.peer_neighbor_mapping[neighbor].score == pytest.approx(3)

    def test_scoring_system_penalty_b(
        self, setup_scenario, setup_engine, monkeypatch
    ) -> None:
        """
        This function tests the case for penalty_b
        :param setup_scenario: fixture
        :param setup_engine: fixture
        :param monkeypatch: tool for fake function.
        :return: None
        """

        # Setting for this case:
        # my_peer's initial status:
        # Pending table: there is an Order instance from the same neighbor
        # Behavior: neighbor sends order to my_peer
        # Result: The second copy rejected since there's a duplicate in pending table from the same
        # neighbor (penalty_b); however, the first version will be stored finally (reward_d)

        # Arrange.

        my_peer: Peer = create_a_test_peer(setup_scenario, setup_engine)[0]
        neighbor: Peer = create_a_test_peer(setup_scenario, setup_engine)[0]
        order: Order = create_a_test_order(setup_scenario)

        # establish neighborhood
        my_peer.add_neighbor(neighbor)
        neighbor.add_neighbor(my_peer)

        # let neighbor own the order that it should have
        neighbor.receive_order_external(order)
        neighbor.store_orders()

        # setup the initial status for my_peer
        my_peer.receive_order_internal(neighbor, order)

        # clear score sheet for neighbor
        my_peer.peer_neighbor_mapping[neighbor].share_contribution[-1] = 0

        # define fake functions.

        # This fake function sets storage_decision as True for any orderinfo.
        def fake_store_or_discard_orders(peer):
            for orderinfo_list in peer.order_pending_orderinfo_mapping.values():
                for orderinfo in orderinfo_list:
                    orderinfo.storage_decision = True

        monkeypatch.setattr(
            setup_engine, "store_or_discard_orders", fake_store_or_discard_orders
        )

        # Act.

        # neighbor sends the order to my_peer
        my_peer.receive_order_internal(neighbor, order)
        # store orders
        my_peer.store_orders()
        # calculate scores. The value equals to the last entry of the score sheet.
        my_peer.rank_neighbors()

        # Assert.

        assert my_peer.peer_neighbor_mapping[neighbor].score == pytest.approx(-10)

    def test_scoring_system_reward_c(
        self, setup_scenario, setup_engine, monkeypatch
    ) -> None:
        """
        This function tests the case for reward_c
        :param setup_scenario: fixture
        :param setup_engine: fixture
        :param monkeypatch: tool for fake function.
        :return: None
        """
        # Setting for this case:
        # Order passes should_accept_internal_order() but storage_decision is False
        # Order accepted to pending table, rejected to storage, and gets reward_c

        # Arrange.

        my_peer: Peer = create_a_test_peer(setup_scenario, setup_engine)[0]
        neighbor: Peer = create_a_test_peer(setup_scenario, setup_engine)[0]
        order: Order = create_a_test_order(setup_scenario)

        # establish neighborhood
        my_peer.add_neighbor(neighbor)
        neighbor.add_neighbor(my_peer)

        # let neighbor own the order that it should have
        neighbor.receive_order_external(order)
        neighbor.store_orders()

        # clear score sheet for neighbors
        my_peer.peer_neighbor_mapping[neighbor].share_contribution[-1] = 0

        # define fake functions.

        # This fake function sets storage_decision as True for any orderinfo.
        def fake_store_or_discard_orders(peer):
            for orderinfo_list in peer.order_pending_orderinfo_mapping.values():
                for orderinfo in orderinfo_list:
                    orderinfo.storage_decision = False

        monkeypatch.setattr(
            setup_engine, "store_or_discard_orders", fake_store_or_discard_orders
        )

        # Act.

        # neighbor sends the order to my_peer
        my_peer.receive_order_internal(neighbor, order)
        # store orders
        my_peer.store_orders()
        # calculate scores. The value equals to the last entry of the score sheet.
        my_peer.rank_neighbors()

        # Assert.

        assert my_peer.peer_neighbor_mapping[neighbor].score == pytest.approx(5)

    def test_scoring_system_reward_d(
        self, setup_scenario, setup_engine, monkeypatch
    ) -> None:
        """
        This function tests the case for reward_d
        :param setup_scenario: fixture
        :param setup_engine: fixture
        :param monkeypatch: tool for fake function.
        :return: None
        """

        # Setting for this case:
        # my_peer's initial status:
        # Pending table: there is a pending orderinfo instance from the competitor.
        # Behavior: neighbor sends order to my_peer
        # Result: Order from neighbor stored since neighbor won over competitor (reward_d).

        # Arrange.

        my_peer: Peer = create_a_test_peer(setup_scenario, setup_engine)[0]
        neighbor: Peer = create_a_test_peer(setup_scenario, setup_engine)[0]
        competitor: Peer = create_a_test_peer(setup_scenario, setup_engine)[0]
        order: Order = create_a_test_order(setup_scenario)

        # establish neighborhood
        for anyone in (neighbor, competitor):
            my_peer.add_neighbor(anyone)
            anyone.add_neighbor(my_peer)

        # let neighbor and competitor own the order that it should have
        for anyone in (neighbor, competitor):
            anyone.receive_order_external(order)
            anyone.store_orders()

        # setup the initial status for my_peer
        my_peer.receive_order_internal(competitor, order)

        # clear score sheet for neighbor
        my_peer.peer_neighbor_mapping[neighbor].share_contribution[-1] = 0

        # define fake functions.

        # This fake function sets storage_decision as True for any orderinfo.
        def fake_store_or_discard_orders(peer):
            for orderinfo_list in peer.order_pending_orderinfo_mapping.values():
                for orderinfo in orderinfo_list:
                    if orderinfo.prev_owner == neighbor:
                        orderinfo.storage_decision = True
                    else:
                        orderinfo.storage_decision = False

        monkeypatch.setattr(
            setup_engine, "store_or_discard_orders", fake_store_or_discard_orders
        )

        # Act.

        # neighbor sends the order to my_peer
        my_peer.receive_order_internal(neighbor, order)
        # store orders
        my_peer.store_orders()
        # calculate scores. The value equals to the last entry of the score sheet.
        my_peer.rank_neighbors()

        # Assert.
        assert my_peer.peer_neighbor_mapping[neighbor].score == pytest.approx(7)

    def test_scoring_system_reward_e(
        self, setup_scenario, setup_engine, monkeypatch
    ) -> None:
        """
        This function tests the case for reward_d
        :param setup_scenario: fixture
        :param setup_engine: fixture
        :param monkeypatch: tool for fake function.
        :return: None
        """

        # Setting for this case:
        # my_peer's initial status:
        # Pending table: there is a pending orderinfo instance from the competitor.
        # Behavior: neighbor sends order to my_peer
        # Result: Order from neighbor not stored since competitor won over neighbor (reward_e).

        # Arrange.

        my_peer: Peer = create_a_test_peer(setup_scenario, setup_engine)[0]
        neighbor: Peer = create_a_test_peer(setup_scenario, setup_engine)[0]
        competitor: Peer = create_a_test_peer(setup_scenario, setup_engine)[0]
        order: Order = create_a_test_order(setup_scenario)

        # establish neighborhood
        for anyone in (neighbor, competitor):
            my_peer.add_neighbor(anyone)
            anyone.add_neighbor(my_peer)

        # let neighbor and competitor own the order that it should have
        for anyone in (neighbor, competitor):
            anyone.receive_order_external(order)
            anyone.store_orders()

        # setup the initial status for my_peer
        my_peer.receive_order_internal(competitor, order)

        # clear score sheet for neighbor
        my_peer.peer_neighbor_mapping[neighbor].share_contribution[-1] = 0

        # define fake functions.

        # This fake function sets storage_decision as True for any orderinfo.
        def fake_store_or_discard_orders(peer):
            for orderinfo_list in peer.order_pending_orderinfo_mapping.values():
                for orderinfo in orderinfo_list:
                    if orderinfo.prev_owner == neighbor:
                        orderinfo.storage_decision = False
                    else:
                        orderinfo.storage_decision = True

        monkeypatch.setattr(
            setup_engine, "store_or_discard_orders", fake_store_or_discard_orders
        )

        # Act.

        # neighbor sends the order to my_peer
        my_peer.receive_order_internal(neighbor, order)
        # store orders
        my_peer.store_orders()
        # calculate scores. The value equals to the last entry of the score sheet.
        my_peer.rank_neighbors()

        # Assert.

        assert my_peer.peer_neighbor_mapping[neighbor].score == pytest.approx(11)


class TestDelNeighborWithRemoveOrder:
    """
    This class contains test cases for del_neighbor() with remove order enabled.
    """

    def test_del_neighbor_with_remove_order__in_storage(
        self, setup_scenario, setup_engine
    ) -> None:
        """
        Test when there is an order from the deleted neighbor in the local storage.
        :param setup_scenario: fixture.
        :param setup_engine: fixture.
        :return: None.
        """

        # Arrange.

        # create my_peer and a neighbor. Later, the neighbor will be deleted.
        my_peer: Peer = create_a_test_peer(setup_scenario, setup_engine)[0]
        neighbor: Peer = create_a_test_peer(setup_scenario, setup_engine)[0]
        my_peer.add_neighbor(neighbor)
        neighbor.add_neighbor(my_peer)

        # we have a new order. Neighbor has it.
        order: Order = create_a_test_order(setup_scenario)
        neighbor.receive_order_external(order)
        neighbor.store_orders()

        # my_peer will have the order in local storage, from the neighbor
        my_peer.receive_order_internal(neighbor, order)
        my_peer.store_orders()

        # Act.

        # my_peer deletes neighbor and cancels orders from it.
        my_peer.del_neighbor(neighbor, remove_order=True)

        # Assert.

        # Now order should have been deleted from local storage.
        assert order not in my_peer.order_orderinfo_mapping

    def test_del_neighbor_with_remove_order__single_pending_orderinfo(
        self, setup_scenario, setup_engine
    ) -> None:
        """
        Test if there is a single orderinfo from the deleted neighbor in the pending table.
        :param setup_scenario: fixture.
        :param setup_engine: fixture.
        :return: None.
        """

        # Arrange.

        # create my_peer and a neighbor. Later, the neighbor will be deleted.
        my_peer: Peer = create_a_test_peer(setup_scenario, setup_engine)[0]
        neighbor: Peer = create_a_test_peer(setup_scenario, setup_engine)[0]
        my_peer.add_neighbor(neighbor)
        neighbor.add_neighbor(my_peer)

        # we have a new order. Neighbor has it.
        order: Order = create_a_test_order(setup_scenario)
        neighbor.receive_order_external(order)
        neighbor.store_orders()

        # my_peer will have the order in the pending table, from the neighbor
        my_peer.receive_order_internal(neighbor, order)

        # Act.

        # my_peer deletes neighbor and cancels orders from it.
        my_peer.del_neighbor(neighbor, remove_order=True)

        # Assert.

        # Now order should have been deleted from local storage.
        assert order not in my_peer.order_pending_orderinfo_mapping

    def test_del_neighbor_with_remove_order__multi_pending_orderinfo(
        self, setup_scenario, setup_engine
    ) -> None:
        """
        Test if there are multiple orderinfos, one from the deleted neighbor, in the pending table.
        :param setup_scenario: fixture.
        :param setup_engine: fixture.
        :return: None.
        """

        # Arrange.

        # create my_peer and neighbors. Later, neighbor_list[0] will be deleted.
        my_peer: Peer = create_a_test_peer(setup_scenario, setup_engine)[0]
        neighbor_list: List[Peer] = create_test_peers(setup_scenario, setup_engine, 2)
        for neighbor in neighbor_list:
            my_peer.add_neighbor(neighbor)
            neighbor.add_neighbor(my_peer)

        # new order.
        order: Order = create_a_test_order(setup_scenario)
        for neighbor in neighbor_list:
            neighbor.receive_order_external(order)
            neighbor.store_orders()

        # my_peer also has order in pending table. It has versions from both neighbors.
        for neighbor in neighbor_list:
            my_peer.receive_order_internal(neighbor, order)

        # Act.

        # my_peer deletes neighbor 0 and cancels orders from it.
        my_peer.del_neighbor(neighbor_list[0], remove_order=True)

        # Assert.

        # Now order should still be in the pending table, but the copy is not from neighbor[0]
        assert len(my_peer.order_pending_orderinfo_mapping[order]) == 1
        assert (
            my_peer.order_pending_orderinfo_mapping[order][0].prev_owner
            == neighbor_list[1]
        )
