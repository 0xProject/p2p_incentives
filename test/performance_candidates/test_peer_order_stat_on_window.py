"""
This module contains test functions for peer_order_stat_on_window()
"""

import copy
from typing import List, NamedTuple
import pytest
from node import Peer
from message import Order
from scenario import Scenario
from engine import Engine
import performance_candidates
from .__init__ import (
    SCENARIO_SAMPLE,
    ENGINE_SAMPLE,
    create_test_orders,
    create_a_test_peer,
)


class CaseType(NamedTuple):
    """
    Data type for test cases in this module.
    """

    scenario: Scenario
    engine: Engine
    num_order: int
    order_birth_time_list: List[int]  # list of birth times of input orders
    max_age: int  # max_age_to_track
    window: int  # statistical_window
    order_for_stat_idx_list: List[
        int
    ]  # list of indices of the orders in the peer's storage,
    # that will be considered in statistics
    extra_order_num: int  # number of other orders that will also be considered in statistics.
    # This should have no impact to the test cases.
    expected_result: List[
        int
    ]  # expected output, list of number of orders that this peer has,
    # arranged in the sub-intervals according to order ages.


# Case 1 is a very simple one where there is only one order and it is within the range of
# statistics.

CASE_1 = CaseType(
    scenario=SCENARIO_SAMPLE,
    engine=ENGINE_SAMPLE,
    num_order=1,
    order_birth_time_list=[100],
    max_age=100,
    window=50,
    order_for_stat_idx_list=[0],
    extra_order_num=0,
    expected_result=[1, 0],
)

# Case 2 is the same as Case 1 except that an additional of 100 orders are added into statistics.
# There should be no impact at all.

CASE_2 = CaseType(
    scenario=SCENARIO_SAMPLE,
    engine=ENGINE_SAMPLE,
    num_order=1,
    order_birth_time_list=[100],
    max_age=100,
    window=50,
    order_for_stat_idx_list=[0],
    extra_order_num=100,
    expected_result=[1, 0],
)

# Case 3 is the same as Case 1, except that max_age = 101 so that the sub-intervals are divided
# as [0, 49], [50, 99], [100].

CASE_3 = CaseType(
    scenario=SCENARIO_SAMPLE,
    engine=ENGINE_SAMPLE,
    num_order=1,
    order_birth_time_list=[100],
    max_age=101,
    window=50,
    order_for_stat_idx_list=[0],
    extra_order_num=0,
    expected_result=[1, 0, 0],
)

# Case 4 is a generalized one.

CASE_4 = CaseType(
    scenario=SCENARIO_SAMPLE,
    engine=ENGINE_SAMPLE,
    num_order=10,
    # age:                   0, 1,  2,  28, 35, 70, 80, 90, 95, 100
    order_birth_time_list=[100, 99, 98, 72, 65, 30, 20, 10, 5, 0],
    max_age=100,  # order 9's age is beyond so it won't be counted.
    window=10,
    order_for_stat_idx_list=[0, 1, 3, 4, 5, 6, 7, 8, 9],  # order 2 is exempted.
    extra_order_num=100,
    expected_result=[2, 0, 1, 1, 0, 0, 0, 1, 1, 2],
)


@pytest.mark.parametrize(
    "scenario, engine, num_order, birth_time_list, max_age, window, order_for_stat_idx_list, "
    "extra_order_num, expected_output",
    [CASE_1, CASE_2, CASE_3, CASE_4],
)
def test_peer_order_stat_on_window__normal(
    scenario: Scenario,
    engine: Engine,
    num_order: int,
    birth_time_list: List[int],
    max_age: int,
    window: int,
    order_for_stat_idx_list: List[int],
    extra_order_num: int,
    expected_output: List[int],
):

    """
    This function tests peer_order_stat_on_window() in normal cases.
    """

    # Arrange.

    # Create the peer, clear the storage, and store the new orders.

    peer: Peer = create_a_test_peer(scenario, engine)[0]
    for order in list(peer.order_orderinfo_mapping):
        peer.del_order(order)

    # Prepare the order list for the peer, and store them.
    order_list: List[Order] = create_test_orders(scenario, num_order)
    for idx in range(num_order):
        order_list[idx].birth_time = birth_time_list[idx]
        peer.receive_order_external(order_list[idx])
    peer.store_orders()

    # Put a subset of these orders into the order-for-statistics list in peer_order_stat_on_window()
    order_for_stat_list: List[Order] = list()
    for idx in order_for_stat_idx_list:
        order_for_stat_list.append(order_list[idx])

    # Put extra orders into the order-for-statistics list
    # This is allowed by the function but this procedure should have no effect at all.
    extra_order_list: List[Order] = create_test_orders(scenario, extra_order_num)
    order_for_stat_list += extra_order_list

    # Act.
    order_stat: List[int] = performance_candidates.peer_order_stat_on_window(
        peer=peer,
        cur_time=100,
        max_age_to_track=max_age,
        statistical_window=window,
        order_set=set(order_for_stat_list),
    )

    # Assert
    assert order_stat == expected_output


# Case 5 is the same as case 4 except that one order's age is negative.

CASE_5 = copy.deepcopy(CASE_4)
CASE_5.order_birth_time_list[-1] = 101


@pytest.mark.parametrize(
    "scenario, engine, num_order, birth_time_list, max_age, window, order_for_stat_idx_list, "
    "extra_order_num, _expected_output",
    [CASE_5],
)
def test_peer_order_stat_on_window__negative_age(
    scenario: Scenario,
    engine: Engine,
    num_order: int,
    birth_time_list: List[int],
    max_age: int,
    window: int,
    order_for_stat_idx_list: List[int],
    extra_order_num: int,
    _expected_output: List[int],
):
    """
    This tests negative order age.
    """
    # Arrange.

    # Create the peer, clear the storage, and store the new orders.

    peer: Peer = create_a_test_peer(scenario, engine)[0]
    for order in list(peer.order_orderinfo_mapping):
        peer.del_order(order)

    # Prepare the order list for the peer, and store them.
    order_list: List[Order] = create_test_orders(scenario, num_order)
    for idx in range(num_order):
        order_list[idx].birth_time = birth_time_list[idx]
        peer.receive_order_external(order_list[idx])
    peer.store_orders()

    # Put a subset of these orders into the order-for-statistics list in peer_order_stat_on_window()
    order_for_stat_list: List[Order] = list()
    for idx in order_for_stat_idx_list:
        order_for_stat_list.append(order_list[idx])

    # Put extra orders into the order-for-statistics list
    # This is allowed by the function but this procedure should have no effect at all.
    extra_order_list: List[Order] = create_test_orders(scenario, extra_order_num)
    order_for_stat_list += extra_order_list

    # Act and Assert.
    with pytest.raises(ValueError, match="Order age should not be negative."):
        performance_candidates.peer_order_stat_on_window(
            peer=peer,
            cur_time=100,
            max_age_to_track=max_age,
            statistical_window=window,
            order_set=set(order_for_stat_list),
        )
