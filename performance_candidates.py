"""
This module contains possible implementations for performance measurement functions.
"""

import statistics
from typing import TYPE_CHECKING, Set, List, Optional
from data_types import SpreadingRatio


if TYPE_CHECKING:
    from message import Order
    from node import Peer


def order_spreading_ratio_stat(
    cur_time: int,
    order_set: Set["Order"],
    peer_set: Set["Peer"],
    max_age_to_track: int,
    statistical_window: int,
) -> SpreadingRatio:
    """
    This method calculates the order spreading ratio statistics, arranged by statistical windows.
    :param cur_time: current time
    :param order_set: set of orders to evaluate
    :param peer_set: set of peers to evaluate
    :param max_age_to_track: the maximal age of orders that we consider in the statistics
    :param statistical_window: we divide the orders into age intervals
    [n * statistical_interval, (n+1)* statistical_interval), n = 0, 1, ... ,
    and all orders that falls into an interval are all in this window.
    :return: a list of order spreading ratios, corresponding to each statistical window.
    the index being the i-th statistical window, and each value being the spreading ratio of
    orders of that window. If all orders of a window are all invalid, then value for that entry
    is 'None'.
    The spreading ratio of an order, is defined as the number of peers holding this order,
    over the total number of peers in the peer set.
    The spreading ratio of a statistical window, is the average spreading ratio of all orders in
    this window.
    """

    if cur_time < 0 or max_age_to_track < 0 or statistical_window <= 0:
        raise ValueError("There is some invalid negative input value.")

    num_active_peers: int = len(peer_set)
    order_spreading_record: List[List[float]] = [
        [] for _ in range(int((max_age_to_track - 1) / statistical_window) + 1)
    ]

    for order in order_set:
        num_peers_holding_order: int = len(
            list(item for item in order.holders if item in peer_set)
        )
        ratio: float = num_peers_holding_order / num_active_peers
        age: int = cur_time - order.birth_time
        if age < max_age_to_track:
            order_spreading_record[int(age / statistical_window)].append(ratio)

    order_spreading_ratio: SpreadingRatio = [
        0.0 for _ in range(len(order_spreading_record))
    ]
    for idx, sublist in enumerate(order_spreading_record):
        if sublist:
            order_spreading_ratio[idx] = statistics.mean(sublist)
        else:
            order_spreading_ratio[idx] = None
    return order_spreading_ratio


def order_num_stat_on_age(
    cur_time: int,
    max_age_to_track: int,
    statistical_window: int,
    order_set: Set["Order"],
) -> List[int]:
    """
    This is a helper function. It calculates the number of orders in each window.
    :param cur_time: same as above function.
    :param max_age_to_track: same as above function.
    :param statistical_window: same as above function.
    :param order_set: same as above function.
    :return: a list, each element being the number of orders whose age falls into
    [k * statistical_window, (k+1) * statistical_window).
    """

    if cur_time < 0 or max_age_to_track < 0 or statistical_window <= 0:
        raise ValueError("There is some invalid negative input value.")

    num_orders_in_age_range: List[int] = [0] * int(
        ((max_age_to_track - 1) / statistical_window) + 1
    )
    for order in order_set:
        age: int = cur_time - order.birth_time
        if age < max_age_to_track:
            bin_idx: int = int(age / statistical_window)
            num_orders_in_age_range[bin_idx] += 1
    return num_orders_in_age_range


