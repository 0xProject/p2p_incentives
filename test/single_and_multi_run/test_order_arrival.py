"""
This module contains unit tests for order_arrival().
"""

import pytest

from scenario import Scenario
from engine import Engine
from performance import Performance
from node import Peer

from simulator import SingleRun
from .__init__ import (
    SCENARIO_SAMPLE_1,
    ENGINE_SAMPLE,
    PERFORMANCE_SAMPLE,
    create_a_test_peer,
)


@pytest.mark.parametrize(
    "scenario, engine, performance",
    [(SCENARIO_SAMPLE_1, ENGINE_SAMPLE, PERFORMANCE_SAMPLE)],
)
def test_order_arrival__normal(
    scenario: Scenario, engine: Engine, performance: Performance
) -> None:
    """
    This is to test function order_arrival().
    """
    # Arrange.

    # create the single_run instance and a peer.
    single_run_instance = SingleRun(scenario, engine, performance)
    single_run_instance.peer_arrival("normal", 0)
    peer: Peer = next(iter(single_run_instance.peer_full_set))
    peer.order_pending_orderinfo_mapping.clear()

    # Act.
    single_run_instance.order_arrival(target_peer=peer, expiration=300)

    # Assert.
    assert len(peer.order_pending_orderinfo_mapping) == 1
    order = next(iter(peer.order_pending_orderinfo_mapping))
    assert order.expiration == 300
    assert order in single_run_instance.order_full_set
    assert single_run_instance.latest_order_seq == 1


@pytest.mark.parametrize(
    "scenario, engine, performance",
    [(SCENARIO_SAMPLE_1, ENGINE_SAMPLE, PERFORMANCE_SAMPLE)],
)
def test_order_arrival__error(
    scenario: Scenario, engine: Engine, performance: Performance
) -> None:
    """
    This is to test function order_arrival().
    """
    # Arrange.

    # create the single_run instance and a peer.
    single_run_instance = SingleRun(scenario, engine, performance)
    peer: Peer = create_a_test_peer(scenario, engine)[0]
    peer.order_pending_orderinfo_mapping.clear()

    # Act and Assert.
    with pytest.raises(ValueError, match="Cannot find target peer."):
        single_run_instance.order_arrival(target_peer=peer, expiration=300)
