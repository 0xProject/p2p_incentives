"""
This module contains data processing tools (e.g., finding the max, min, average, frequency...)
to work on performance evaluation results.
"""

import statistics
from typing import List, Iterator, Tuple
from data_types import SpreadingRatio


def find_best_worst_lists(
    sequence_of_lists: List[SpreadingRatio]
) -> Tuple[SpreadingRatio, SpreadingRatio]:
    """
    This function finds the "best" and "worst" lists from a set of lists. See explanation below.
    :param sequence_of_lists: a sequence of equal-length lists.
    An element in the list is of type SpreadingRatio, i.e., either a float or None.
    :return: the best and worst lists, selected from all lists in this sequence. We will explain
    what we refer to as "best" and "worst."

    Each element in the input list is of type SpreadingRatio. The data type SpreadingRatio
    is a list, with each element being either a float or None. For example, it may look like [
    0.1, 0.5, 0.7, 0.8], or [0.1, 0.5, None, 0.8], or [None, None, None, None].

    Let us explain a bit more on the physical meaning of this concept. In our simulator context,
    we divide orders into various intervals according to their ages. For example, we have 10, 20,
    15, and 5 orders whose ages are in ranges [0,5), [5, 10), [10, 15) and [15, 20),
    respectively. Each order's spreading ratio is defined as the # of peers who received this
    order, divided by the total number of peers in consideration. By taking the average of all
    individual order's spreading ratios within each range, we record this value in the
    corresponding venue of a list, and this list is the "average spreading ratio" of orders,
    with respect to their age range. However, if there is no order in a certain age range,
    we put a None in this list. SpreadingRatio is the data type to represent this list.

    This function takes a number of SpreadingRatio data as input (and each SpreadingRatio data is
    of the same length), and returns the best and worst of these data. The best/worst data is
    defined by comparing the last entry: the largest one is the best and the smallest one is the
    worst. For example:

    >>> spreading_ratio_1: SpreadingRatio = [0.1, 0.2, 0.3, 0.4]
    >>> spreading_ratio_2: SpreadingRatio = [0.1, 0.2, 0.3, 0.5]
    >>> find_best_worst_lists([spreading_ratio_1, spreading_ratio_2])
    ([0.1, 0.2, 0.3, 0.5], [0.1, 0.2, 0.3, 0.4])

    If for some SpreadingRatio data, the last element is None, then we don't include it in
    consideration. For example:

    >>> spreading_ratio_1: SpreadingRatio = [0.1, 0.2, 0.3, 0.4]
    >>> spreading_ratio_2: SpreadingRatio = [0.1, 0.2, 0.3, 0.5]
    >>> spreading_ratio_3: SpreadingRatio = [0.1, 0.2, 0.8, None]
    >>> find_best_worst_lists([spreading_ratio_1, spreading_ratio_2, spreading_ratio_3])
    ([0.1, 0.2, 0.3, 0.5], [0.1, 0.2, 0.3, 0.4])

    If for all SpreadingRatio data, the last element is None, then we compare the second last,
    third last, ..., up till the first element. For example:

    >>> spreading_ratio_1: SpreadingRatio = [0.1, 0.2, 0.3, None]
    >>> spreading_ratio_2: SpreadingRatio = [0.1, 0.2, 0.4, None]
    >>> spreading_ratio_3: SpreadingRatio = [0.1, 0.2, None, None]
    >>> find_best_worst_lists([spreading_ratio_1, spreading_ratio_2, spreading_ratio_3])
    ([0.1, 0.2, 0.4, None], [0.1, 0.2, 0.3, None])

    If for all SpreadingRatio data all elements are None, then raise an error with ValueError
    message.

    [Note 1]: Under our simulator context, the values in a SpreadingRatio list must be in [0,
    1]. However we preserve the generality of this function and we only check if they are floats
    or None, but we don't check if values are in range [0,1].

    [Note 2]: Currently this function does not check if all input SpreadingRatio data are of the
    same length. I will add this check in the next PR.
    This message should be deleted in the next PR.

    """

    last_effective_idx: int = -1
    while last_effective_idx >= -len(sequence_of_lists[0]):
        if any(item[last_effective_idx] is not None for item in sequence_of_lists):
            break
        last_effective_idx -= 1

    if last_effective_idx == -len(sequence_of_lists[0]) - 1:
        raise ValueError("All entries are None. Invalid to compare.")

    it1: Iterator[SpreadingRatio] = iter(
        (item for item in sequence_of_lists if item[last_effective_idx] is not None)
    )
    best_list: SpreadingRatio = max(it1, key=lambda x: x[last_effective_idx])
    it2: Iterator[SpreadingRatio] = iter(
        (item for item in sequence_of_lists if item[last_effective_idx] is not None)
    )
    worst_list: SpreadingRatio = min(it2, key=lambda x: x[last_effective_idx])

    return best_list, worst_list