def peer_order_stat_on_window(
    peer: "Peer",
    cur_time: int,
    max_age_to_track: int,
    statistical_window: int,
    order_set: Set["Order"],
) -> List[int]:
    """
    This is a helper function. It returns the aggregated number of orders in the set order_set,
    that falls into each statistical window, that a particular peer observes.
    :param peer: the peer instance of the node in observation.
    :param cur_time: same as above function.
    :param max_age_to_track: same as above function.
    :param statistical_window: same as above function.
    :param order_set: same as above function.
    :return: a list, each element being the number of orders observed by this peer that fall into
    the corresponding statistical window.
    """

    if cur_time < 0 or max_age_to_track < 0 or statistical_window <= 0:
        raise ValueError("There is some invalid negative input value.")

    num_orders_this_peer_stores: List[int] = [0] * int(
        ((max_age_to_track - 1) / statistical_window) + 1
    )

    for order in peer.order_orderinfo_mapping:
        age: int = cur_time - order.birth_time
        if age < max_age_to_track and order in order_set:
            bin_index: int = int(age / statistical_window)
            num_orders_this_peer_stores[bin_index] += 1

    return num_orders_this_peer_stores


def single_peer_order_receipt_ratio(
    cur_time: int,
    peer: "Peer",
    max_age_to_track: int,
    statistical_window: int,
    order_set: Set["Order"],
) -> SpreadingRatio:
    """
    This is a helper function. It calculates the ratios of orders that a peer receives, over the
    set of orders given to this function that fall into this window.
    If there is no order in this window, the value for this entry is None.
    :param cur_time: same as above function.
    :param peer: same as above function.
    :param max_age_to_track: same as above function.
    :param statistical_window: same as above function.
    :param order_set: same as above function.
    :return: a list, each element being the ratio of orders that this peer receives over all
    orders in order_set, for this statistical window. If there's no order in that range,
    the value is set as None.
    """

    def try_division(numerator: int, denominator: int) -> Optional[float]:
        try:
            result: float = numerator / denominator
            return result
        except ZeroDivisionError:
            return None

    # no need to do input argument check since order_num_stat_on_age() and
    # peer_order_stat_on_window() will do exactly the same check

    order_stat_based_on_age: List[int] = order_num_stat_on_age(
        cur_time=cur_time,
        max_age_to_track=max_age_to_track,
        statistical_window=statistical_window,
        order_set=order_set,
    )
    num_orders_this_peer_stores: List[int] = peer_order_stat_on_window(
        peer=peer,
        cur_time=cur_time,
        max_age_to_track=max_age_to_track,
        statistical_window=statistical_window,
        order_set=order_set,
    )
    peer_observation_ratio: SpreadingRatio = list(
        map(try_division, num_orders_this_peer_stores, order_stat_based_on_age)
    )

    return peer_observation_ratio


def single_peer_satisfaction_neutral(
    cur_time: int,
    peer: "Peer",
    max_age_to_track: int,
    statistical_window: int,
    order_set: Set["Order"],
) -> float:
    """
    This function calculates a peer's satisfaction based on his observation ratios.
    The neutral implementation is taking average of each observation ratio
    (neutral to every order), or return None of every element is None.
    :param cur_time: same as above function.
    :param peer: same as above function.
    :param max_age_to_track: same as above function.
    :param statistical_window: same as above function.
    :param order_set: same as above function.
    :return: A single value for this peer's satisfaction, or None if it did not receive anything.
    """

    # no need to do input argument check since single_peer_order_receipt_ratio() will do exactly
    # the same check

    peer_observation_ratio: SpreadingRatio = single_peer_order_receipt_ratio(
        cur_time=cur_time,
        peer=peer,
        max_age_to_track=max_age_to_track,
        statistical_window=statistical_window,
        order_set=order_set,
    )

    try:
        return statistics.mean(
            item for item in peer_observation_ratio if item is not None
        )
    except statistics.StatisticsError:
        # There is no order in the system. Normally the code should never reach here.
        raise RuntimeError(
            "Unable to judge a single peer satisfaction since there are no orders "
            "in the system for now."
        )


def fairness_dummy(_peer_set: Set["Peer"], _order_set: Set["Order"]) -> float:
    """
    This function calculates the fairness index for all peers. Right now, it is not implemented.
    :param _peer_set: set of peers. Not useful for now.
    :param _order_set: set of orders. Not useful for now.
    :return: 0.
    """
    return 0.0
