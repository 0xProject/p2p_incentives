"""
This __init__.py file contains specific mock/fake functions for this sub-module.
"""

from typing import List


def mock_random_choice(candidates: List, weights: List[float], *, k: int) -> List:
    """
    This is a mock function for random.choice(). It generates a deterministic sequence of the
    candidates, each one with frequency weights[i] (count: int(len(candidates) * k). If the
    sum of total count is less than number, then the deficiency is given to the candidates
    with the highest weight.
    :param candidates: candidates to choose from.
    :param weights: frequency of each candidate to be chosen.
    :param k: total number of output list.
    :return: a list of items in the candidates.
    """

    # normalization

    sum_of_weights = sum(weights)
    weights = [weight / sum_of_weights for weight in weights]

    counts: List[int] = [int(k * weights[i]) for i in range(len(weights))]

    if sum(counts) < k:
        max_idx: int = weights.index(max(weights))
        counts[max_idx] += k - sum(counts)

    result: List = list()
    for i in range(len(counts)):
        result += [candidates[i] for _ in range(counts[i])]
    return result


def test_mock_random_choice__no_remains() -> None:
    """
    This is to make sure mock_random_choice() works correct.
    """
    actual_result: List = mock_random_choice(
        candidates=["a", "b", "c"], weights=[0.1, 0.3, 0.6], k=10
    )
    expected_result: List = ["a", "b", "b", "b", "c", "c", "c", "c", "c", "c"]
    assert actual_result == expected_result


def test_mock_random_choice__with_remains() -> None:
    """
    This is to make sure mock_random_choice() works correct.
    """
    actual_result: List = mock_random_choice(
        candidates=["a", "b", "c"], weights=[0.1, 0.6, 0.3], k=11
    )
    expected_result: List = ["a", "b", "b", "b", "b", "b", "b", "b", "c", "c", "c"]
    assert actual_result == expected_result


def fake_gauss(mean: float, _var: float) -> int:
    """
    This is a fake function for Gaussian variable. It simply convert mean to integer and return it.
    """
    return int(mean)
