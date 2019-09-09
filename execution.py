"""
This module contains class MultiRunInParallel only.
"""

# HACK (weijiewu8): Propose to change the name of the module to "multi_run_in_parallel.py"
# If I change the name now, no comparison of changes can be seen. So I will change it after the
# PR is approved.

from multiprocessing import Pool
from typing import List, Tuple, TYPE_CHECKING

from simulator import SingleRun
from data_types import SingleRunPerformanceResult, MultiRunPerformanceResult

if TYPE_CHECKING:
    from scenario import Scenario
    from engine import Engine
    from performance import Performance


class MultiRunInParallel:
    """
    This class contains functions that runs the simulator multiple times, using a multiprocessing
    manner, and finally, calculates the performance measures for each run.
    The need of running the simulator multiple times comes from randomness. Due to randomness,
    each time the simulator is run, the result can be quite different, so figures are not smooth.
    Since each time the simulator running is totally independent, we use multiprocessing to reduce
    execution time.
    """

    def __init__(
        self,
        scenario: "Scenario",
        engine: "Engine",
        performance: "Performance",
        rounds: int = 40,
        multi_pools: int = 32,
    ) -> None:

        self.scenario: "Scenario" = scenario  # assumption
        self.engine: "Engine" = engine  # design choice
        self.performance: "Performance" = performance  # performance evaluation method
        self.rounds: int = rounds  # how many times the simulator is run. Typically 40.

    @staticmethod
    def single_run_helper(
        args: Tuple["Scenario", "Engine", "Performance"]
    ) -> SingleRunPerformanceResult:
        """
        This is a helper method called by method parallel_run(), to realize multi-processing.
        It actually runs the single_run_execution() function in SingleRun.
        :param args: arbitrary inputs.
        :return: SingleRun.run()
        """
        return SingleRun(*args).single_run_execution()

    @staticmethod
    def reorganize_performance_results(
        performance_result_list: List[SingleRunPerformanceResult]
    ) -> MultiRunPerformanceResult:
        """
        This methods takes a list of single_run performance results, reorganizes them and returns a
        tuple in the form of MultiRunPerformanceResult, where each element is a list of the
        performance results from all runs, associated with a certain key.
        """
        multi_run_performance_by_measure = MultiRunPerformanceResult(
            order_spreading=[],
            normal_peer_satisfaction=[],
            free_rider_satisfaction=[],
            fairness=[],
        )

        for measure_key, value_list in multi_run_performance_by_measure.items():
            for item in performance_result_list:
                value = getattr(item, measure_key)
                # the isinstance() judgement should always pass and it is only to make mypy work
                if not isinstance(value_list, list):
                    raise TypeError(
                        "List is expected for performance_measure.values() in "
                        "runtime, but it is not. This should never happen."
                    )
                if value is not None:
                    value_list.append(value)
        return multi_run_performance_by_measure

    def multi_run_execution(self) -> MultiRunPerformanceResult:
        """
        This method runs the simulator for a number of "self.rounds" times in parallel,
        using "self.multi_pools" processes. It also re-organizes the performance
        evaluation results in a dictionary, where the value for performance_measure[key] is a
        list of performance results in all runs for metric "key."
        :return: performance results.
        """

        # Note: this method is simple so we don't have a unit test for it.

        # Run multiple times in parallel
        with Pool() as my_pool:
            performance_result_list: List[SingleRunPerformanceResult] = my_pool.map(
                self.single_run_helper,
                [
                    (self.scenario, self.engine, self.performance)
                    for _ in range(self.rounds)
                ],
            )

        return self.reorganize_performance_results(performance_result_list)
