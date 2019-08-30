"""
This module contains Neighbor and Peer classes. They are both representatives of nodes.
Note that sometimes we use "node" and "peer" interchangeably in the comment.
"""

import collections
from typing import Deque, Set, Dict, List, Tuple, TYPE_CHECKING
from message import OrderInfo, Order
from data_types import PeerTypeName, Preference, NameSpacing, Priority

if TYPE_CHECKING:
    from engine import Engine


class Neighbor:
    """
    Each peer maintains a set of neighbors. Note, a neighbor is physically also a node,
    but a neighbor instance is not a peer instance; instead, it has specialized information
    from a peer's viewpoint. For information stored in the Peer instance,
    refer to the mapping table in the SingleRun instance and find the corresponding Peer instance.
    """

    def __init__(
        self,
        engine: "Engine",
        peer: "Peer",
        master: "Peer",
        est_time: int,
        preference: Preference = None,
    ) -> None:

        self.engine: Engine = engine  # design choice
        self.est_time: int = est_time  # establishment time

        self.preference: Preference = preference

        # "peer" is the peer instance of this neighbor
        # "master" is the peer instance of whom that regards me as a neighbor.
        # The following function sets up the master node's preference to this neighbor
        self.engine.set_preference_for_neighbor(
            neighbor=self, peer=peer, master=master, preference=preference
        )

        # If peer A shares his info to peer B, we say peer A contributes to B.
        # Such contribution is recorded in peer B's local record, i.e.,
        # the neighbor instance for peer A in the local storage of peer B.
        # Formally, "share_contribution" is a queue to record a length of "score_length"
        # of contributions, each corresponding to the score in one of the previous batches.
        self.share_contribution: Deque[float] = collections.deque()
        for _ in range(engine.score_length):
            self.share_contribution.append(0.0)

        self.score: float = 0.0  # the score to evaluate my neighbor.

        # lazy_round is the number of batch periods over which this peer has be regarded as a
        # lazy neighbor. A neighbor is regarded as lazy if its score in one batch is below a
        # certain value. Default for lazy_round is 0. Increased by 1 if its score is below that
        # certain value, or reset to 0 otherwise.
        self.lazy_round: int = 0


# Peer class, each peer instance being a node in the mesh.


