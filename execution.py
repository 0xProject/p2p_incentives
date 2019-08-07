"""
This module contains class Execution only.
"""

from multiprocessing import Pool
from typing import List, Tuple, TYPE_CHECKING

import matplotlib.pyplot as plt
from simulator import Simulator
import data_processing
from data_types import (
    SingleRunPerformanceResult,
    MultiRunPerformanceResult,
    OrderSpreading,
    Fairness,
    UserSatisfaction,
    BestAndWorstLists,
)


if TYPE_CHECKING:
    from scenario import Scenario
    from engine import Engine
    from performance import Performance


class Execution:
    """
    This class contains functions that runs the simulator multiple times, using a multiprocessing
    manner, and finally, average the performance measures and output corresponding figures.
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
        self.multi_pools: int = multi_pools  # how many processes we have. Typically 16 or 32.

    @staticmethod
    def make_run(
        args: Tuple["Scenario", "Engine", "Performance"]
    ) -> SingleRunPerformanceResult:
        """
        This is a helper method called by method run(), to realize multi-processing.
        It actually runs the run() function in Simulator.
        :param args: arbitrary inputs.
        :return: Simulator.run()
        """
        return Simulator(*args).run()

    def run(self) -> None:
        """
        This method stimulates the simulator to run for a number of "self.rounds" times,
        using "self.multi_pools" processes.
        It records and re-organizes the performance results from each run, put them into
        data processing, and draw corresponding figures.
        :return: None.
        """

        with Pool(self.multi_pools) as my_pool:
            performance_result_list: List[SingleRunPerformanceResult] = my_pool.map(
                self.make_run,
                [
                    (self.scenario, self.engine, self.performance)
                    for _ in range(self.rounds)
                ],
            )

        # Unpacking and re-organizing the performance evaluation results such that
        # performance_measure[key] is a list of performance results in all runs for metric "key."

        performance_measure: MultiRunPerformanceResult = MultiRunPerformanceResult(
            order_spreading=[],
            normal_peer_satisfaction=[],
            free_rider_satisfaction=[],
            fairness=[],
        )

        # Logic of the following code section is slightly changed in order to make mypy run
        # without a need of using cast.
        # This change should not impact any result since keys in performance_measure should be
        # exactly the same keys in any item in performance_result_list.
        # This comment should be deleted in the next PR.

        for measure_key, value_list in performance_measure.items():
            for item in performance_result_list:
                # we don't do type check for value, but will check its type in the following lines.
                value = getattr(item, measure_key)
                # the isinstance() judgement should always pass and it is only to make mypy work
                if not isinstance(value_list, list):
                    raise TypeError(
                        "List is expected for performance_measure.values() in "
                        "runtime, but it is not. This should never happen."
                    )
                if value is not None:
                    value_list.append(value)

        # process each performance result

        # processing spreading ratio, calculate best, worst, and average spreading ratios
        spreading_ratio_lists: List[OrderSpreading] = performance_measure[
            "order_spreading"
        ]
        if spreading_ratio_lists:
            best_worst_ratios: BestAndWorstLists = data_processing.find_best_worst_lists(
                spreading_ratio_lists
            )
            average_order_spreading_ratio: List[float] = data_processing.average_lists(
                spreading_ratio_lists
            )

            plt.plot(average_order_spreading_ratio)
            plt.plot(best_worst_ratios.worst)  # worst ratio
            plt.plot(best_worst_ratios.best)  # best ratio

            plt.legend(
                ["average spreading", "worst spreading", "best spreading"],
                loc="upper left",
            )
            plt.xlabel("age of orders")
            plt.ylabel("spreading ratio")
            plt.show()

        # processing user satisfaction if it exists.
        legend_label: List[str] = []

        # Normal peers first.
        normal_peer_satisfaction_lists: List[UserSatisfaction] = performance_measure[
            "normal_peer_satisfaction"
        ]
        if normal_peer_satisfaction_lists:
            legend_label.append("normal peer")
            normal_satisfaction_density: List[
                float
            ] = data_processing.calculate_density(normal_peer_satisfaction_lists)
            plt.plot(normal_satisfaction_density)

        # Free riders next.
        free_rider_satisfaction_lists: List[UserSatisfaction] = performance_measure[
            "free_rider_satisfaction"
        ]
        if free_rider_satisfaction_lists:
            legend_label.append("free rider")
            free_rider_satisfaction_density: List[
                float
            ] = data_processing.calculate_density(free_rider_satisfaction_lists)
            plt.plot(free_rider_satisfaction_density)

        # plot normal peers and free riders satisfactions in one figure.
        if legend_label:
            plt.legend(legend_label, loc="upper left")
            plt.xlabel("satisfaction")
            plt.ylabel("density")
            plt.show()

        # processing fairness index if it exists. Now it is dummy.

        # deleted an error catch since it is duplicate. It is already caught in
        # data_processing.calculate_density.
        # This comment should be deleted in the next PR.

        system_fairness: List[Fairness] = performance_measure["fairness"]
        if system_fairness:
            system_fairness_density: List[float] = data_processing.calculate_density(
                [system_fairness]
            )
            plt.plot(system_fairness_density)
            plt.legend(["fairness density"], loc="upper left")
            plt.xlabel("fairness")
            plt.ylabel("density")
            plt.show()
