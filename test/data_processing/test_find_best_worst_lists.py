"""
This module contains unit tests of find_best_worst_lists().
"""

from typing import List, Tuple
import pytest
from data_processing import find_best_worst_lists
from data_types import BestAndWorstLists, InvalidInputError, SpreadingRatio
from .__init__ import RATIO_LIST


# test normal cases

CASES_BEST_WORST_LISTS: List[Tuple[List[SpreadingRatio], BestAndWorstLists]] = [
    # tuples: (input, output)
    (
        [RATIO_LIST[0], RATIO_LIST[1], RATIO_LIST[2]],
        BestAndWorstLists(best=RATIO_LIST[2], worst=RATIO_LIST[0]),
    ),
    (
        [RATIO_LIST[0], RATIO_LIST[1], RATIO_LIST[2], RATIO_LIST[3]],
        BestAndWorstLists(best=RATIO_LIST[2], worst=RATIO_LIST[0]),
    ),
    (
        [RATIO_LIST[3], RATIO_LIST[4], RATIO_LIST[5]],
        BestAndWorstLists(best=RATIO_LIST[4], worst=RATIO_LIST[4]),
    ),
    (
        [RATIO_LIST[4], RATIO_LIST[5], RATIO_LIST[6]],
        BestAndWorstLists(best=RATIO_LIST[6], worst=RATIO_LIST[4]),
    ),
    (
        [RATIO_LIST[5], RATIO_LIST[7], RATIO_LIST[8]],
        BestAndWorstLists(best=RATIO_LIST[5], worst=RATIO_LIST[8]),
    ),
    (
        [RATIO_LIST[3], RATIO_LIST[9], RATIO_LIST[10], RATIO_LIST[11]],
        BestAndWorstLists(best=RATIO_LIST[10], worst=RATIO_LIST[11]),
    ),
    (
        [
            RATIO_LIST[0],
            RATIO_LIST[1],
            RATIO_LIST[2],
            RATIO_LIST[3],
            RATIO_LIST[4],
            RATIO_LIST[5],
            RATIO_LIST[6],
            RATIO_LIST[7],
            RATIO_LIST[8],
            RATIO_LIST[9],
            RATIO_LIST[10],
        ],
        BestAndWorstLists(best=RATIO_LIST[6], worst=RATIO_LIST[0]),
    ),
]


@pytest.mark.parametrize("ratio_list, expected_output", CASES_BEST_WORST_LISTS)
def test_find_best_worst_lists__normal(
    ratio_list: List[SpreadingRatio], expected_output: BestAndWorstLists
) -> None:
    """
    This function tests find_best_worst_lists in normal cases
    :param ratio_list: list of SpreadingRatio instances
    :param expected_output: an instance of BestAndWorstLists
    :return: None
    """
    actual_output: BestAndWorstLists = find_best_worst_lists(ratio_list)
    for idx in range(2):
        assert len(expected_output[idx]) == len(actual_output[idx])
        for value_idx in range(len(expected_output)):
            if isinstance(expected_output[idx][value_idx], float):
                assert actual_output[idx][value_idx] == pytest.approx(
                    expected_output[idx][value_idx]
                )
            else:  # this is a None
                assert expected_output[idx][value_idx] is actual_output[idx][value_idx]


# test exceptions


def test_find_best_worst_lists__all_none() -> None:
    """
    This function tests find_best_worst_lists when every element is None.
    :return: None
    """
    with pytest.raises(ValueError, match="All entries are None."):
        find_best_worst_lists([RATIO_LIST[3], RATIO_LIST[12], RATIO_LIST[13]])


def test_find_best_worst_lists__empty_input() -> None:
    """
    This function tests find_best_worst_lists when the input is empty.
    :return: None
    """
    with pytest.raises(InvalidInputError):
        find_best_worst_lists([])


def test_find_best_worst_lists__different_length() -> None:
    """
    This function tests find_best_worst_lists when the input length varies.
    :return: None
    """
    with pytest.raises(ValueError, match="Input lists are of different length."):
        find_best_worst_lists([RATIO_LIST[0], RATIO_LIST[1], RATIO_LIST[14]])
