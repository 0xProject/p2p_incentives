"""
This module contains test functions for reorganize_performance_results() in multi_run_in_parallel.py
"""

from data_types import SingleRunPerformanceResult, MultiRunPerformanceResult
from execution import MultiRunInParallel


SINGLE_RESULT_1 = SingleRunPerformanceResult(
    order_spreading=[0.2, 0.5, 0.7, 0.9, None],
    normal_peer_satisfaction=[0.6, 0.8, 0.5, 1.0],
    free_rider_satisfaction=[0.2, 0.3],
    fairness=None,
)

SINGLE_RESULT_2 = SingleRunPerformanceResult(
    order_spreading=[0.3, 0.6, 0.8, None, 1],
    normal_peer_satisfaction=[0.8, 0.9, 0.6],
    free_rider_satisfaction=None,
    fairness=None,
)

SINGLE_RESULT_3 = SingleRunPerformanceResult(
    order_spreading=[0.2, 1.0, 1.0, 1.0, 1.0],
    normal_peer_satisfaction=None,
    free_rider_satisfaction=[0.2, 0.3],
    fairness=None,
)

SINGLE_RESULT_LIST = [SINGLE_RESULT_1, SINGLE_RESULT_2, SINGLE_RESULT_3]

EXPECTED_RESULT = MultiRunPerformanceResult(
    order_spreading=[
        [0.2, 0.5, 0.7, 0.9, None],
        [0.3, 0.6, 0.8, None, 1],
        [0.2, 1.0, 1.0, 1.0, 1.0],
    ],
    normal_peer_satisfaction=[[0.6, 0.8, 0.5, 1.0], [0.8, 0.9, 0.6]],
    free_rider_satisfaction=[[0.2, 0.3], [0.2, 0.3]],
    fairness=[],
)


def test_reorganize_performance_results():
    """
    This is the unit test for reorganize_performance_result() in multi_run_in_parallel.py
    """
    real_result = MultiRunInParallel.reorganize_performance_results(SINGLE_RESULT_LIST)
    assert real_result == EXPECTED_RESULT
