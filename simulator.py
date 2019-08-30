"""
This module contains the SingleRun class only.
"""

# HACK (weijiewu8): Propose to change the name of the module to "single_run".
# If I change the name now, no comparison of changes can be seen. So I will change it after the
# PR is approved.

import random
from typing import Dict, Set, List, TYPE_CHECKING, cast
import numpy
from message import Order
from node import Peer
from data_types import (
    SingleRunPerformanceResult,
    PeerTypeName,
    OrderTypeName,
    PeerProperty,
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

        self.scenario: "Scenario" = scenario  # assumptions
        self.engine: "Engine" = engine  # design choices
        self.performance: "Performance" = performance  # performance evaluation measures

    def create_initial_peers_orders(self) -> None:
        """
        This method creates the initial orders and peers for a SingleRun instance, and maintain
        their references in two sets.
        Sequence numbers of peers and neighbors begin from 0 and increase by 1 each time.
        Right now there is no use for the sequence numbers but we keep them for potential future use
        :return: None
        """

        # HACK (weijiewu8): There is only one type of orders (default) and it is hard coded.
        # This appears not only in this method, but need to check "default" for the entire code
        # base.

        # order sequence number should start from zero, but can be customized
        order_seq: int = self.latest_order_seq
        peer_seq: int = self.latest_peer_seq  # same as above

        # determine the peer types

        peer_type_candidates: List[PeerTypeName] = []
        peer_weights: List[float] = []
        for peer_type, peer_property in self.scenario.peer_type_property.items():
            # This is similar to the cast in __init__ function of this class.
            # peer_type is certainly of type PeerTypeName, since PeerTypeName is the literal
            # containing all keys in order_type_property. However mypy doesn't know that. We have to
            # use a cast.
            peer_type_candidates.append(cast(PeerTypeName, peer_type))

            # this check is only to help mypy judge data types. Not expected to raise an error.
            if isinstance(peer_property, PeerProperty):
                peer_weights.append(peer_property.ratio)
            else:
                raise RuntimeError("Data type in a mass.")

        peer_type_vector: List[PeerTypeName] = random.choices(
            peer_type_candidates, weights=peer_weights, k=self.scenario.init_size
        )

        # first create all peer instances with no neighbors

        for peer_type in peer_type_vector:

            # decide the birth time for this peer. Randomized over [0, birth_time_span] to avoid
            # sequentiality issue.
            birth_time: int = random.randint(0, self.scenario.birth_time_span - 1)

            # decide the number of orders for this peer

            num_mean: float = self.scenario.peer_type_property[
                peer_type
            ].initial_orderbook_size.mean

            num_var: float = self.scenario.peer_type_property[
                peer_type
            ].initial_orderbook_size.var
            num_orders: int = max(0, round(random.gauss(num_mean, num_var)))

            # create all order instances, and the initial orderbooks
            cur_order_set: Set["Order"] = set()

            for _ in range(num_orders):
                # decide the max expiration for this order
                expiration_mean: float = self.scenario.order_type_property[
                    "default"
                ].expiration.mean
                expiration_var: float = self.scenario.order_type_property[
                    "default"
                ].expiration.var
                expiration: int = max(
                    0, round(random.gauss(expiration_mean, expiration_var))
                )

                # create the order. Order's birth time is cur_time, different from peer's birth
                # time. Order's creator is set to be None since the peer is not initiated,
                # but will be changed in the peer's initiation function.

                new_order = Order(
                    self.scenario, order_seq, self.cur_time, None, expiration
                )
                self.order_full_set.add(new_order)
                self.order_type_set_mapping["default"].add(new_order)
                cur_order_set.add(new_order)
                order_seq += 1

            # create the peer instance. Neighbor set is empty.
            new_peer = Peer(
                self.engine, peer_seq, birth_time, cur_order_set, None, peer_type
            )
            new_peer.local_clock = self.scenario.birth_time_span - 1
            self.peer_full_set.add(new_peer)
            self.peer_type_set_mapping[peer_type].add(new_peer)
            peer_seq += 1

        # update the latest order sequence number and latest peer sequence number
        self.latest_order_seq = order_seq
        self.latest_peer_seq = peer_seq

        # add neighbors to the peers. Use shuffle function to avoid preference of forming
        # neighbors for peers with small sequence number.
        peer_list: List["Peer"] = list(self.peer_full_set)
        random.shuffle(peer_list)
        self.check_adding_neighbor()

    def peer_arrival(self, peer_type: PeerTypeName, num_orders: int) -> None:
        """
        This method deals with peer arrival.
        When a new peer arrives, it may already have a set of orders. It only needs to specify
        the number of initial orders, and the function will specify the sequence numbers for the
        peers and orders.
        :param peer_type: the type of the newly arrived peer.
        :param num_orders: number of orders that this peer brings to the system initially.
        :return: None
        """

        # decide this peer's sequence number
        peer_seq: int = self.latest_peer_seq

        # create the initial orders for this peer and update global order set
        cur_order_set: Set["Order"] = set()
        order_seq: int = self.latest_order_seq
        for _ in range(num_orders):
            expiration_mean: float = self.scenario.order_type_property[
                "default"
            ].expiration.mean
            expiration_var: float = self.scenario.order_type_property[
                "default"
            ].expiration.var
            expiration: int = max(
                0, round(random.gauss(expiration_mean, expiration_var))
            )
            # Now we initiate the new orders, whose creator should be the new peer.
            # But the new peer has not been initiated, so we set the creator to be None temporarily.
            # We will modify it when the peer is initiated.
            # This is tricky and informal, but I don't have a better way of doing it right now.
            new_order = Order(
                scenario=self.scenario,
                seq=order_seq,
                birth_time=self.cur_time,
                creator=None,
                expiration=expiration,
            )
            self.order_full_set.add(new_order)
            self.order_type_set_mapping["default"].add(new_order)
            cur_order_set.add(new_order)
            order_seq += 1

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

        # update latest sequence numbers for peer and order
        self.latest_peer_seq += 1
        self.latest_order_seq = order_seq

    def peer_departure(self, peer: Peer) -> None:
        """
        This method deals with node departing the system
        :param peer: peer instance of the node departing the system.
        :return: None.
        """

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

    def order_arrival(self, target_peer: Peer, expiration: int) -> None:
        """
        This method initiates an external order arrival, whose creator is the "target_peer"
        :param target_peer: See explanation above.
        :param expiration: expiration for this order.
        :return: None
        """

        # create a new order
        new_order_seq: int = self.latest_order_seq
        new_order = Order(
            scenario=self.scenario,
            seq=new_order_seq,
            birth_time=self.cur_time,
            creator=target_peer,
            expiration=expiration,
        )

        # update the set of orders for the SingleRun
        self.order_full_set.add(new_order)
        self.order_type_set_mapping["default"].add(new_order)
        self.latest_order_seq += 1

        # update the order info to the target peer
        target_peer.receive_order_external(new_order)

    def update_global_orderbook(self, order_cancel_set: List[Order] = None) -> None:
        """
        This method takes a set of orders to cancel as input, deletes them, and deletes all other
        invalid orders from both order set of SingleRun instance, and all peers' pending table and
        storage.
        :param order_cancel_set: a set of orders to be canceled
        :return: None.
        """

        if order_cancel_set:
            for order in order_cancel_set:
                order.is_canceled = True

        for order in list(self.order_full_set):
            if (
                (not order.holders)
                and (not order.hesitators)
                or (self.cur_time - order.birth_time >= order.expiration)
                or order.is_settled
                or order.is_canceled
            ):
                for peer in list(order.holders):
                    peer.del_order(order)
                for peer in list(order.hesitators):
                    peer.del_order(order)
                self.order_full_set.remove(order)
                self.order_type_set_mapping["default"].remove(order)

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
            raise ValueError(
                "Wrong in requested number(s) or range for adding neighbors."
            )

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
        peers to depart, this method randomly selects the peers and let them depart.
        """
        for peer_to_depart in random.sample(
            self.peer_full_set, min(len(self.peer_full_set), peer_dept_num)
        ):
            self.peer_departure(peer_to_depart)

    def group_of_peers_arrival_helper(self, peer_arr_num: int) -> None:
        """
        This is a helper method for operations_in_a_time_round(). Given a certain number of
        peers to arrive, this method determines the peers' types according to their weights in
        the system, and the values of attributes of each peer, and create them.
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
            num_mean: float = self.scenario.peer_type_property[
                peer_type
            ].initial_orderbook_size.mean
            num_var: float = self.scenario.peer_type_property[
                peer_type
            ].initial_orderbook_size.var
            num_init_orders: int = max(0, round(random.gauss(num_mean, num_var)))
            self.peer_arrival(peer_type, num_init_orders)

    def group_of_orders_arrival_helper(self, order_arr_num):
        """
        This is a helper method for operations_in_a_time_round(). Given a certain number of
        order arrival, this method determines the initial holders (peers) of these orders, and
        the values of attributes of the orders, and create them.
        """

        # Decide which peers to hold these orders.
        # The probability for any peer to get an order is proportional to its init orderbook size.
        # Free riders will not be candidates since they don't have init orderbook.

        candidate_peer_list: List[Peer] = list(self.peer_full_set)
        peer_capacity_weight: List[int] = list(
            item.init_orderbook_size for item in candidate_peer_list
        )

        target_peer_list: List[Peer] = random.choices(
            candidate_peer_list, weights=peer_capacity_weight, k=order_arr_num
        )

        for target_peer in target_peer_list:
            # decide the max expiration for this order.
            # Assuming there is only one type of orders 'default'. Subject to change later.
            expiration_mean: float = self.scenario.order_type_property[
                "default"
            ].expiration.mean
            expiration_var: float = self.scenario.order_type_property[
                "default"
            ].expiration.var
            expiration: int = max(
                0, round(random.gauss(expiration_mean, expiration_var))
            )
            self.order_arrival(target_peer, expiration)

    def group_of_orders_cancellation_and_update_status(self, order_cancel_num):
        """
        This is a helper method for operations_in_a_time_round(). Given a number of orders to be
        canceled, this method randomly selects the orders to cancel, and then update the status
        of the rest orders and update the global orderbook status.
        """
        order_to_cancel: List[Order] = random.sample(
            self.order_full_set, min(len(self.order_full_set), order_cancel_num)
        )

        for order in self.order_full_set:
            order.update_settled_status()

        self.update_global_orderbook(order_to_cancel)

    def operations_in_a_time_round(
        self,
        peer_arr_num: int,
        peer_dept_num: int,
        order_arr_num: int,
        order_cancel_num: int,
    ) -> None:
        """
        This method runs normal operations at a particular time point.
        It includes peer/order dept/arrival, order status update, and peer's order acceptance,
        storing, and sharing.
        :param peer_arr_num: number of peers arriving the system
        :param peer_dept_num: number of peers departing the system
        :param order_arr_num: number of orders arriving the system
        :param order_cancel_num: number of orders which are canceled
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

        # existing orders canceled, orders settled, and global orderbook updated
        self.group_of_orders_cancellation_and_update_status(order_cancel_num)

        # peer operations
        self.check_adding_neighbor()
        for peer in self.peer_full_set:
            if (self.cur_time - peer.birth_time) % self.engine.batch == 0:
                peer.store_orders()
                (orders_to_share, neighbors_to_share) = peer.share_orders()
                for internal_order in orders_to_share:
                    for beneficiary_peer in neighbors_to_share:
                        beneficiary_peer.receive_order_internal(peer, internal_order)

    def single_run_execution(self) -> SingleRunPerformanceResult:
        """
        This is the method that runs the simulator for one time, including setup, and growth and
        stable periods.
        :return: Performance evaluation results in terms of a list, each element being the result
        of one particular metric (or None if not applicable).
        """

        self.cur_time = 0  # the current system time
        self.latest_order_seq = 0  # the next order sequence number that can be used
        self.latest_peer_seq = 0  # the next peer sequence number that can be used
        self.peer_full_set.clear()  # for each round of simulation, clear everything
        for peer_set in self.peer_type_set_mapping.values():
            peer_set.clear()
        self.order_full_set.clear()
        for order_set in self.order_type_set_mapping.values():
            order_set.clear()

        # Create initial peers and orders. Orders are only held by creators.
        # Peers do not exchange orders at this moment.
        self.create_initial_peers_orders()
        self.update_global_orderbook()

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
        peer_arrival_count, peer_dept_count, order_arrival_count, order_dept_count = map(
            lambda x, y: list(x) + list(y), counts_growth, counts_stable
        )

        # growth period and stable period
        self.cur_time = self.scenario.birth_time_span
        for i in range(self.scenario.growth_rounds + self.scenario.stable_rounds):
            self.operations_in_a_time_round(
                peer_arrival_count[i],
                peer_dept_count[i],
                order_arrival_count[i],
                order_dept_count[i],
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
