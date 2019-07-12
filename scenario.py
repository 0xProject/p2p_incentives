"""
This module contains class Scenario only.
"""

from typing import TYPE_CHECKING, Tuple, Dict, List, Any
import numpy
import scenario_candidates
if TYPE_CHECKING:
    from message import Order


class Scenario:
    # pylint: disable=too-many-instance-attributes
    # It is fine to have many instance attributes here.

    """
    The class Scenario describes our assumptions on the system setting.
    For examples, peer and order parameters, system evolving dynamics, event arrival pattern, etc.
    They describe the feature of the system, but is NOT part of our design space.
    """

    def __init__(self, parameters: Tuple[Dict[str, float], Dict[str, float],
                                         Dict[str, Dict[str, float]],
                                         Dict[str, Dict[str, float]],
                                         Dict[str, int],
                                         Dict[str, float],
                                         Dict[str, float]],
                 options: Tuple[Dict[str, str], Dict[str, str]]) -> None:

        # unpacking parameters
        (order_type_ratios, peer_type_ratios, order_par_dict,
         peer_par_dict, init_par, growth_par, stable_par) = parameters

        # ratios of each type of orders, in forms of a dictionary.
        self.order_type_ratios: Dict[str, float] = order_type_ratios
        # ratios for each type of peers, in forms of a dictionary.
        self.peer_type_ratios: Dict[str, float] = peer_type_ratios

        # each value is (mean, var) of order expiration of this order type
        self.order_parameter_dict: Dict[str, Dict[str, float]] = order_par_dict
        # each value is (mean, var) of the initial orderbook size of this type
        self.peer_parameter_dict: Dict[str, Dict[str, float]] = peer_par_dict

        # init period, init_size is number of peers joining the mesh at the very beginning,
        # and the birth time of such peers is randomly distributed over [0,birth_time_span]
        self.init_size: int = init_par['num_peers']
        self.birth_time_span: int = init_par['birth_time_span']

        # growing period (when # of peers increases)
        # An event (peer/order arrival/departure) happens according to some random process
        # (e.g., Poisson or Hawkes) that takes the rate as an input parameter(s).

        self.growth_rounds: int = int(growth_par['rounds'])
        self.growth_rates: List[float] = [growth_par['peer_arrival'], growth_par['peer_dept'],
                                          growth_par['order_arrival'], growth_par['order_cancel']]

        # stable period (# of peers and # of orders remain relatively stable)
        # We should choose the parameters such that peer arrival rate is approximately equal to
        # peer departure rate, and that order arrival rate is approximately equal to the total
        # order departure rate (due to cancellation, settlement, or expiration).

        self.stable_rounds: int = int(stable_par['rounds'])
        self.stable_rates: List[float] = [stable_par['peer_arrival'], stable_par['peer_dept'],
                                          stable_par['order_arrival'], stable_par['order_cancel']]

        # unpacking and setting options
        # options will determine the forms of implementations for functions in this class.
        # option_number_of_events determines event happening (peer/order arrival/dept) pattern.
        # Poisson and Hawkes processes are implemented.
        # option_settle determines when an order is settled. Now only "never settle" is implemented.
        self.option_number_of_events: Dict[str, str] = options[0]
        self.option_settle: Dict[str, str] = options[1]

    def generate_event_counts_over_time(self, rate: Any, max_time: int) -> List[int]:
        """
        This method generates events according to some pattern. It reads
        self.option_number_of_events['method'] to determine the pattern, takes the expected rate
        (could be a value or a tuple of values), & the length of time slots as input, and outputs
        the number of incidents in each time slot.
        Current pattern implementations: Poisson process and Hawkes process.
        :param rate: expected rate of event happening. The type of this input depends on the
        method of generating the event.
        :param max_time: maximal time to generate events.
        :return: A realization of event happening, in terms of # of events happening in each slot.
        """

        if self.option_number_of_events['method'] == 'Poisson':
            # check if "rate" is in the correct format
            if not isinstance(rate, float):
                raise TypeError('Type of the rate is incorrect. Float is expected, but it is: ' +
                                str(type(rate)) + '.')
            return list(numpy.random.poisson(rate, max_time))

        if self.option_number_of_events['method'] == 'Hawkes':
            # Note that the rate parameters for Hawkes are a tuple of variables,
            # explained in hawkes() function.
            if not isinstance(rate, tuple):
                raise TypeError('Type of the rate is incorrect. Tuple[float, float, float] is '
                                'expected, but it is: ' + str(type(rate)) + '.')
            return scenario_candidates.hawkes(rate, max_time)
        raise ValueError('No such option to generate events: {}'.
                         format(self.option_number_of_events['method']))

    # This function updates the is_settled status for orders.
    def update_orders_settled_status(self, order: 'Order') -> None:
        """
        This method updates the is_settled status for an order.
        :param order: the order to be updated
        :return: None
        """

        if self.option_settle['method'] == 'Never':
            scenario_candidates.settle_dummy(order)
        else:
            raise ValueError('No such option to change settlement status for orders: {}'.
                             format(self.option_settle['method']))
