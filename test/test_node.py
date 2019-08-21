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


def test_order(setup_scenario) -> None:
    """
    This function tests an order initialization.
    :param setup_scenario: the fixture function's return value
    :return: None
    """
    my_order: Order = create_a_test_order(setup_scenario)
    assert my_order.seq == 5
    assert my_order.birth_time == 12
    assert my_order.scenario.peer_type_property["normal"].ratio == pytest.approx(0.9)
    assert my_order.scenario.peer_type_property["free_rider"].ratio == pytest.approx(
        0.1
    )


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


def create_a_test_peer(
    scenario: Scenario, engine: Engine
) -> Tuple[Peer, Set[Order]]:
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


def test_peer(setup_scenario, setup_engine) -> None:
    """
    This function tests peer initialization.
    :param setup_scenario: fixture.
    :param setup_engine: fixture.
    :return: None.
    """

    my_peer, order_set = create_a_test_peer(setup_scenario, setup_engine)

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


def test_add_neighbor(setup_scenario, setup_engine) -> None:
    """
    Test function for add_neighbor() function.
    :param setup_scenario: fixture.
    :param setup_engine: fixture.
    :return: None
    """

    # We have three peers.
    peer_list: List[Peer] = create_test_peers(setup_scenario, setup_engine, 3)

    # add peer_list[1] and peer_list[2] into peer_list[0]'s neighbor,
    # assert if the neighbor can be found and if neighbor size is correct.
    peer_list[0].add_neighbor(peer_list[1])
    assert peer_list[1] in peer_list[0].peer_neighbor_mapping
    peer_list[0].add_neighbor(peer_list[2])
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

    # add an existing neighbor again
    with pytest.raises(ValueError):
        peer_list[0].add_neighbor(peer_list[1])

    # add self
    with pytest.raises(ValueError):
        peer_list[0].add_neighbor(peer_list[0])


def test_should_accept_neighbor_request(
    setup_scenario, setup_engine, monkeypatch
) -> None:
    """
    This function tests should_accept_neighbor_request() function.
    :param setup_scenario: fixture.
    :param setup_engine: fixture.
    :param monkeypatch: tool for fake attribute
    :return: None
    """

    # create two peers
    peer_list: List[Peer] = create_test_peers(setup_scenario, setup_engine, 2)

    # should accept invitation
    assert peer_list[0].should_accept_neighbor_request(peer_list[1]) is True

    peer_list[0].add_neighbor(peer_list[1])
    peer_list[1].add_neighbor(peer_list[0])

    # when they're already neighbors and peer_two still requests, an error should be raised.
    with pytest.raises(ValueError):
        peer_list[0].should_accept_neighbor_request(peer_list[1])
    with pytest.raises(ValueError):
        peer_list[1].should_accept_neighbor_request(peer_list[0])

    # a peer sends a request to itself. An error should be raised.
    with pytest.raises(ValueError):
        peer_list[0].should_accept_neighbor_request(peer_list[0])

    # Now, fake max neighbor size to 1.
    def fake_max_size():
        return 1

    monkeypatch.setattr(setup_engine, "neighbor_max", fake_max_size())

    # peer one has already had a neighbor, so it should reject this time.
    another_peer, _ = create_a_test_peer(setup_scenario, setup_engine)
    assert peer_list[0].should_accept_neighbor_request(another_peer) is False


def test_del_neighbor(setup_scenario, setup_engine) -> None:
    """
    Test del_neighbor() function.
    :param setup_scenario: fixture.
    :param setup_engine: fixture.
    :return: None
    """

    peer_list: List[Peer] = create_test_peers(setup_scenario, setup_engine, 2)

    peer_list[0].add_neighbor(peer_list[1])
    peer_list[1].add_neighbor(peer_list[0])

    # This deletion should be normal. Both sides should delete the other one.
    peer_list[0].del_neighbor(peer_list[1])

    assert not peer_list[0].peer_neighbor_mapping
    assert not peer_list[1].peer_neighbor_mapping

    # Delete an non-existing neighbor
    with pytest.raises(ValueError):
        peer_list[0].del_neighbor(peer_list[1])

    with pytest.raises(ValueError):
        peer_list[1].del_neighbor(peer_list[0])

    # Delete self.
    with pytest.raises(ValueError):
        peer_list[0].del_neighbor(peer_list[0])

    # Note: we have not tested the "remove_order" option here. However, in order to test it we
    # will need to use functions receive_order_internal() and store_orders(). We will test them
    # first and later, test this function.


