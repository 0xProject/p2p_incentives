"""
This module contains class Scenario only.
"""

from typing import TYPE_CHECKING, List
import numpy
import scenario_candidates
from data_types import (
    ScenarioParameters,
    ScenarioOptions,
    OrderTypePropertyDict,
    PeerTypePropertyDict,
    EventOption,
    SettleOption,
    EventArrivalRate,
    PoissonArrivalRate,
    HawkesArrivalRate,
)


if TYPE_CHECKING:
    from message import Order


class Scenario:
    """
    The class Scenario describes our assumptions on the system setting.
    For examples, peer and order parameters, system evolving dynamics, event arrival pattern, etc.
    They describe the feature of the system, but is NOT part of our design space.
    """

    def __init__(
        self, parameters: ScenarioParameters, options: ScenarioOptions
    ) -> None:

        # unpacking parameters

        # order types and properties
        self.order_type_property: OrderTypePropertyDict = parameters.order_type_property
        # peer types and properties
        self.peer_type_property: PeerTypePropertyDict = parameters.peer_type_property

        # init period, init_size is number of peers joining the mesh at the very beginning,
        # and the birth time of such peers is randomly distributed over [0,birth_time_span]
        self.init_size: int = parameters.init_state.num_peers
        self.birth_time_span: int = parameters.init_state.birth_time_span

        # growing period (when number of peers increases)
        # An event (peer/order arrival/cancellation) happens according to some random process
        # (e.g., Poisson or Hawkes) that takes the rate as an input parameter(s).

        self.growth_rounds: int = parameters.growth_period.rounds
        self.growth_rates: List[EventArrivalRate] = [
            parameters.growth_period.peer_arrival,
            parameters.growth_period.peer_dept,
            parameters.growth_period.order_arrival,
            parameters.growth_period.order_cancel,
        ]

        # stable period (number of peers and number of orders remain relatively stable)
        # We should choose the parameters such that peer arrival rate is approximately equal to
        # peer departure rate, and that order arrival rate is approximately equal to the total
        # order departure rate (due to cancellation, settlement, or expiration).

        self.stable_rounds: int = parameters.stable_period.rounds
        self.stable_rates: List[EventArrivalRate] = [
            parameters.stable_period.peer_arrival,
            parameters.stable_period.peer_dept,
            parameters.stable_period.order_arrival,
            parameters.stable_period.order_cancel,
        ]

        # unpacking and setting options
        # options will determine the forms of implementations for functions in this class.
        # option_number_of_events determines event happening (peer/order arrival/dept) pattern.
        # Poisson and Hawkes processes are implemented.
        # option_settle determines when an order is settled. Now only "never settle" is implemented.
        self.option_number_of_events: EventOption = options.event
        self.option_settle: SettleOption = options.settle

    def generate_event_counts_over_time(
        self, rate: EventArrivalRate, max_time: int
    ) -> List[int]:
        """
        This method generates events according to some pattern. It reads
        self.option_number_of_events['method'] to determine the pattern, takes the expected rate
        (could be a value or a tuple of values), & the length of time slots as input, and outputs
        the number of incidents in each time slot.
        Current pattern implementations: Poisson process and Hawkes process.
        :param rate: expected rate of event happening. The type of this input depends on the
        method of generating the event.
        :param max_time: maximal time to generate events.
        :return: A realization of event happening, in terms of number of events happening in each
        slot.
        """

        # Slightly modified the following code section (Poisson), just to keep it consistent with
        # the next code section (Hawkes). Nothing special and it shouldn't impact the logic.
        # This comment should be deleted in the next PR.

        if self.option_number_of_events["method"] == "Poisson":
            # check if "rate" is in the correct format
            if isinstance(rate, PoissonArrivalRate):
                return list(numpy.random.poisson(rate, max_time))
            raise TypeError(
                "Type of the rate is incorrect. Float is expected, but it is: "
                + str(type(rate))
                + "."
            )

        if self.option_number_of_events["method"] == "Hawkes":
            # Note that the rate parameters for Hawkes are a named tuple of variables,
            # explained in hawkes() function.
            if isinstance(rate, HawkesArrivalRate):
                return scenario_candidates.hawkes(rate, max_time)
            raise TypeError(
                "Type of the rate is incorrect. A tuple of 4 floats is "
                "expected, but it is: " + str(type(rate)) + "."
            )

        raise ValueError(
            f"No such option to generate events: {self.option_number_of_events['method']}"
        )

    # This function updates the is_settled status for orders.
    def update_orders_settled_status(self, order: "Order") -> None:
        """
        This method updates the is_settled status for an order.
        :param order: the order to be updated
        :return: None
        """

        if self.option_settle["method"] == "Never":
            scenario_candidates.settle_dummy(order)
        else:
            raise ValueError(
                f"No such option to change settlement status for orders: "
                f"{self.option_settle['method']}"
            )
