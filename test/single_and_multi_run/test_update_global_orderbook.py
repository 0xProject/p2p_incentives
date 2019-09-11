"""
This module contains unit tests for update_global_orderbook().
"""

from typing import Tuple
import pytest

from single_run import SingleRun
from node import Peer
from message import Order
from scenario import Scenario
from engine import Engine
from performance import Performance
from ..__init__ import SCENARIO_SAMPLE, ENGINE_SAMPLE
from .__init__ import PERFORMANCE_SAMPLE


def create_an_instance_with_one_peer_one_order(
    scenario: Scenario, engine: Engine, performance: Performance
) -> Tuple[SingleRun, Peer, Order]:
    """
    This is a helper function. It creates a single_run instance, with a peer and an order.
    """

    # create a single_run instance and a peer
    single_run_instance = SingleRun(scenario, engine, performance)
    single_run_instance.peer_arrival("normal", 0)
    peer: Peer = next(iter(single_run_instance.peer_full_set))
    peer.order_pending_orderinfo_mapping.clear()

    # create an order and let it be held by peer.
    # 300 is arbitrarily set. As long as it is large, it is okay.
    single_run_instance.order_arrival(target_peer=peer, expiration=300)
    order: Order = next(iter(single_run_instance.order_full_set))

    return single_run_instance, peer, order


@pytest.mark.parametrize(
    "scenario, engine, performance",
    [(SCENARIO_SAMPLE, ENGINE_SAMPLE, PERFORMANCE_SAMPLE)],
)
def test_update_global_orderbook__active_order(
    scenario: Scenario, engine: Engine, performance: Performance
) -> None:
    """
    This is to test how the function treats an active order. Nothing should happen.
    """

    # Arrange.
    single_run_instance, peer, order = create_an_instance_with_one_peer_one_order(
        scenario, engine, performance
    )

    # Act.
    single_run_instance.update_global_orderbook()

    # Assert
    assert order in single_run_instance.order_full_set
    assert order in single_run_instance.order_type_set_mapping["default"]
    assert order in peer.order_pending_orderinfo_mapping


@pytest.mark.parametrize(
    "scenario, engine, performance",
    [(SCENARIO_SAMPLE, ENGINE_SAMPLE, PERFORMANCE_SAMPLE)],
)
def test_update_global_orderbook__order_no_count(
    scenario: Scenario, engine: Engine, performance: Performance
) -> None:
    """
    This is to test if an order does not have any holder or hesitator. Should remove.
    """

    # Arrange.
    single_run_instance, _peer, order = create_an_instance_with_one_peer_one_order(
        scenario, engine, performance
    )

    # manually remove the order holders and hesitators
    order.hesitators.clear()

    # Act.
    single_run_instance.update_global_orderbook()

    # Assert
    assert order not in single_run_instance.order_full_set
    assert order not in single_run_instance.order_type_set_mapping["default"]


@pytest.mark.parametrize(
    "scenario, engine, performance",
    [(SCENARIO_SAMPLE, ENGINE_SAMPLE, PERFORMANCE_SAMPLE)],
)
def test_update_global_orderbook__expired(
    scenario: Scenario, engine: Engine, performance: Performance
) -> None:
    """
    This is to test when an order expires.
    """

    # Arrange.
    single_run_instance, peer, order = create_an_instance_with_one_peer_one_order(
        scenario, engine, performance
    )

    # manually change expiration, birth time, etc. Let every order expire.
    single_run_instance.cur_time = 100
    order.birth_time = 50
    order.expiration = 30

    # Act.
    single_run_instance.update_global_orderbook()

    # Assert
    assert order not in single_run_instance.order_full_set
    assert order not in single_run_instance.order_type_set_mapping["default"]
    assert order not in peer.order_pending_orderinfo_mapping
    assert order not in peer.order_orderinfo_mapping


@pytest.mark.parametrize(
    "scenario, engine, performance",
    [(SCENARIO_SAMPLE, ENGINE_SAMPLE, PERFORMANCE_SAMPLE)],
)
def test_update_global_orderbook__settled(
    scenario: Scenario, engine: Engine, performance: Performance
) -> None:
    """
    This is to test when an order is settled.
    """

    # Arrange.
    single_run_instance, peer, order = create_an_instance_with_one_peer_one_order(
        scenario, engine, performance
    )

    # manually change is_settled
    order.is_settled = True

    # Act.
    single_run_instance.update_global_orderbook()

    # Assert
    assert order not in single_run_instance.order_full_set
    assert order not in single_run_instance.order_type_set_mapping["default"]
    assert order not in peer.order_pending_orderinfo_mapping
    assert order not in peer.order_orderinfo_mapping


@pytest.mark.parametrize(
    "scenario, engine, performance",
    [(SCENARIO_SAMPLE, ENGINE_SAMPLE, PERFORMANCE_SAMPLE)],
)
def test_update_global_orderbook__canceled(
    scenario: Scenario, engine: Engine, performance: Performance
) -> None:
    """
    This is to test when an order is canceled.
    """

    # Arrange.
    single_run_instance, peer, order = create_an_instance_with_one_peer_one_order(
        scenario, engine, performance
    )

    # Act.
    single_run_instance.update_global_orderbook([order])

    # Assert
    assert order not in single_run_instance.order_full_set
    assert order not in single_run_instance.order_type_set_mapping["default"]
    assert order not in peer.order_pending_orderinfo_mapping
    assert order not in peer.order_orderinfo_mapping