def test_receive_order_external(setup_scenario, setup_engine) -> None:
    """
    This function tests receive_order_external()
    :param setup_scenario: fixture.
    :param setup_engine: fixture.
    :return: None
    """

    peer: Peer = create_a_test_peer(setup_scenario, setup_engine)[0]
    order: Order = create_a_test_order(setup_scenario)
    peer.receive_order_external(order)
    assert order in peer.order_pending_orderinfo_mapping
    assert order not in peer.order_orderinfo_mapping
    assert peer in order.hesitators


def test_store_orders(setup_scenario, setup_engine, monkeypatch) -> None:
    """
    Before testing receive_order_internal(), we test store_orders() first. This is because
    store_order() will be used during the test of receive_order_internal().
    :param setup_scenario: fixture.
    :param setup_engine: fixture.
    :param monkeypatch: tool for fake function.
    :return: None.
    """
    # pylint: disable=too-many-branches, too-many-statements
    # This test function needs to deal with lots of cases and it is fine to have a long one.

    # Create a peer and four neighbors for this peer.
    # peer will be connected with all neighbors, but for neighbor_list[3], it will disconnect later.
    peer: Peer = create_a_test_peer(setup_scenario, setup_engine)[0]
    neighbor_list: List[Peer] = create_test_peers(setup_scenario, setup_engine, 4)

    # orders 0 and 1 will have multiple orderinfo instances but only one will be stored
    # order 2 will not be stored since no copy is labeled as to store
    # order 3 will be stored with the orderinfo from neighbor_disconnect (though it is
    # disconnected).
    # order 4 will have multiple orderinfo instances to store and raise an error
    order_list: List[Order] = create_test_orders(setup_scenario, 5)

    for neighbor in neighbor_list:
        # each neighbor first receives the orders.
        for order in order_list:
            neighbor.receive_order_external(order)
        neighbor.add_neighbor(peer)
        peer.add_neighbor(neighbor)

        # this is a normal call of store_orders(). Should store everything.
        neighbor.store_orders()
        for order in order_list:
            # check if every order is stored in every neighbor.
            assert order in neighbor.order_orderinfo_mapping

    # since receive_order_internal() function has not been tested, we manually put the orders 0-3
    # into peer's pending table

    for order in order_list[0:4]:
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

    # check peer's pending table.
    # It should contain four orders, each with four orderinfo instances.
    assert len(peer.order_pending_orderinfo_mapping) == 4
    for orderinfo_list in peer.order_pending_orderinfo_mapping.values():
        assert len(orderinfo_list) == 4

    # manually set storage_decisions for each order.
    # Store neighbor_0's orderinfo instance for order_0, neighbor_2's instance for order_1,
    # do not store order_2, and store neighbor_3's instance for order_3

    for orderinfo in peer.order_pending_orderinfo_mapping[order_list[0]]:
        if orderinfo.prev_owner == neighbor_list[0]:
            orderinfo.storage_decision = True
        else:
            orderinfo.storage_decision = False

    for orderinfo in peer.order_pending_orderinfo_mapping[order_list[1]]:
        if orderinfo.prev_owner == neighbor_list[2]:
            orderinfo.storage_decision = True
        else:
            orderinfo.storage_decision = False

    for orderinfo in peer.order_pending_orderinfo_mapping[order_list[2]]:
        orderinfo.storage_decision = False

    for orderinfo in peer.order_pending_orderinfo_mapping[order_list[3]]:
        if orderinfo.prev_owner == neighbor_list[3]:
            orderinfo.storage_decision = True
        else:
            orderinfo.storage_decision = False

    # now let us disconnect neighbor_disconnect
    peer.del_neighbor(neighbor_list[3])
    assert neighbor_list[3] not in peer.peer_neighbor_mapping

    # Disable engine.store_or_discard_orders which will otherwise
    # change the values for orderinfo.storage_decision
    def fake_storage_decision(_node):
        pass

    monkeypatch.setattr(setup_engine, "store_or_discard_orders", fake_storage_decision)

    # Now let us check store_orders()
    peer.store_orders()

    # order_0 should have been stored
    assert order_list[0] in peer.order_orderinfo_mapping
    assert peer.order_orderinfo_mapping[order_list[0]].prev_owner == neighbor_list[0]

    # order_1 too
    assert order_list[1] in peer.order_orderinfo_mapping
    assert peer.order_orderinfo_mapping[order_list[1]].prev_owner == neighbor_list[2]

    # order_2 should have not been stored
    assert order_list[2] not in peer.order_orderinfo_mapping

    # order_3 should have been stored, though the neighbor left.
    assert order_list[3] in peer.order_orderinfo_mapping
    assert peer.order_orderinfo_mapping[order_list[3]].prev_owner == neighbor_list[3]

    # check peer's pending table. It should have been cleared.
    assert peer.order_pending_orderinfo_mapping == {}

    # Now lets consider order_4. Let it have multiple versions labeled to store.
    # manually put order_4 into peer's pending table

    for neighbor in neighbor_list:
        orderinfo = OrderInfo(
            engine=setup_engine,
            order=order_list[4],
            master=neighbor,
            arrival_time=peer.birth_time,
            priority=None,
            prev_owner=neighbor,
            novelty=0,
        )
        if order_list[4] not in peer.order_pending_orderinfo_mapping:
            peer.order_pending_orderinfo_mapping[order_list[4]] = [orderinfo]
        else:
            peer.order_pending_orderinfo_mapping[order_list[4]].append(orderinfo)
        order_list[4].hesitators.add(peer)

    # label orderinfo be stored for versions from both neighbor_0 and neighbor_1
    for orderinfo in peer.order_pending_orderinfo_mapping[order_list[4]]:
        if orderinfo.prev_owner == neighbor_list[0] or neighbor_list[1]:
            orderinfo.storage_decision = True
        else:
            orderinfo.storage_decision = False

    # call store(). Error is expected.
    with pytest.raises(ValueError):
        peer.store_orders()


