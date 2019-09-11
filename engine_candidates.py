"""
This module contains all possible realizations of functions in the Engine class.
"""

import random
from typing import Set, List, TYPE_CHECKING
from data_types import Preference, Priority

if TYPE_CHECKING:
    from node import Peer, Neighbor
    from message import Order, OrderInfo


def set_preference_passive(
    neighbor: "Neighbor", _peer: "Peer", _master: "Peer", preference: Preference
) -> None:
    """
    This is a candidate design for setting preference of a neighbor instance.
    It is called by method neighbor_set_preference() in class Engine.
    The passive implementation just sets the neighbor's preference as preference.
    The physical meaning is: if the neighbor knows the value to set, then set it as that value;
    otherwise, the default value for preference is None, so simply set it as None.
    :param neighbor: the neighbor instance of the neighbor to be set a preference
    :param _peer: the peer instance for this neighbor. In the passive implementation we don't
    need to use it.
    :param _master: the peer instance of the node who wants to set the preference for its neighbor.
    In the passive implementation we don't need to use it.
    :param preference: the pre-set value of the preference. Default is None.
    :return: None.
    """
    neighbor.preference = preference


def set_priority_passive(
    orderinfo: "OrderInfo", _order: "Order", _master: "Peer", priority: Priority
) -> None:
    """
    This is a candidate design for setting a priority of an orderinfo instance.
    It is called by method orderinfo_set_priority() in class Engine.
    The physical meaning of a passive implementation is similar to the above method.
    :param orderinfo: the orderinfo instance of the orderinfo to be set a priority
    :param _order: the order instance of the orderinfo. Unused in passive implementation
    :param _master: the peer instance of the node who wants to set the priority
    :param priority: the pre-set priority. Default is None.
    :return: None.
    """
    orderinfo.priority = priority


def store_first(peer: "Peer") -> None:
    """
    This is a candidate design for storing orders.
    It is called by method order_storage() in class Engine.
    Note that there might be multiple orderinfo instances for a given order instance.
    The design needs to make sure to store at most one of such orderinfo instances.
    The choice is: store the first instance of orderinfo for every order.
    :param peer: the peer instance of the node to make a decision
    :return: None. Results are recorded in orderinfo.storage_decision.
    """

    # Let "order_a" and "order_b" be two order instances. Let "orderinfo_a1" and "orderinfo_a2"
    # be two orderinfo instances which both refer to order_a. Let "orderinfo_b1" and "orderinfo_b2"
    # be two orderinfo instances which both refer to order_b. Then
    # peer.order_pending_orderinfo_mapping will look like:
    # peer.order_pending_orderinfo_mapping =
    # { order_a: [orderinfo_a1, orderinfo_a2],
    #   order_b: [orderinfo_b1, orderinfo_b2] }.
    # We will use "orderinfo_list" to refer to lists like [orderinfo_a1, orderinfo_a2].

    for orderinfo_list in peer.order_pending_orderinfo_mapping.values():
        orderinfo_list[0].storage_decision = True  # first orderinfo is stored
        for orderinfo in orderinfo_list[1:]:  # the rest (if any) are not stored
            orderinfo.storage_decision = False


def share_all_new_selected_old(
    max_to_share: int, old_prob: float, peer: "Peer"
) -> Set["Order"]:
    """
    This is a candidate design for deciding which orders to share.
    It is called by method orders_to_share() in class Engine.
    The choice is: share min(max_to_share, number of new_orders) of new orders,
    and share min(remaining_quota, [number of old peers] * old_prob) of old orders,
    where remaining_quota = max(0, max_to_share minus #_of_new_orders_selected).
    :param max_to_share: the maximal number of orders to share.
    :param old_prob: the probability of sharing an old order.
    :param peer: the peer instance of the node to make a decision.
    :return: set of order instances selected to share
    """

    new_order_set: Set["Order"] = peer.new_order_set
    old_order_set: Set["Order"] = set(peer.order_orderinfo_mapping) - peer.new_order_set
    selected_order_set: Set["Order"] = set()

    selected_order_set |= set(
        random.sample(new_order_set, min(max_to_share, len(new_order_set)))
    )

    remaining_share_size: int = max(0, max_to_share - len(new_order_set))
    probability_selection_size: int = round(len(old_order_set) * old_prob)
    selected_order_set |= set(
        random.sample(
            old_order_set, min(remaining_share_size, probability_selection_size)
        )
    )
    return selected_order_set


