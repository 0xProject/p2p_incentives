"""
=================================
Candidates of performance evaluation
=================================
"""

# This module contains possible implementations for performance measurement functions.

import statistics

# The following function returns the spreading ratios of orders, arranged by statistical windows.
# The return value is a list, the index being the i-th statistical window, and
# each value being the spreading ratio of orders of that window.

# Statistical window: We divide the orders into age intervals
# [n * statistical_interval, (n+1)* statistical_interval), n = 0, 1, ...,
# and all orders that falls into an interval are all in this window.

# The spreading ratio of an order, is defined as the # of peers holding this
# order, over the total # of peers in the peer set.
# The spreading ratio of a statistical window, is the average spreading ratio
# of all orders in this window.

# The maximal age of orders that we consider, is max_age_to_track.

# The return value is a list of order spreading ratios, corresponding to each statistical window.
# if all orders of a window are all invalid, then value for that entry is 'None'.


def orderSpreadingRatioStat(
    cur_time, order_set, peer_set, max_age_to_track, statistical_window
):

    num_active_peers = len(peer_set)
    order_spreading_ratio = [
        [] for _ in range(int((max_age_to_track - 1) / statistical_window) + 1)
    ]

    for order in order_set:
        num_peers_holding_order = len(
            list(item for item in order.holders if item in peer_set)
        )
        ratio = num_peers_holding_order / num_active_peers
        age = cur_time - order.birthtime
        if age < max_age_to_track:
            order_spreading_ratio[int(age / statistical_window)].append(ratio)

    for idx, sublist in enumerate(order_spreading_ratio):
        if sublist != []:
            order_spreading_ratio[idx] = statistics.mean(
                sublist
            )  # sum(item for item in sublist) / len(sublist)
        else:
            order_spreading_ratio[idx] = None
    return order_spreading_ratio


# The following function is a helper function. It returns a vector,
# each value being the # of orders whose age falls into
# [k * statistical_window, (k+1) * statistical_window).


def orderNumStatOnAge(
    cur_time, max_age_to_track, statistical_window, order_set
):

    num_orders_in_age_range = [0] * int(
        ((max_age_to_track - 1) / statistical_window) + 1
    )
    for order in order_set:
        age = cur_time - order.birthtime
        if age < max_age_to_track:
            bin_idx = int(age / statistical_window)
            num_orders_in_age_range[bin_idx] += 1
    return num_orders_in_age_range


# The following function is a helper function. It returns the aggregated number
# of orders in the set order_set, that falls into each statistical window, that a particular peer observes.


def peerInfoObservation(
    peer, cur_time, max_age_to_track, statistical_window, order_set
):

    num_orders_this_peer_stores = [0] * int(
        ((max_age_to_track - 1) / statistical_window) + 1
    )

    for order in peer.order_orderinfo_mapping:
        age = cur_time - order.birthtime
        if age < max_age_to_track and order in order_set:
            bin_num = int(age / statistical_window)
            num_orders_this_peer_stores[bin_num] += 1

    return num_orders_this_peer_stores


# The following function is a helper function. It returns a list of the ratios of orders that this peer
# receives, each ratio is calculated based on the total # of orders of this window.
# If there is no order in this window, the value for this entry is None.


def singlePeerInfoRatio(
    cur_time, peer, max_age_to_track, statistical_window, order_set
):
    def try_division(x, y):
        try:
            z = x / y
        except:
            z = None
        return z

    order_stat_based_on_age = orderNumStatOnAge(
        cur_time, max_age_to_track, statistical_window, order_set
    )

    num_orders_this_peer_stores = peerInfoObservation(
        peer, cur_time, max_age_to_track, statistical_window, order_set
    )

    peer_observation_ratio = list(
        map(try_division, num_orders_this_peer_stores, order_stat_based_on_age)
    )

    return peer_observation_ratio


# This function calculates a peer's satisfaction based on his info observation ratios
# The neutral implementation is taking average of each observation ratio
# (neutral to every order), or return None of every element is None.


def singlePeerSatisfactionNeutral(
    cur_time, peer, max_age_to_track, statistical_window, order_set
):

    peer_observation_ratio = singlePeerInfoRatio(
        cur_time, peer, max_age_to_track, statistical_window, order_set
    )

    try:
        return statistics.mean(
            item for item in peer_observation_ratio if item is not None
        )
    except:
        return None  # this peer does not have any orders


# This function calculates the fairness index for all peers
# Right now, it is not implemented.


def fairnessDummy(peer_set, order_set):
    return 0