def test_receive_order_internal(setup_scenario, setup_engine) -> None:
    """
    This function tests receive_order_internal().
    :param setup_scenario: fixture.
    :param setup_engine: fixture.
    :return: None.
    """

    # each of the peers have five distinct orders. The first two are neighbors. The third isn't.
    peer_list: List[Peer] = create_test_peers(setup_scenario, setup_engine, 3)
    peer_list[0].add_neighbor(peer_list[1])
    peer_list[1].add_neighbor(peer_list[0])

    # Here are two new orders.
    # The first one will be stored by all three peers.
    new_order_list: List[Order] = create_test_orders(setup_scenario, 2)

    # peer 0 uses receive_order_external() to receive this order, and uses store_orders() to
    # store this order.
    peer_list[0].receive_order_external(new_order_list[0])
    peer_list[0].store_orders()
    # Now, peer 0 should have 6 orders.
    assert len(peer_list[0].order_orderinfo_mapping) == 6

    # same for peers 1 and 2. Note that the extra one order they stored is exactly the
    # same one.
    peer_list[1].receive_order_external(new_order_list[0])
    peer_list[1].store_orders()
    peer_list[2].receive_order_external(new_order_list[0])
    peer_list[2].store_orders()

    # Non-neighbors should not be able to send orders.
    with pytest.raises(ValueError):
        peer_list[0].receive_order_internal(peer_list[2], new_order_list[0])

    # peer 1 sends orders to peer 0.
    # Five of the orders are new to peer one. One is duplicate.
    # Peer 0 should only accept the five new ones to pending list.
    for order in peer_list[1].order_orderinfo_mapping:
        peer_list[0].receive_order_internal(peer_list[1], order)

    assert len(peer_list[0].order_pending_orderinfo_mapping) == 5

    # peer 0 moves the five new orders from pending list to local storage.
    peer_list[0].store_orders()
    assert len(peer_list[0].order_orderinfo_mapping) == 11
    assert not peer_list[0].order_pending_orderinfo_mapping

    # test receiving duplicate new orders

    # new order 1 is stored by peer 1 and peer 2.
    peer_list[1].receive_order_external(new_order_list[1])
    peer_list[1].store_orders()

    # peer 0 receives a copy from peer 1. This order is new to peer 0.
    peer_list[0].receive_order_internal(peer_list[1], new_order_list[1])
    assert len(peer_list[0].order_pending_orderinfo_mapping) == 1
    assert len(peer_list[0].order_pending_orderinfo_mapping[new_order_list[1]]) == 1

    # peer 0 receives another copy again from peer 1. Duplicated copy from the same neighbor,
    # so peer 0 should ignore it.
    peer_list[0].receive_order_internal(peer_list[1], new_order_list[1])
    assert len(peer_list[0].order_pending_orderinfo_mapping) == 1
    assert len(peer_list[0].order_pending_orderinfo_mapping[new_order_list[1]]) == 1

    # peer 2 also has this new order and it is now a neighbor of peer 0.
    peer_list[2].receive_order_external(new_order_list[1])
    peer_list[2].store_orders()
    peer_list[0].add_neighbor(peer_list[2])
    peer_list[2].add_neighbor(peer_list[0])

    # peer 0 received a duplicated order but a different orderinfo instance, from a different
    # neighbor peer 2, so it needs to put it into the pending list.
    peer_list[0].receive_order_internal(peer_list[2], new_order_list[1])
    assert len(peer_list[0].order_pending_orderinfo_mapping) == 1
    assert len(peer_list[0].order_pending_orderinfo_mapping[new_order_list[1]]) == 2

    # peer 0 finally stores this order. It should store one copy only.
    # this is actually to test store_order() function.
    peer_list[0].store_orders()
    assert len(peer_list[0].order_orderinfo_mapping) == 12


