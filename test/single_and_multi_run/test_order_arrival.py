"""
This module contains unit tests of order_arrival().
"""

import pytest

from scenario import Scenario
from engine import Engine
from performance import Performance
from node import Peer
from data_types import ConcaveParameters, RandomParameter

from single_run import SingleRun
from ..__init__ import (
    SCENARIO_SAMPLE,
    ENGINE_SAMPLE,
    create_a_test_peer,
    PERFORMANCE_SAMPLE,
)


@pytest.mark.parametrize(
    "scenario, engine, performance",
    [(SCENARIO_SAMPLE, ENGINE_SAMPLE, PERFORMANCE_SAMPLE)],
)
def test_order_arrival__normal(
    scenario: Scenario, engine: Engine, performance: Performance
) -> None:
    """
    This tests order_arrival() in normal case.
    """
    # Arrange.

    # create the single_run instance and a peer.
    single_run_instance = SingleRun(scenario, engine, performance)
    single_run_instance.peer_arrival("normal", {})
    peer: Peer = next(iter(single_run_instance.peer_full_set))
    peer.order_pending_orderinfo_mapping.clear()

    # Preparing parameters
    expiration_value = 300
    settlement = ConcaveParameters(sensitivity=1.0, max_prob=0.0)
    cancellation = RandomParameter(prob=0.0)

    # Act.

    single_run_instance.order_arrival(
        target_peer=peer,
        order_type="default",
        expiration=expiration_value,
        settlement=settlement,
        cancellation=cancellation,
    )
    single_run_instance.order_arrival(
        target_peer=peer,
        order_type="nft",
        expiration=expiration_value,
        settlement=settlement,
        cancellation=cancellation,
    )

    # Assert.
    assert len(peer.order_pending_orderinfo_mapping) == 2
    order_iterator = iter(peer.order_pending_orderinfo_mapping)
    order_type_set = set()
    for _ in range(2):
        order = next(order_iterator)
        order_type_set.add(order.order_type)
        assert order.expiration == expiration_value
        assert order in single_run_instance.order_full_set

    assert "default" in order_type_set
    assert "nft" in order_type_set
    assert single_run_instance.latest_order_seq == 2


@pytest.mark.parametrize(
    "scenario, engine, performance",
    [(SCENARIO_SAMPLE, ENGINE_SAMPLE, PERFORMANCE_SAMPLE)],
)
def test_order_arrival__error(
    scenario: Scenario, engine: Engine, performance: Performance
) -> None:
    """
    This tests order_arrival() when the target peer does not exist.
    """
    # Arrange.

    # create the single_run instance and a peer.
    single_run_instance = SingleRun(scenario, engine, performance)
    peer: Peer = create_a_test_peer(scenario, engine)[0]
    peer.order_pending_orderinfo_mapping.clear()

    settlement = ConcaveParameters(sensitivity=1.0, max_prob=0.0)
    cancellation = RandomParameter(prob=0.0)

    # Act and Assert.
    with pytest.raises(ValueError, match="Cannot find target peer."):
        single_run_instance.order_arrival(
            target_peer=peer,
            order_type="default",
            expiration=300,
            settlement=settlement,
            cancellation=cancellation,
        )
