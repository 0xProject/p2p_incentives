"""
=========================
Data processing tools
=========================
"""
# This module contains data processing tools (e.g., finding the max, min, average, frequency...)
# to work on performance evaluation results, possibly for results of running the simulator multiple times.

import itertools
import statistics

# This function takes a sequence of equal-length lists and find the best and worst lists.
# An element in the list is either a non-negative value or None.
# the best/worst list is the one who's last entry is the largest/smallest among all lists given.
# If any entry is None, it is ignored (neither the best nor the worst).
# If the last entries of all lists are all None, then we look at the second last entry, etc.,
# up till the first entry. If all entries of all lists are None, raise an exception.
# For example, if list_1 = [0.1, 0.2, 0.3, None], list_2 = [0.29, 0.29, 0.29, None],
# then list_1 is the best and list_2 is the worst.
# For effeciency consideration, this function does not check validity of the argument (same length)
# since it should have been guaranteed in the function that calls it.


def findBestWorstLists(sequence_of_lists):

    last_effective_idx = -1
    while last_effective_idx >= -len(sequence_of_lists[0]):
        if any(
            item[last_effective_idx] is not None for item in sequence_of_lists
        ):
            break
        last_effective_idx -= 1

    if last_effective_idx == -len(sequence_of_lists[0]) - 1:
        raise ValueError("All entries are None. Invalid to compare.")

    it1, it2 = itertools.tee(
        (
            item
            for item in sequence_of_lists
            if item[last_effective_idx] is not None
        ),
        2,
    )
    best_list = max(it1, key=lambda x: x[last_effective_idx])
    worst_list = min(it2, key=lambda x: x[last_effective_idx])

    return (best_list, worst_list)


# The following function takes a sequence of equal-length lists as input,
# and outputs a list of the same length.
# Each element in each input list is either a value or None.
# Each element in the output list is the average of the values in the corresponding place
# of all input lists, ignoring all None elements.
# If all elements in a place of all input lists are None, then the output element in that place is 0.


def averageLists(sequence_of_lists):

    average_list = [None for _ in range(len(sequence_of_lists[0]))]

    for idx in range(len(average_list)):
        try:
            average_list[idx] = statistics.mean(
                any_list[idx]
                for any_list in sequence_of_lists
                if any_list[idx] is not None
            )
        except:
            average_list[idx] = 0

    return average_list


# The following function takes a sequence of lists, and a division unit, as input.
# Each element in each list is a real value over [0,1).
# It outputs the density distribution of such values. Each list/element is equally weighted.
# In other words, one can imagine merging all lists into one long list as the input,
# and the result is the density of elements in that long list.


def densityOverAll(sequence_of_lists, division_unit=0.01):

    total_points = sum(len(single_list) for single_list in sequence_of_lists)

    if total_points == 0:
        raise ValueError("Invalid to calculate density for nothing.")

    largest_index = int(1 / division_unit)
    density_list = [0 for _ in range(largest_index + 1)]

    for single_list in sequence_of_lists:
        for value in single_list:
            density_list[int(value / division_unit)] += 1

    density_list = [value / total_points for value in density_list]

    return density_list