def test_share_orders(setup_scenario, setup_engine, monkeypatch) -> None:
    """
    This function tests share_orders(). It mocks find_orders_to_share() and
    find_neighbors_to_share() function by only seleting orders/peers with sequence number less
    than 100.
    :param setup_scenario: fixture.
    :param setup_engine: fixture.
    :param monkeypatch: mocking tool.
    :return: None.
    """

    # mock the method of find orders/peers to share

    def mock_find_orders_to_share(peer):
        return set(order for order in peer.order_orderinfo_mapping if order.seq < 100)

    def mock_find_neighbors_to_share(_time_now, peer):
        return set(peer for peer in peer.peer_neighbor_mapping if peer.seq < 100)

    monkeypatch.setattr(setup_engine, "find_orders_to_share", mock_find_orders_to_share)
    monkeypatch.setattr(
        setup_engine, "find_neighbors_to_share", mock_find_neighbors_to_share
    )

    # peer_one is a normal peer. We will add three neighbors for it.
    # We will change the sequence number of neighbor_three and one of the initial orders that
    # peer_one has

    peer_one, order_set = create_a_test_peer(setup_scenario, setup_engine)

    neighbor_list = create_test_peers(setup_scenario, setup_engine, 3)
    neighbor_list[2].seq = 101

    one_random_order = random.sample(order_set, 1)[0]
    one_random_order.seq = 280

    peer_one.add_neighbor(neighbor_list[0])
    peer_one.add_neighbor(neighbor_list[1])
    peer_one.add_neighbor(neighbor_list[2])

    # check for the neighbors and orders that peer_one shares. It should share everything expect
    # the ones with modified sequence numbers.

    order_sharing_set, beneficiary_set = peer_one.share_orders()

    assert neighbor_list[0] in beneficiary_set
    assert neighbor_list[1] in beneficiary_set
    assert neighbor_list[2] not in beneficiary_set
    for order in order_set:
        if order.seq == 280:
            assert order not in order_sharing_set
        else:
            assert order in order_sharing_set

    # after share, the new_order_set should be cleared.
    assert peer_one.new_order_set == set()

    # peer_two is a free rider. It should not share anything to anyone.

    peer_two: Peer = create_a_test_peer(setup_scenario, setup_engine)[0]
    peer_two.is_free_rider = True

    peer_two.add_neighbor(neighbor_list[0])
    assert peer_two.share_orders() == (set(), set())


