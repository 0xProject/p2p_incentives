"""
====================
Candidates of Scenarios
====================
"""

# This module contains contains all possible realizations for functions in Scenario.

import random
import math

# This is the function to generate Hawkes process.
# The expected arrival rate lambda(t) at time point t is:
# lambda(t) = a + (lambda_0 - a ) * exp(-delta * t) +
# summation of [ gamma * exp(-delta * (t- T_i)) ] for all T_i < t,
# where T_i is any time point when an previous event happens.
# Other parameters (a, lambda_0, gamma, delta) are input arguments.
# If you are not familiar with the definition of "expected arrival rate,"
# please refer to the defnition of Poisson process.

# It takes parameters (a, lambda_0, delta, gamma) from rate, and max time slots as input,
# and outputs a random realization of event happening counts over time slots [0, max_time].

# This simulation method was proposed by Dassios and Zhao in a paper
# entitled 'Exact simulation of Hawkes process
# with exponentially decaying intensity,' published in Electron.
# Commun. Probab. 18 (2013) no. 62, 1-13.
# It is believed to be running faster than other methods.


def Hawkes(rate, max_time):

    (a, lambda_0, delta, gamma) = rate
    # check paramters
    if not (a >= 0 and lambda_0 >= a and delta > 0 and gamma >= 0):
        raise ValueError(
            "Parameter setting is incorrect for the Hawkes process."
        )

    T = [0]
    lambda_minus = lambda_0
    lambda_plus = lambda_0

    while T[-1] < max_time:
        u0 = random.random()
        try:
            s0 = -1 / a * math.log(u0)
        except:
            s0 = float("inf")
        u1 = random.random()
        try:
            d = 1 + delta * math.log(u1) / (lambda_plus - a)
        except:
            d = float("-inf")
        if d > 0:
            try:
                s1 = (-1 / delta) * math.log(d)
            except:
                s1 = float("inf")
            tau = min(s0, s1)
        else:
            tau = s0
        T.append(T[-1] + tau)
        lambda_minus = (lambda_plus - a) * math.exp(-delta * tau) + a
        lambda_plus = lambda_minus + gamma

    num_events = [0] * (max_time)
    for t in T[1:-1]:
        num_events[int(t)] += 1

    return num_events


# The following function determines to change an order's is_settled status or not.
# This is a dummy implementation that never changes the status.


def settleDummy(order):
    pass
