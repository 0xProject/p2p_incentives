"""
This module contains unit tests for group_of_peers_arrival_helper().
"""

import random
from typing import Dict, cast
import pytest

from single_run import SingleRun
from engine import Engine
from performance import Performance
from scenario import Scenario
from data_types import PeerTypeName

from ..__init__ import SCENARIO_SAMPLE, ENGINE_SAMPLE
from .__init__ import (
    SCENARIO_SAMPLE_NON_INT,
    PERFORMANCE_SAMPLE,
    mock_random_choice,
    fake_gauss,
)


@pytest.mark.parametrize(
    "scenario, engine, performance, num_arrival",
    [
        (SCENARIO_SAMPLE, ENGINE_SAMPLE, PERFORMANCE_SAMPLE, SCENARIO_SAMPLE.init_size),
        (
            SCENARIO_SAMPLE_NON_INT,
            ENGINE_SAMPLE,
            PERFORMANCE_SAMPLE,
            SCENARIO_SAMPLE_NON_INT.init_size,
        ),
    ],
)
def test_group_of_peers_arrival_helper(
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

    # Act.
    # create the instance and run group_of_peers_arrival_helper()
    single_run_instance = SingleRun(scenario, engine, performance)
    single_run_instance.group_of_peers_arrival_helper(num_arrival)

    # Assert.

    # First of all, calculate the expected number of peers in each type. This is non-trivial and
    # it follows the logic in mock_random_choice().

    max_peer_type: PeerTypeName = "normal"

    expected_peer_nums: Dict[str, int] = dict()
    for peer_type in scenario.peer_type_property:
        peer_type = cast(PeerTypeName, peer_type)
        if (
            scenario.peer_type_property[peer_type].ratio
            > scenario.peer_type_property[max_peer_type].ratio
        ):
            max_peer_type = peer_type
        expected_peer_nums[peer_type] = int(
            num_arrival * scenario.peer_type_property[peer_type].ratio
        )

    if sum(num for num in expected_peer_nums.values()) < num_arrival:
        expected_peer_nums[max_peer_type] += num_arrival - sum(
            num for num in expected_peer_nums.values()
        )

    # Assert the total number of peers created.
    assert len(single_run_instance.peer_full_set) == num_arrival
    # Assert the peer numbers of each type.
    for peer_type in scenario.peer_type_property:
        peer_type = cast(PeerTypeName, peer_type)
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
    assert single_run_instance.latest_peer_seq == num_arrival

    # Calculate the expected order sequence number update
    expected_order_nums = 0
    for peer_type in scenario.peer_type_property:
        peer_type = cast(PeerTypeName, peer_type)
        expected_order_nums += expected_peer_nums[peer_type] * int(
            scenario.peer_type_property[peer_type].initial_orderbook_size.mean
        )
    # Assert the order sequence number update
    assert single_run_instance.latest_order_seq == expected_order_nums
