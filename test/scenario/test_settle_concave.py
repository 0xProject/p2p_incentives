"""
This module contains unit tests of settle_concave().
"""

import math
from typing import NamedTuple, List
import pytest

from scenario_candidates import settle_concave
from scenario import Scenario
from engine import Engine
from message import Order
from node import Peer

from ..__init__ import (
    SCENARIO_SAMPLE,
    ENGINE_SAMPLE,
    create_a_test_order,
    create_test_peers,
)


class CaseType(NamedTuple):
    """
    Data type for test cases.
    """

    scenario: Scenario
    engine: Engine
    num_holders: int
    sensitivity: float
    max_prob: float


# Test normal cases.

CASE_1 = CaseType(
    scenario=SCENARIO_SAMPLE,
    engine=ENGINE_SAMPLE,
    num_holders=50,
    sensitivity=0.5,
    max_prob=0.5,
)

CASE_2 = CaseType(
    scenario=SCENARIO_SAMPLE,
    engine=ENGINE_SAMPLE,
    num_holders=10,
    sensitivity=2,
    max_prob=1.0,
)


CASE_3 = CaseType(
    scenario=SCENARIO_SAMPLE,
    engine=ENGINE_SAMPLE,
    num_holders=0,
    sensitivity=3,
    max_prob=0.9,
)

CASE_4 = CaseType(
    scenario=SCENARIO_SAMPLE,
    engine=ENGINE_SAMPLE,
    num_holders=20,
    sensitivity=0,
    max_prob=0.9,
)

CASE_5 = CaseType(
    scenario=SCENARIO_SAMPLE,
    engine=ENGINE_SAMPLE,
    num_holders=20,
    sensitivity=1,
    max_prob=0,
)

CASE_LIST: List[CaseType] = [CASE_1, CASE_2, CASE_3, CASE_4, CASE_5]


@pytest.mark.parametrize(
    "scenario, engine, num_holders, sensitivity, max_prob", CASE_LIST
)
def test_settle_concave__normal(
    scenario: Scenario,
    engine: Engine,
    num_holders: int,
    sensitivity: float,
    max_prob: float,
) -> None:
    """
    Unit test for settle_concave().
    We will create an order for the test, and a set of peers that have this order (total number
    of the peers is `num_orders`). Then we will call the function settle_concave() for this
    order. With an expected probability of max_prob * (1 - math.exp(-sensitivity * num_holders)),
    this order will be settled. We repeat this process for `times` times, so the expected counts
    of settlement should be times * expected_probability. We finally compare the actual times that
    this order is settled, with expected counts (which = times * expected_probability),
    with an allowance of difference equal to error_allowance * expected_counts.

    :param scenario: Scenario instance.
    :param engine: Engine instance.
    :param num_holders: number of holders for the order
    :param sensitivity: parameter in settle_concave().
    :param max_prob: parameter in settle_concave().
    :return: None.
    """

    times: int = 1000
    error_allowance = 0.05
    count = 0

    for _ in range(times):

        # Arrange.
        order: Order = create_a_test_order(scenario)
        holders: List[Peer] = create_test_peers(scenario, engine, num_holders)
        for holder in holders:
            order.holders.add(holder)

        # Act.
        settle_concave(order, sensitivity, max_prob)
        if order.is_settled:
            count += 1

    # Assert.
    expected_prob: float = max_prob * (1 - math.exp(-sensitivity * num_holders))
    assert count == pytest.approx(times * expected_prob, times * error_allowance)


# Test invalid inputs.

CASE_6 = CaseType(
    scenario=SCENARIO_SAMPLE,
    engine=ENGINE_SAMPLE,
    num_holders=20,
    sensitivity=-1,
    max_prob=1.0,
)

CASE_7 = CaseType(
    scenario=SCENARIO_SAMPLE,
    engine=ENGINE_SAMPLE,
    num_holders=20,
    sensitivity=1,
    max_prob=-0.1,
)

CASE_8 = CaseType(
    scenario=SCENARIO_SAMPLE,
    engine=ENGINE_SAMPLE,
    num_holders=20,
    sensitivity=1,
    max_prob=1.5,
)

INVALID_CASE_LIST = [CASE_6, CASE_7, CASE_8]


@pytest.mark.parametrize(
    "scenario, engine, num_holders, sensitivity, max_prob", INVALID_CASE_LIST
)
def test_settle_concave__error(
    scenario: Scenario,
    engine: Engine,
    num_holders: int,
    sensitivity: float,
    max_prob: float,
) -> None:
    """
    Unit test for settle_concave() when input arguments are invalid.
    """

    # Arrange.
    order: Order = create_a_test_order(scenario)
    holders: List[Peer] = create_test_peers(scenario, engine, num_holders)
    for holder in holders:
        order.holders.add(holder)

    # Act and Assert.
    with pytest.raises(ValueError, match="Invalid input argument value."):
        settle_concave(order, sensitivity, max_prob)
