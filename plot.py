"""
This module contains the function that plots the performance results.
"""

from typing import List
import matplotlib.pyplot as plt
import data_processing
from performance import Performance

from data_types import (
    MultiRunPerformanceResult,
    OrderSpreading,
    Fairness,
    UserSatisfaction,
    BestAndWorstLists,
    InvalidInputError,
)


def plot_performance(
    performance: Performance,
    multi_run_performance_by_measure: MultiRunPerformanceResult,
) -> None:
    """
    This method plots the performance results.
    :param performance: an instance of Performance
    :param multi_run_performance_by_measure: performance results from multi-run for each measure
    :return: None.
    """

    # process each performance result

    # The following part of the code is to fetch data from multi_run_performance_by_measure
    # (which is of type MultiRunPerformanceResult). For each key, if there is a corresponding
    # non-empty value, we plot the figure for this performance metric.
    #
    # There is a chance that we are supposed to run a particular performance metric
    # evaluation (say, free-rider satisfaction), but the value part is empty. This is because
    # for every single run of the simulator, there was no meaningful result (e.g., at the end
    # of the run there were never any free rider in the system). We have stated that due to
    # some randomness there is a chance that for some run, there is no meaningful result (
    # e.g., in a particular run all free riders happen to have left the system at the end),
    # but if it happens in every run, there must be some problem and an error should be raised.

    # processing spreading ratio, calculate best, worst, and average spreading ratios

    if performance.measures_to_execute.order_spreading:
        spreading_ratio_lists: List[OrderSpreading] = multi_run_performance_by_measure[
            "order_spreading"
        ]
        try:
            best_worst_ratios: BestAndWorstLists = data_processing.find_best_worst_lists(
                spreading_ratio_lists
            )
            average_order_spreading_ratio: List[float] = data_processing.average_lists(
                spreading_ratio_lists
            )
        except InvalidInputError:
            raise RuntimeError(
                "Running order spreading performance measurement but there was "
                "no result from any run."
            )

        plt.plot(average_order_spreading_ratio)
        plt.plot(best_worst_ratios.worst)  # worst ratio
        plt.plot(best_worst_ratios.best)  # best ratio

        plt.legend(
            ["average spreading", "worst spreading", "best spreading"], loc="upper left"
        )
        plt.xlabel("age of orders")
        plt.ylabel("spreading ratio")
        plt.show()

    # processing user satisfaction if it exists.
    legend_label: List[str] = []

    # Normal peers first.
    if performance.measures_to_execute.normal_peer_satisfaction:
        normal_peer_satisfaction_lists: List[
            UserSatisfaction
        ] = multi_run_performance_by_measure["normal_peer_satisfaction"]
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
    if performance.measures_to_execute.free_rider_satisfaction:
        free_rider_satisfaction_lists: List[
            UserSatisfaction
        ] = multi_run_performance_by_measure["free_rider_satisfaction"]
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

    if performance.measures_to_execute.system_fairness:
        system_fairness: List[Fairness] = multi_run_performance_by_measure["fairness"]
        try:
            system_fairness_density: List[float] = data_processing.calculate_density(
                [system_fairness]
            )
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
