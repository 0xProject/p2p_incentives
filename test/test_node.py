"""
This module contains test functions for instances of Peer and Neighbor.

Note that we will need to have instances of Order and OrderInfo first. However, due to the
simplicity of the definitions of Order and OrderInfo, we will not test them.

Also note that in order to create the instances, we will need an instance of Scenario and an
instance of Engine. We will simply set up a scenario and an engine instance for the test
functions to run, but we will not test Scenario or Engine in here. We will have extensive tests
over them separately.

"""

import pytest, collections

from message import Order, OrderInfo
from node import Peer, Neighbor
from data_types import *

from scenario import Scenario
from engine import Engine


@pytest.fixture(scope="module")
def setup_scenario():

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

    # create my_scenario instance
    my_scenario = Scenario(s_parameters, s_options)

    return my_scenario


@pytest.fixture(scope="module")
def setup_engine():

    batch: int = 10  # length of a batch period

    topology = Topology(max_neighbor_size=30, min_neighbor_size=20)

    incentive = Incentive(
        score_sheet_length=3,
        reward_a=0.0,
        reward_b=0.0,
        reward_c=0.0,
        reward_d=1.0,
        reward_e=0.0,
        penalty_a=0.0,
        penalty_b=-1.0,
    )

    # creating engine parameters, in type of a namedtuple.
    e_parameters = EngineParameters(batch, topology, incentive)

    # options

    # set preference for neighbors
    preference = PreferenceOption(method="Passive")

    # set priority for orders
    priority = PriorityOption(method="Passive")

    # accepting an external order or not
    external = ExternalOption(method="Always")

    # accepting an internal order or not
    internal = InternalOption(method="Always")

    # storing an order or not
    store = StoreOption(method="First")

    # This TypedDict describes how to determine the orders to share with neighbors.
    share = AllNewSelectedOld(
        method="AllNewSelectedOld", max_to_share=5000, old_share_prob=0.5
    )

    # This TypedDict describes how to determine neighbor scoring system.
    score = Weighted(
        method="Weighted",
        lazy_contribution_threshold=2,
        lazy_length_threshold=6,
        weights=[1.0, 1.0, 1.0],
    )  # must be of the same length as incentive

    # This TypedDict describes how to determine the neighbors that receive my orders.
    beneficiary = TitForTat(
        method="TitForTat", baby_ending_age=0, mutual_helpers=3, optimistic_choices=1
    )

    # how to recommendation neighbors when a peer asks for more.
    rec = RecommendationOption(method="Random")

    # creating engine option, in type of a namedtuple

    e_options = EngineOptions(
        preference, priority, external, internal, store, share, score, beneficiary, rec
    )

    # creating my_engine, an instance of Engine, in type pf a namedtuple.
    my_engine = Engine(e_parameters, e_options)

    return my_engine


def create_an_order(scenario, seq, birth_time, creator):
    return Order(scenario=scenario, seq=seq, birth_time=birth_time, creator=creator)


def test_order(setup_scenario):
    my_order = create_an_order(setup_scenario, 5, 12, None)
    assert my_order.seq == 5
    assert my_order.birth_time == 12
    assert my_order.scenario.peer_type_property["normal"].ratio == pytest.approx(0.9)
    assert my_order.scenario.peer_type_property["free_rider"].ratio == pytest.approx(
        0.1
    )


def create_orders(scenario, num, seq_list, birth_time_list, creator_list):
    order_set = set()
    for i in range(num):
        order_set.add(
            Order(
                scenario=scenario,
                seq=seq_list[i],
                birth_time=birth_time_list[i],
                creator=creator_list[i],
            )
        )
    return order_set


def create_a_peer_constant(scenario, engine):
    """
    This function creates a peer constant. Parameters are hard coded.
    It does not pursue any generality, but merely for use of following test functions.
    :param scenario: scenario to pass to order init.
    :param engine: engine to pass to peer init.
    :return: a peer instance, and the set of initial order instances.
    """

    # manually create 5 orders for this peer.

    order_set = create_orders(
        scenario=scenario,
        num=5,
        seq_list=[0, 1, 2, 3, 4],
        birth_time_list=[3, 7, 10, 15, 20],
        creator_list=[None, None, None, None, None],
    )

    my_peer = Peer(
        engine=engine,
        seq=10,
        birth_time=12,
        init_orders=order_set,
        namespacing=None,
        peer_type="normal",
    )

    return my_peer, order_set


