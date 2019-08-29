"""
This module contains test functions for peer_order_stat_on_window()
"""

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


CASE_1 = CaseType(
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


@pytest.mark.parametrize(
    "scenario, engine, num_order, birth_time_list, max_age, window, order_for_stat_idx_list, "
    "extra_order_num, expected_output",
    [CASE_1],
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
