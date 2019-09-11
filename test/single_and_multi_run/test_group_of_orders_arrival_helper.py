"""
This module contains unit tests for group_of_orders_arrival_helper().
"""
import random
from typing import List
import pytest

from simulator import SingleRun
from engine import Engine
from performance import Performance
from scenario import Scenario

from .__init__ import (
    SCENARIO_SAMPLE_1,
    SCENARIO_SAMPLE_2,
    ENGINE_SAMPLE,
    PERFORMANCE_SAMPLE,
    mock_random_choice,
    fake_gauss,
)


@pytest.mark.parametrize(
    "scenario, engine, performance, num_arrival",
    [
        (
            SCENARIO_SAMPLE_1,
            ENGINE_SAMPLE,
            PERFORMANCE_SAMPLE,
            SCENARIO_SAMPLE_1.init_size,
        ),
        (
            SCENARIO_SAMPLE_2,
            ENGINE_SAMPLE,
            PERFORMANCE_SAMPLE,
            SCENARIO_SAMPLE_2.init_size,
        ),
    ],
)
def test_group_of_orders_arrival_helper(
    scenario: Scenario,
    engine: Engine,
    performance: Performance,
    num_arrival: int,
    monkeypatch,
) -> None:
    """
    This is the unit test for function group_of_peers_arrival_helper(). We test if the group of
    peers and their orders are properly created.
    There are a lot of randomness here, and we fake/mock them.
    """

    # Arrange.

    # This is to mock random.choice(). Please refer to the explanation in mock_random_choice().
    monkeypatch.setattr(random, "choices", mock_random_choice)
    # This is to fake random.gauss() by returning the integer of mean.
    monkeypatch.setattr(random, "gauss", fake_gauss)

    # create the instance and 10 peers.
    total_num_peers = 10
    single_run_instance = SingleRun(scenario, engine, performance)
    for _ in range(total_num_peers):
        single_run_instance.peer_arrival("normal", 0)

    single_run_instance.order_full_set.clear()

    # Manually set the size of the peers' initial orderbook size.
    # This will serve as a weight to distribute the orders.
    # It is: [20, 10, 10, 10, 10, 5, 5, 5, 0, 0]
    peer_list = list(single_run_instance.peer_full_set)
    peer_list[0].init_orderbook_size = 20
    for peer in peer_list[1:5]:
        peer.init_orderbook_size = 10
    for peer in peer_list[5:8]:
        peer.init_orderbook_size = 5
    for peer in peer_list[8:10]:
        peer.init_orderbook_size = 0

    # Act.
    single_run_instance.group_of_orders_arrival_helper(num_arrival)

    # Assert.
    assert len(single_run_instance.order_full_set) == num_arrival

    # First of all, calculate the expected number of orders that each peer will get. This is
    # non-trivial and it follows the logic in mock_random_choice().

    max_init_size_peer_id = 0
    sum_orderbook_size = sum(peer.init_orderbook_size for peer in peer_list)
    expected_order_nums: List[int] = [0] * len(peer_list)

    for idx in range(total_num_peers):
        expected_order_nums[idx] = int(
            num_arrival * peer_list[idx].init_orderbook_size / sum_orderbook_size
        )
        if (
            peer_list[idx].init_orderbook_size
            > peer_list[max_init_size_peer_id].init_orderbook_size
        ):
            max_init_size_peer_id = idx

    if sum(expected_order_nums) < num_arrival:
        expected_order_nums[max_init_size_peer_id] += num_arrival - sum(
            expected_order_nums
        )

    # Assert the total number of orders created.
    assert len(single_run_instance.order_full_set) == num_arrival
    # Assert the number of orders each peer has.
    for idx in range(total_num_peers):
        assert (
            len(peer_list[idx].order_pending_orderinfo_mapping)
            == expected_order_nums[idx]
        )

    # Assert the order sequence number update
    assert single_run_instance.latest_order_seq == num_arrival
