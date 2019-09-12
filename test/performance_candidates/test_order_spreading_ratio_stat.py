"""
This module contains unit tests of order_spreading_ratio_stat().
"""

import copy
from typing import List, NamedTuple, Tuple
import pytest
from node import Peer
from message import Order
from scenario import Scenario
from engine import Engine
from data_types import SpreadingRatio
import performance_candidates
from ..__init__ import (
    SCENARIO_SAMPLE,
    ENGINE_SAMPLE,
    create_test_orders,
    create_test_peers,
)


def arrange_for_test(
    scenario: Scenario,
    engine: Engine,
    num_peer: int,
    num_order: int,
    order_birth_time_list: List[int],
    order_spreading_sheet: List[List[int]],
) -> Tuple[List[Order], List[Peer]]:
    """
    This is a helper function for arrangement for test functions. It creates a set of orders and
    a set of peers, sets up birth times for the orders, and propagates them to the peers.
    :param scenario: Scenario instance.
    :param engine: Engine instance.
    :param num_peer: number of peers to create
    :param num_order: number of orders to create
    :param order_birth_time_list: list of orders' birth times
    :param order_spreading_sheet: list of list, each sublist corresponds to a certain order in
    place, and contains the indices of the peers that has the corresponding order.
    :return: list of orders, list of peers.
    """

    # Prepare peers and orders.
    peer_list: List[Peer] = create_test_peers(scenario, engine, num_peer)
    order_list: List[Order] = create_test_orders(scenario, num_order)

    # Setup birth time and spread orders to peers.
    for i in range(num_order):
        order_list[i].birth_time = order_birth_time_list[i]
        for peer_index in order_spreading_sheet[i]:
            peer_list[peer_index].receive_order_external(order_list[i])
            peer_list[peer_index].store_orders()  # now order.holder should include peer

    return order_list, peer_list


class CaseType(NamedTuple):
    """
    Data type for test cases in this module.
    """

    scenario: Scenario
    engine: Engine
    num_order: int
    num_peer: int
    # List, each element corresponding to a list of peer
    order_spreading_sheet: List[List[int]]
    # indices that stores this order
    order_birth_time_list: List[
        int
    ]  # List, each element corresponding to a list of peer
    max_age: int  # max_age_to_track for order_num_stat_on_age()
    statistical_window: int  # statistical_window for order_num_stat_on_age()
    expected_result: SpreadingRatio  # expected output from order_spreading_ratio_stat()


# Case 1 is a simple one. There is only one order and one peer. The age of the order is 1 (less than
# the maximal track age), and the age track range is evenly divided into two sub-intervals:
# [0, 49], and [50, 99]. Expected output is [1, None] since the only order in [0, 49] is spread
# to all peers (in fact, only one peer) and there's no order in the other range [50, 99].

CASE_1 = CaseType(
    scenario=SCENARIO_SAMPLE,
    engine=ENGINE_SAMPLE,
    num_order=1,
    num_peer=1,
    order_spreading_sheet=[[0]],
    order_birth_time_list=[99],
    max_age=100,
    statistical_window=50,
    expected_result=[1, None],
)

# Case 2 is very similar to case 1, only exception is the age track interval changes from [0,
# 99] to [0, 100] so the division becomes three sub-intervals: [0, 49], [50, 99], [100].

CASE_2 = CaseType(
    scenario=SCENARIO_SAMPLE,
    engine=ENGINE_SAMPLE,
    num_order=1,
    num_peer=1,
    order_spreading_sheet=[[0]],
    order_birth_time_list=[99],
    max_age=101,
    statistical_window=50,
    expected_result=[1, None, None],
)

# Case 3 is a generalized one.

CASE_3 = CaseType(
    scenario=SCENARIO_SAMPLE,
    engine=ENGINE_SAMPLE,
    num_order=10,
    num_peer=10,
    order_spreading_sheet=[
        [0, 1, 2],
        [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
        [3, 5, 8, 9],
        [3, 5, 8, 9],
        [1],
        [],
        [6, 1],
        [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
        [0, 1, 2, 3, 4, 5, 6, 7, 8],
        [],
    ],
    # age:              100, 98, 88, 86, 45, 45, 40, 30, 1, 0
    order_birth_time_list=[0, 2, 12, 14, 55, 55, 60, 70, 99, 100],
    max_age=100,
    statistical_window=10,
    expected_result=[0.45, None, None, 1.0, 0.1, None, None, None, 0.4, 1.0],
)


@pytest.mark.parametrize(
    "scenario, engine, num_order, num_peer, order_spreading_sheet, order_birth_time_list, "
    "max_age, statistical_window, expected_result",
    [CASE_1, CASE_2, CASE_3],
)
def test_order_spreading__normal(
    scenario: Scenario,
    engine: Engine,
    num_order: int,
    num_peer: int,
    order_spreading_sheet: List[List[int]],
    order_birth_time_list: List[int],
    max_age: int,
    statistical_window: int,
    expected_result: SpreadingRatio,
) -> None:
    """
    This tests normal cases.
    """

    # Arrange.
    order_list, peer_list = arrange_for_test(
        scenario=scenario,
        engine=engine,
        num_peer=num_peer,
        num_order=num_order,
        order_birth_time_list=order_birth_time_list,
        order_spreading_sheet=order_spreading_sheet,
    )

    # Act.
    order_spreading_result: SpreadingRatio = performance_candidates.order_spreading_ratio_stat(
        cur_time=100,
        order_set=set(order_list),
        peer_set=set(peer_list),
        max_age_to_track=max_age,
        statistical_window=statistical_window,
    )

    # Assert
    assert len(order_spreading_result) == len(expected_result)
    length = len(order_spreading_result)
    for idx in range(length):
        try:
            assert order_spreading_result[idx] == pytest.approx(expected_result[idx])
        except TypeError:  # at least one is None
            assert order_spreading_result[idx] == expected_result[idx]


# Case 4 is similar to Case 3 except that we let the age of one order be negative.

CASE_4 = copy.deepcopy(CASE_3)
CASE_4.order_birth_time_list[-1] = 101


@pytest.mark.parametrize(
    "scenario, engine, num_order, num_peer, order_spreading_sheet, order_birth_time_list, "
    "max_age, statistical_window, _expected_result",
    [CASE_4],
)
def test_order_spreading__negative_age(
    scenario: Scenario,
    engine: Engine,
    num_order: int,
    num_peer: int,
    order_spreading_sheet: List[List[int]],
    order_birth_time_list: List[int],
    max_age: int,
    statistical_window: int,
    _expected_result: SpreadingRatio,
) -> None:
    """
    This tests negative order age.
    """

    # Arrange.
    order_list, peer_list = arrange_for_test(
        scenario,
        engine,
        num_peer,
        num_order,
        order_birth_time_list,
        order_spreading_sheet,
    )

    # Act and Assert
    with pytest.raises(ValueError, match="Order age should not be negative."):
        performance_candidates.order_spreading_ratio_stat(
            cur_time=100,
            order_set=set(order_list),
            peer_set=set(peer_list),
            max_age_to_track=max_age,
            statistical_window=statistical_window,
        )
