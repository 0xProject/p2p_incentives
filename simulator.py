"""
===========================================
Simulator functions.
===========================================
"""

# The Simulator class contains all function that is directly called by the simulator.
# For example, initilization of the system, and operations in each time round.

import random
import numpy
from order import Order
from node import Peer


class Simulator:
    def __init__(self, scenario, engine, performance):

        self.order_full_set = set()  # set of orders
        # mapping from order type to order sets. The value element is a set containing
        # all orders of a particular type.
        self.order_type_set_mapping = {}
        for type_name in scenario.order_type_ratios:
            self.order_type_set_mapping[type_name] = set()

        self.peer_full_set = set()  # set of peers
        # mapping from peer type to peer sets. The value element is a set containing
        # all peers of a particular type.
        self.peer_type_set_mapping = {}
        for type_name in scenario.peer_type_ratios:
            self.peer_type_set_mapping[type_name] = set()

        self.cur_time = 0  # current system time
        self.latest_order_seq = 0  # sequence number for next order to use
        self.latest_peer_seq = 0  # sequence number for next peer to use

        self.scenario = scenario  # assumptions
        self.engine = engine  # design choices
        self.performance = performance  # performance evaluation measures

    # This is the global initialization function for system status.
    # Construct a number of peers and a number of orders and maintain their references in two sets.
    # Sequence numbers of peers and neighbors begin from 0 and increase by 1 each time.
    # Right now there is no use for the sequence numbers but we keep them for potential future use.
    # We only consider one type of orders for now. However, we do consider multiple peer types.
    """
    In current implementation we assume there is only one order type.
    There is a hard-coded line of creating orders of type 'default',
    where we create the initial orderbooks for initial peers.
    """

    def globalInit(self):

        order_seq = (
            self.latest_order_seq
        )  # order sequence number should start from zero, but can be customized
        peer_seq = self.latest_peer_seq  # same as above

        # determine the peer types
        peer_type_candidates = list(self.scenario.peer_type_ratios)
        peer_weights = [
            self.scenario.peer_type_ratios[item]
            for item in peer_type_candidates
        ]
        peer_type_vector = random.choices(
            peer_type_candidates,
            weights=peer_weights,
            k=self.scenario.init_size,
        )

        # first create all peer instances with no neighbors

        for peer_type in peer_type_vector:

            # decide the birth time for this peer.
            # Randomized over [0, birth_time_span] to avoid sequentiality issue.
            birth_time = random.randint(0, self.scenario.birth_time_span - 1)

            # decide the number of orders for this peer
            num_orders = max(
                0,
                round(
                    random.gauss(
                        self.scenario.peer_parameter_dict[peer_type]["mean"],
                        self.scenario.peer_parameter_dict[peer_type]["var"],
                    )
                ),
            )

            # create all order instances, and the initial orderbooks
            cur_order_set = set()

            for _ in range(num_orders):
                # decide the max expiration for this order
                expiration = max(
                    0,
                    round(
                        random.gauss(
                            self.scenario.order_parameter_dict["default"][
                                "mean"
                            ],
                            self.scenario.order_parameter_dict["default"][
                                "var"
                            ],
                        )
                    ),
                )

                # create the order. Order's birth time is cur_time, different from peer's birthtime.
                # Order's creator is set to be None since the peer is not initiated, but will be changed
                # in the peer's initiation function.
                new_order = Order(
                    self.scenario, order_seq, self.cur_time, None, expiration
                )
                self.order_full_set.add(new_order)
                self.order_type_set_mapping["default"].add(new_order)
                cur_order_set.add(new_order)
                order_seq += 1

            # create the peer instance. Neighbor set is empty.
            new_peer = Peer(
                self.engine,
                peer_seq,
                birth_time,
                cur_order_set,
                None,
                peer_type,
            )
            new_peer.local_clock = self.scenario.birth_time_span - 1
            self.peer_full_set.add(new_peer)
            self.peer_type_set_mapping[peer_type].add(new_peer)
            peer_seq += 1

        # update the latest order sequence number and latest peer sequence number
        self.latest_order_seq = order_seq
        self.latest_peer_seq = peer_seq

        # add neighbors to the peers. Use shuffle function to avoid preference of forming neighbors for
        # peers with small sequence number.
        peer_list = list(self.peer_full_set)
        random.shuffle(peer_list)
        self.checkAddingNeighbor()

    # when a new peer arrives, it may already have a set of orders. It only needs to specify the number of initial orders,
    # and the function will specify the sequence numbers for the peers and orders.
    """
    In current implementation we assume there is only one order type.
    There is a hard-coded line of creating orders of type 'default',
    where we create the initial orderbook for this peer.
    """

    def peerArrival(self, peer_type, num_orders):

        # decide this peer's sequence number
        peer_seq = self.latest_peer_seq

        # create the initial orders for this peer and update global order set
        cur_order_set = set()
        order_seq = self.latest_order_seq
        for _ in range(num_orders):
            expiration = max(
                0,
                round(
                    random.gauss(
                        self.scenario.order_parameter_dict["default"]["mean"],
                        self.scenario.order_parameter_dict["default"]["var"],
                    )
                ),
            )
            # Now we initiate the new orders, whose creator should be the new peer.
            # But the new peer has not been initiated, so we set the creator to be None temporarily.
            # We will modify it when the peer is initiated.
            # This is tricky and informal, but I don't have a better way of doing it right now.
            new_order = Order(
                self.scenario, order_seq, self.cur_time, None, expiration
            )
            self.order_full_set.add(new_order)
            self.order_type_set_mapping["default"].add(new_order)
            cur_order_set.add(new_order)
            order_seq += 1

        # create the new peer, and add it to the table
        new_peer = Peer(
            self.engine,
            peer_seq,
            self.cur_time,
            cur_order_set,
            None,
            peer_type,
        )
        self.peer_full_set.add(new_peer)
        self.peer_type_set_mapping[peer_type].add(new_peer)

        # update latest sequence numbers for peer and order
        self.latest_peer_seq += 1
        self.latest_order_seq = order_seq

    # This peer departs from the system.

    def peerDeparture(self, peer):

        # update number of replicas of all stored/pending orders with this peer
        for order in peer.order_orderinfo_mapping:
            order.holders.remove(peer)
        for order in peer.order_pending_orderinfo_mapping:
            order.hesitators.remove(peer)

        # update existing peers
        for other_peer in self.peer_full_set:
            if peer in other_peer.peer_neighbor_mapping:
                other_peer.delNeighbor(peer)

        # update the peer set of the Simulator
        self.peer_full_set.remove(peer)
        self.peer_type_set_mapping[peer.peer_type].remove(peer)

    # This function initiates an external order arrival, whose creator is the "target_peer"

    def orderArrival(self, target_peer, expiration):

        # create a new order
        new_order_seq = self.latest_order_seq
        new_order = Order(
            self.scenario,
            new_order_seq,
            self.cur_time,
            target_peer,
            expiration,
        )

        # update the set of orders for the Simulator
        self.order_full_set.add(new_order)
        self.order_type_set_mapping["default"].add(new_order)
        self.latest_order_seq += 1

        # update the order info to the target peer
        target_peer.receiveOrderExternal(new_order)

    # This function takes a set of orders to depart as input,
    # deletes them, and deletes all other invalid orders
    # from both order set of Simulator, and all peers' pending tables and storages.

    def updateGlobalOrderbook(self, order_dept_set=None):

        if order_dept_set:
            for order in order_dept_set:
                order.is_canceled = True

        for order in list(self.order_full_set):
            if (
                ((not order.holders) and (not order.hesitators))
                or (self.cur_time - order.birthtime >= order.expiration)
                or order.is_settled
                or order.is_canceled
            ):
                for peer in list(order.holders):
                    peer.delOrder(order)
                for peer in list(order.hesitators):
                    peer.delOrder(order)
                self.order_full_set.remove(order)
                self.order_type_set_mapping["default"].remove(order)

        return self.order_full_set

    # The following function helps the requester peer to add neighbors, and is called only by checkAddingNeighbor().
    # It targets at adding demand neighbors, but is fine if the final added number
    # is in the range [mininum, demand], or stops when all possible links are added.
    # This function will call the corresponding peers' functions to add the neighbors, respectively.

    def addNewLinksHelper(self, requester, demand, minimum):

        if demand <= 0 or minimum < 0 or demand < minimum:
            raise ValueError(
                "Wrong in requested number(s) or range for adding neighbors."
            )

        candidates_pool = self.peer_full_set - set([requester])
        selection_size = demand
        links_added = 0

        while links_added < minimum and candidates_pool:

            links_added_this_round = 0
            selected_peer_set = self.engine.neighborRec(
                requester, candidates_pool, selection_size
            )
            for candidate in selected_peer_set:
                # if this peer is already the requester's neighbor, if not,
                # check if the candidate is willing to add the requester.
                if (
                    candidate not in requester.peer_neighbor_mapping
                    and candidate.acceptNeighborRequest(requester)
                ):
                    # mutual add neighbors
                    if not candidate.addNeighbor(
                        requester
                    ) or not requester.addNeighbor(candidate):
                        raise RuntimeError(
                            "Function addNewLinksHelper tries to add some existing neighbor again."
                        )
                    links_added += 1
                    links_added_this_round += 1

            candidates_pool -= selected_peer_set
            selection_size -= links_added_this_round

    # This function checks for all peers if they need to add neighbors,
    # if the number of neighbors is not enough.
    # It aims at adding up to neighbor_max neighbors, but is fine if
    # added up to neighbor_min, or all possibilities have been tried.
    # This function needs to be proactively called every time round.

    def checkAddingNeighbor(self):
        for peer in self.peer_full_set:
            cur_neighbor_size = len(peer.peer_neighbor_mapping)
            if cur_neighbor_size < self.engine.neighbor_min:
                self.addNewLinksHelper(
                    peer,
                    self.engine.neighbor_max - cur_neighbor_size,
                    self.engine.neighbor_min - cur_neighbor_size,
                )

    # The following function runs normal operations at a particular time point.
    # It includes peer/order dept/arrival, order status update,
    # and peer's order acceptance, storing, and sharing.
    # This is a temparaty version. In the next PR, mode will not exist. Please ignore the missing of
    # explanation of "mode" for now.

    def operationsInATimeRound(
        self, peer_arr_num, peer_dept_num, order_arr_num, order_dept_num
    ):

        # peers leave
        for peer_to_depart in random.sample(
            self.peer_full_set, min(len(self.peer_full_set), peer_dept_num)
        ):
            self.peerDeparture(peer_to_depart)

        # existing peers adjust clock
        for peer in self.peer_full_set:
            peer.local_clock += 1
            if peer.local_clock != self.cur_time:
                raise RuntimeError("Clock system in a mass.")

        # new peers come in
        peer_type_candidates = list(self.scenario.peer_type_ratios)
        peer_weights = [
            self.scenario.peer_type_ratios[item]
            for item in peer_type_candidates
        ]
        peer_type_vector = random.choices(
            peer_type_candidates, weights=peer_weights, k=peer_arr_num
        )

        for peer_type in peer_type_vector:
            num_init_orders = max(
                0,
                round(
                    random.gauss(
                        self.scenario.peer_parameter_dict[peer_type]["mean"],
                        self.scenario.peer_parameter_dict[peer_type]["var"],
                    )
                ),
            )
            self.peerArrival(peer_type, num_init_orders)

        # Now, if the system does not have any peers, stop operations in this round.
        # The simulator can still run, hoping that in the next round peers will appear.

        if not self.peer_full_set:
            return

        # if there are only free-riders, then there will be no new order arrival.
        # However, other operations will continue.

        if (
            self.peer_full_set == self.peer_type_set_mapping["free-rider"]
        ):  # all peers are free-riders
            order_arr_num = 0

        # external orders arrival

        # Decide which peers to hold these orders.
        # The probablity for any peer to get an order is proportional to its init orderbook size.
        # Free riders will not be candidates since they don't have init orderbook.
        candidate_peer_list = list(self.peer_full_set)
        peer_capacity_weight = list(
            item.init_orderbook_size for item in candidate_peer_list
        )

        target_peer_list = random.choices(
            candidate_peer_list, weights=peer_capacity_weight, k=order_arr_num
        )

        for target_peer in target_peer_list:
            # decide the max expiration for this order. Assuming there is only one type of orders 'default'. Subject to change later.
            expiration = max(
                0,
                round(
                    random.gauss(
                        self.scenario.order_parameter_dict["default"]["mean"],
                        self.scenario.order_parameter_dict["default"]["var"],
                    )
                ),
            )
            self.orderArrival(target_peer, expiration)

        # existing orders depart, orders settled, and global orderbook updated
        order_to_depart = random.sample(
            self.order_full_set, min(len(self.order_full_set), order_dept_num)
        )

        for order in self.order_full_set:
            order.updateSettledStatus()

        self.updateGlobalOrderbook(order_to_depart)

        # peer operations
        self.checkAddingNeighbor()
        for peer in self.peer_full_set:
            if (self.cur_time - peer.birthtime) % self.engine.batch == 0:
                peer.storeOrders()
                peer.shareOrders()

    # This is the function that runs the simulator, including the initilization, and growth and stable periods.
    # It returns performance evaluation results.

    def run(self):

        self.cur_time = 0  # the current system time
        self.latest_order_seq = 0  # the next order ID that can be used
        self.latest_peer_seq = 0  # the next peer ID that can be used
        self.peer_full_set.clear()  # for each round of simulation, clear everything
        for item in self.peer_type_set_mapping.values():
            item.clear()
        self.order_full_set.clear()
        for item in self.order_type_set_mapping.values():
            item.clear()

        # Initialization, orders are only held by creators
        # Peers do not exchange orders at this moment.
        self.globalInit()
        self.updateGlobalOrderbook()

        # initiate vectors of each event happening count in each time round
        numpy.random.seed()  # this is very important since numpy.random is not multiprocessing safe (when we call Hawkes process)
        counts_growth = list(
            map(
                lambda x: self.scenario.numEvents(
                    x, self.scenario.growth_rounds
                ),
                self.scenario.growth_rates,
            )
        )
        numpy.random.seed()
        counts_stable = list(
            map(
                lambda x: self.scenario.numEvents(
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
        for i in range(
            self.scenario.growth_rounds + self.scenario.stable_rounds
        ):
            self.operationsInATimeRound(
                peer_arrival_count[i],
                peer_dept_count[i],
                order_arrival_count[i],
                order_dept_count[i],
            )
            self.cur_time += 1

        # performance evaluation
        # input arguments are: time, peer set, normal peer set, free rider set, order set
        performance_result = self.performance.run(
            self.cur_time,
            self.peer_full_set,
            self.peer_type_set_mapping["normal"],
            self.peer_type_set_mapping["free-rider"],
            self.order_full_set,
        )

        return performance_result
