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


def weighted_sum(discount: List[float], peer: "Peer") -> None:
    """
    This is a candidate design for calculating the scores of neighbors of the peer. It calculates
    the current score by a weighted sum of all elements in the queue.
    Note, the queue is not updated here; it is updated in engine.find_neighbors_to_share().
    :param discount: a list of weights for each element of the score queue. The score is a
    weighted sum of the elements in the queue.
    :param peer: the peer instance of the node that does the calculation.
    :return: None. The score is recorded in neighbor.score
    """
    for neighbor in peer.peer_neighbor_mapping.values():
        neighbor.score = sum(
            a * b for a, b in zip(neighbor.share_contribution, discount)
        )


def remove_lazy_neighbors(
    lazy_contribution: float, lazy_length: int, peer: "Peer"
) -> List["Peer"]:
    """
    This is a candidate design for neighborhood refreshment.
    The choice is: delete a neighbor if it has been lazy for a long time.
    If a neighbor's score is under lazy_contribution, it is "lazy" in this round;
    If a neighbor has been lazy for lazy_length batches, it is permanently lazy and gets
    kicked off.
    :param lazy_contribution: see explanation above.
    :param lazy_length: see explanation above.
    :param peer: the peer instance to be executed
    :return: the peer instances of the neighbors to be removed.
    """
    lazy_neighbor_list: List["Peer"] = []

    for neighboring_peer in list(peer.peer_neighbor_mapping):
        neighbor: "Neighbor" = peer.peer_neighbor_mapping[neighboring_peer]
        # update laziness
        if neighbor.share_contribution[-1] <= lazy_contribution:
            neighbor.lazy_round += 1
        else:
            neighbor.lazy_round = 0
        # delete neighbor if necessary
        if neighbor.lazy_round >= lazy_length:
            lazy_neighbor_list.append(neighboring_peer)
    return lazy_neighbor_list


def tit_for_tat(
    baby_ending: int,
    mutual: int,
    optimistic: int,
    time_now: int,
    peer: "Peer",
    time_start: int,
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
    :param time_start: the peer's starting time. Normally it is peer's birth time; a special
    case is for initial peers in the simulator, their birth times span over [0, birth_time_span),
    but we will use birth_time_span - 1 as their starting time for judgment on whether they are baby
    peers or not.
    :return: set of peer instances of the nodes selected as beneficiaries.
    """

    selected_peer_set: Set["Peer"] = set()
    if time_now - time_start <= baby_ending:
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


def after_previous(peer: "Peer", time_now: int) -> bool:
    """
    This implements engine.should_a_peer_start_a_new_loop() in such a way that a peer's new loop
    will begin immediately after the old loop finishes.
    :param peer: the peer to decide the loop
    :param time_now: Mesh system time
    :return: True or False
    """

    # Our implementation simply checks if time_now is in peer.verification_completion_time. If
    # yes, it means some on-chain verification has completed so the previous loop is ending.
    # Such an implementation implicitly requires that judgment on should_start_a_new_loop needs
    # to come before processing the verified orders and removing them from the
    # peer.verification_completion_time dictionary.

    return time_now in peer.verification_completion_time


def fixed_interval(peer: "Peer", time_now: int, interval: int) -> bool:
    """
    This implements engine.should_a_peer_start_a_new_loop() in such a way that a peer's new loop
    will begin after "interval" rounds of time slots, counting from the starting time of the
    previous loop.
    :param peer:
    :param time_now: Mesh system time.
    :param interval: time rounds for a new loop to begin
    :return: True or False
    """
    return (time_now - peer.previous_loop_starting_time) % interval == 0


def hybrid(peer: "Peer", time_now: int, min_time: int, max_time: int):
    """
    This implements engine.should_a_peer_start_a_new_loop() in such a way that a peer's new loop
    will begin immediately after the previous loop ends if the number of time slots that have
    passed is within [min_time, max_time], or it will start after min_time if the previous loop
    has ended, or it will start after max_time if the previous loop is still in processing.
    """

    raise NotImplementedError("To be implemented.")





