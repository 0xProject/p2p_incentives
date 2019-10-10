"""
This module contains unit tests of store_first().
"""

from typing import List
import pytest

from node import Peer
from message import Order, OrderInfo
from scenario import Scenario
from engine import Engine

import engine_candidates

from ..__init__ import (
    ENGINE_SAMPLE,
    SCENARIO_SAMPLE,
    create_a_test_order,
    create_test_peers,
    create_a_test_peer,
)


@pytest.mark.parametrize("scenario,engine", [(SCENARIO_SAMPLE, ENGINE_SAMPLE)])
def test_store_first__multi_orderinfo(scenario: Scenario, engine: Engine) -> None:
    """
    Unit test of multiple orderinfo instances from different neighbors, in the pending table
    """
    # Arrange.

    peer: Peer = create_a_test_peer(scenario, engine)[0]
    order: Order = create_a_test_order(scenario)
    neighbor_list: List[Peer] = create_test_peers(scenario, engine, 2)

    for neighbor in neighbor_list:
        neighbor.receive_order_external(order)
        # Manually set verification done
        neighbor.send_orders_to_on_chain_check(neighbor.local_clock)
        neighbor.store_orders()
        peer.add_neighbor(neighbor)
        neighbor.add_neighbor(peer)

        peer.receive_order_internal(neighbor, order)

    # Act.
    engine_candidates.store_first(peer)

    # Assert.

    orderinfo_list: List[OrderInfo] = peer.order_pending_orderinfo_mapping[order]
    for orderinfo in orderinfo_list:
        if orderinfo.prev_owner == neighbor_list[0]:
            assert orderinfo.storage_decision is True
        else:
            assert orderinfo.storage_decision is False


@pytest.mark.parametrize("scenario,engine", [(SCENARIO_SAMPLE, ENGINE_SAMPLE)])
def test_store_first__single_orderinfo(scenario: Scenario, engine: Engine) -> None:
    """
    Unit test of multiple orderinfo instances from different neighbors, in the pending table
    """

    # Arrange.
    peer: Peer = create_a_test_peer(scenario, engine)[0]
    order: Order = create_a_test_order(scenario)
    peer.receive_order_external(order)

    # Manually set verification done
    peer.send_orders_to_on_chain_check(peer.local_clock)

    # Act.
    engine_candidates.store_first(peer)

    # Assert.
    orderinfo_list: List[OrderInfo] = peer.order_pending_orderinfo_mapping[order]
    assert orderinfo_list[0].storage_decision is True