def test_peer_init(setup_scenario, setup_engine):

    my_peer, order_set = create_a_peer_constant(setup_scenario, setup_engine)

    assert my_peer.engine == setup_engine
    assert my_peer.seq == 10
    assert my_peer.birth_time == 12
    assert my_peer.init_orderbook_size == 5
    assert my_peer.namespacing is None
    assert my_peer.peer_type == "normal"
    assert my_peer.is_free_rider is False

    for order in order_set:
        assert order.creator == my_peer

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

    for order in order_set:
        assert order.holders == {my_peer}

    assert my_peer.peer_neighbor_mapping == {}
    assert my_peer.order_pending_orderinfo_mapping == {}


def test_add_neighbor(setup_scenario, setup_engine):

    peer_one, _ = create_a_peer_constant(setup_scenario, setup_engine)
    peer_two, _ = create_a_peer_constant(setup_scenario, setup_engine)
    peer_three, _ = create_a_peer_constant(setup_scenario, setup_engine)

    peer_one.add_neighbor(peer_two)
    assert peer_two in peer_one.peer_neighbor_mapping
    peer_one.add_neighbor(peer_three)
    assert peer_three in peer_one.peer_neighbor_mapping
    assert len(peer_one.peer_neighbor_mapping) == 2

    neighbor_two = peer_one.peer_neighbor_mapping[peer_two]
    assert neighbor_two.engine == setup_engine
    assert neighbor_two.est_time == peer_one.birth_time
    assert neighbor_two.preference is None

    expected_score_sheet = collections.deque()
    for _ in range(setup_engine.score_length):
        expected_score_sheet.append(0.0)
    assert neighbor_two.share_contribution == expected_score_sheet
    assert neighbor_two.score == pytest.approx(0.0)
    assert neighbor_two.lazy_round == 0

    with pytest.raises(ValueError):
        peer_one.add_neighbor(peer_two)

    with pytest.raises(ValueError):
        peer_one.add_neighbor(peer_one)


def test_should_accept_neighbor_request(setup_scenario, setup_engine):

    peer_one, _ = create_a_peer_constant(setup_scenario, setup_engine)
    peer_two, _ = create_a_peer_constant(setup_scenario, setup_engine)

    assert peer_one.should_accept_neighbor_request(peer_two) is True

    peer_one.add_neighbor(peer_two)
    peer_two.add_neighbor(peer_one)

    with pytest.raises(ValueError):
        peer_one.should_accept_neighbor_request(peer_two)

    with pytest.raises(ValueError):
        peer_one.should_accept_neighbor_request(peer_one)

    with pytest.raises(ValueError):
        peer_two.should_accept_neighbor_request(peer_one)


def test_should_accept_neighbor_request_reaching_capacity(
    setup_scenario, setup_engine, monkeypatch
):
    def mock_max_size():
        return 1

    monkeypatch.setattr(setup_engine, "neighbor_max", mock_max_size())

    peer_one, _ = create_a_peer_constant(setup_scenario, setup_engine)
    peer_two, _ = create_a_peer_constant(setup_scenario, setup_engine)

    peer_one.add_neighbor(peer_two)
    peer_two.add_neighbor(peer_one)

    peer_three, _ = create_a_peer_constant(setup_scenario, setup_engine)

    assert peer_one.should_accept_neighbor_request(peer_three) is False


def test_del_neighbor_(setup_scenario, setup_engine):

    peer_one, _ = create_a_peer_constant(setup_scenario, setup_engine)
    peer_two, _ = create_a_peer_constant(setup_scenario, setup_engine)

    peer_one.add_neighbor(peer_two)
    peer_two.add_neighbor(peer_one)

    peer_one.del_neighbor(peer_two)

    assert len(peer_one.peer_neighbor_mapping) == 0
    assert len(peer_two.peer_neighbor_mapping) == 0

    with pytest.raises(ValueError):
        peer_one.del_neighbor(peer_two)

    with pytest.raises(ValueError):
        peer_two.del_neighbor(peer_one)

    with pytest.raises(ValueError):
        peer_one.del_neighbor(peer_one)

    # Note: we have not tested the "remove_order" option here. Need to come back soon.


