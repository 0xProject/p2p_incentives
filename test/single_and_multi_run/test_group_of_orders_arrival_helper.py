"""
This module contains unit tests of group_of_orders_arrival_helper().
"""
import random
import pytest

from single_run import SingleRun
from engine import Engine
from performance import Performance
from scenario import Scenario

from ..__init__ import SCENARIO_SAMPLE, ENGINE_SAMPLE, PERFORMANCE_SAMPLE
from .__init__ import mock_random_choice, fake_gauss


NUM_ORDERS_TO_ARRIVE = 240


@pytest.mark.parametrize(
    "scenario, engine, performance, num_arrival",
    [(SCENARIO_SAMPLE, ENGINE_SAMPLE, PERFORMANCE_SAMPLE, NUM_ORDERS_TO_ARRIVE)],
)
def test_group_of_orders_arrival_helper(
    scenario: Scenario,
    engine: Engine,
    performance: Performance,
    num_arrival: int,
    monkeypatch,
) -> None:
    """
    This tests group_of_orders_arrival_helper().
    We test if the group of orders are properly created.
    """

    # pylint: disable=too-many-locals
    # This test function is a bit long but still fine.

    # Arrange.

    # Mock/fake functions. Similar to test_group_of_peers_arrival_helper.py.
    monkeypatch.setattr(random, "choices", mock_random_choice)
    monkeypatch.setattr(random, "gauss", fake_gauss)

    # create the instance and 10 normal peers and 5 free rider.
    total_num_normal_peers = 20
    total_num_free_riders = 5
    single_run_instance = SingleRun(scenario, engine, performance)
    for _ in range(total_num_normal_peers):
        single_run_instance.peer_arrival("normal", {})
    for _ in range(total_num_free_riders):
        single_run_instance.peer_arrival("free_rider", {})

    normal_peer_list = list(single_run_instance.peer_type_set_mapping["normal"])
    free_rider_list = list(single_run_instance.peer_type_set_mapping["free_rider"])

    single_run_instance.order_full_set.clear()

    # Act.
    single_run_instance.group_of_orders_arrival_helper(num_arrival)

    # Assert.
    assert len(single_run_instance.order_full_set) == num_arrival

    # First of all, calculate the expected number of orders that each peer will get. This is
    # non-trivial and it follows the logic in mock_random_choice().

    for idx in range(total_num_normal_peers):
        assert (
            len(normal_peer_list[idx].order_pending_orderinfo_mapping)
            == NUM_ORDERS_TO_ARRIVE / total_num_normal_peers
        )
        num_default_order = sum(
            1
            for order in normal_peer_list[idx].order_pending_orderinfo_mapping
            if order.order_type == "default"
        )
        sum_of_weights = sum(
            value.mean
            for value in scenario.peer_type_property[
                "normal"
            ].initial_orderbook_size_dict.values()
        )
        assert (
            num_default_order
            == len(normal_peer_list[idx].order_pending_orderinfo_mapping)
            * scenario.peer_type_property["normal"]
            .initial_orderbook_size_dict["default"]
            .mean
            / sum_of_weights
        )
        num_nft = sum(
            1
            for order in normal_peer_list[idx].order_pending_orderinfo_mapping
            if order.order_type == "nft"
        )
        assert (
            num_nft
            == len(normal_peer_list[idx].order_pending_orderinfo_mapping)
            * scenario.peer_type_property["normal"]
            .initial_orderbook_size_dict["nft"]
            .mean
            / sum_of_weights
        )

    # Assert free riders.
    for peer in free_rider_list:
        assert not peer.order_pending_orderinfo_mapping

    # Assert the order sequence number update
    assert single_run_instance.latest_order_seq == num_arrival
