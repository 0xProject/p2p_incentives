"""
This module contains unit tests for operations_in_a_time_round().
"""

import random
import pytest

from single_run import SingleRun
from scenario import Scenario
from engine import Engine
from performance import Performance
from .__init__ import (
    SCENARIO_SAMPLE_1,
    ENGINE_SAMPLE,
    ENGINE_SAMPLE_STORE_SHARE_MUST_HAPPEN,
    PERFORMANCE_SAMPLE,
    fake_gauss,
    mock_random_choice,
)


@pytest.fixture(autouse=True)
def mock_or_fake_functions(monkeypatch) -> None:
    """
    This is a fixture function that mocks/fakes some functions for test functions to use.
    It is set to "autouse" so that every test function in this module will call it.
    """

    # Use a fake Gauss distribution, by returning the mean only.
    monkeypatch.setattr(random, "gauss", fake_gauss)
    # This is to mock random.choice(). Please refer to the explanation in mock_random_choice().
    monkeypatch.setattr(random, "choices", mock_random_choice)


def create_single_run_with_initial_peers(
    scenario: Scenario, engine: Engine, performance: Performance
) -> SingleRun:
    """
    Helper function to create a single run instance and call create_initial_peers_orders()
    function, return this instance.
    """
    single_run_instance = SingleRun(scenario, engine, performance)
    single_run_instance.create_initial_peers_orders()
    single_run_instance.cur_time = single_run_instance.scenario.birth_time_span
    return single_run_instance


@pytest.mark.parametrize(
    "scenario, engine, performance",
    [(SCENARIO_SAMPLE_1, ENGINE_SAMPLE, PERFORMANCE_SAMPLE)],
)
def test_operations_in_a_time_round__assert_order_number(
    scenario: Scenario, engine: Engine, performance: Performance
) -> None:

    """
    This is the unit test for operations_in_a_time_round().
    It asserts if the order number is correct after a time round of operations.
    """

    # Arrange.
    single_run_instance: SingleRun = create_single_run_with_initial_peers(
        scenario, engine, performance
    )
    initial_order_number = len(single_run_instance.order_full_set)

    # Act.

    # We will need to set the peer_dept_number to 0 to evaluate the order number change.
    # The reason for it is that if a peer departs and it is the only one that has a certain
    # order, then this order will disappear too. This is very hard to record.
    # Strictly speaking our unit test does not cover such case. However, we have already tested
    # such scenario in test_peer_departure.py so it should be okay.

    # We let the peer arrival number be the same as scenario.init_size, so that we expect the
    # order arrival number is also initial_order_number.

    order_arr_num = 39
    order_cancel_num = 19

    single_run_instance.operations_in_a_time_round(
        peer_arr_num=scenario.init_size,
        peer_dept_num=0,
        order_arr_num=order_arr_num,
        order_cancel_num=order_cancel_num,
    )

    assert (
        len(single_run_instance.order_full_set)
        == 2 * initial_order_number + order_arr_num - order_cancel_num
    )
    assert len(single_run_instance.peer_full_set) == 2 * scenario.init_size


@pytest.mark.parametrize(
    "scenario, engine, performance",
    [(SCENARIO_SAMPLE_1, ENGINE_SAMPLE, PERFORMANCE_SAMPLE)],
)
def test_operations_in_a_time_round__assert_peer_number_normal(
    scenario: Scenario, engine: Engine, performance: Performance
) -> None:
    """
    This is the unit test for operations_in_a_time_round().
    It asserts if the peer number is correct after a time round of operations.
    """

    # Arrange.
    single_run_instance: SingleRun = create_single_run_with_initial_peers(
        scenario, engine, performance
    )

    # Act.
    peer_arr_num = 37
    peer_dept_num = 5
    order_arr_num = 8
    order_cancel_num = 12

    single_run_instance.operations_in_a_time_round(
        peer_arr_num=peer_arr_num,
        peer_dept_num=peer_dept_num,
        order_arr_num=order_arr_num,
        order_cancel_num=order_cancel_num,
    )

    assert len(single_run_instance.peer_full_set) == scenario.init_size - 5 + 37