def weighted_sum(
    lazy_contribution: int, lazy_length: int, discount: List[float], peer: "Peer"
) -> None:
    """
    This is a candidate design for calculating the scores of neighbors of the peer.
    It is called by method score_neighbors() in class Engine.
    The choice is: (1) calculate the current score by a weighted sum of all elements in the queue
    (2) update the queue by moving one step forward and delete the oldest element, and
    (3) delete a neighbor if it has been lazy for a long time.
    If a neighbor's score is under self.lazy_contribution, it is "lazy" in this batch;
    If a neighbor has been lazy for self.lazy_length batches, it is permanently lazy and gets
    kicked off.
    :param lazy_contribution: see explanation above.
    :param lazy_length: see explanation above.
    :param discount: a list of weights for each element of the score queue. The score is a
    weighted sum of the elements in the queue.
    :param peer: the peer instance of the node that does the calculation.
    :return: None. The score is recorded in neighbor.score
    """

    # HACK (weijiewu): Need to move out the operation of deleting neighbors from this function.
    # It is totally independent to calculating scores.

    # neighboring_peer is the peer instance for a neighbor
    # neighbor is the neighbor instance for a neighbor
    for neighboring_peer in list(peer.peer_neighbor_mapping):
        neighbor: "Neighbor" = peer.peer_neighbor_mapping[neighboring_peer]
        # update laziness
        if neighbor.share_contribution[-1] <= lazy_contribution:
            neighbor.lazy_round += 1
        else:
            neighbor.lazy_round = 0
        # delete neighbor if necessary
        if neighbor.lazy_round >= lazy_length:
            peer.del_neighbor(neighboring_peer)
            continue
        neighbor.score = sum(
            a * b for a, b in zip(neighbor.share_contribution, discount)
        )


def tit_for_tat(
    baby_ending: int, mutual: int, optimistic: int, time_now: int, peer: "Peer"
) -> Set["Peer"]:
    """
    This is a candidate design to select beneficiaries from neighbors.
    It is called by method neighbors_to_share() in class Engine.
    The choice is similar to tit-for-tat in BitTorrent.
    If this is a new peer (age <= baby_ending) so it does not know its neighbors well, it shares
    to random neighbors (# = mutual + optimistic). Otherwise, it shares to (# = "mutual")
    high-reputation neighbors, and (# = "optimistic") of other random neighbors.
    In the case fewer than (# = "mutual") neighbors have positive scores, only select the
    neighbors with positive scores as high-reputation neighbors. The number of other random
    neighbors is still "optimistic" (i.e., the quota for beneficiaries is not fully utilized in
    such a case).
    :param baby_ending: see explanation above.
    :param mutual: see explanation above.
    :param optimistic: see explanation above.
    :param time_now: current time.
    :param peer: the peer instance of the node who is making the decision.
    :return: set of peer instances of the nodes selected as beneficiaries.
    """

    selected_peer_set: Set["Peer"] = set()
    if (
        time_now - peer.birth_time <= baby_ending
    ):  # This is a new peer. Random select neighbors.
        # HACK (weijiewu8): There is a minor issue here. Note that we have birth_time_span
        # in scenario instance, where the initial peers can have birth times of any value over
        # [0, birth_time_span). Immediately after that, say, if a new peer was born at
        # birth_time_span, then it should still be considered as a baby peer since it knows
        # nothing about its neighbors, but it is possible that birth_time_span - peer.birth_time
        # > baby_ending. So strictly speaking, we should have the if judgment as:
        # ```if time_now - max(peer.birth_time, scenario.birth_time_span] <= baby_ending```
        # However, we require some changes in codes to make it and I prefer leaving it to the
        # next PR.

        selected_peer_set |= set(
            random.sample(
                list(peer.peer_neighbor_mapping),
                min(len(peer.peer_neighbor_mapping), mutual + optimistic),
            )
        )
    else:  # This is an old peer
        # ranked_list_of_peers is a list of peer instances who are my neighbors
        # and they are ranked according to their scores that I calculate.
        ranked_list_of_peers: List["Peer"] = peer.rank_neighbors()
        mutual = min(mutual, len(ranked_list_of_peers))
        while (
            mutual > 0
            and peer.peer_neighbor_mapping[ranked_list_of_peers[mutual - 1]].score == 0
        ):
            mutual -= 1

        highly_ranked_peers_list: List["Peer"] = ranked_list_of_peers[:mutual]
        lowly_ranked_peers_list: List["Peer"] = ranked_list_of_peers[mutual:]
        selected_peer_set |= set(highly_ranked_peers_list)
        selected_peer_set |= set(
            random.sample(
                lowly_ranked_peers_list, min(len(lowly_ranked_peers_list), optimistic)
            )
        )
    return selected_peer_set


def random_recommendation(
    _requester: "Peer", base: Set["Peer"], target_number: int
) -> Set["Peer"]:
    """
    This is a candidate design for neighbor recommendation.
    It is called by method neighbor_rec() in class Engine.
    The choice is to choose (# = target_number) elements from the base
    (the set of all candidates) in a totally random manner.
    The current implementation does not need to take in the argument of requester.
    :param _requester: the peer instance of the node who makes request for neighbor introduction.
    :param base: see above for explanation.
    :param target_number: see above for explanation.
    :return: set of peer instances selected from base.
    """
    if not base or not target_number:
        raise ValueError("Base set is empty or target number is zero.")
    # if the target number is larger than the set size, output the whole set.
    return set(random.sample(base, min(target_number, len(base))))
