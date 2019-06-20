"""
======================
Multiprocessing execution
======================
"""

# This class contains functions that runs the simulator multiple times, using a
# multiprocessing manner, and finally, average the performance measures and
# output corresponding figures.
# The need of running the simulator multiple times comes from randomness. Due
# to randomness, each time the simulator is run, the result can be quite
# different, so figures are not smooth.
# Due to the fact that each time the simulator running is totally independent,
# we use multiprocessing to reduce execution time.

from simulator import Simulator
from multiprocessing import Pool
import matplotlib.pyplot as plt
import data_processing


class Execution:
    def __init__(
        self, scenario, engine, performance, rounds=40, multipools=32
    ):
        self.scenario = scenario  # assumption
        self.engine = engine  # design choice
        self.performance = performance  # performance evaluation method

        self.rounds = (
            rounds
        )  # how many times the simulator is run. Typtically 40.
        self.multipools = (
            multipools
        )  # how many processes we have. Typically 16 or 32.

    def make_run(self, args):
        return Simulator(*args).run()

    def run(self):
        with Pool(self.multipools) as my_pool:
            performance_result_list = my_pool.map(
                self.make_run,
                [
                    (self.scenario, self.engine, self.performance)
                    for _ in range(self.rounds)
                ],
            )

        # Unpacking and re-organizing the performance evaluation results such
        # that performance_measure[i] is the list of i-th performance result in
        # all runs.
        performance_measure = (
            dict()
        )  # [None for _ in range(len(performance_result_list[0]))]

        for measure_key in performance_result_list[0].keys():
            performance_measure[measure_key] = list(
                item[measure_key]
                for item in performance_result_list
                if item[measure_key] is not None
            )

        # process each performance result

        # processing spreading ratio, calculate best, worst, and average
        # spreading ratios
        spreading_ratio_lists = performance_measure["order_spreading"]
        if spreading_ratio_lists:
            (
                best_order_spreading_ratio,
                worst_order_spreading_ratio,
            ) = data_processing.findBestWorstLists(spreading_ratio_lists)
            average_order_spreading_ratio = data_processing.averageLists(
                spreading_ratio_lists
            )

            plt.plot(average_order_spreading_ratio)
            plt.plot(worst_order_spreading_ratio)
            plt.plot(best_order_spreading_ratio)

            plt.legend(
                ["average spreading", "worst spreading", "best spreading"],
                loc="upper left",
            )
            plt.xlabel("age of orders")
            plt.ylabel("spreading ratio")
            plt.show()

        legend_label = []
        # processing user satisfaction if it exists. Normal peers first.
        normal_peer_satisfaction_lists = performance_measure[
            "normal_peer_satisfaction"
        ]
        if normal_peer_satisfaction_lists:
            legend_label.append("normal peer")
            normal_satistaction_density = data_processing.densityOverAll(
                normal_peer_satisfaction_lists
            )
            plt.plot(normal_satistaction_density)

        # processing user satisfaction if it exists. Free riders next.
        free_rider_satisfaction_lists = performance_measure[
            "free_rider_satisfaction"
        ]
        if free_rider_satisfaction_lists:
            legend_label.append("free rider")
            freerider_satistaction_density = data_processing.densityOverAll(
                free_rider_satisfaction_lists
            )
            plt.plot(freerider_satistaction_density)

        # plot normal peers and free riders satisfactions in one figure.
        if legend_label != []:
            plt.legend(legend_label, loc="upper left")
            plt.xlabel("satisfaction")
            plt.ylabel("density")
            plt.show()

        # processing fairness index if it exists. Now it is dummy.
        system_fairness = performance_measure["fairness"]
        if system_fairness:
            try:
                system_fairness_density = data_processing.densityOverAll(
                    [[item for item in system_fairness if item is not None]]
                )
            except:
                raise RuntimeError(
                    "Seems wrong somewhere since there is no result for"
                    " fairness in any run."
                )
            else:
                plt.plot(system_fairness_density)
                plt.legend(["fairness density"], loc="upper left")
                plt.xlabel("fairness")
                plt.ylabel("density")
                plt.show()
