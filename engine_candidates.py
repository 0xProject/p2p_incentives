"""
====================
Candidates of design choices
====================
"""
# This module contains all possible realizations of functions in the Engine class.

import random

# This is a candidate design for setting preference of a neighbor instance.
# The choice is: set the value as "preference" if preference is not None, or set it as None otherwise.


def setPreferencePassive(neighbor, peer, master, preference):
    neighbor.preference = preference


# This is a candidate design for setting a priority of an orderinfo instance.
# The choice is: set the value as "priority" if priority is not None, or set it as None otherwise.


def setPriorityPassive(orderinfo, order, master, priority):
    orderinfo.priority = priority


# This is a candidate design for storing orders.
# Note that there might be multiple orderinfo instances for a given order instance.
# The design needs to make sure to store at most one of such orderinfo instances.
# The choice is: store the first instance of orderinfo for every order.

# Let "order_a" and "order_b" be two order instances. Let "orderinfo_a1" and "orderinfo_a2"
# be two orderinfo instances which both refer to order_a. Let "orderinfo_b1" and "orderinfo_b2"
# be two orderinfo instances which both refer to order_b. Then peer.order_pending_orderinfo_mapping
# will look like:
# peer.order_pending_orderinfo_mapping =
# { order_a: [orderinfo_a1, orderinfo_a2],
#   order_b: [orderinfo_b1, orderinfo_b2] }.
# We will use "pending_orderinfolist_for_same_order"
# to refer to lists like [orderinfo_a1, orderinfo_a2] or [orderinfo_b1, orderinfo_b2].


def storeFirst(peer):
    for (
        pending_orderinfolist_for_same_order
    ) in peer.order_pending_orderinfo_mapping.values():
        pending_orderinfolist_for_same_order[
            0
        ].storage_decision = True  # first orderinfo is stored
        for orderinfo in pending_orderinfolist_for_same_order[
            1:
        ]:  # the rest (if any) are not stored
            orderinfo.storage_decision = False


# This is a candidate design for sharing orders.
# The choice is: share min(max_to_share, # of new_orders) of new orders,
# and share min(remaining_quota, [# of old peers] * old_prob) of old orders,
# where remaining_quota = max(0, max_to_share minus #_of_new_orders_selected).


def shareAllNewSelectedOld(max_to_share, old_prob, peer):

    new_order_set = peer.new_order_set
    old_order_set = set(peer.order_orderinfo_mapping) - peer.new_order_set
    selected_order_set = set()

    selected_order_set |= set(
        random.sample(new_order_set, min(max_to_share, len(new_order_set)))
    )

    remaining_share_size = max(0, max_to_share - len(new_order_set))
    probability_selection_size = round(len(old_order_set) * old_prob)
    selected_order_set |= set(
        random.sample(
            old_order_set,
            min(remaining_share_size, probability_selection_size),
        )
    )
    return selected_order_set


# This is a candidate design for calculating the scores of neighbors of a peer.
# The choice is: (1) calculate the current score by a weighted sum of all elements in the queue
# (2) update the queue by moving one step forward and delete the oldest element, and
# (3) delete a neighbor if it has been lazy for a long time.


def weightedSum(lazy_contri, lazy_length, discount, peer):

    # If a neighbor's score is under self.lazy_contri, it is "lazy" in this batch;
    # If a neighbor has been lazy for self.lazy_length batches,
    # it is permanently lazy and gets kicked off.
    # Discount is a list of weights weights for each element of the score queue.
    # Usually recent elements are of higher weights.

    for neighboring_peer in list(
        peer.peer_neighbor_mapping
    ):  # neighboring_peer is the peer instance for a neighbor

        neighbor = peer.peer_neighbor_mapping[
            neighboring_peer
        ]  # neighbor is the neighbor instance for a neighbor
        # update laziness
        if neighbor.share_contribution[-1] <= lazy_contri:
            neighbor.lazy_round += 1
        else:
            neighbor.lazy_round = 0
        # delete neighbor if necessary
        if neighbor.lazy_round >= lazy_length:
            peer.delNeighbor(neighboring_peer)
            continue

        neighbor.score = sum(
            a * b for a, b in zip(neighbor.share_contribution, discount)
        )


# This is a candidate design to select beneficiaries from neighbors.
# The choice is similar to tit-for-tat.
# If this is a new peer (age <= baby_ending) so it does not know its neighbors well,
# it shares to random neighbors (# = mutual + optimistic).
# Otherwise, it shares to (# = "mutual") highly-reputated neighbors, and
# (# = "optimistic") of other random neighbors.
# In the case fewer than (# = "mutual") neighbors have positive scores, only
# select the neithbors with positive scores as highly-reputated neighbors.
# The number of other random neighbors is still "optimistic"
# (i.e., the quota for beneficiaries is wasted in such a case).


def titForTat(baby_ending, mutual, optimistic, time_now, peer):

    selected_peer_set = set()
    if (
        time_now - peer.birthtime <= baby_ending
    ):  # This is a new peer. Random select neighbors.
        selected_peer_set |= set(
            random.sample(
                list(peer.peer_neighbor_mapping),
                min(len(peer.peer_neighbor_mapping), mutual + optimistic),
            )
        )
    else:  # This is an old peer
        # ranked_list_of_peers is a list of peer instances who are my neighbors
        # and they are ranked according to their scores that I calculate.
        ranked_list_of_peers = peer.rankNeighbors()
        mutual = min(mutual, len(ranked_list_of_peers))
        while (
            mutual > 0
            and peer.peer_neighbor_mapping[
                ranked_list_of_peers[mutual - 1]
            ].score
            == 0
        ):
            mutual -= 1

        highly_ranked_peers_list = ranked_list_of_peers[:mutual]
        lowly_ranked_peers_list = ranked_list_of_peers[mutual:]
        selected_peer_set |= set(highly_ranked_peers_list)
        selected_peer_set |= set(
            random.sample(
                lowly_ranked_peers_list,
                min(len(lowly_ranked_peers_list), optimistic),
            )
        )
    return selected_peer_set


# This is a candidate design for neighbor recommendation.
# The choice is to choose (# = target_number) elements from the base in a totally random manner.
# The current implementation does not take requester into consideration.


def randomRec(requester, base, target_number):
    if not base or not target_number:
        raise ValueError("Base set is empty or target number is zero.")

    # if the target number is larger than the set size, output the whole set.
    return set(random.sample(base, min(target_number, len(base))))
