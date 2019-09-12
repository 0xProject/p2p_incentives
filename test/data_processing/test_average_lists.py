"""
This module contains unit tests of average_lists()
"""

from typing import List, Tuple
import pytest
from data_processing import average_lists
from data_types import InvalidInputError, SpreadingRatio
from .__init__ import RATIO_LIST


# test normal cases

CASES_AVERAGE_LISTS: List[Tuple[List[SpreadingRatio], List[float]]] = [
    # tuple: (input, output)
    ([RATIO_LIST[0], RATIO_LIST[1], RATIO_LIST[2]], [0.5 / 3, 0.3, 1.4 / 3, 0.6]),
    (
        [RATIO_LIST[0], RATIO_LIST[1], RATIO_LIST[3], RATIO_LIST[4]],
        [0.1, 0.2, 0.3, 0.5],
    ),
    ([RATIO_LIST[8], RATIO_LIST[9], RATIO_LIST[10]], [0.8 / 3, 1.6 / 3, 0.7, 0.0]),
    ([RATIO_LIST[3], RATIO_LIST[12], RATIO_LIST[13]], [0.0, 0.0, 0.0, 0.0]),
]


@pytest.mark.parametrize("ratio_list, expected_output", CASES_AVERAGE_LISTS)
def test_average_lists__normal(
    ratio_list: List[SpreadingRatio], expected_output: List[float]
) -> None:
    """
    This function tests normal cases of average_lists()
    :param ratio_list: List of SpreadingRatios
    :param expected_output: List[float]
    :return: None
    """
    actual_output: List[float] = average_lists(ratio_list)
    length: int = len(expected_output)
    assert len(actual_output) == length
    for idx in range(length):
        assert expected_output[idx] == pytest.approx(actual_output[idx])


# test exceptions


def test_average_lists__no_input() -> None:
    """
    This function tests average_lists() when the input is empty.
    :return: None
    """
    with pytest.raises(InvalidInputError):
        average_lists([])


def test_average_lists__dif_length() -> None:
    """
    This function tests average_lists() when the input length varies.
    :return: None
    """
    with pytest.raises(ValueError, match="Input lists are of different length."):
        average_lists([RATIO_LIST[0], RATIO_LIST[1], RATIO_LIST[14]])
