"""
This module contains test functions for single_peer_satisfaction_neutral()
"""

import copy
from typing import List, NamedTuple
import pytest
from scenario import Scenario
from engine import Engine
import performance_candidates

from ..__init__ import SCENARIO_SAMPLE, ENGINE_SAMPLE

# The arrange helper function needed in this module is exactly the same as in
# test_single_peer_order_receipt_ratio.py so we import it.
# We will be using the same CASE_3 as in test_single_peer_order_receipt_ratio.py so we import it.
from .test_single_peer_order_receipt_ratio import arrange_for_test, CASE_3


class CaseType(NamedTuple):
    """
    Data type for test cases in this module. All elements are the same as CaseType in
    test_single_peer_order_receipt_ratio.py except the last one.
    """

    scenario: Scenario
    engine: Engine
    num_order: int
    order_birth_time_list: List[int]
    order_id_owned_by_peer: List[int]
    order_id_in_stat: List[int]
    max_age: int
    window: int
    expected_result: float  # expected satisfaction result.


# Case 1 is very similar to case 1 in test_single_peer_order_receipt_ratio.py.
# Expected result is the average of non-None elements in expected_result in case 1 in
# test_single_peer_order_receipt_ratio.py

CASE_1 = CaseType(
    scenario=SCENARIO_SAMPLE,
    engine=ENGINE_SAMPLE,
    num_order=11,
    order_birth_time_list=[100, 100, 99, 70, 60, 55, 55, 12, 6, 1, 0],
    order_id_owned_by_peer=[0, 1, 3, 7, 9, 10],
    order_id_in_stat=[0, 2, 3, 4, 5, 6, 7, 8, 10],
    max_age=100,
    window=10,
    expected_result=0.5,
)

# Case 2 is very similar to case 2 in test_single_peer_order_receipt_ratio.py.
# Expected result is the average of non-None elements in expected_result in case 2 in
# test_single_peer_order_receipt_ratio.py

CASE_2 = CaseType(
    scenario=SCENARIO_SAMPLE,
    engine=ENGINE_SAMPLE,
    num_order=11,
    order_birth_time_list=[100, 100, 99, 70, 60, 55, 55, 12, 6, 1, 0],
    order_id_owned_by_peer=[0, 1, 3, 7, 9, 10],
    order_id_in_stat=[0, 2, 3, 4, 5, 6, 7, 8, 10],
    max_age=101,
    window=10,
    expected_result=3.5 / 6,
)


@pytest.mark.parametrize(
    "scenario, engine, num_order, order_birth_time_list, order_id_owned_by_peer, "
    "order_id_in_stat, max_age, window, expected_result",
    [CASE_1, CASE_2],
)
def test_single_peer_satisfaction_neutral__normal(
    scenario: Scenario,
    engine: Engine,
    num_order: int,
    order_birth_time_list: List[
        int
    ],  # all order birth time will be normal in this test.
    order_id_owned_by_peer: List[int],
    order_id_in_stat: List[int],
    max_age: int,
    window: int,
    expected_result: float,
):
    """
    This function tests for normal cases for single_peer_order_receipt_ratio()
    """

    # Arrange
    peer, order_set = arrange_for_test(
        scenario,
        engine,
        num_order,
        order_birth_time_list,
        order_id_owned_by_peer,
        order_id_in_stat,
    )

    # Act
    satisfaction = performance_candidates.single_peer_satisfaction_neutral(
        cur_time=100,
        peer=peer,
        max_age_to_track=max_age,
        statistical_window=window,
        order_set=order_set,
    )

    # Assert.
    assert satisfaction == expected_result


# Case 3 is the same as case 3 in test_single_peer_order_receipt_ratio.py. Some error expected.


@pytest.mark.parametrize(
    "scenario, engine, num_order, order_birth_time_list_abnormal, order_id_owned_by_peer, "
    "order_id_in_stat, max_age, window, _expected_result",
    [CASE_3],
)
def test_single_peer_satisfaction_neutral__negative_age(
    scenario: Scenario,
    engine: Engine,
    num_order: int,
    order_birth_time_list_abnormal: List[
        int
    ],  # one birth time will be abnormal (> cur_time)
    order_id_owned_by_peer: List[int],
    order_id_in_stat: List[int],
    max_age: int,
    window: int,
    _expected_result: float,
):
    """
    This function tests for negative order age.
    """

    # Arrange
    peer, order_set = arrange_for_test(
        scenario,
        engine,
        num_order,
        order_birth_time_list_abnormal,
        order_id_owned_by_peer,
        order_id_in_stat,
    )

    # Act and Asset.
    with pytest.raises(ValueError, match="Some order age is negative."):
        performance_candidates.single_peer_satisfaction_neutral(
            cur_time=100,
            peer=peer,
            max_age_to_track=max_age,
            statistical_window=window,
            order_set=order_set,
        )


# Case 4 contains no order for statistics. Error expected.

CASE_4 = copy.deepcopy(CASE_2)
CASE_4.order_id_in_stat.clear()


@pytest.mark.parametrize(
    "scenario, engine, num_order, order_birth_time_list, order_id_owned_by_peer, "
    "order_id_in_stat_empty, max_age, window, _expected_result",
    [CASE_4],
)
def test_single_peer_satisfaction_neutral__no_order(
    scenario: Scenario,
    engine: Engine,
    num_order: int,
    order_birth_time_list: List[int],
    order_id_owned_by_peer: List[int],
    order_id_in_stat_empty: List[int],  # This will be empty
    max_age: int,
    window: int,
    _expected_result: float,
):
    """
    This function tests for negative order age.
    """

    # Arrange
    peer, order_set = arrange_for_test(
        scenario,
        engine,
        num_order,
        order_birth_time_list,
        order_id_owned_by_peer,
        order_id_in_stat_empty,
    )

    # Act and Asset.
    with pytest.raises(
        RuntimeError, match="Unable to judge a single peer satisfaction"
    ):
        performance_candidates.single_peer_satisfaction_neutral(
            cur_time=100,
            peer=peer,
            max_age_to_track=max_age,
            statistical_window=window,
            order_set=order_set,
        )
