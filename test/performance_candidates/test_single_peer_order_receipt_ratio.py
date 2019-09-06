"""
This module contains test functions for single_peer_order_receipt_ratio()
"""

import copy
from typing import List, NamedTuple, Set, Tuple
import pytest
from node import Peer
from message import Order
from scenario import Scenario
from engine import Engine
import performance_candidates
from data_types import SpreadingRatio
from .__init__ import (
    SCENARIO_SAMPLE,
    ENGINE_SAMPLE,
    create_test_orders,
    create_a_test_peer,
)


def arrange_for_test(
    scenario: Scenario,
    engine: Engine,
    num_order: int,
    order_birth_time_list: List[int],
    order_id_owned_by_peer: List[int],
    order_id_in_stat: List[int],
) -> Tuple[Peer, Set[Order]]:
    """
    This is a helper function for arrangement for test functions.
    It creates the peer, the full set of orders, stores orders according to
    order_id_owned_by_peer, puts the (sub)set of orders according to order_id_in_stat,
    and finally, returns the peer and the (sub)set of orders.
    :param scenario: Scenario instance
    :param engine: Engine instance
    :param num_order: total number of orders that will be created
    :param order_birth_time_list: birth time for these orders
    :param order_id_owned_by_peer: IDs of the orders that this peer owns
    :param order_id_in_stat: IDs of orders in statistics.
    :return: the peer instance, and the set of orders for statistics.
    """

    # create the peer
    peer: Peer = create_a_test_peer(scenario, engine)[0]

    # create the orders
    order_list: List[Order] = create_test_orders(scenario, num_order)
    for idx in range(num_order):
        order_list[idx].birth_time = order_birth_time_list[idx]

    # let the peer store corresponding orders
    for order_id in order_id_owned_by_peer:
        peer.receive_order_external(order_list[order_id])
    peer.store_orders()

    # prepare the set of orders for statistics
    order_set: Set[Order] = set(order_list[idx] for idx in order_id_in_stat)

    return peer, order_set


class CaseType(NamedTuple):
    """
    Data type for test cases in this module.
    """

    scenario: Scenario
    engine: Engine
    num_order: int
    order_birth_time_list: List[int]  # list of birth times of input orders
    order_id_owned_by_peer: List[int]  # list of ids of orders that this peer stores
    # list of ids of orders that will be in order_set for statistics
    order_id_in_stat: List[int]
    max_age: int  # max_age_to_track
    window: int  # statistical_window
    expected_result: SpreadingRatio  # expected receipt ratio


# Case 1 divides the range into equal length ones and include cases where orders are stored or not.

CASE_1 = CaseType(
    scenario=SCENARIO_SAMPLE,
    engine=ENGINE_SAMPLE,
    num_order=11,
    # age:                 0,   0,   1,  30, 40, 45, 45, 88, 94, 99, 100
    order_birth_time_list=[100, 100, 99, 70, 60, 55, 55, 12, 6, 1, 0],
    order_id_owned_by_peer=[0, 1, 3, 7, 9, 10],
    order_id_in_stat=[0, 2, 3, 4, 5, 6, 7, 8, 10],  # orders 1 and 9 are excluded
    max_age=100,
    window=10,
    # Order 0, 2 (1 excluded) in the first range [0, 9], one (0) stored, so 0.5 for the first range.
    # No order in range [10, 19], [20, 29] so None for them.
    # Order 3 in range [30, 39] and is stored, so 1 for this range
    # Orders 4, 5, 6 in range [40, 49] but none stored, so 0 for this range.
    # No order in range [50, 59], [60, 69], [70, 79], so all None
    # Order 7 in range [80, 89] and stored so 1 for this range.
    # Order 8 in range [90, 99] (9 excluded) but not stored so 0 for this range.
    # Order 10 too old, out of track.
    expected_result=[0.5, None, None, 1, 0, None, None, None, 1, 0],
)

# Case 2 is similar as case 1, only difference is we consider age up to 100 so the division of
# windows becomes of unequal length.

