"""
This module contains unit tests of calculate_density().
"""


from typing import List, Tuple
import pytest
from data_processing import calculate_density
from data_types import InvalidInputError
from .__init__ import SATISFACTORY_LIST

# test normal cases

CASES_CALCULATE_DENSITY: List[Tuple[List[List[float]], float, List[float]]] = [
    # satisfactory_list, division_unit, result
    (
        [
            SATISFACTORY_LIST[0],
            SATISFACTORY_LIST[1],
            SATISFACTORY_LIST[2],
            SATISFACTORY_LIST[3],
        ],
        0.1,
        [0.1, 0.1, 0.2, 0, 0.1, 0, 0.1, 0, 0.2, 0.1, 0.1],
    ),
    ([SATISFACTORY_LIST[0], SATISFACTORY_LIST[1]], 0.5, [4 / 9, 4 / 9, 1 / 9]),
]


@pytest.mark.parametrize(
    "satisfactory_list, division_unit, expected_output", CASES_CALCULATE_DENSITY
)
def test_calculate_density__normal(
    satisfactory_list: List[List[float]],
    division_unit: float,
    expected_output: List[float],
) -> None:
    """
    This function tests calculate_density() with normal inputs.
    :param satisfactory_list: first input in calculate_density()
    :param division_unit: second input in calculate_density()
    :param expected_output: expected output.
    :return: None
    """
    actual_output: List[float] = calculate_density(satisfactory_list, division_unit)
    assert actual_output == pytest.approx(expected_output)


# test exceptions


def test_calculate_density__no_input() -> None:
    """
    This function tests calculate_density() with empty input.
    :return: None
    """
    with pytest.raises(InvalidInputError):
        calculate_density([], 0.1)


def test_calculate_density__no_value() -> None:
    """
    This function tests calculate_density() with non-empty input, but every list in the input is
    empty.
    :return: None
    """
    with pytest.raises(ValueError, match="There is no data in any input lists."):
        calculate_density([[], []], 0.1)


def test_calculate_density__out_of_range() -> None:
    """
    This function tests calculate_density() with number out of range.
    :return: None
    """
    with pytest.raises(ValueError, match="Some input data is out of range."):
        calculate_density([SATISFACTORY_LIST[4]], 0.1)


def test_calculate_density__invalid_division_unit() -> None:
    """
    This function tests calculate_density() with invalid division unit.
    :return: None
    """
    with pytest.raises(ValueError, match="Invalid division unit."):
        calculate_density([SATISFACTORY_LIST[0]], 2)