def test_receive_order_external(setup_scenario, setup_engine):

    peer, _ = create_a_peer_constant(setup_scenario, setup_engine)
    order = create_an_order(setup_scenario, seq=15, birth_time=9, creator=None)
    peer.receive_order_external(order)
    assert order in peer.order_pending_orderinfo_mapping
    assert order not in peer.order_orderinfo_mapping
    assert peer in order.hesitators


def test_receive_order_internal(setup_scenario, setup_engine):

    # each of the two peers have five distinct orders (though their sequence IDs are duplicate)
    peer_one, _ = create_a_peer_constant(setup_scenario, setup_engine)
    peer_two, _ = create_a_peer_constant(setup_scenario, setup_engine)

    peer_one.add_neighbor(peer_two)
    peer_two.add_neighbor(peer_one)

    peer_three, _ = create_a_peer_constant(setup_scenario, setup_engine)

    # Here is a new order that will be stored by all three peers.

    a_new_order = create_an_order(setup_scenario, seq=10, birth_time=9, creator=None)

    peer_one.receive_order_external(a_new_order)
    peer_one.store_orders()
    assert len(peer_one.order_orderinfo_mapping) == 6

    peer_two.receive_order_external(a_new_order)
    peer_two.store_orders()

    peer_three.receive_order_external(a_new_order)
    peer_three.store_orders()

    # Non-neighbors should not be able to send orders.
    with pytest.raises(ValueError):
        peer_one.receive_order_internal(peer_three, a_new_order)

    # peer two sends orders to peer one. Five of the orders are new to peer one. One is duplicate.
    # Peer one should only accept the five new ones to pending list.
    for order in peer_two.order_orderinfo_mapping:
        peer_one.receive_order_internal(peer_two, order)

    assert len(peer_one.order_pending_orderinfo_mapping) == 5

    # peer one moves the five new orders from pending list to local storage.
    peer_one.store_orders()
    assert len(peer_one.order_orderinfo_mapping) == 11
    assert len(peer_one.order_pending_orderinfo_mapping) == 0

    # test receiving duplicate new orders

    # create another new order that is stored by peer two and peer three.

    second_new_order = create_an_order(
        setup_scenario, seq=10, birth_time=9, creator=None
    )
    peer_two.receive_order_external(second_new_order)
    peer_two.store_orders()

    # peer one receives a copy from peer two. It is new to peer one.

    peer_one.receive_order_internal(peer_two, second_new_order)
    assert len(peer_one.order_pending_orderinfo_mapping) == 1
    assert len(peer_one.order_pending_orderinfo_mapping[second_new_order]) == 1

    # peer one receives another copy again from peer two. Duplicated copy from the same neighbor,
    # so ignore it.
    peer_one.receive_order_internal(peer_two, second_new_order)
    assert len(peer_one.order_pending_orderinfo_mapping) == 1
    assert len(peer_one.order_pending_orderinfo_mapping[second_new_order]) == 1

    # peer three also has this new order and it is now a neighbor of peer one.
    peer_three.receive_order_external(second_new_order)
    peer_three.store_orders()
    peer_one.add_neighbor(peer_three)
    peer_three.add_neighbor(peer_one)

    # peer one received a duplicated one from a different neighbor so it needs to put it into the
    # pending list.
    peer_one.receive_order_internal(peer_three, second_new_order)
    assert len(peer_one.order_pending_orderinfo_mapping) == 1
    assert len(peer_one.order_pending_orderinfo_mapping[second_new_order]) == 2

    # peer one finally stores this order. It should store one copy only.
    peer_one.store_orders()
    assert len(peer_one.order_orderinfo_mapping) == 12

    # Note that we did not test the change of neighbor scores. Need to add them later.


