"""
This module contains unit tests for create_initial_peer_orders().

"""
import random
from typing import Dict
import pytest

from simulator import SingleRun
from .__init__ import (
    SCENARIO_SAMPLE_1,
    SCENARIO_SAMPLE_2,
    ENGINE_SAMPLE,
    PERFORMANCE_SAMPLE,
    mock_random_choice,
    fake_gauss
)


@pytest.mark.parametrize(
    "scenario, engine, performance",
    [
        (SCENARIO_SAMPLE_1, ENGINE_SAMPLE, PERFORMANCE_SAMPLE),
        (SCENARIO_SAMPLE_2, ENGINE_SAMPLE, PERFORMANCE_SAMPLE),
    ],
)
def test_create_initial_peers_orders(scenario, engine, performance, monkeypatch):
    """
    This is the unit test for function create_initial_peers_orders(). We test if the initial
    peers and orders are properly created.
    There are a lot of randomness here, and we fake/mock them.
    """

    # Arrange.

    # This is to mock random.choice(). Please refer to the explanation in mock_random_choice().
    monkeypatch.setattr(random, "choices", mock_random_choice)
    # This is to fake random.gauss() by returning the integer of mean.
    monkeypatch.setattr(random, "gauss", fake_gauss)

    # Act.
    # create the instance and run create_initial_peers_orders()
    single_run_instance = SingleRun(scenario, engine, performance)
    single_run_instance.create_initial_peers_orders()

    # Assert.

    # First of all, calculate the expected number of peers in each type. This is non-trivial and
    # it follows the logic in mock_random_choice().
    expected_peer_nums: Dict[str, int] = dict()
    for peer_type in scenario.peer_type_property:
        expected_peer_nums[peer_type] = int(
            scenario.init_size * scenario.peer_type_property[peer_type].ratio
        )

    if sum(num for num in expected_peer_nums.values()) < scenario.init_size:
        max_peer_type = "normal"
        for peer_type in scenario.peer_type_property:
            if (
                scenario.peer_type_property[peer_type].ratio
                > scenario.peer_type_property[max_peer_type].ratio
            ):
                max_peer_type = peer_type
        expected_peer_nums[max_peer_type] += scenario.init_size - sum(
            num for num in expected_peer_nums.values()
        )

    # Assert the total number of peers.
    assert len(single_run_instance.peer_full_set) == scenario.init_size
    # Assert the peer numbers of each type.
    for peer_type in scenario.peer_type_property:
        assert (
            len(single_run_instance.peer_type_set_mapping[peer_type])
            == expected_peer_nums[peer_type]
        )

    # Assert each peer's attribute and the orders they own
    for peer in single_run_instance.peer_full_set:
        assert peer.birth_time in range(0, scenario.birth_time_span)
        assert len(peer.order_orderinfo_mapping) == int(
            scenario.peer_type_property[peer.peer_type].initial_orderbook_size.mean
        )
        for order in peer.order_orderinfo_mapping:
            assert order.creator is peer

    # Assert the peer sequence number update
    assert single_run_instance.latest_peer_seq == scenario.init_size

    # Calculate the expected order sequence number update
    expected_order_nums = 0
    for peer_type in scenario.peer_type_property:
        expected_order_nums += expected_peer_nums[peer_type] * int(
            scenario.peer_type_property[peer_type].initial_orderbook_size.mean
        )
    # Assert the order sequence number update
    assert single_run_instance.latest_order_seq == expected_order_nums
