"""
This module contains the SingleRun class only.
"""

import random
from typing import Dict, Set, List, TYPE_CHECKING, cast, Tuple, Optional
import numpy
from message import Order
from node import Peer
from data_types import (
    SingleRunPerformanceResult,
    PeerTypeName,
    OrderTypeName,
    PeerProperty,
    OrderProperty,
    ConcaveProperty,
    RandomProperty,
    AgeBasedProperty,
    SettleParameters,
    CancelParameters,
    ConcaveParameters,
    RandomParameter,
    AgeBasedParameters,
    InvalidOrdersStat,
)


if TYPE_CHECKING:
    from engine import Engine
    from scenario import Scenario
    from performance import Performance


class SingleRun:
    """
    The SingleRun class contains all function that is directly called by the simulator to run one
    time. For example, initialization of the system, and operations in each time round.
    """

    def __init__(
        self, scenario: "Scenario", engine: "Engine", performance: "Performance"
    ) -> None:
        """
        This init function sets up the attribute values for the class instance. It does not
        really create the initial order set or peer set; instead, the method followed
        (create_initial_peers_orders()) creates them.
        """

        # server_response_time refers to the random response time of the Ethereum hosting service
        # for on-chain check.
        # Theoretically, the response time for a batch of n orders verification is:
        # some_random_value + constant_factor * size(orders).
        # Now let's assume that some_random_value is the major factor and let it represent the
        # total response time, which is server_response_time. It is a random number between 0-30
        # seconds, with 95% probability <= 1 seconds and 99% probability <= 5 seconds.
        # We further assume that this random variable depends on the Ethereum hosting
        # server's workload and is a variable upon time. Given a time point, we assume that the
        # Ethereum hosting service's response time is determined and it is the same value if
        # there are various verification requests from multiple peers.

        self.server_response_time: List[int] = scenario.generate_server_response_time()

        self.order_full_set: Set["Order"] = set()  # set of orders

        # mapping from order type to order sets. The value element is a set containing all orders
        # of a particular type.
        self.order_type_set_mapping: Dict[OrderTypeName, Set["Order"]] = {}

        # Now we need to initialize order_type_set_mapping, whose keys are of type OrderTypeName
        # (which is a Literal in typing_extensions module). However, there is no way for us to
        # get (or iterate over) all possible values in this Literal. So we choose to iterate over
        # all keys of scenario.order_type_ratios, which is a TypedDict with keys that can take
        # values in this exactly the same Literal.

        for type_name in scenario.order_type_property:
            # Though type_name is a key of scenario.order_type_property and it must be of type
            # OrderTypeName (a Literal containing all order names), however, mypy does not know
            # that and only treats it as a normal str type. There is no isinstance() check for it
            # either. So we can only use cast to tell mypy that the type of type_name is
            # OrderTypeName.
            self.order_type_set_mapping[cast(OrderTypeName, type_name)] = set()

        self.peer_full_set: Set["Peer"] = set()  # set of peers

        # mapping from peer type to peer sets. The value element is a set containing all peers of
        # a particular type.
        self.peer_type_set_mapping: Dict[PeerTypeName, Set["Peer"]] = {}
        for type_name in scenario.peer_type_property:
            # Use cast to tell mypy that the type of type_name is PeerTypeName
            # Similar reason as above.
            self.peer_type_set_mapping[cast(PeerTypeName, type_name)] = set()

        self.cur_time: int = 0  # current system time
        self.latest_order_seq: int = 0  # sequence number for next order to use
        self.latest_peer_seq: int = 0  # sequence number for next peer to use

        self.invalid_orders_stat = InvalidOrdersStat(
            expired_count=0, settled_count=0, canceled_count=0, missing_count=0
        )

        self.scenario: "Scenario" = scenario  # assumptions
        self.engine: "Engine" = engine  # design choices
        self.performance: "Performance" = performance  # performance evaluation measures

    def create_initial_peers_orders(self) -> None:
        """
        This method creates the initial orders and peers for a SingleRun instance, and maintains
        their references in two sets.
        Sequence numbers of peers and neighbors begin from 0 and increase by 1 each time.
        Right now there is no use for the sequence numbers but we keep them for potential future use
        :return: None
        """

        # Note: Since the code logic is very simple (mainly calling
        # group_of_peers_arrival_helper() and check_adding_neighbor() methods), we will not have
        # unit test for this method, but we will make sure the methods it calls are correct.

        # Call function group_of_peers_arrival_helper() to create the initial peers.
        self.group_of_peers_arrival_helper(self.scenario.init_size)

        # Only special thing in the init, comparing to a normal group of peers arrival,
        # is to randomize the peer's birth time and set up their local clocks.
        for peer in self.peer_full_set:
            peer.birth_time = random.randint(0, self.scenario.birth_time_span - 1)
            peer.local_clock = self.scenario.birth_time_span - 1

        self.check_adding_neighbor()

    @staticmethod
    def set_properties_for_an_order_instance_helper(
        order_type_property: OrderProperty,
    ) -> Tuple[int, SettleParameters, CancelParameters]:
        """
        This is a helper function to generate an order instance's properties (expiration,
        settlement, cancellation) from the property distribution of the order type it belongs to.
        :param order_type_property: property distribution of the order type.
        :return: expiration, settlement, cancellation.
        """
        # expiration
        this_expire = order_type_property.expiration
        expiration: int = max(0, round(random.gauss(this_expire.mean, this_expire.var)))

        # settlement
        this_settle = order_type_property.settlement
        if this_settle["method"] == "ConcaveProperty":
            this_settle = cast(ConcaveProperty, this_settle)
            sensitivity = max(
                0,
                random.gauss(
                    this_settle["sensitivity"].mean, this_settle["sensitivity"].var
                ),
            )
            max_prob = max(
                0,
                random.gauss(this_settle["max_prob"].mean, this_settle["max_prob"].var),
            )
            settlement = ConcaveParameters(
                method="ConcaveParameters", sensitivity=sensitivity, max_prob=max_prob
            )
        else:
            raise ValueError("No such way of generating settlement parameters.")

        # cancellation

        cancellation: CancelParameters = CancelParameters(method="RandomParameter")

        this_cancel = order_type_property.cancellation
        if this_cancel["method"] == "RandomProperty":
            this_cancel = cast(RandomProperty, this_cancel)
            prob = max(
                0, random.gauss(this_cancel["prob"].mean, this_cancel["prob"].var)
            )
            cancellation = RandomParameter(method="RandomParameter", prob=prob)
        elif this_cancel["method"] == "AgeBasedProperty":
            this_cancel = cast(AgeBasedProperty, this_cancel)
            sensitivity = max(
                0,
                random.gauss(
                    this_cancel["sensitivity"].mean, this_cancel["sensitivity"].var
                ),
            )
            max_prob = max(
                0,
                random.gauss(this_cancel["max_prob"].mean, this_cancel["max_prob"].var),
            )
            cancellation = AgeBasedParameters(
                method="AgeBasedParameters", sensitivity=sensitivity, max_prob=max_prob
            )
        else:
            raise ValueError("No such way of generating settlement parameters.")

        return expiration, settlement, cancellation

    def peer_arrival(
        self, peer_type: PeerTypeName, num_orders_dict: Dict[OrderTypeName, int]
    ) -> None:
        """
        This method deals with peer arrival.
        When a new peer arrives, it may already have a set of orders. It only needs to specify
        the number of initial orders, and the function will specify the sequence numbers for the
        peers and orders.
        :param peer_type: the type of the newly arrived peer.
        :param num_orders_dict: a dictionary, keys are (subset of) order types and values
        are the numbers of initial orders of that type that this new peer has.
        :return: None.
        """

        # free riders must have no orders
        if peer_type == "free_rider" and any(
            order_num != 0 for order_num in num_orders_dict.values()
        ):
            raise ValueError("Free riders do not have orders.")

        # decide this peer's sequence number
        peer_seq: int = self.latest_peer_seq

        # create the initial orders for this peer and update global order set
        cur_order_set: Set["Order"] = set()
        for order_type, order_num in num_orders_dict.items():
            for _ in range(order_num):
                (
                    expiration,
                    settlement,
                    cancellation,
                ) = self.set_properties_for_an_order_instance_helper(
                    self.scenario.order_type_property[order_type]
                )

                # Now we initiate the new orders, whose creator should be the new peer.
                # But the new peer has not been initiated, so we set the creator to be None
                # temporarily. We will modify it when the peer is initiated.
                # This is tricky and informal, but I don't have a better way of doing it right now.
                new_order = self.order_arrival(
                    target_peer=None,
                    order_type=order_type,
                    expiration=expiration,
                    settlement=settlement,
                    cancellation=cancellation,
                )
                cur_order_set.add(new_order)
        # create the new peer, and add it to the table
        new_peer = Peer(
            engine=self.engine,
            seq=peer_seq,
            birth_time=self.cur_time,
            init_orders=cur_order_set,
            namespacing=None,
            peer_type=peer_type,
        )
        self.peer_full_set.add(new_peer)
        self.peer_type_set_mapping[peer_type].add(new_peer)

        # update latest sequence numbers for peer (order seq has been updated by order_arrival)
        self.latest_peer_seq += 1

    def peer_departure(self, peer: Peer) -> None:
        """
        This method deals with node departing the system
        :param peer: peer instance of the node departing the system.
        :return: None.
        """

        if peer not in self.peer_full_set:
            raise ValueError("No such peer to depart.")

        # update number of replicas of all stored/pending orders with this peer
        for order in peer.order_orderinfo_mapping:
            order.holders.remove(peer)
        for order in peer.order_pending_orderinfo_mapping:
            order.hesitators.remove(peer)

        # update existing peers
        for other_peer in self.peer_full_set:
            if peer in other_peer.peer_neighbor_mapping:
                other_peer.del_neighbor(peer)

        # update the peer set for the SingleRun instance.

        self.peer_full_set.remove(peer)
        # use cast due to similar reason in __init__() function of this class.
        self.peer_type_set_mapping[cast(PeerTypeName, peer.peer_type)].remove(peer)

    def order_arrival(
        self,
        target_peer: Optional[Peer],
        order_type: OrderTypeName,
        expiration: int,
        settlement: SettleParameters,
        cancellation: CancelParameters,
    ) -> Order:
        """
        This method initiates an external order arrival, whose creator is the "target_peer"
        :param target_peer: See explanation above. We allow None for this attribute since there
        is a special use case of this method in self.peer_arrival().
        :param order_type: order type.
        :param expiration: expiration for this order.
        :param settlement: settlement parameter for this order
        :param cancellation: cancellation parameter for this order
        :return: None
        """

        if target_peer and target_peer not in self.peer_full_set:
            raise ValueError("Cannot find target peer.")

        # create a new order
        new_order_seq: int = self.latest_order_seq
        new_order = Order(
            scenario=self.scenario,
            seq=new_order_seq,
            birth_time=self.cur_time,
            creator=target_peer,
            order_type=order_type,
            expiration=expiration,
            settlement=settlement,
            cancellation=cancellation,
        )

        # update the set of orders for the SingleRun
        self.order_full_set.add(new_order)
        self.order_type_set_mapping[order_type].add(new_order)
        self.latest_order_seq += 1

        # update the order info to the target peer
        if target_peer:
            target_peer.receive_order_external(new_order)

        return new_order

    def update_global_orderbook(self) -> None:
        """
        This method deletes all invalid orders from both order set of SingleRun instance,
        and all peers' pending table and storage.
        :return: None.
        """

        for order in list(self.order_full_set):
            if not order.is_valid:

                # update invalid order statistics
                if order.is_canceled:
                    self.invalid_orders_stat["canceled_count"] += 1
                elif order.is_settled:
                    self.invalid_orders_stat["settled_count"] += 1
                elif order.is_expired:
                    self.invalid_orders_stat["expired_count"] += 1
                else:
                    self.invalid_orders_stat["missing_count"] += 1

                # delete this order
                for peer in list(order.holders):
                    peer.del_order(order)
                for peer in list(order.hesitators):
                    peer.del_order(order)
                self.order_full_set.remove(order)
                self.order_type_set_mapping[order.order_type].remove(order)

    def add_new_links_helper(self, requester: Peer, demand: int, minimum: int) -> None:
        """
        This is a helper method for the requester peer to add neighbors, and is called only by
        check_adding_neighbor().
        It targets at adding a number of "demand" neighbors, but is fine if the final added number
        is in the range [minimum, demand], or stops when all possible links are added.
        This method will call the corresponding peers' functions to add the neighbor, respectively.
        :param requester: peer instance of the node requesting more neighbors
        :param demand: max number of neighbors to be added
        :param minimum: min number of neighbors to be added
        :return: None
        """

        if demand <= 0 or minimum < 0 or demand < minimum:
            raise ValueError("Input value is invalid.")

        candidates_pool: Set[Peer] = self.peer_full_set - {requester}
        selection_size: int = demand
        links_added: int = 0

        while links_added < minimum and candidates_pool:

            links_added_this_round: int = 0
            selected_peer_set: Set[Peer] = self.engine.recommend_neighbors(
                requester, candidates_pool, selection_size
            )
            for candidate in selected_peer_set:
                # if this peer is already the requester's neighbor, if not,
                # check if the candidate is willing to add the requester.
                if (
                    candidate not in requester.peer_neighbor_mapping
                    and candidate.should_accept_neighbor_request(requester)
                ):
                    # mutual add neighbors
                    candidate.add_neighbor(requester)
                    requester.add_neighbor(candidate)
                    links_added += 1
                    links_added_this_round += 1

            candidates_pool -= selected_peer_set
            selection_size -= links_added_this_round

    def check_adding_neighbor(self) -> None:
        """
        This method checks for all peers if they need to add neighbors, if the number of
        neighbors is not enough. It calls the method add_new_links_helper().
        It aims at adding up to neighbor_max neighbors, but is fine if added up to neighbor_min,
        or all possibilities have been tried. This function needs to be proactively called every
        time round.
        :return: None
        """

        # Note: this method is simple so we don't have a unit test for it.

        for peer in self.peer_full_set:
            cur_neighbor_size: int = len(peer.peer_neighbor_mapping)
            if cur_neighbor_size < self.engine.neighbor_min:
                self.add_new_links_helper(
                    requester=peer,
                    demand=self.engine.neighbor_max - cur_neighbor_size,
                    minimum=self.engine.neighbor_min - cur_neighbor_size,
                )

    def group_of_peers_departure_helper(self, peer_dept_num: int) -> None:
        """
        This is a helper method for operations_in_a_time_round(). Given a certain number of
        peers to depart, this method randomly selects the peers and lets them depart.
        """

        # Note: this method is simple so we don't have a unit test for it.

        for peer_to_depart in random.sample(
            self.peer_full_set, min(len(self.peer_full_set), peer_dept_num)
        ):
            self.peer_departure(peer_to_depart)

    def group_of_peers_arrival_helper(self, peer_arr_num: int) -> None:
        """
        This is a helper method for operations_in_a_time_round(). Given a certain number of
        peers to arrive, this method determines the peers' types according to their weights in
        the system, and the values of attributes of each peer, and creates them.
        """

        peer_type_candidates: List[PeerTypeName] = []
        peer_weights: List[float] = []
        for peer_type, peer_property in self.scenario.peer_type_property.items():
            # peer_type is certainly of type PeerTypeName since PeerTypeName is the literal
            # containing all keys in peer_type_property. However mypy doesn't know that and there
            # is no isinstance() check for Literal. The only way I can do for now is to use a cast.
            peer_type_candidates.append(cast(PeerTypeName, peer_type))

            # this check is only to help mypy judge data types. Not expected to raise an error.
            if isinstance(peer_property, PeerProperty):
                peer_weights.append(peer_property.ratio)
            else:
                raise RuntimeError("Data types in a mass.")

        peer_type_vector: List[PeerTypeName] = random.choices(
            peer_type_candidates, weights=peer_weights, k=peer_arr_num
        )

        for peer_type in peer_type_vector:
            num_init_orders_dict = dict()
            for (
                order_type,
                init_orderbook_size_distribution,
            ) in self.scenario.peer_type_property[
                peer_type
            ].initial_orderbook_size_dict.items():
                num_mean: float = init_orderbook_size_distribution.mean
                num_var: float = init_orderbook_size_distribution.var
                num_init_orders_dict[order_type] = max(
                    0, round(random.gauss(num_mean, num_var))
                )
            self.peer_arrival(peer_type, num_init_orders_dict)

    def group_of_orders_arrival_helper(self, order_arr_num):
        """
        This is a helper method for operations_in_a_time_round(). Given a certain number of
        order arrivals, this method determines the initial holders (peers) of these orders,
        the order type, and expiration, and creates them.
        """

        # Decide which peers to hold these orders and the type of each of these orders
        # The probability of each order being of type i and having peer j as its holder,
        # is proportional to the peer j's expected number of initial orders of type i.
        # Free riders will not be candidates since they don't have init orderbook.

        candidate_peer_and_order_type_combination: List[
            Tuple[Peer, OrderTypeName]
        ] = list()
        candidate_weights: List[float] = list()
        for peer in list(self.peer_full_set):
            peer_property = self.scenario.peer_type_property[peer.peer_type]
            for order_type in peer_property.initial_orderbook_size_dict.keys():
                candidate_peer_and_order_type_combination.append((peer, order_type))
                candidate_weights.append(
                    peer_property.initial_orderbook_size_dict[order_type].mean
                )

        target_peer_and_type_list: List[Tuple[Peer, OrderTypeName]] = random.choices(
            candidate_peer_and_order_type_combination,
            weights=candidate_weights,
            k=order_arr_num,
        )

        for target_peer, this_order_type in target_peer_and_type_list:
            order_type_property = self.scenario.order_type_property[this_order_type]

            (
                expiration,
                settlement,
                cancellation,
            ) = self.set_properties_for_an_order_instance_helper(order_type_property)

            self.order_arrival(
                target_peer, this_order_type, expiration, settlement, cancellation
            )

    def operations_in_a_time_round(
        self, peer_arr_num: int, peer_dept_num: int, order_arr_num: int
    ) -> None:
        """
        This method runs normal operations at a particular time point.
        It includes peer/order dept/arrival, order status update, and peer's order acceptance,
        storing, and sharing.
        :param peer_arr_num: number of peers arriving the system
        :param peer_dept_num: number of peers departing the system
        :param order_arr_num: number of orders arriving the system
        :return: None
        """

        # peers leave
        self.group_of_peers_departure_helper(peer_dept_num)

        # existing peers adjust clock
        for peer in self.peer_full_set:
            peer.local_clock += 1
            if peer.local_clock != self.cur_time:
                raise RuntimeError("Clock system in a mass.")

        # new peers come in
        self.group_of_peers_arrival_helper(peer_arr_num)

        # Now, if the system does not have any peers, stop operations in this round.
        # The simulator can still run, hoping that in the next round peers will appear.
        if not self.peer_full_set:
            return

        # if there are only free-riders, then there will be no new order arrival.
        # However, other operations will continue.
        if self.peer_full_set == self.peer_type_set_mapping["free_rider"]:
            order_arr_num = 0  # all are free-riders

        # external orders arrival
        self.group_of_orders_arrival_helper(order_arr_num)

        # order status update and global orderbook update
        for order in self.order_full_set:
            order.update_valid_status(self.cur_time)
        self.update_global_orderbook()

        # peer operations

        # HACK (weijiewu8): this might differ a bit from real system implementation where the
        # check_adding_neighbor is done when a peer starts a loop.
        self.check_adding_neighbor()

        for peer in self.peer_full_set:

            # should start a loop
            if peer.should_start_a_new_loop(self.scenario.birth_time_span):
                peer.previous_loop_starting_time = self.cur_time
                peer.send_orders_to_on_chain_check(
                    expected_completion_time=self.cur_time
                    + self.server_response_time[self.cur_time]
                )
            # should finish a loop
            if self.cur_time in peer.verification_time_orders_mapping:
                peer.store_orders()
                peer.score_neighbors()
                peer.refresh_neighbors()
                (orders_to_share, neighbors_to_share) = peer.share_orders(
                    self.scenario.birth_time_span
                )
                for internal_order in orders_to_share:
                    for beneficiary_peer in neighbors_to_share:
                        beneficiary_peer.receive_order_internal(peer, internal_order)
                del peer.verification_time_orders_mapping[self.cur_time]

    def generate_events_during_whole_process(
        self,
    ) -> Tuple[List[int], List[int], List[int]]:
        """
        This function generates the number of events during each time interval of the single_run
        process. This is a helper method to single_run_execution().
        :return: Tuple, each element being a list of integers, representing the number of counts
        of peer arrivals, departures, and order arrivals, during each time interval. The
        time interval starts from the first one of the growth period till the last one of the
        stable period.
        """

        # initiate vectors of each event happening count in each time round
        # This is very important since numpy.random is not multiprocessing safe in Hawkes Process.
        numpy.random.seed()
        counts_growth: List[List[int]] = list(
            map(
                lambda x: self.scenario.generate_event_counts_over_time(
                    x, self.scenario.growth_rounds
                ),
                self.scenario.growth_rates,
            )
        )
        numpy.random.seed()
        counts_stable: List[List[int]] = list(
            map(
                lambda x: self.scenario.generate_event_counts_over_time(
                    x, self.scenario.stable_rounds
                ),
                self.scenario.stable_rates,
            )
        )
        peer_arrival_count, peer_dept_count, order_arrival_count = map(
            lambda x, y: list(x) + list(y), counts_growth, counts_stable
        )

        return peer_arrival_count, peer_dept_count, order_arrival_count

    def single_run_execution(self) -> SingleRunPerformanceResult:
        """
        This is the method that runs the simulator for one time, including setup, and growth and
        stable periods.
        :return: Performance evaluation results in terms of a tuple, each element being the result
        of one particular metric (or None if not applicable).
        """

        # Note: This method is simple (mostly calling other methods) and we made sure
        # other methods are correct. So we don't have unit test for this method.

        # Create initial peers and orders. Orders are only held by creators.
        # Peers do not exchange orders at this moment.
        self.create_initial_peers_orders()
        self.update_global_orderbook()

        # Generate event counts.
        (
            peer_arrival_count,
            peer_dept_count,
            order_arrival_count,
        ) = self.generate_events_during_whole_process()

        # Growth period and stable period. Run operations_in_a_time_round().
        self.cur_time = self.scenario.birth_time_span
        for i in range(self.scenario.growth_rounds + self.scenario.stable_rounds):
            self.operations_in_a_time_round(
                peer_arrival_count[i], peer_dept_count[i], order_arrival_count[i]
            )
            self.cur_time += 1

        # performance evaluation
        # input arguments are: time, peer set, normal peer set, free rider set, order set
        performance_result: SingleRunPerformanceResult = self.performance.run(
            self.cur_time,
            self.peer_full_set,
            self.peer_type_set_mapping["normal"],
            self.peer_type_set_mapping["free_rider"],
            self.order_full_set,
        )

        return performance_result