class Peer:

    """
    The Peer class is the main representation of a node in the Mesh.
    """

    def __init__(
        self,
        engine: "Engine",
        seq: int,
        birth_time: int,
        init_orders: Set[Order],
        namespacing: NameSpacing,
        peer_type: PeerTypeName,
    ) -> None:

        # Note: initialization deals with initial orders, but does not establish neighborhood
        # relationships.

        self.local_clock: int = birth_time

        # simple parameter setting
        self.engine: "Engine" = engine  # design choice
        self.seq: int = seq  # sequence number. Not in use now, for reserve purpose only.
        self.birth_time: int = birth_time
        self.init_orderbook_size: int = len(init_orders)
        # interest in certain trading groups
        self.namespacing: NameSpacing = namespacing
        self.peer_type: PeerTypeName = peer_type  # e.g., big/small relayer

        # This denotes if this peer is a free rider (no contribution to other peers)
        # This is a redundant variable, for better readability only.
        # A free rider sits in the system, listens to orders, and does nothing else.
        # It does not generate orders by itself.
        self.is_free_rider: bool = (peer_type == "free_rider")

        # mapping from the order instance to orderinfo instances that have been formally stored.
        self.order_orderinfo_mapping: Dict[Order, OrderInfo] = {}
        # mapping from the peer instance to neighbor instance. Note, neighborhood relationship
        # must be bilateral.
        self.peer_neighbor_mapping: Dict["Peer", Neighbor] = {}
        # set of newly and formally-stored orders that have NEVER been shared out by this peer.
        self.new_order_set: Set[Order] = set()

        # The following mapping maintains a table of pending orders, by recording their orderinfo
        # instance. Note that an order can have multiple orderinfo instances, because it can be
        # forwarded by different neighbors.
        self.order_pending_orderinfo_mapping: Dict[Order, List[OrderInfo]] = {}

        if self.is_free_rider and init_orders:
            raise ValueError("Free riders should not have their own orders.")

        # initiate orderinfo instances
        # initial orders will directly be stored without going through the storage decision.
        for order in init_orders:
            # if this order is created by this peer, but in the peer initialization,
            # it was unable to define the creator as this peer since the peer has not been created.
            # there we defined the creator as None, and we will modify here.
            if order.creator is None:
                order.creator = self

            priority: Priority = None  # we don't set the priority for now
            new_orderinfo = OrderInfo(
                engine=engine,
                order=order,
                master=self,
                arrival_time=birth_time,
                priority=priority,
            )
            self.order_orderinfo_mapping[order] = new_orderinfo
            self.new_order_set.add(order)

            # not sure if this is useful. Just keep it here to keep consistency.
            new_orderinfo.storage_decision = True
            order.holders.add(self)

    def should_accept_neighbor_request(self, requester: "Peer") -> bool:
        """
        This method is for a peer instance to determine whether they accept a neighbor
        establishment request or not.
        It is called when a request of establishing a neighborhood relationship is called from
        another peer. This peer, which is requested, will return True for agreement by default,
        False if the current number of neighbors already reaches the maximal.
        :param requester: the peer instance of another node requesting to establish a new
        neighborhood relationship.
        :return: True if accepted, or False otherwise.
        Note: this method does not establish neighborhood relationship by itself.
        It accepts or rejects the request only.
        """

        if requester in self.peer_neighbor_mapping or requester == self:
            raise ValueError("Called by a wrong peer.")

        return len(self.peer_neighbor_mapping) < self.engine.neighbor_max

    def add_neighbor(self, peer: "Peer") -> None:
        """
        This method establishes a neighborhood relationship.
        This method can only be called in method add_new_links_helper() in class SingleRun.
        Once it is called, a neighborhood relationship should be ready for establishment;
        otherwise, it is an error (e.g., one party has already had the other party as a neighbor).
        :param peer: the peer instance of the node to be added as a neighbor.
        :return: None
        """
        if peer in self.peer_neighbor_mapping or peer == self:
            raise ValueError("Function called by a wrong peer.")
        # create new neighbor in my local storage
        new_neighbor = Neighbor(
            engine=self.engine, peer=peer, master=self, est_time=self.local_clock
        )
        self.peer_neighbor_mapping[peer] = new_neighbor

    def accept_neighbor_cancellation(self, requester: "Peer") -> None:
        """
        This method defines what a peer will do if it's notified by someone for cancelling a
        neighborhood relationship. It will always accept the cancellation, and delete that peer
        from his neighbor. Note that this is different from a real system that a peer simply
        drops a neighborhood relationship without need of being accepted by the other side. This
        function is for simulation bookkeeping purpose only.
        :param requester: peer instance of the node requesting to cancel neighborhood.
        :return: None.
        Explanation: If I am removed as a neighbor by my neighbor, I will delete him as well.
        But I will not remove orders from him, and I don't need to inform him to delete me again.
        """
        if requester in self.peer_neighbor_mapping:
            self.del_neighbor(peer=requester, remove_order=False, notification=False)

    def del_neighbor(
        self, peer: "Peer", remove_order: bool = False, notification: bool = True
    ) -> None:
        """
        This method deletes a neighbor.
        :param peer: the peer instance of the neighbor to be deleted.
        :param remove_order: If remove_order is True, then all orderinfo instances with the
        prev_owner being this neighbor will also be deleted (order instances are still there).
        :param notification: whether to notify the other party to cancel neighborhood.
        :return: None
        """
        if peer not in self.peer_neighbor_mapping:
            raise ValueError("This peer is not my neighbor. Unable to delete.")

        # if remove_order is True, delete all orders whose previous owner is this neighbor

        if remove_order:
            for order in list(self.order_orderinfo_mapping):
                orderinfo = self.order_orderinfo_mapping[order]
                if orderinfo.prev_owner == peer:
                    order.holders.remove(self)
                    self.new_order_set.discard(order)
                    del self.order_orderinfo_mapping[order]

            for order in list(self.order_pending_orderinfo_mapping):
                orderinfo_list = self.order_pending_orderinfo_mapping[order]
                for idx, orderinfo in enumerate(orderinfo_list):
                    if orderinfo.prev_owner == peer:
                        del orderinfo_list[idx]
                if (
                    not orderinfo_list
                ):  # no pending orderinfo. need to delete this entry
                    order.hesitators.remove(self)
                    del self.order_pending_orderinfo_mapping[order]

        # if this neighbor is still an active peer, notify him to delete me as well.
        if notification:
            peer.accept_neighbor_cancellation(self)

        # delete this neighbor
        del self.peer_neighbor_mapping[peer]

    def receive_order_external(self, order: Order) -> None:
        """
        This method is called by method order_arrival() in class SingleRun.
        An OrderInfo instance will be created and put into pending table (just to keep consistent
        with method receive_order_internal(), though most likely it will be accepted).
        :param order: the order instance of the order arrived externally.
        :return: None
        """
        if order in self.order_pending_orderinfo_mapping:
            raise ValueError("Duplicated external order in pending table.")
        if order in self.order_orderinfo_mapping:
            raise ValueError("Duplicated external order in local storage.")

        if self.engine.should_accept_external_order(self, order):
            # create the orderinfo instance and add it into the local mapping table
            new_orderinfo = OrderInfo(
                engine=self.engine,
                order=order,
                master=self,
                arrival_time=self.local_clock,
            )
            self.order_pending_orderinfo_mapping[order] = [new_orderinfo]
            # update the number of replicas for this order and hesitator of this order
            # a peer is a hesitator of an order if this order is in its pending table
            order.hesitators.add(self)

    def receive_order_internal(
        self, peer: "Peer", order: Order, novelty_update: bool = False
    ) -> None:
        """
        The method is called by method share_order() in class SingleRun.
        It will immediately decide whether to put the order from the peer (who is my neighbor)
        into my pending table.
        :param peer: the peer instance of the node who sends the order
        :param order: the order instance.
        :param novelty_update: an binary option. if True, the value of OrderInfo
        instance will increase by one once transmitted.
        :return: None
        """

        if (
            self not in peer.peer_neighbor_mapping
            or peer not in self.peer_neighbor_mapping
        ):
            raise ValueError("Receiving order from non-neighbor.")

        neighbor: Neighbor = self.peer_neighbor_mapping[peer]

        if not self.engine.should_accept_internal_order(self, peer, order):
            # update the contribution of my neighbor for his sharing
            neighbor.share_contribution[-1] += self.engine.penalty_a
            return

        if order in self.order_orderinfo_mapping:  # no need to store again
            orderinfo: OrderInfo = self.order_orderinfo_mapping[order]
            if orderinfo.prev_owner == peer:
                # I have this order in my local storage. My neighbor is sending me the same order
                # again. It may be due to randomness of sharing old orders.
                neighbor.share_contribution[-1] += self.engine.reward_a
            else:
                # I have this order in my local storage, but it was from someone else.
                # No need to store it anymore. Just update the reward for the uploader.
                neighbor.share_contribution[-1] += self.engine.reward_b
            return

        # If this order has not been formally stored: Need to write it into the pending table (
        # even if there has been one with the same sequence number).

        if novelty_update:
            order_novelty = peer.order_orderinfo_mapping[order].novelty + 1
        else:
            order_novelty = peer.order_orderinfo_mapping[order].novelty

        # create an orderinfo instance
        new_orderinfo: OrderInfo = OrderInfo(
            engine=self.engine,
            order=order,
            master=self,
            arrival_time=self.local_clock,
            priority=None,
            prev_owner=peer,
            novelty=order_novelty,
        )

        # If no such order in the pending list, create an entry for it
        if order not in self.order_pending_orderinfo_mapping:
            # order not in the pending set
            self.order_pending_orderinfo_mapping[order] = [new_orderinfo]
            order.hesitators.add(self)
            # Put into the pending table. Reward will be updated when storing decision is made.
            return

        # If there is such an order in the pending list, check if it is from the same prev_owner.
        for existing_orderinfo in self.order_pending_orderinfo_mapping[order]:
            if peer == existing_orderinfo.prev_owner:
                # This neighbor is sending duplicates to me in a short period of time. Likely to
                # be a malicious one.
                # Penalty is imposed to this neighbor. But please be noted that this peer's
                # previous copy is still in the pending list, and if it is finally stored,
                # this peer will still get a reward for the order being stored.
                neighbor.share_contribution[-1] += self.engine.penalty_b
                return

        # My neighbor is honest, but he is late in sending me the message.
        # Add it to the pending list anyway since later, his version of the order might be selected.
        self.order_pending_orderinfo_mapping[order].append(new_orderinfo)

    def store_orders(self) -> None:
        """
        This method determines which orders to store and which to discard, for all orders
        in the pending table. It is proactively called by each peer at the end of a batch period.
        :return: None
        """

        if (self.local_clock - self.birth_time) % self.engine.batch != 0:
            raise RuntimeError(
                "Store order decision should not be called at this time."
            )

        # change orderinfo.storage_decision to True if you would like to store this order.
        self.engine.store_or_discard_orders(self)

        # Now store an orderinfo if necessary

        for order, orderinfo_list in self.order_pending_orderinfo_mapping.items():

            # Sort the list of pending orderinfo with the same order instance, so that if
            # there is some order to be stored, it will be the first one.
            orderinfo_list.sort(key=lambda item: item.storage_decision, reverse=True)

            # Update the order instance, e.g., number of pending orders, and remove the
            # hesitator, in advance.
            order.hesitators.remove(self)

            # After sorting, for all pending orderinfo with the same order instance,
            # either (1) no one is to be stored, or (2) only the first one is stored

            if not orderinfo_list[0].storage_decision:  # if nothing is to be stored
                for pending_orderinfo in orderinfo_list:
                    # Find the global instance of the sender, and update it.
                    # If it is an internal order and sender is still a neighbor
                    if pending_orderinfo.prev_owner in self.peer_neighbor_mapping:
                        self.peer_neighbor_mapping[
                            pending_orderinfo.prev_owner
                        ].share_contribution[-1] += self.engine.reward_c

            else:  # the first element is to be stored
                first_pending_orderinfo: OrderInfo = orderinfo_list[0]
                # Find the global instance for the sender, and update it.
                # If it is an internal order and sender is still a neighbor
                if first_pending_orderinfo.prev_owner in self.peer_neighbor_mapping:
                    self.peer_neighbor_mapping[
                        first_pending_orderinfo.prev_owner
                    ].share_contribution[-1] += self.engine.reward_d
                # Add the orderinfo instance into the local storage, and update the order instance
                self.order_orderinfo_mapping[order] = first_pending_orderinfo
                self.new_order_set.add(order)
                order.holders.add(self)

                # For the remaining pending orderinfo in the list, no need to store them,
                # but may need updates.
                for pending_orderinfo in orderinfo_list[1:]:
                    if pending_orderinfo.storage_decision:
                        raise ValueError(
                            "Should not store multiple copies of same orders."
                        )
                    # internal order, sender is still neighbor
                    if pending_orderinfo.prev_owner in self.peer_neighbor_mapping:
                        # update the share contribution
                        self.peer_neighbor_mapping[
                            pending_orderinfo.prev_owner
                        ].share_contribution[-1] += self.engine.reward_e

        # clear the pending mapping table
        self.order_pending_orderinfo_mapping.clear()

    def share_orders(self) -> Tuple[Set[Order], Set["Peer"]]:
        """
        This method determines which orders to be shared to which neighbors.
        It will return the set of orders to share, and the set of neighboring peers to share.
        This method is only called by each peer proactively at the end of a batch period.
        :return: Tuple[set of orders to share, set of peers to share]
        """

        if (self.local_clock - self.birth_time) % self.engine.batch != 0:
            raise RuntimeError(
                "Share order decision should not be called at this time."
            )

        # free riders do not share any order.
        if self.is_free_rider:
            self.new_order_set.clear()
            return set(), set()

        # Otherwise, this function has to go through order by order and neighbor by neighbor.

        # orders to share
        order_to_share_set: Set[Order] = self.engine.find_orders_to_share(self)

        # clear self.new_order_set for future use
        self.new_order_set.clear()

        # peers to share
        peer_to_share_set: Set["Peer"] = self.engine.find_neighbors_to_share(
            self.local_clock, self
        )

        return order_to_share_set, peer_to_share_set

    def del_order(self, order: Order) -> None:
        """
        This method deletes all orderinfo instances of a particular order.
        :param order: the order instance of the order to be deleted.
        :return: None
        """
        # check if this order is in the pending table
        if order in self.order_pending_orderinfo_mapping:
            order.hesitators.remove(self)
            del self.order_pending_orderinfo_mapping[order]
        # check if this order is in the local storage
        if order in self.order_orderinfo_mapping:
            self.new_order_set.discard(order)
            del self.order_orderinfo_mapping[order]
            order.holders.remove(self)

    def rank_neighbors(self) -> List["Peer"]:
        """
        This method ranks neighbors according to their scores. It is called by internal method
        share_orders().
        :return: a list peer instances ranked by the scores of their corresponding neighbor
        instances, from top to down.
        """
        self.engine.score_neighbors(self)
        peer_list: List["Peer"] = list(self.peer_neighbor_mapping)
        peer_list.sort(
            key=lambda item: self.peer_neighbor_mapping[item].score, reverse=True
        )
        return peer_list
