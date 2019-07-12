"""
This module contains data processing tools (e.g., finding the max, min, average, frequency...)
to work on performance evaluation results, and possibly for results of running the
simulator multiple times.
"""

import statistics
from typing import List, Iterator, Optional, Tuple


def find_best_worst_lists(sequence_of_lists: List[List[Optional[float]]])\
        -> Tuple[List[Optional[float]], List[Optional[float]]]:
    """
    This function finds the "best" and "worst" lists from a set of lists. See explanation below.
    :param sequence_of_lists: a sequence of equal-length lists.
    An element in the list is either a non-negative value or None.
    :return: the best and worst lists, selected from all lists in this sequence.

    The best/worst list is the one who's last entry is the largest/smallest among all lists given.
    If any entry is None, it is ignored (neither the best nor the worst).
    If the last entries of all lists are all None, then we look at the second last entry, etc.,
    up till the first entry. If all entries of all lists are None, raise an exception.
    For example, if list_1 = [0.1, 0.2, 0.3, None], list_2 = [0.29, 0.29, 0.29, None],
    then list_1 is the best and list_2 is the worst.
    For efficiency consideration, this function does not check validity of the argument (same
    length)
    since it should have been guaranteed in the function that calls it.
    """

    last_effective_idx: int = -1
    while last_effective_idx >= -len(sequence_of_lists[0]):
        if any(item[last_effective_idx] is not None for item in sequence_of_lists):
            break
        last_effective_idx -= 1

    if last_effective_idx == -len(sequence_of_lists[0]) - 1:
        raise ValueError('All entries are None. Invalid to compare.')

    it1: Iterator = iter((item for item in sequence_of_lists if item[last_effective_idx] is not
                          None))
    best_list = max(it1, key=lambda x: x[last_effective_idx])
    it2: Iterator = iter((item for item in sequence_of_lists if item[last_effective_idx] is not
                          None))
    worst_list = min(it2, key=lambda x: x[last_effective_idx])

    return best_list, worst_list


def average_lists(sequence_of_lists: List[List[Optional[float]]]) -> List[float]:
    """
    This function calculates the position-wise average of all values from all lists.
    :param sequence_of_lists: a sequence of equal-length lists. Each element in each list is
    either a value or None
    :return: a list of the same length. Each element in the output list is the average of the values
    in the corresponding place of all input lists, ignoring all None elements.
    If all elements in a place of all input lists are None, the output element in that place is 0.
    """

    average_list: List[float] = [0.0 for _ in range(len(sequence_of_lists[0]))]
    length_of_list: int = len(average_list)

    idx: int = 0
    while idx < length_of_list:
        processing_list: List[float] = []
        for any_list in sequence_of_lists:
            list_item = any_list[idx]
            if list_item is not None:
                processing_list.append(list_item)
        try:
            average_list[idx] = statistics.mean(processing_list)
        except statistics.StatisticsError:
            average_list[idx] = 0.0
        idx += 1

    return average_list


def calculate_density(sequence_of_lists: List[List[float]],
                      division_unit: float = 0.01) -> List[float]:
    """
    This function calculates the density of the values of all elements from all input lists.
    :param sequence_of_lists: a sequence of lists. Each element in each list is a real value over
    [0,1).
    :param division_unit: a real value < 1 to divide [0,1] into intervals [n * division_unit,
    (n+1) * division_unit).
    :return: density distribution of all values in all lists over the intervals specified above.
    In other words, one can imagine merging all lists into one long list as the input,
    and the result is the density of elements in that long list.
    """

    total_points: int = sum(len(single_list) for single_list in sequence_of_lists)

    if total_points == 0:
        raise ValueError('Invalid to calculate density for nothing.')

    largest_index: int = int(1/division_unit)
    density_list: List[float] = [0.0 for _ in range(largest_index + 1)]

    for single_list in sequence_of_lists:
        for value in single_list:
            density_list[int(value/division_unit)] += 1

    density_list = [value/total_points for value in density_list]

    return density_list
