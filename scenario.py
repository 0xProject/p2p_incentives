"""
====================
System Assumptions
====================
"""

# The class Scenario describes our assumptions on the system setting.
# For examples, peer and order parameters, system evolving dynamics, event arrival pattern, etc.
# They describe the feature of the system, but is NOT part of our design space.

import numpy
import scenario_candidates


class Scenario:
    def __init__(self, parameters, options):

        # unpacking parameters
        (
            order_type_ratios,
            peer_type_ratios,
            order_par_dict,
            peer_par_dict,
            init_par,
            growth_par,
            stable_par,
        ) = parameters

        self.order_type_ratios = (
            order_type_ratios
        )  # ratios of each type of orders, in forms of a dictionary.
        self.peer_type_ratios = (
            peer_type_ratios
        )  # ratios for each type of peers, in forms of a dictionary.

        self.order_parameter_dict = (
            order_par_dict
        )  # each value is (mean, var) of order expirations of this order type
        self.peer_parameter_dict = (
            peer_par_dict
        )  # each value is (mean, var) of the initial orderbook size of this peer type

        # init period, init_size is number of peers joining the P2P at the very beginning,
        # and the birth time of such peers is randomly distributed over [0,birth_time_span]
        self.init_size = init_par["num_peers"]
        self.birth_time_span = init_par["birth_time_span"]

        # growing period (when # of peers increases)
        # parameters are: # of time rounds for growth period
        # peer arrival rate, peer dept rate, order arrival rate, order dept rate.
        # An event (peer/order arrival/departure) happens according to some random process
        # (e.g., Poisson or Hawkes) that takes the rate as an input parameter(s).

        """
        # please be noted that, the order dept rate refers to the rate that an order is proactively
        # canceled. This is a poor naming. In reality, an order departs when it is (1) canceled, (2) expired, or (3) settled.
        # So the real departure rate of an order is larger than the order dept rate we define here.
        # I remain the name here just to reduce the difference for this PR review. Will probably change the name
        # to order_cancel in the next version.
        """

        self.growth_rounds = growth_par["rounds"]
        self.growth_rates = [
            growth_par["peer_arrival"],
            growth_par["peer_dept"],
            growth_par["order_arrival"],
            growth_par["order_dept"],
        ]

        # stable period (# of peers and # of orders remain relatively stable)
        # parameters refer to: # of time rounds,
        # peer arrival rate, peer dept rate, order arrival rate, order dept rate.

        # We should choose the parameters such that peer arrival rate is approximately equal to peer departure rate,
        # and that order arrival rate is appoximately equal to the total order departure rate
        # (due to cancellation, settlement, or expiration).

        self.stable_rounds = stable_par["rounds"]
        self.stable_rates = [
            stable_par["peer_arrival"],
            stable_par["peer_dept"],
            stable_par["order_arrival"],
            stable_par["order_dept"],
        ]

        # unpacking and setting options
        # options will determine the forms of implementations for functions in this class.
        # option_numEvent determines event happening (peer/order arrival/dept) pattern.
        # Poisson and Hawkes processes are implemented.
        # option_settle determines when an order is settled. Now only "never settle" is implementd.
        (self.option_numEvent, self.option_settle) = options

    # This function generates events according to some pattern.
    # It reads option_numEvent['method'] to determine the pattern,
    # takes the expected rate (could be a value or a tuple of values)
    # and the length of time slots as input, and
    # outputs the number of incidents in each time slot.
    # Current pattern implementations: Poisson process and Hawkes process.

    def numEvents(self, rate, max_time):
        if self.option_numEvent["method"] == "Poisson":
            return numpy.random.poisson(rate, max_time)
        elif self.option_numEvent["method"] == "Hawkes":
            # note that the rate parameter for Hawkes is a tuple of variables.
            # They are explained in Hawkes function implementation.
            return scenario_candidates.Hawkes(rate, max_time)
        else:
            raise ValueError(
                "No such option to generate events: {}".format(
                    self.option_numEvent["method"]
                )
            )

    # This function updates the is_settled status for orders.
    def orderUpdateSettleStatus(self, order):
        if self.option_settle["method"] == "Never":
            return scenario_candidates.settleDummy(order)
        else:
            raise ValueError(
                "No such option to change settlement status for orders: {}".format(
                    self.option_settle["method"]
                )
            )
