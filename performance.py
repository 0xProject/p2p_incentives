"""
This module contains the class Performance only.
"""

import performance_candidates


class Performance:
    """
    This class contains parameters, measures, and methods to carry out performance evaluation.
    Methods in this class will call realizations from module performance_candidates.
    """

    def __init__(self, parameters, options, executions):

        # unpacking and setting parameters

        # the oldest age of orders to track
        self.max_age_to_track = parameters['max_age_to_track']

        # the age beyond which a peer is considered an Adult.
        # Only adults will be evaluated for user satisfaction (because new peers receive limited orders only).
        self.adult_age = parameters['adult_age']

        # This is the window length to aggregate orders for statistics.
        # All orders that falls into the same window will be considered in the same era for calculation.
        # For example if statistical_window = 10, then orders whose ages are between 0 and 9 will be
        # put into the same category for statistics.
        # The reason for this window is when order arrival rate is very low, then in many time slots
        # there's no new arrived orders. So it is better to aggregate the orders for statistics.
        self.statistical_window = parameters['statistical_window']

        # unpacking and setting options.

        # "spreading_option" is how to measurement the spreading pattern of order
        # (e.g., spreading ratio, spreading speed).
        # "satisfaction_option" is how a peer evaluates its satisfaction based on the orders that it receives.
        # "fairness_option" is how to evaluate the fairness for a group of peers. Currently we have no implementation.
        (self.spreading_option, self.satisfaction_option, self.fairness_option) = options

        # measurement to execute, i.e., which measurement functions to execute.
        self.measures_to_execute = executions

    # In what follows we have performance evaluation functions.
    # In most of these functions they take peers_to_evaluate and orders_to_evaluate as input.
    # The reason is to add flexibility in considering evaluating over reasonable peers and reasonable
    # orders only (given that there are possibly free riders and wash trading orders).

    def measure_order_spreading(self, cur_time, peers_to_evaluate, orders_to_evaluate):
        """
        This method returns a particular measurement on order spreading.
        The measurement is defined by the function called.
        :param cur_time: current time.
        :param peers_to_evaluate: the set of peer instances of the nodes to be evaluated.
        :param orders_to_evaluate: the set of order instances of the orders to be evaluated.
        :return: the return value of the function called.
        """

        if not peers_to_evaluate or not orders_to_evaluate:
            raise ValueError('Invalid to measure the spreading based on no orders or no peers.')

        # Currently we only implemented spreading ratio. In future we may also want to investigate
        # new orders spreading rate, etc.

        if self.spreading_option['method'] == 'Ratio':
            return performance_candidates.order_spreading_ratio_stat(cur_time, orders_to_evaluate,
                                                                     peers_to_evaluate, self.max_age_to_track,
                                                                     self.statistical_window)
        raise ValueError('No such option to evaluate order spreading: {}'.format(self.spreading_option['method']))

    def measure_user_satisfaction(self, cur_time, peers_to_evaluate, orders_to_evaluate):
        """
        This method returns some measurement of peer satisfactory.
        The measurement is defined by the function called.
        Note, the statistics is based on 'adult peers' only whose age is beyond a threshold specified in scenario,
        :param cur_time: same as above.
        :param peers_to_evaluate: same as above.
        :param orders_to_evaluate: same as above.
        :return: a (non-fixed length) list of satisfactions of every adult peer.
        These values are simply put in a list without specifying which peer they correspond to.
        """

        if not peers_to_evaluate or not orders_to_evaluate:
            raise ValueError('Invalid to evaluate user satisfaction if there are no peers or no orders.')

        # A "neutral" implementation refers to that a peer regards each order as equally important.
        # This is a naive implementation only. Later we will need to consider new orders as more important.

        if self.satisfaction_option['method'] == 'Neutral':
            single_calculation = performance_candidates.single_peer_satisfaction_neutral
        else:
            raise ValueError('No such option to evaluate peer satisfaction: {}'.
                             format(self.satisfaction_option['method']))

        set_of_adult_peers_to_evaluate = set(peer for peer in peers_to_evaluate
                                             if cur_time - peer.birth_time >= self.adult_age)

        satisfaction_list = [single_calculation(cur_time, peer, self.max_age_to_track,
                                                self.statistical_window, orders_to_evaluate)
                             for peer in set_of_adult_peers_to_evaluate]

        return satisfaction_list

    def measure_fairness(self, peers_to_evaluate, orders_to_evaluate):
        """
        This method returns some measurement on fairness for a given set of peers and orders.
        We don't have a real implementation yet.
        :param peers_to_evaluate: same as above.
        :param orders_to_evaluate: same as above.
        :return: The system-wide fairness index, returned by the function called.
        """

        if not peers_to_evaluate:
            raise ValueError('Invalid to evaluate fairness for an empty set of peers.')

        if self.fairness_option['method'] == 'Dummy':
            return performance_candidates.fairness_dummy(peers_to_evaluate, orders_to_evaluate)
        raise ValueError('No such option to evaluate fairness: {}'.format(self.fairness_option['method']))

    def run(self, cur_time, peer_full_set, normal_peer_set, free_rider_set, order_full_set):

        # pylint: disable=too-many-arguments
        # It is fine to have many arguments for this function.

        """
        This method runs the performance evaluation. It reads self.measures_to_execute dictionary to
        decide which evaluation measures are required to run, and returns a list of results.
        If some measure is not run, or it is infeasible to generate any result for that measure,
        the corresponding value in the return list is None.
        :param cur_time: current_time
        :param peer_full_set: all peers to be evaluated
        :param normal_peer_set: all normal peers (excluding free riders) to be evaluated.
        :param free_rider_set: all free riders to be evaluated.
        :param order_full_set: all orders to be evaluated.
        :return: a list of results, each element being the result for each metric.
        """

        # Generate order spreading measure for all orders over all peers
        if self.measures_to_execute['order_spreading_measure']:
            try:
                result_order_spreading = self.measure_order_spreading(cur_time, peer_full_set, order_full_set)
            except ValueError:
                result_order_spreading = None
        else:
            result_order_spreading = None

        # Generate normal peer satisfaction measure over all orders
        if self.measures_to_execute['normal_peer_satisfaction_measure']:
            try:
                result_normal_peer_satisfaction = \
                    self.measure_user_satisfaction(cur_time, normal_peer_set, order_full_set)
            except ValueError:
                result_normal_peer_satisfaction = None
        else:
            result_normal_peer_satisfaction = None

        # Generate free rider satisfaction measure over all orders
        if self.measures_to_execute['free_rider_satisfaction_measure']:
            try:
                result_free_rider_satisfaction = \
                    self.measure_user_satisfaction(cur_time, free_rider_set, order_full_set)
            except ValueError:
                result_free_rider_satisfaction = None
        else:
            result_free_rider_satisfaction = None

        # Generate system fairness measure over all peers and all orders
        if self.measures_to_execute['fairness']:
            try:
                result_fairness = self.measure_fairness(peer_full_set, order_full_set)
            except ValueError:
                result_fairness = None
        else:
            result_fairness = None

        # Organize the results in a list
        result = {'order_spreading': result_order_spreading,
                  'normal_peer_satisfaction': result_normal_peer_satisfaction,
                  'free_rider_satisfaction': result_free_rider_satisfaction,
                  'fairness': result_fairness
                  }
        return result