def test_del_order(setup_scenario, setup_engine) -> None:
    """
    This function tests del_orders().
    :param setup_scenario: fixture.
    :param setup_engine: fixture.
    :return: None.
    """

    # create peers.
    peer_list: List[Peer] = create_test_peers(setup_scenario, setup_engine, 3)
    my_peer: Peer = peer_list[0]
    neighbor_one: Peer = peer_list[1]
    neighbor_two: Peer = peer_list[2]

    # create new orders
    new_order_list: List[Order] = create_test_orders(setup_scenario, 4)

    # my_peer first receives an external order new_order_list[0] and stores it.
    # Now, besides the original five orders, this new order is also in my_peer's local storage.
    my_peer.receive_order_external(new_order_list[0])
    my_peer.store_orders()

    # receive internal orders from neighbors
    my_peer.add_neighbor(neighbor_one)
    my_peer.add_neighbor(neighbor_two)
    neighbor_one.add_neighbor(my_peer)
    neighbor_two.add_neighbor(my_peer)

    # both new_order_list[1] and new_order_list[2] will be put into both neighbor's local storage,
    # for new_order_list[1], my_peer will receive from both neighbors, but for new_order_list[2],
    # it will only receive from neighbor_one

    for neighbor in [neighbor_one, neighbor_two]:
        for new_order in (new_order_list[1], new_order_list[2]):
            neighbor.receive_order_external(new_order)
            neighbor.store_orders()

    my_peer.receive_order_internal(neighbor_one, new_order_list[1])
    my_peer.receive_order_internal(neighbor_two, new_order_list[1])
    my_peer.receive_order_internal(neighbor_one, new_order_list[2])

    # Now, my_peer's pending table should look like
    # {new_order_list[1]: [orderinfo_11, orderinfo_12],
    #  new_order_list[2]: [orderinfo_21]}

    # check status before deletion
    assert len(my_peer.order_orderinfo_mapping) == 6
    assert len(my_peer.order_pending_orderinfo_mapping) == 2
    assert new_order_list[0] in my_peer.order_orderinfo_mapping
    assert new_order_list[1] in my_peer.order_pending_orderinfo_mapping
    assert new_order_list[2] in my_peer.order_pending_orderinfo_mapping
    assert my_peer in new_order_list[0].holders
    assert my_peer in new_order_list[1].hesitators
    assert my_peer in new_order_list[2].hesitators

    # delete all new orders
    my_peer.del_order(new_order_list[1])
    my_peer.del_order(new_order_list[2])
    my_peer.del_order(new_order_list[0])

    # assert status after deletion
    assert len(my_peer.order_orderinfo_mapping) == 5
    assert not my_peer.order_pending_orderinfo_mapping
    assert new_order_list[0] not in my_peer.order_orderinfo_mapping
    assert new_order_list[1] not in my_peer.order_pending_orderinfo_mapping
    assert new_order_list[2] not in my_peer.order_pending_orderinfo_mapping
    assert my_peer not in new_order_list[0].holders
    assert my_peer not in new_order_list[1].hesitators
    assert my_peer not in new_order_list[2].hesitators

    # test deleting an order (new_order_list[3]) that this peer does not have.
    # Nothing should happen.

    assert new_order_list[3] not in my_peer.order_pending_orderinfo_mapping
    assert new_order_list[3] not in my_peer.order_orderinfo_mapping
    my_peer.del_order(new_order_list[3])
    assert new_order_list[3] not in my_peer.order_pending_orderinfo_mapping
    assert new_order_list[3] not in my_peer.order_orderinfo_mapping


def test_rank_neighbors(setup_scenario, setup_engine, monkeypatch) -> None:
    """
    This function tests rank_neighbors(). We disable score_neighbors() function which will change
    the score of neighbors, and use a mocked one to replace it.
    :param setup_scenario: fixture.
    :param setup_engine: fixture.
    :param monkeypatch: tool for fake function.
    :return: None
    """

    # disable score_neighbors() function. Otherwise rank_neighbors() will change the scores that
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

    # assert the return value of rank_neighbors(). Should be a list of peer instances ranked by
    # the score of their corresponding neighbor instances at peer_list[0], from highest to lowest.
    assert peer_list[0].rank_neighbors() == [peer_list[3], peer_list[1], peer_list[2]]


