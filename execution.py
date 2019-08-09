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
    InvalidInputError,
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

        # pylint: disable=too-many-branches, too-many-statements
        # temporarily disable the pylint warning for now.
        # This function is really too long. Will split it in future PR.
        # This comment should be deleted in the next PR.

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

        performance_measure = MultiRunPerformanceResult(
            order_spreading=[],
            normal_peer_satisfaction=[],
            free_rider_satisfaction=[],
            fairness=[],
        )

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

        # Note: There are additional try... except... judgments newly added in this PR. They are
        # necessary.
        # In short, the following part of the code is to fetch data from performance_measure
        # (which is of type MultiRunPerformanceResult). For each key, if there is a corresponding
        # non-empty value, we plot the figure for this performance metric.
        #
        # Previously we merely check if the value is non-empty. This is actually not enough.
        # There is a chance that we are supposed to run a particular performance metric
        # evaluation (say, free-rider satisfaction), but the value part is empty. This is because
        # for avery single run of the simulator, there was no meaningful result (e.g., at the end
        # of the run there were never any free rider in the system). We have stated that due to
        # some randomness there is a chance that for some run, there is no meaningful result (
        # e.g., in a particular run all free riders happen to have left the system at the end),
        # but if it happens in every run, there must be some problem and an error should be raised.
        # What I basically added here is to raise such errors.
        #
        # This explanation should be deleted (or remained but modified) in the next PR.

        # processing spreading ratio, calculate best, worst, and average spreading ratios

        if self.performance.measures_to_execute.order_spreading:
            spreading_ratio_lists: List[OrderSpreading] = performance_measure[
                "order_spreading"
            ]
            try:
                best_worst_ratios: BestAndWorstLists = data_processing.find_best_worst_lists(
                    spreading_ratio_lists
                )
                average_order_spreading_ratio: List[
                    float
                ] = data_processing.average_lists(spreading_ratio_lists)
            except InvalidInputError:
                raise RuntimeError(
                    "Running order spreading performance measurement but there was "
                    "no result from any run."
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
        if self.performance.measures_to_execute.normal_peer_satisfaction:
            normal_peer_satisfaction_lists: List[
                UserSatisfaction
            ] = performance_measure["normal_peer_satisfaction"]
            try:
                normal_satisfaction_density: List[
                    float
                ] = data_processing.calculate_density(normal_peer_satisfaction_lists)
            except InvalidInputError:
                raise RuntimeError(
                    "Running normal peer satisfaction performance measure but "
                    "there was no result from any run."
                )

            legend_label.append("normal peer")
            plt.plot(normal_satisfaction_density)

        # Free riders next.
        if self.performance.measures_to_execute.free_rider_satisfaction:
            free_rider_satisfaction_lists: List[UserSatisfaction] = performance_measure[
                "free_rider_satisfaction"
            ]
            try:
                free_rider_satisfaction_density: List[
                    float
                ] = data_processing.calculate_density(free_rider_satisfaction_lists)
            except InvalidInputError:
                raise RuntimeError(
                    "Running free rider satisfaction performance measure but there "
                    "was no result from any run."
                )

            legend_label.append("free rider")
            plt.plot(free_rider_satisfaction_density)

        # plot normal peers and free riders satisfactions in one figure.
        if legend_label:
            plt.legend(legend_label, loc="upper left")
            plt.xlabel("satisfaction")
            plt.ylabel("density")
            plt.show()

        # processing fairness index if it exists. Now it is dummy.

        if self.performance.measures_to_execute.system_fairness:
            system_fairness: List[Fairness] = performance_measure["fairness"]
            try:
                system_fairness_density: List[
                    float
                ] = data_processing.calculate_density([system_fairness])
            except ValueError:  # note that this is special. There is always a non-empty input to
                # the function, and if it is [[]], then there will be an ValueError raised.
                raise RuntimeError(
                    "Running system fairness performance measure but there was "
                    "no result from any run."
                )

            plt.plot(system_fairness_density)
            plt.legend(["fairness density"], loc="upper left")
            plt.xlabel("fairness")
            plt.ylabel("density")
            plt.show()
