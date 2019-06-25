"""
This module contains class Execution only.
"""

from multiprocessing import Pool
import matplotlib.pyplot as plt
from simulator import Simulator
import data_processing


class Execution:
    """
    This class contains functions that runs the simulator multiple times, using a multiprocessing
    manner, and finally, average the performance measures and output corresponding figures.
    The need of running the simulator multiple times comes from randomness. Due to randomness,
    each time the simulator is run, the result can be quite different, so figures are not smooth.
    Since each time the simulator running is totally independent, we use multiprocessing to reduce
    execution time.
    """

    def __init__(self, scenario, engine, performance, rounds=40, multi_pools=32):

        # pylint: disable=too-many-arguments
        # It is fine to have six arguments here.

        self.scenario = scenario  # assumption
        self.engine = engine  # design choice
        self.performance = performance  # performance evaluation method

        self.rounds = rounds  # how many times the simulator is run. Typically 40.
        self.multi_pools = multi_pools  # how many processes we have. Typically 16 or 32.

    @staticmethod
    def make_run(args):
        """
        This is a helper method called by method run(), to realize multi-processing.
        :param args: arbitrary inputs.
        :return: Simulator.run()
        """
        return Simulator(*args).run()

    def run(self):
        """
        This method stimulates the simulator to run for a number of "self.rounds" times,
        using "self.multi_pools" processes.
        It records and re-organizes the performance results from each run, put them into
        data processing, and draw corresponding figures.
        :return: None.
        """

        # pylint: disable=too-many-locals
        # It is fine to have many locals here.

        with Pool(self.multi_pools) as my_pool:
            performance_result_list = my_pool.map\
                (self.make_run, [(self.scenario, self.engine, self.performance) for _ in range(
                    self.rounds)])

        # Unpacking and re-organizing the performance evaluation results such that
        # performance_measure[key] is a list of performance results in all runs for metric "key."

        performance_measure = dict()
        for measure_key in performance_result_list[0].keys():
            performance_measure[measure_key] = list(item[measure_key] for item in
                                                    performance_result_list
                                                    if item[measure_key] is not None)

        # process each performance result

        # processing spreading ratio, calculate best, worst, and average spreading ratios
        spreading_ratio_lists = performance_measure['order_spreading']
        if spreading_ratio_lists:
            (best_order_spreading_ratio, worst_order_spreading_ratio)\
                        = data_processing.find_best_worst_lists(spreading_ratio_lists)
            average_order_spreading_ratio = data_processing.average_lists(spreading_ratio_lists)

            plt.plot(average_order_spreading_ratio)
            plt.plot(worst_order_spreading_ratio)
            plt.plot(best_order_spreading_ratio)

            plt.legend(['average spreading', 'worst spreading', 'best spreading'], loc='upper left')
            plt.xlabel('age of orders')
            plt.ylabel('spreading ratio')
            plt.show()

        # processing user satisfaction if it exists.
        legend_label = []

        # Normal peers first.
        normal_peer_satisfaction_lists = performance_measure['normal_peer_satisfaction']
        if normal_peer_satisfaction_lists:
            legend_label.append('normal peer')
            normal_satisfaction_density = data_processing.calculate_density(
                normal_peer_satisfaction_lists)
            plt.plot(normal_satisfaction_density)

        # Free riders next.
        free_rider_satisfaction_lists = performance_measure['free_rider_satisfaction']
        if free_rider_satisfaction_lists:
            legend_label.append('free rider')
            free_rider_satisfaction_density = data_processing.calculate_density(
                free_rider_satisfaction_lists)
            plt.plot(free_rider_satisfaction_density)

        # plot normal peers and free riders satisfactions in one figure.
        if legend_label:
            plt.legend(legend_label, loc='upper left')
            plt.xlabel('satisfaction')
            plt.ylabel('density')
            plt.show()

        # processing fairness index if it exists. Now it is dummy.

        system_fairness = performance_measure['fairness']
        if system_fairness:
            try:
                system_fairness_density = data_processing.\
                    calculate_density([[item for item in system_fairness if item is not None]])
            except ValueError:
                raise RuntimeError('Seems wrong somewhere since there is no result for fairness '
                                   'in any run.')
            else:
                plt.plot(system_fairness_density)
                plt.legend(['fairness density'], loc='upper left')
                plt.xlabel('fairness')
                plt.ylabel('density')
                plt.show()
