"""
This class contains all test functions for all_new_selected_old()
"""

from typing import NamedTuple, Tuple, List
import pytest
from node import Peer
from message import Order
from scenario import Scenario
from engine import Engine
import engine_candidates

from ..__init__ import (
    SCENARIO_SAMPLE,
    ENGINE_SAMPLE,
    create_a_test_peer,
    create_test_orders,
)

# Cases for the test function.
# Basic setting: We create a peer (with 5 initial orders) and a set of other orders (total number
# is `total`). We manually clear the new_order_set for the peer, and add some orders into the
# new_order_set (total number is `new`). We set the max_share and old_prob as defined by function
# `all_new_selected_old()`. Expected_result is a tuple of three elements: total number of orders
# selected; total number of new orders selected; and total number of old orders selected.
#
# There are three cases that we consider:
# Case 1: The peer has a total of (12+5=17) orders, of which 8 are new. The maximal share number
# is 6, so the total number of orders selected is 6 and all of them are new.
#
# Case 2: The peer has a total of (12+5=17) orders, of which 4 are new. The maximal share number
# is 6, so the total number of orders selected is 6, of which 4 of them are new and 2 are old (
# note that the old_prob = 0.5, but we cannot select so many old orders due to limit).
#
# Case 3: The peer has a total of (12+5=17) orders, of which 4 are new. The maximal share number
# is 200, so all new orders (4) are selected; for the 13 old orders 13*0.5=6 are selected,
# and the total number of orders selected is 10.


class CaseType(NamedTuple):
    """
    Data type for cases for test_all_new_selected_old.py.
    """

    scenario: Scenario
    engine: Engine
    total: int
    new: int
    max_share: int
    old_prob: float
    expected_result: Tuple[int, int, int]


# Please refer to explanations above for meanings of the cases.

CASE_1 = CaseType(
    scenario=SCENARIO_SAMPLE,
    engine=ENGINE_SAMPLE,
    total=12,
    new=8,
    max_share=6,
    old_prob=0.5,
    expected_result=(6, 6, 0),
)

CASE_2 = CaseType(
    scenario=SCENARIO_SAMPLE,
    engine=ENGINE_SAMPLE,
    total=12,
    new=4,
    max_share=6,
    old_prob=0.5,
    expected_result=(6, 4, 2),
)

CASE_3 = CaseType(
    scenario=SCENARIO_SAMPLE,
    engine=ENGINE_SAMPLE,
    total=12,
    new=4,
    max_share=200,
    old_prob=0.5,
    expected_result=(10, 4, 6),
)


@pytest.mark.parametrize(
    "scenario,engine,total,new,max_share,old_prob,expected_results",
    [CASE_1, CASE_2, CASE_3],
)
def test_all_new_selected_old__many_new(
    scenario: Scenario,
    engine: Engine,
    total: int,
    new: int,
    max_share: int,
    old_prob: float,
    expected_results: Tuple[int, int, int],
) -> None:
    """
    Unit tests for all_new_selected_old()
    """

    # Arrange.

    # create peer and orders. The peer should have (initial + total) orders for now.
    peer: Peer = create_a_test_peer(scenario, engine)[0]
    order_list: List[Order] = create_test_orders(scenario, total)
    for order in order_list:
        peer.receive_order_external(order)
    peer.store_orders()

    # Manually set orders as new ones.
    peer.new_order_set.clear()
    for order in order_list[:new]:
        peer.new_order_set.add(order)

    # Act.
    selected_order_set = engine_candidates.share_all_new_selected_old(
        max_to_share=max_share, old_prob=old_prob, peer=peer
    )

    # Assert.
    # Assert total number of orders selected
    assert len(selected_order_set) == expected_results[0]
    # Assert new orders selected.
    assert len(selected_order_set & peer.new_order_set) == expected_results[1]
    # Assert old orders selected
    assert (
        len(
            selected_order_set
            & (set(peer.order_orderinfo_mapping) - peer.new_order_set)
        )
        == expected_results[2]
    )
