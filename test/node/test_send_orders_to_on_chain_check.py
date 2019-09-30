"""
This module contains unit tests of send_orders_to_on_chain_check().
"""

from typing import List
import pytest
from message import Order
from node import Peer
from ..__init__ import (
    SCENARIO_SAMPLE,
    ENGINE_SAMPLE,
    create_a_test_peer,
    create_test_orders,
)


@pytest.mark.parametrize("scenario,engine", [(SCENARIO_SAMPLE, ENGINE_SAMPLE)])
def test_send_orders_to_on_chain_check__new_entry(scenario, engine) -> None:
    """
    This function is the unit test of send_orders_to_on_chain_check(), when the
    peer.verification_time_orders_mapping[new_entry] does not exist.
    """

    # Arrange.
    my_peer: Peer = create_a_test_peer(scenario, engine)[0]
    order_list: List[Order] = create_test_orders(scenario, 7)
    # let the first three orders be in my_peer.verification_time_orders_mapping[0]
    my_peer.verification_time_orders_mapping[0] += order_list[0:3]
    # let the rest four orders be in my_peer.verification_time_orders_mapping[8]
    my_peer.verification_time_orders_mapping[8] = order_list[3:7]

    # Act.
    # now send orders to on-chain check and it is supposed to be finished at time 6.
    my_peer.send_orders_to_on_chain_check(6)

    # Assert.
    for order in order_list[0:3]:
        assert order in my_peer.verification_time_orders_mapping[6]

    for order in order_list[3:7]:
        assert order in my_peer.verification_time_orders_mapping[8]

    assert not my_peer.verification_time_orders_mapping[0]


@pytest.mark.parametrize("scenario,engine", [(SCENARIO_SAMPLE, ENGINE_SAMPLE)])
def test_send_orders_to_on_chain_check__existing_entry(scenario, engine) -> None:
    """
    This function is the unit test of send_orders_to_on_chain_check(), when the
    peer.verification_time_orders_mapping[new_entry] already exists.
    """

    # Arrange.
    my_peer: Peer = create_a_test_peer(scenario, engine)[0]
    order_list: List[Order] = create_test_orders(scenario, 7)
    # let the first three orders be in my_peer.verification_time_orders_mapping[0]
    my_peer.verification_time_orders_mapping[0] += order_list[0:3]
    # let the rest four orders be in my_peer.verification_time_orders_mapping[8]
    my_peer.verification_time_orders_mapping[6] = order_list[3:7]

    # Act.
    # now send orders to on-chain check and it is supposed to be finished at time 6.
    my_peer.send_orders_to_on_chain_check(6)

    # Assert.
    for order in order_list:
        assert order in my_peer.verification_time_orders_mapping[6]
    assert not my_peer.verification_time_orders_mapping[0]
