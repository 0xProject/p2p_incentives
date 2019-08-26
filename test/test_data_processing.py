"""
This module contains test functions to all functions in data_processing module
"""

import pytest
from data_processing import find_best_worst_lists, average_lists, calculate_density
from data_types import BestAndWorstLists, InvalidInputError


#  constructing input data

RATIO_1 = [0.1, 0.2, 0.3, 0.4]
RATIO_2 = [0.1, 0.2, 0.3, 0.5]
RATIO_3 = [0.3, 0.5, 0.8, 0.9]
RATIO_4 = [None, None, None, None]
RATIO_5 = [0.1, 0.2, None, 0.6]
RATIO_6 = [0.1, 0.1, 1.0, None]
RATIO_7 = [None, 0.3, 0.5, 1.0]
RATIO_8 = [0.3, 0.5, 0.8, None]
RATIO_9 = [0.3, 0.5, 0.7, None]
RATIO_10 = [0.3, 0.5, None, None]
RATIO_11 = [0.2, 0.6, None, None]
RATIO_12 = [1.0, 0.1, None, None]
RATIO_13 = [None, None, None, None]
RATIO_14 = [None, None, None, None]
RATIO_15 = [0.1, 0.4, 0.9]

SATISFACTORY_1 = [0.88, 0.25, 0.67, 0.83]
SATISFACTORY_2 = [0.99, 0.13, 0.22, 0.01, 1.00]
SATISFACTORY_3 = []
SATISFACTORY_4 = [0.45]
SATISFACTORY_5 = [2]


# test find_best_worst_lists()

# test normal cases

CASES_BEST_WORST_LISTS = [
    # tuples: (input, output)
    ([RATIO_1, RATIO_2, RATIO_3], BestAndWorstLists(best=RATIO_3, worst=RATIO_1)),
    (
        [RATIO_1, RATIO_2, RATIO_3, RATIO_4],
        BestAndWorstLists(best=RATIO_3, worst=RATIO_1),
    ),
    ([RATIO_4, RATIO_5, RATIO_6], BestAndWorstLists(best=RATIO_5, worst=RATIO_5)),
    ([RATIO_5, RATIO_6, RATIO_7], BestAndWorstLists(best=RATIO_7, worst=RATIO_5)),
    ([RATIO_6, RATIO_8, RATIO_9], BestAndWorstLists(best=RATIO_6, worst=RATIO_9)),
    (
        [RATIO_4, RATIO_10, RATIO_11, RATIO_12],
        BestAndWorstLists(best=RATIO_11, worst=RATIO_12),
    ),
    (
        [
            RATIO_1,
            RATIO_2,
            RATIO_3,
            RATIO_4,
            RATIO_5,
            RATIO_6,
            RATIO_7,
            RATIO_8,
            RATIO_9,
            RATIO_10,
            RATIO_11,
        ],
        BestAndWorstLists(best=RATIO_7, worst=RATIO_1),
    ),
]


@pytest.mark.parametrize("ratio_list, expected_output", CASES_BEST_WORST_LISTS)
def test_find_best_worst_lists(ratio_list, expected_output):
    """
    This function tests find_best_worst_lists in normal cases
    :param ratio_list: list of SpreadingRatio instances
    :param expected_output: an instance of BestAndWorstLists
    :return: None
    """
    actual_output = find_best_worst_lists(ratio_list)
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


def test_find_best_worst_lists__all_none():
    """
    This function tests find_best_worst_lists when every element is None.
    :return: None
    """
    with pytest.raises(ValueError, match="All entries are None."):
        find_best_worst_lists([RATIO_4, RATIO_13, RATIO_14])


def test_find_best_worst_lists__empty_input():
    """
    This function tests find_best_worst_lists when the input is empty.
    :return: None
    """
    with pytest.raises(InvalidInputError):
        find_best_worst_lists([])