@pytest.mark.parametrize(
    "scenario, engine, performance",
    [(SCENARIO_SAMPLE_1, ENGINE_SAMPLE, PERFORMANCE_SAMPLE)],
)
def test_operations_in_a_time_round__assert_peer_number_all_peers_departed(
    scenario: Scenario, engine: Engine, performance: Performance
) -> None:

    """
    This is the unit test for operations_in_a_time_round().
    It asserts the scenario where all peers depart the system.
    """

    # Arrange.
    single_run_instance: SingleRun = create_single_run_with_initial_peers(
        scenario, engine, performance
    )

    # Act.

    peer_arr_num = 37
    order_arr_num = 8
    order_cancel_num = 12

    single_run_instance.operations_in_a_time_round(
        peer_arr_num=peer_arr_num,
        peer_dept_num=(scenario.init_size + 1),
        order_arr_num=order_arr_num,
        order_cancel_num=order_cancel_num,
    )

    assert len(single_run_instance.peer_full_set) == peer_arr_num


@pytest.mark.parametrize(
    "scenario, engine, performance",
    [(SCENARIO_SAMPLE_1, ENGINE_SAMPLE, PERFORMANCE_SAMPLE)],
)
def test_operations_in_a_time_round__assert_neighborhood(
    scenario: Scenario, engine: Engine, performance: Performance
) -> None:

    """
    This is the unit test for operations_in_a_time_round().
    It asserts the neighborhood connection establishment.
    """

    # Arrange.
    single_run_instance: SingleRun = create_single_run_with_initial_peers(
        scenario, engine, performance
    )

    # Act.

    single_run_instance.operations_in_a_time_round(
        peer_arr_num=37, peer_dept_num=5, order_arr_num=8, order_cancel_num=12
    )

    # Assert. For each peer, it has at least engine.neighbor_min neighbors, or all its neighbors
    # reach the maximal neighbor size.

    for peer in single_run_instance.peer_full_set:
        assert engine.neighbor_min <= len(
            peer.peer_neighbor_mapping
        ) <= engine.neighbor_max or all(
            (
                len(neighbor.peer_neighbor_mapping) == engine.neighbor_max
                for neighbor in peer.peer_neighbor_mapping
            )
        )


@pytest.mark.parametrize(
    "scenario, engine, performance",
    [(SCENARIO_SAMPLE_1, ENGINE_SAMPLE_STORE_SHARE_MUST_HAPPEN, PERFORMANCE_SAMPLE)],
)
def test_operations_in_a_time_round__assert_store_and_share_must_happen(
    scenario, engine, performance
) -> None:
    """
    This is the unit test for operations_in_a_time_round().
    It asserts the scenario where storing and sharing orders must happen.
    In order to do it, we pass a specific engine instance to it where batch == 1 and it forms
    a full mesh network; every peer will contribute to every neighbor.
    So finally, every peer will receive all orders in the network, either in its local storage (
    this is because store_orders() is called during the process) or pending table (this is because
    the peer may receive orders from some other peer that operates after it).
    """

    # Arrange.
    single_run_instance: SingleRun = create_single_run_with_initial_peers(
        scenario, engine, performance
    )

    # Act.
    single_run_instance.operations_in_a_time_round(
        peer_arr_num=0, peer_dept_num=0, order_arr_num=0, order_cancel_num=0
    )

    # Assert. For each peer, it should have received something in the pending table.
    for peer in single_run_instance.peer_full_set:
        assert len(peer.order_orderinfo_mapping) + len(
            peer.order_pending_orderinfo_mapping
        ) == len(single_run_instance.order_full_set)


@pytest.mark.parametrize(
    "scenario, engine, performance",
    [(SCENARIO_SAMPLE_1, ENGINE_SAMPLE_STORE_SHARE_MUST_HAPPEN, PERFORMANCE_SAMPLE)],
)
def test_operations_in_a_time_round__assert_store_and_share_might_happen(
    scenario: Scenario, engine: Engine, performance: Performance
) -> None:
    """
    This is the unit test for operations_in_a_time_round().
    It asserts the scenario where storing and sharing orders might happen, in the general case.
    """

    # Arrange.
    single_run_instance: SingleRun = create_single_run_with_initial_peers(
        scenario, engine, performance
    )

    # Act.
    single_run_instance.operations_in_a_time_round(
        peer_arr_num=3, peer_dept_num=5, order_arr_num=27, order_cancel_num=15
    )

    # Assert. There must be some peer that has received something from sharing of others.
    assert any(
        len(peer.order_orderinfo_mapping) + len(peer.order_pending_orderinfo_mapping)
        > single_run_instance.scenario.peer_type_property[
            peer.peer_type
        ].initial_orderbook_size.mean
        for peer in single_run_instance.peer_full_set
    )
