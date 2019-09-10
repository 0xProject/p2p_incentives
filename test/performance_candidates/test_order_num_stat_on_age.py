"""
This module contains test functions for order_num_stat_on_age()
"""

from typing import List, NamedTuple
import pytest
from message import Order
from scenario import Scenario
import performance_candidates
from .__init__ import SCENARIO_SAMPLE, create_test_orders


def arrange_for_test(
    scenario: Scenario, order_birth_time_list: List[int]
) -> List[Order]:
    """
    Helper function for arrangement for test functions. Create the list of orders and set up
    their birth time.
    :param scenario: Scenario instance.
    :param order_birth_time_list: List of order birth time.
    :return: List of orders.
    """

    num_order: int = len(order_birth_time_list)
    order_list: List[Order] = create_test_orders(scenario, num_order)

    for i in range(num_order):
        order_list[i].birth_time = order_birth_time_list[i]

    return order_list


class CaseType(NamedTuple):
    """
    Data type for test cases in this module.
    """

    scenario: Scenario
    order_birth_time_list: List[int]  # list of birth times of input orders
    max_age: int  # max_age_to_track for order_num_stat_on_age()
    statistical_window: int  # statistical_window for order_num_stat_on_age()
    expected_result: List[int]  # expected output from order_num_stat_on_age()


# Case 1 represents orders whose age span over 0~100 and the maximal age we consider is 99 (100
# excluded). Statistical window is 10 so the whole age interval is divided into 10 equal length
# sub-intervals. The expected output should be the number of orders whose age falls in [0,9],
# [10, 19], ... , [90, 99].

CASE_1 = CaseType(
    scenario=SCENARIO_SAMPLE,
    # age:                 88, 95, 94, 93, 22, 1, 0, 100, 75, 33, 1
    order_birth_time_list=[12, 5, 6, 7, 78, 99, 100, 0, 25, 67, 99],
    max_age=100,
    statistical_window=10,
    # calculated based on intervals [0, 9], [10, 19], ..., [90, 99] for ages.
    # Age 100 is excluded.
    expected_result=[3, 0, 1, 1, 0, 0, 0, 1, 1, 3],
)

# Case 2 is similar to Case 1 with the only exception for the maximal age in consideration being
# 100 (101 is excluded). Statistical window is 10 so the whole age interval is divided into 11
# non-equal length sub-intervals. The expected output should be the number of orders whose age
# falls in [0,9], [10, 19], ... , [90, 99], and [100].

CASE_2 = CaseType(
    scenario=SCENARIO_SAMPLE,
    # age:                 88, 95, 94, 93, 22, 1, 0, 100, 75, 33, 1
    order_birth_time_list=[12, 5, 6, 7, 78, 99, 100, 0, 25, 67, 99],
    max_age=101,
    statistical_window=10,
    # calculated based on intervals [0, 9], [10, 19], ..., [90, 99], [100, 100] for ages.
    expected_result=[3, 0, 1, 1, 0, 0, 0, 1, 1, 3, 1],
)


@pytest.mark.parametrize(
    "scenario, order_birth_time_list, max_age, statistical_window, expected_result",
    [CASE_1, CASE_2],
)
def test_order_num_stat_on_age__normal(
    scenario: Scenario,
    order_birth_time_list: List[int],
    max_age: int,
    statistical_window: int,
    expected_result: List[int],
) -> None:
    """
    Tests for normal case.
    Without loss of generality, we fix the cur_time as 100.
    """

    # Arrange.
    order_list: List[Order] = arrange_for_test(scenario, order_birth_time_list)

    # Act.
    order_num_stat: List[int] = performance_candidates.order_num_stat_on_age(
        cur_time=100,
        max_age_to_track=max_age,
        statistical_window=statistical_window,
        order_set=set(order_list),
    )

    # Assert.
    assert order_num_stat == expected_result


# Case 3 represents a wrong input with an order of negative age. Error expected when running the
# function.

CASE_3 = CaseType(
    scenario=SCENARIO_SAMPLE,
    # age:                 88, 95, 94, 93, 22, 1, 0, 100, 75, 33, -1
    order_birth_time_list=[12, 5, 6, 7, 78, 99, 100, 0, 25, 67, 101],
    max_age=101,
    statistical_window=10,
    # Error expected.
    expected_result=[],
)


@pytest.mark.parametrize(
    "scenario, order_birth_time_list, max_age, statistical_window, _expected_result",
    [CASE_3],
)
def test_order_num_stat_on_age__negative_age(
    scenario: Scenario,
    order_birth_time_list: List[int],
    max_age: int,
    statistical_window: int,
    _expected_result: List[int],
) -> None:
    """
    Test if an order's age is negative.
    """

    # Arrange.
    order_list = arrange_for_test(scenario, order_birth_time_list)

    # Act and Assert.
    with pytest.raises(ValueError, match="Some order age is negative."):
        performance_candidates.order_num_stat_on_age(
            cur_time=100,
            max_age_to_track=max_age,
            statistical_window=statistical_window,
            order_set=set(order_list),
        )