def test_scoring_system(setup_scenario, setup_engine, monkeypatch) -> None:
    """
    This function tests the scoring system for neighbors to contribute. Score changes happen in
    receive_order_internal() and store_orders(), but it is difficult to cover all cases when
    tests of these two functions are focused on other perspectives.
    So we decided to have an individual test function for the score updates.
    :param setup_scenario: fixture
    :param setup_engine: fixture
    :param monkeypatch: tool for fake function.
    :return: None
    """

    # Setting: my_peer is the one who accepts and stores orders. We will check scores
    # for neighbors 0-6. Neighbor 7 is some other neighbor as a competitor.
    #
    # my_peer's initial status:
    # Local storage: Order 1 from Neighbor 1, Order 2 from Neighbor 7.
    # Pending table: Order 3 from Neighbor 3, Order 5 from Neighbor 7, Order 6 from Neighbor 7.
    #
    # Behavior: neighbor i sends order i to my_peer, i in [0,6].
    # Assumption:
    # Order 0 does not pass should_accept_internal_order()
    # Order 4's storage_decision is set False
    # Order 5: version from Neighbor 7 is accepted
    # Order 6: version from Neighbor 6 is accepted.
    # Result:
    # Order 0 rejected since it doesn't pass should_accept_internal_order() (penalty_a).
    # Order 1 rejected since there's a duplicate in local storage from same neighbor (reward_a).
    # Order 2 rejected since there's a duplicate in local storage from someone else (reward_b).
    # Order 3 rejected since there's a duplicate in pending table from same neighbor (penalty_b).
    # however, there is another copy of order 3 from neighbor 3 and finally it gets stored,
    # so neighbor 3 will finally get reward_d as well.
    # Order 4's storage_decision is set False so it is accepted to pending table but rejected in
    # storage. (reward_c)
    # Order 5 is accepted to pending table but finally rejected to storage (reward_e)
    # Order 6 is accepted to pending table and is finally stored (reward_d).

    my_peer: Peer = create_a_test_peer(setup_scenario, setup_engine)[0]
    neighbor_list: List[Peer] = create_test_peers(setup_scenario, setup_engine, 8)
    order_list: List[Order] = create_test_orders(setup_scenario, 7)

    # setup the environment

    # establish neighborhood

    for i in range(8):
        my_peer.add_neighbor(neighbor_list[i])
        neighbor_list[i].add_neighbor(my_peer)

    # let every neighbor own the orders that it should have
    for i in range(7):
        neighbor_list[i].receive_order_external(order_list[i])
        neighbor_list[i].store_orders()

    # let neighbor 7 have orders 2 and 5 and 6
    for order in [order_list[2], order_list[5], order_list[6]]:
        neighbor_list[7].receive_order_external(order)
    neighbor_list[7].store_orders()

    # setup the initial status for my_peer
    my_peer.receive_order_internal(neighbor_list[1], order_list[1])
    my_peer.receive_order_internal(neighbor_list[7], order_list[2])
    my_peer.store_orders()

    my_peer.receive_order_internal(neighbor_list[3], order_list[3])
    my_peer.receive_order_internal(neighbor_list[7], order_list[5])
    my_peer.receive_order_internal(neighbor_list[7], order_list[6])

    # clear score sheet for neighbors
    for neighbor_peer in neighbor_list:
        my_peer.peer_neighbor_mapping[neighbor_peer].share_contribution[-1] = 0

    # define fake functions.
    # Order 0 will cannot be accepted to the pending list; the rest might be accepted.
    def fake_should_accept_internal_order(_receiver, _sender, order):
        if order == order_list[0]:
            return False
        return True

    # This fake function does not change the storage_decision for any orderinfo instance.
    # We will manually change them.
    def fake_store_or_discard_orders(peer):
        pass

    monkeypatch.setattr(
        setup_engine, "store_or_discard_orders", fake_store_or_discard_orders
    )
    monkeypatch.setattr(
        setup_engine, "should_accept_internal_order", fake_should_accept_internal_order
    )

    # every neighbor sends the order to my_peer
    for i in range(7):
        my_peer.receive_order_internal(neighbor_list[i], order_list[i])

    # my_peer labels storage_decision for every orderinfo
    for order, orderinfo_list in my_peer.order_pending_orderinfo_mapping.items():
        for orderinfo in orderinfo_list:
            orderinfo.storage_decision = True

        if order == order_list[4]:
            for orderinfo in orderinfo_list:
                orderinfo.storage_decision = False

        if order == order_list[5]:
            for orderinfo in orderinfo_list:
                if orderinfo.prev_owner == neighbor_list[5]:
                    orderinfo.storage_decision = False

        if order == order_list[6]:
            for orderinfo in orderinfo_list:
                if orderinfo.prev_owner == neighbor_list[7]:
                    orderinfo.storage_decision = False

    # store orders
    my_peer.store_orders()

    # calculate scores. The value equals to the last entry of the score sheet.
    my_peer.rank_neighbors()

    # check scores
    assert my_peer.peer_neighbor_mapping[neighbor_list[0]].score == pytest.approx(-13)
    assert my_peer.peer_neighbor_mapping[neighbor_list[1]].score == pytest.approx(2)
    assert my_peer.peer_neighbor_mapping[neighbor_list[2]].score == pytest.approx(3)
    assert my_peer.peer_neighbor_mapping[neighbor_list[3]].score == pytest.approx(-10)
    assert my_peer.peer_neighbor_mapping[neighbor_list[4]].score == pytest.approx(5)
    assert my_peer.peer_neighbor_mapping[neighbor_list[5]].score == pytest.approx(11)
    assert my_peer.peer_neighbor_mapping[neighbor_list[6]].score == pytest.approx(7)