def average_lists(sequence_of_lists: List[SpreadingRatio]) -> List[float]:
    """
    This function calculates the position-wise average of all values from all lists.
    :param sequence_of_lists: a list of equal-length SpreadingRatios. See explanation above.
    :return: a list of the same length as any SpreadingRatio in the input. Each element in the
    returning list is the average of the values in the corresponding place of all SpreadingRatio
    inputs, ignoring all None elements. When ignoring an element, we don't count its head into
    the denominator for the averaging calculation.

    For example,

    >>> spreading_ratio_1: SpreadingRatio = [0.1, 0.2, 0.3, None]
    >>> spreading_ratio_2: SpreadingRatio = [0.3, 0.2, None, 0.4]
    >>> average_lists([spreading_ratio_1, spreading_ratio_2])
    [0.2, 0.2, 0.3, 0.4]

    If all elements in a place of all SpreadingRatios are  None, the output element in that place
    is 0. For example:
    >>> spreading_ratio_1: SpreadingRatio = [0.1, 0.2, 0.3, None]
    >>> spreading_ratio_2: SpreadingRatio = [0.3, 0.2, None, None]
    >>> average_lists([spreading_ratio_1, spreading_ratio_2])
    [0.2, 0.2, 0.3, 0.0]

    [Note]: Equal length condition not checked in the function for now. Need to do it in the
    next PR.
    This message should be deleted in the next PR.
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


def calculate_density(
    sequence_of_lists: List[List[float]], division_unit: float = 0.01
) -> List[float]:
    """
    This function calculates the density of the values of all elements from all input lists.
    :param sequence_of_lists: a list of list of floats. Each float is a value over [0,1].
    :param division_unit: a real value < 1 to divide [0,1] into intervals [n * division_unit,
    (n+1) * division_unit). The last interval might be shorter than the rest ones.
    :return: density distribution of all values in all sub-lists over the intervals specified above.
    In other words, one can imagine merging all sub-lists into one long list as the input,
    and the result is the density of elements in that long list.

    For example, if we have
    >>> list_1 = [0.25, 0.67, 0.83]
    >>> list_2 = [0.26, 0.91]
    >>> division_unit = 0.10
    >>> calculate_density([list_1, list_2], division_unit)
    [0.0, 0.0, 0.4, 0.0, 0.0, 0.0, 0.2, 0.0, 0.2, 0.2, 0.0]

    """

    total_points: int = sum(len(single_list) for single_list in sequence_of_lists)

    if total_points == 0:
        raise ValueError("Invalid to calculate density for nothing.")

    largest_index: int = int(1 / division_unit)
    count_list: List[int] = [0 for _ in range(largest_index + 1)]

    for single_list in sequence_of_lists:
        for value in single_list:
            count_list[int(value / division_unit)] += 1

    density_list: List[float] = [value / total_points for value in count_list]

    return density_list