CASE_2 = CaseType(
    scenario=SCENARIO_SAMPLE,
    engine=ENGINE_SAMPLE,
    num_order=11,
    # age:                 0,   0,   1,  30, 40, 45, 45, 88, 94, 99, 100
    order_birth_time_list=[100, 100, 99, 70, 60, 55, 55, 12, 6, 1, 0],
    order_id_owned_by_peer=[0, 1, 3, 7, 9, 10],
    order_id_in_stat=[0, 2, 3, 4, 5, 6, 7, 8, 10],  # orders 1 and 9 are excluded
    max_age=101,
    window=10,
    # Order 0, 2 (1 excluded) in the first range [0, 9], one (0) stored, so 0.5 for the first range.
    # No order in range [10, 19], [20, 29] so None for them.
    # Order 3 in range [30, 39] and is stored, so 1 for this range
    # Orders 4, 5, 6 in range [40, 49] but none stored, so 0 for this range.
    # No order in range [50, 59], [60, 69], [70, 79], so all None
    # Order 7 in range [80, 89] and stored so 1 for this range.
    # Order 8 in range [90, 99] (9 excluded) but not stored so 0 for this range.
    # Order 10 in range [100, 100] and is stored, so 1 for this range.
    expected_result=[0.5, None, None, 1, 0, None, None, None, 1, 0, 1],
)


@pytest.mark.parametrize(
    "scenario, engine, num_order, order_birth_time_list, order_id_owned_by_peer, "
    "order_id_in_stat, max_age, window, expected_result",
    [CASE_1, CASE_2],
)
def test_single_peer_order_receipt_ratio__normal(
    scenario: Scenario,
    engine: Engine,
    num_order: int,
    order_birth_time_list: List[int],
    order_id_owned_by_peer: List[int],
    order_id_in_stat: List[int],
    max_age: int,
    window: int,
    expected_result: SpreadingRatio,
):
    """
    This function tests for normal cases for single_peer_order_receipt_ratio()
    """

    # Arrange
    peer, order_set = arrange_for_test(
        scenario=scenario,
        engine=engine,
        num_order=num_order,
        order_birth_time_list=order_birth_time_list,
        order_id_owned_by_peer=order_id_owned_by_peer,
        order_id_in_stat=order_id_in_stat,
    )

    # Act
    receipt_ratio = performance_candidates.single_peer_order_receipt_ratio(
        cur_time=100,
        peer=peer,
        max_age_to_track=max_age,
        statistical_window=window,
        order_set=order_set,
    )

    # Assert.
    assert len(receipt_ratio) == len(expected_result)
    length = len(receipt_ratio)
    for idx in range(length):
        try:
            assert receipt_ratio[idx] == pytest.approx(expected_result[idx])
        except TypeError:  # at least one is None
            assert receipt_ratio[idx] == expected_result[idx]


# Case 3 is also similar but there's one order with a negative age. Error expected.

CASE_3 = copy.deepcopy(CASE_2)
CASE_3.order_birth_time_list[-1] = 101


@pytest.mark.parametrize(
    "scenario, engine, num_order, order_birth_time_list, order_id_owned_by_peer, "
    "order_id_in_stat, max_age, window, _expected_result",
    [CASE_3],
)
def test_single_peer_order_receipt_ratio__negative_age(
    scenario: Scenario,
    engine: Engine,
    num_order: int,
    order_birth_time_list: List[int],
    order_id_owned_by_peer: List[int],
    order_id_in_stat: List[int],
    max_age: int,
    window: int,
    _expected_result: SpreadingRatio,
):
    """
    This function tests for negative order age.
    """

    # Arrange
    peer, order_set = arrange_for_test(
        scenario=scenario,
        engine=engine,
        num_order=num_order,
        order_birth_time_list=order_birth_time_list,
        order_id_owned_by_peer=order_id_owned_by_peer,
        order_id_in_stat=order_id_in_stat,
    )

    # Act and Assert.
    with pytest.raises(ValueError, match="Some order age is negative."):
        performance_candidates.single_peer_order_receipt_ratio(
            cur_time=100,
            peer=peer,
            max_age_to_track=max_age,
            statistical_window=window,
            order_set=order_set,
        )
