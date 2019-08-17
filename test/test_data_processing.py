"""
This module contains test functions to all functions in data_processing module
"""

import pytest
from data_processing import find_best_worst_lists
from data_types import BestAndWorstLists, InvalidInputError

# cases for function test_find_best_worst_lists()

ratio_1 = [0.1, 0.2, 0.3, 0.4]
ratio_2 = [0.1, 0.2, 0.3, 0.5]
ratio_3 = [0.3, 0.5, 0.8, 0.9]
ratio_4 = [None, None, None, None]
ratio_5 = [0.1, 0.2, None, 0.6]
ratio_6 = [0.1, 0.1, 1.0, None]
ratio_7 = [None, 0.3, 0.5, 1.0]
ratio_8 = [0.3, 0.5, 0.8, None]
ratio_9 = [0.3, 0.5, 0.7, None]
ratio_10 = [0.3, 0.5, None, None]
ratio_11 = [0.2, 0.6, None, None]
ratio_12 = [1.0, 0.1, None, None]

case_list = list()

ratios = [ratio_1, ratio_2, ratio_3]
result = BestAndWorstLists(best=ratio_3, worst=ratio_1)
case_list.append((ratios, result))

ratios = [ratio_1, ratio_2, ratio_3, ratio_4]
result = BestAndWorstLists(best=ratio_3, worst=ratio_1)
case_list.append((ratios, result))

ratios = [ratio_4, ratio_5, ratio_6]
result = BestAndWorstLists(best=ratio_5, worst=ratio_5)
case_list.append((ratios, result))

ratios = [ratio_5, ratio_6, ratio_7]
result = BestAndWorstLists(best=ratio_7, worst=ratio_5)
case_list.append((ratios, result))

ratios = [ratio_6, ratio_8, ratio_9]
result = BestAndWorstLists(best=ratio_6, worst=ratio_9)
case_list.append((ratios, result))

ratios = [ratio_4, ratio_10, ratio_11, ratio_12]
result = BestAndWorstLists(best=ratio_11, worst=ratio_12)
case_list.append((ratios, result))

ratios = [
    ratio_1,
    ratio_2,
    ratio_3,
    ratio_4,
    ratio_5,
    ratio_6,
    ratio_7,
    ratio_8,
    ratio_9,
    ratio_10,
    ratio_11,
]
result = BestAndWorstLists(best=ratio_7, worst=ratio_1)
case_list.append((ratios, result))


@pytest.mark.parametrize("ratio_list, expected_output", case_list)
def test_find_best_worst_lists(ratio_list, expected_output):
    actual_output = find_best_worst_lists(ratio_list)
    for idx in range(2):
        if isinstance(expected_output[idx], float):
            assert expected_output[idx] == pytest.approx(actual_output[idx])
        else:
            assert expected_output[idx] is actual_output[idx]


ratio_13 = [None, None, None, None]
ratio_14 = [None, None, None, None]
ratios = [ratio_4, ratio_13, ratio_14]


def test_find_best_worst_lists__all_none():
    with pytest.raises(ValueError):
        find_best_worst_lists(ratios)


def test_find_best_worst_lists__empty_input():
    with pytest.raises(InvalidInputError):
        find_best_worst_lists([])