def test_find_best_worst_lists__different_length():
    """
    This function tests find_best_worst_lists when the input length varies.
    :return: None
    """
    with pytest.raises(ValueError, match="Input lists are of different length."):
        find_best_worst_lists([RATIO_1, RATIO_2, RATIO_15])


# test average_lists()

# test normal cases

CASES_AVERAGE_LISTS = [
    # tuple: (input, output)
    ([RATIO_1, RATIO_2, RATIO_3], [0.5 / 3, 0.3, 1.4 / 3, 0.6]),
    ([RATIO_1, RATIO_2, RATIO_4, RATIO_5], [0.1, 0.2, 0.3, 0.5]),
    ([RATIO_9, RATIO_10, RATIO_11], [0.8 / 3, 1.6 / 3, 0.7, 0.0]),
    ([RATIO_4, RATIO_13, RATIO_14], [0.0, 0.0, 0.0, 0.0]),
]


@pytest.mark.parametrize("ratio_list, expected_output", CASES_AVERAGE_LISTS)
def test_average_lists(ratio_list, expected_output):
    """
    This function tests normal cases for average_lists()
    :param ratio_list: List of SpreadingRatios
    :param expected_output: None
    :return: None
    """
    actual_output = average_lists(ratio_list)
    length = len(expected_output)
    assert len(actual_output) == length
    for idx in range(length):
        if isinstance(expected_output[idx], float):
            assert expected_output[idx] == pytest.approx(actual_output[idx])
        else:
            assert expected_output[idx] is actual_output[idx]


# test exceptions


def test_average_lists__no_input():
    """
    This function tests average_lists() when the input is empty.
    :return: None
    """
    with pytest.raises(InvalidInputError):
        average_lists([])


def test_average_lists__dif_length():
    """
    This function tests average_lists() when the input length varies.
    :return: None
    """
    with pytest.raises(ValueError, match="Input lists are of different length."):
        average_lists([RATIO_1, RATIO_2, RATIO_15])


# test calculate_density()

# test normal cases

CASES_CALCULATE_DENSITY = [
    # satisfactory_list, division_unit, result
    (
        [SATISFACTORY_1, SATISFACTORY_2, SATISFACTORY_3, SATISFACTORY_4],
        0.1,
        [0.1, 0.1, 0.2, 0, 0.1, 0, 0.1, 0, 0.2, 0.1, 0.1],
    ),
    ([SATISFACTORY_1, SATISFACTORY_2], 0.5, [4 / 9, 4 / 9, 1 / 9]),
]


@pytest.mark.parametrize(
    "satisfactory_list, division_unit, expected_output", CASES_CALCULATE_DENSITY
)
def test_calculate_density(satisfactory_list, division_unit, expected_output):
    """
    This function tests calculate_density() with normal inputs.
    :param satisfactory_list: first input in calculate_density()
    :param division_unit: second input in calculate_density()
    :param expected_output: expected output.
    :return: None
    """
    actual_output = calculate_density(satisfactory_list, division_unit)
    assert actual_output == pytest.approx(expected_output)


# test exceptions


def test_calculate_density__no_input():
    """
    This function tests calculate_density() with empty input.
    :return: None
    """
    with pytest.raises(InvalidInputError):
        calculate_density([], 0.1)


def test_calculate_density__no_value():
    """
    This function tests calculate_density() with non-empty input, but every list in the input is
    empty.
    :return: None
    """
    with pytest.raises(ValueError, match="There is no data in any input lists."):
        calculate_density([[], []], 0.1)


def test_calculate_density__out_of_range():
    """
    This function tests calculate_density() with number out of range.
    :return: None
    """
    with pytest.raises(ValueError, match="Some input data is out of range."):
        calculate_density([SATISFACTORY_5], 0.1)


def test_calculate_density__invalid_division_unit():
    """
    This function tests calculate_density() with invalid division unit.
    :return: None
    """
    with pytest.raises(ValueError, match="Invalid division unit."):
        calculate_density([SATISFACTORY_1], 2)
