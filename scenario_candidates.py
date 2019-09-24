"""
This module contains contains all possible realizations for functions in Scenario.
"""

import random
import math
from typing import List, TYPE_CHECKING
from data_types import HawkesArrivalRate


if TYPE_CHECKING:
    from message import Order


def hawkes(rate: HawkesArrivalRate, max_time: int) -> List[int]:
    """
    This is the function to generate Hawkes process. The expected arrival rate lambda(t) at time
    point t is:
    lambda(t) = a + (lambda_0 - a ) * exp(-delta * t) + summation of [ gamma * exp(-delta * (t-
    T_i)) ] for all T_i < t,
    where T_i is any time point when an previous event happens, and other parameters (a,
    lambda_0, gamma, delta) are input arguments. If you are not familiar with the definition of
    "expected arrival rate," please refer to the definition of Poisson process.
    It takes parameters (a, lambda_0, delta, gamma) from rate, and max time slots as input,
    and outputs a random realization of event happening counts over time slots [0, max_time].

    This simulation method was proposed by Dassios and Zhao in a paper entitled 'Exact simulation
    of Hawkes process with exponentially decaying intensity,' published in Electron. Commun. Probab.
    18 (2013) no. 62, 1-13.
    It is believed to be running faster than other methods.

    Please note that it is very difficult to write unit test for this function due to randomness.
    Right now we just leave it without unit tests. It is pretty safe since we simply copied the
    logic from the original paper.

    :param rate: see above for explanation.
    :param max_time: maximal time to generate events.
    :return: One realization, in terms of a list, each element being number of events in each time
    slot.
    """

    # pylint: disable=invalid-name
    # pylint: disable=too-many-locals
    # Inside this function, variable names are kept the same as the original paper.
    # Fine to violate naming regulations merely inside this function.

    a: float = rate.a
    lambda_0: float = rate.lambda_0
    delta: float = rate.delta
    gamma: float = rate.gamma

    # check parameters
    if not (lambda_0 >= a >= 0 and delta > 0 and gamma >= 0):
        raise ValueError("Parameter setting is incorrect for the Hawkes process.")

    T: List[float] = [0.0]  # this is the list of event happening time.
    lambda_plus = lambda_0

    while T[-1] < max_time:
        u0 = random.random()
        try:
            s0 = -1 / a * math.log(u0)
        except ZeroDivisionError:
            s0 = float("inf")
        u1 = random.random()
        try:
            d = 1 + delta * math.log(u1) / (lambda_plus - a)
        except ZeroDivisionError:
            d = float("-inf")
        if d > 0:
            try:
                s1 = (-1 / delta) * math.log(d)
            except ZeroDivisionError:
                s1 = float("inf")
            tau = min(s0, s1)
        else:
            tau = s0
        T.append(T[-1] + tau)
        lambda_minus = (lambda_plus - a) * math.exp(-delta * tau) + a
        lambda_plus = lambda_minus + gamma

    num_events: List[int] = [0] * max_time
    for t in T[1:-1]:
        num_events[int(t)] += 1

    return num_events


def settle_concave(order: "Order", sensitivity: float, max_prob: float) -> None:
    """
    This function simulates the process of settling an order. The key idea is the more replicas
    an order has in the Mesh, the more likely it is settled in one round.
    We use a concave function to model this, in particular, the probability of settling an order is
    prob = max_prob * (1 - math.exp(- sensitivity * len(order.holders))), so if there is no
    replica, the probability of being settled is 0; if the number of replicas is very large,
    then the probability approaches max_prob.
    :param order: instance of the order, to consider whether is settled in this function
    :param sensitivity: parameter to the exponential function.
    :param max_prob: the maximal probability of being settled in this round
    :return: None
    """

    if sensitivity < 0 or (not 0 <= max_prob <= 1):
        raise ValueError("Invalid input argument value.")

    prob: float = max_prob * (1 - math.exp(-sensitivity * len(order.holders)))
    if random.random() < prob:
        order.is_settled = True


def cancel_random(order: "Order", prob: float) -> None:
    """
    This function simulates the process of cancelling an order. This order will be cancelled with a
    probability of "prob" in any time slot.
    :param order: the order to be considered for cancellation.
    :param prob: probability of being cancelled.
    :return: None.
    """

    if not 0 <= prob <= 1:
        raise ValueError("Invalid cancellation probability.")

    if random.random() < prob:
        order.is_canceled = True


def age_based_cancellation(
    order: "Order", time_now: int, sensitivity: float, max_prob: float
) -> None:
    """
    This function is to simulate that the cancellation probability increases (for example,
    due to price change) as the order stays longer in the system.
    Its math model is very similar to settle_concave(), the only difference being we take the age
    of the order (instead of the number of order holders) in the exponent.
    Due to the similarity we don't write unit tests of this function.
    """

    if sensitivity < 0 or (not 0 <= max_prob <= 1):
        raise ValueError("Invalid argument value.")

    if time_now < order.birth_time:
        raise ValueError("System time in a chaos.")

    prob: float = max_prob * (
        1 - math.exp(-sensitivity * (time_now - order.birth_time))
    )
    if random.random() < prob:
        order.is_canceled = True