def test_del_neighbor_with_remove_order(setup_scenario, setup_engine) -> None:
    """
    This function specifically test remove order option for del_neighbor() function.
    :param setup_scenario: fixture.
    :param setup_engine: fixture.
    :return: None.
    """
    # create my_peer and neighbors. Later, neighbor_list[0] will be deleted.
    my_peer = create_a_test_peer(setup_scenario, setup_engine)[0]
    neighbor_list = create_test_peers(setup_scenario, setup_engine, 2)
    for neighbor in neighbor_list:
        my_peer.add_neighbor(neighbor)
        neighbor.add_neighbor(my_peer)

    # we have 3 new orders. Neighbor 0 has all of them.
    new_order_list = create_test_orders(setup_scenario, 3)
    for order in new_order_list:
        neighbor_list[0].receive_order_external(order)
    neighbor_list[0].store_orders()

    # Neighbor 1 has order 2
    neighbor_list[1].receive_order_external(new_order_list[2])
    neighbor_list[1].store_orders()

    # my_peer will have order 0 in local storage, from neighbor 0
    my_peer.receive_order_internal(neighbor_list[0], new_order_list[0])
    my_peer.store_orders()

    # my_peer also has order 1 and order 2 in pending table. For order 1, it only has a version
    # from neighbor 0; for order 2, it has versions fro neighbor 0 and 1.
    my_peer.receive_order_internal(neighbor_list[0], new_order_list[1])
    my_peer.receive_order_internal(neighbor_list[0], new_order_list[2])
    my_peer.receive_order_internal(neighbor_list[1], new_order_list[2])

    # my_peer deletes neighbor 0 and cancels orders from it.
    my_peer.del_neighbor(neighbor_list[0], remove_order=True)

    # Now order 0 should have been deleted from local storage.
    assert new_order_list[0] not in my_peer.order_orderinfo_mapping

    # Now order 1 should have been deleted from pending table.
    assert new_order_list[1] not in my_peer.order_pending_orderinfo_mapping

    # Now order 2 should still be in the pending table, but the copy is not from neighbor[0]
    assert new_order_list[2] in my_peer.order_pending_orderinfo_mapping
    assert len(my_peer.order_pending_orderinfo_mapping[new_order_list[2]]) == 1
    assert (
        my_peer.order_pending_orderinfo_mapping[new_order_list[2]][0].prev_owner
        == neighbor_list[1]
    )