def test_store_orders(setup_scenario, setup_engine, monkeypatch):

    # peer will be connected with neighbors
    peer, _ = create_a_peer_constant(setup_scenario, setup_engine)
    neighbor_1, _ = create_a_peer_constant(setup_scenario, setup_engine)
    neighbor_2, _ = create_a_peer_constant(setup_scenario, setup_engine)
    neighbor_3, _ = create_a_peer_constant(setup_scenario, setup_engine)

    # peer will later be disconnected from this neighbor
    neighbor_disconnect, _ = create_a_peer_constant(setup_scenario, setup_engine)

    # orders 1 and 2 will have multiple copies but only one will be stored
    # order 3 will not be stored since no copy is labeled as to store
    # order 4 will be stored with the version from neighbor_disconnect (though it is disconnected).
    # order 5 will have multiple copies to store and raise an error

    order_1 = create_an_order(setup_scenario, seq=1, birth_time=0, creator=None)
    order_2 = create_an_order(setup_scenario, seq=2, birth_time=0, creator=None)
    order_3 = create_an_order(setup_scenario, seq=3, birth_time=0, creator=None)
    order_4 = create_an_order(setup_scenario, seq=4, birth_time=0, creator=None)
    order_5 = create_an_order(setup_scenario, seq=5, birth_time=0, creator=None)

    neighbor_list = [neighbor_1, neighbor_2, neighbor_3, neighbor_disconnect]
    order_list = [order_1, order_2, order_3, order_4, order_5]

    for neighbor in neighbor_list:
        for order in order_list:
            neighbor.receive_order_external(order)
        neighbor.add_neighbor(peer)
        peer.add_neighbor(neighbor)

        # this is a normal call of store_orders(). Should store everything.
        neighbor.store_orders()
        for order in order_list:
            # check if every order is stored in every neighbor.
            assert order in neighbor.order_orderinfo_mapping

    # manually put the orders 1-4 into peer's pending table

    for order in [order_1, order_2, order_3, order_4]:
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

    # manually set store decisions for each order.
    # Store neighbor_1's version for order_1, and neighbor_3's version for order_2, and do not
    # store order_3

    for orderinfo in peer.order_pending_orderinfo_mapping[order_1]:
        if orderinfo.prev_owner == neighbor_1:
            orderinfo.storage_decision = True
        else:
            orderinfo.storage_decision = False

    for orderinfo in peer.order_pending_orderinfo_mapping[order_2]:
        if orderinfo.prev_owner == neighbor_3:
            orderinfo.storage_decision = True
        else:
            orderinfo.storage_decision = False

    for orderinfo in peer.order_pending_orderinfo_mapping[order_3]:
        orderinfo.storage_decision = False

    for orderinfo in peer.order_pending_orderinfo_mapping[order_4]:
        if orderinfo.prev_owner == neighbor_disconnect:
            orderinfo.storage_decision = True
        else:
            orderinfo.storage_decision = False

    # now let us disconnect neighbor_disconnect
    peer.del_neighbor(neighbor_disconnect)

    assert neighbor_disconnect not in peer.peer_neighbor_mapping

    # Disable engine.store_or_discard_orders which will otherwise
    # change the values for orderinfo.storage_decision

    def mock_storage_decision(_node):
        pass

    monkeypatch.setattr(setup_engine, "store_or_discard_orders", mock_storage_decision)

    # Now let us check store_orders()

    peer.store_orders()

    assert order_1 in peer.order_orderinfo_mapping
    assert order_2 in peer.order_orderinfo_mapping
    assert peer.order_orderinfo_mapping[order_1].prev_owner == neighbor_1
    assert peer.order_orderinfo_mapping[order_2].prev_owner == neighbor_3
    assert order_3 not in peer.order_orderinfo_mapping
    assert peer.order_orderinfo_mapping[order_4].prev_owner == neighbor_disconnect

    # check peer's pending table. It should have nothing.

    assert peer.order_pending_orderinfo_mapping == {}

    # Now lets consider order_5. Let it have multiple versions labeled to store.

    # manually put order_5 into peer's pending table

    for neighbor in neighbor_list:
        orderinfo = OrderInfo(
            engine=setup_engine,
            order=order_5,
            master=neighbor,
            arrival_time=peer.birth_time,
            priority=None,
            prev_owner=neighbor,
            novelty=0,
        )
        if order_5 not in peer.order_pending_orderinfo_mapping:
            peer.order_pending_orderinfo_mapping[order_5] = [orderinfo]
        else:
            peer.order_pending_orderinfo_mapping[order_5].append(orderinfo)
        order_5.hesitators.add(peer)

    # label orderinfo be stored for versions from both neighbor_1 and neighbor_2
    for orderinfo in peer.order_pending_orderinfo_mapping[order_5]:
        if orderinfo.prev_owner == neighbor_1 or neighbor_2:
            orderinfo.storage_decision = True
        else:
            orderinfo.storage_decision = False

    # call store(). Error expected.
    with pytest.raises(ValueError):
        peer.store_orders()
