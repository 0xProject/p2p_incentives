"""
This module contains the class Engine only.
"""

from typing import Set, TYPE_CHECKING, cast
import engine_candidates
from data_types import (
    EngineParameters,
    EngineOptions,
    PreferenceOption,
    PriorityOption,
    ExternalOption,
    InternalOption,
    StoreOption,
    ShareOption,
    ScoreOption,
    BeneficiaryOption,
    RecommendationOption,
    AllNewSelectedOld,
    Weighted,
    TitForTat,
    Preference,
    Priority,
)

if TYPE_CHECKING:
    from node import Peer, Neighbor
    from message import Order, OrderInfo


class Engine:

    """
    The class Engine describes the design space. By choosing a specific option we refer to a
    particular design choice.
    They include our possible choices on neighbor establishment, order operations and incentives,
    scoring system, etc.
    Such choices are viable, and one can change any/some of them to test the performance.
    Later the Simulator class will call methods from this Engine class for a particular
    realization of implementation.
    """

    def __init__(self, parameters: EngineParameters, options: EngineOptions) -> None:

        # unpacking parameters

        # batch is the length of a batch period.
        # Recall that a peer runs its order storing and sharing algorithms only at the end of a
        # batch period. A batch period contains multiple time rounds.

        self.batch: int = parameters.batch_parameter

        # topology parameters: maximal/minimal size of neighborhood
        self.neighbor_max: int = parameters.topology_parameters.max_neighbor_size
        self.neighbor_min: int = parameters.topology_parameters.min_neighbor_size

        # incentive related parameters: length of the score sheet, reward a-e, penalty a-b
        # reward a-e:
        # a: sharing an order already in my local storage, shared by the same peer
        # b: sharing an order already in my local storage, shared by a different peer
        # c: sharing an order that I accepted to pending table, but I don't store finally
        # d: sharing an order I decide to store
        # e: for sharing an order I have multiple copies in the pending table and decided
        #    to store a copy from someone else
        # penalty a-b:
        # a: sharing an order that I have no interest to accept to the pending table
        # b: sharing an identical and duplicate order within the same batch period

        self.score_length: int = parameters.incentive_parameters.length
        self.reward_a: float = parameters.incentive_parameters.reward_a
        self.reward_b: float = parameters.incentive_parameters.reward_b
        self.reward_c: float = parameters.incentive_parameters.reward_c
        self.reward_d: float = parameters.incentive_parameters.reward_d
        self.reward_e: float = parameters.incentive_parameters.reward_e
        self.penalty_a: float = parameters.incentive_parameters.penalty_a
        self.penalty_b: float = parameters.incentive_parameters.penalty_b

        # Unpacking options. They specify a choice on a function implementation.
        # Each option argument is of type TypedDict. It must contain a key 'method' to specify
        # which function to call. For example, if beneficiary_option['method'] == 'tit_for_tat',
        # then tit-for-tat algorithm is called for neighbor selection.
        # If a particular function realization needs more parameters, their values are specified by
        # other keys in the corresponding option argument, which is an inherited TypedDict from the
        # base one. For example, TitForTat is inherited from BeneficiaryOption. Please refer to
        # data_types module for details.
        # In what follows, the methods in this class will check "method" first to decide
        # which function in engine_candidates to call, and then pass the rest parameters to the
        # function called.

        self.preference_option: PreferenceOption = options.preference_option
        self.priority_option: PriorityOption = options.priority_option
        self.external_option: ExternalOption = options.external_option
        self.internal_option: InternalOption = options.internal_option
        self.store_option: StoreOption = options.store_option
        self.share_option: ShareOption = options.share_option
        self.score_option: ScoreOption = options.score_option
        self.beneficiary_option: BeneficiaryOption = options.beneficiary_option
        self.rec_option: RecommendationOption = options.rec_option

    def set_preference_for_neighbor(
        self,
        neighbor: "Neighbor",
        peer: "Peer",
        master: "Peer",
        preference: Preference = None,
    ) -> None:
        """
        This method helps a peer to set a preference to one of its neighbor.
        A preference represents this peer's attitude towards this neighbor (e.g., friend or foe).
        :param neighbor: the neighbor instance for this neighbor
        :param peer: the peer instance for this neighbor
        :param master: the peer instance who wants to set the preference to the neighbor
        :param preference: an optional argument in case the master node already knows the value
        to set. If preference is not given, it is None by default and the method will decide the
        value to set based on other arguments.
        :return: None
        """
        if self.preference_option["method"] == "Passive":
            engine_candidates.set_preference_passive(neighbor, peer, master, preference)
        else:
            raise ValueError(
                "No such option to set preference: {}".format(
                    self.preference_option["method"]
                )
            )

    def set_priority_for_orderinfo(
        self,
        orderinfo: "OrderInfo",
        order: "Order",
        master: "Peer",
        priority: Priority = None,
    ) -> None:
        """
        This method sets a priority for an orderinfo instance.
        A peer can call this function to manually set a priority value to any orderinfo
        instance that is accepted into his pending table or stored in the local storage.
        :param orderinfo: the orderinfo instance of the order to be set a priority
        :param order: the order instance of the order to be set a priority
        :param master: the peer instance who wants to set the priority
        :param priority: an optional argument in case the master node already knows the value to
        set.
        If priority is not given, it is None by default and the method will decide the
        value to set based on other arguments.
        :return: None
        """
        if self.priority_option["method"] == "Passive":
            engine_candidates.set_priority_passive(orderinfo, order, master, priority)
        else:
            raise ValueError(
                "No such option to set priority: {}".format(
                    self.priority_option["method"]
                )
            )

    def should_accept_external_order(self, _receiver: "Peer", _order: "Order") -> bool:
        """
        This method determines whether to accept an external order into the pending table.
        :param _receiver: the peer instance of the node who is supposed to receive this order
        :param _order: the order instance
        :return: True if the node accepts this order, or False otherwise
        Note: right now, we only have a naive implementation that accepts everything, so the input
        arguments are not useful so they start with an underline. Later, one may need to delete
        the underline.
        """
        if self.external_option["method"] == "Always":
            return True
        raise ValueError(
            "No such option to receive external orders: {}".format(
                self.external_option["method"]
            )
        )

    def should_accept_internal_order(
        self, _receiver: "Peer", _sender: "Peer", _order: "Order"
    ) -> bool:
        """
        This method determines whether to accept an internal order into the pending table.
        :param _receiver: same as the above method
        :param _sender: the peer instance of the node who wants to send this order
        :param _order: same as the above method
        :return: same as the above method
        Note: Underline issue same as the above method.
        """
        if self.internal_option["method"] == "Always":
            return True
        raise ValueError(
            "No such option to receive internal orders: {}".format(
                self.internal_option["method"]
            )
        )

    def store_or_discard_orders(self, peer: "Peer") -> None:
        """
        This method is for a peer to determine whether to store each orderinfo
        in the pending table to the local storage, or discard it.
        Need to make sure that for each order, at most one orderinfo instance is stored.
        However, there is no self-check for this condition in the method itself.
        The check will be done in the Peer's method store_orders().
        :param peer: the peer to make the decision
        :return: None. The decision is recorded in Orderinfo.storage_decision.
        """
        if self.store_option["method"] == "First":
            engine_candidates.store_first(peer)
        else:
            raise ValueError(
                "No such option to store orders: {}".format(self.store_option["method"])
            )

    def find_orders_to_share(self, peer: "Peer") -> Set["Order"]:
        """
        This method determines the set of orders to share for this peer.
        :param peer: the peer to make the decision
        :return: the set of orders to share
        """
        if self.share_option["method"] == "AllNewSelectedOld":
            # in such case, self.share_option must be a sub-type inherited from ShareOption,
            # and this subtype is called AllNewSelectedOld. We have stated in the type definition
            # that we manually enforce the name of this sub-type (AllNewSelectedOld) is exactly
            # the same as the value part of "method".
            # Due to the lack of implementation of isinstance() function for TypedDict, we can't
            # judge the exact type of this sub-type by checking it type. So we use the duplicate
            # information (name of the sub-type and the value of "method" is the same) for judgment.
            # We read the "method" field of self.share_option, know that it is a sub-type
            # AllNewSelectedOld, and then manually cast its type into AllNewSelectedOld.
            # I don't feel great (and actually, weird) about this implementation. But the
            # fundamental problem is lack of isinstance() check, and this is already the best way
            # I can think of for now.
            my_share_option: AllNewSelectedOld = cast(
                AllNewSelectedOld, self.share_option
            )
            return engine_candidates.share_all_new_selected_old(
                my_share_option["max_to_share"], my_share_option["old_share_prob"], peer
            )
        raise ValueError(
            "No such option to share orders: {}".format(self.share_option["method"])
        )

    def score_neighbors(self, peer: "Peer") -> None:
        """
        This method calculates the scores of a given peer, and deletes a neighbor if necessary.
        :param peer: the peer whose neighbors are to be scored
        :return: None. Results of the scores are recorded in neighbor.score.
        """
        if self.score_option["method"] == "Weighted":
            # cast used again due to same reason as the case above.
            my_score_option: Weighted = cast(Weighted, self.score_option)
            engine_candidates.weighted_sum(
                lazy_contribution=my_score_option["lazy_contribution_threshold"],
                lazy_length=my_score_option["lazy_length_threshold"],
                discount=my_score_option["weights"],
                peer=peer,
            )
        else:
            raise ValueError(
                "No such option to calculate scores: {}".format(
                    self.score_option["method"]
                )
            )

    def find_neighbors_to_share(self, time_now: int, peer: "Peer") -> Set["Peer"]:
        """
        This method determines the set of neighboring nodes to share the orders in this batch.
        :param time_now: the current time
        :param peer: the peer who is making the decision
        :return: the set of peer instances of neighboring nodes that are selected as beneficiaries.
        """
        if self.beneficiary_option["method"] == "TitForTat":
            # cast used again due to same reason as the case above.
            my_beneficiary_option: TitForTat = cast(TitForTat, self.beneficiary_option)
            neighbors_selected: Set["Peer"] = engine_candidates.tit_for_tat(
                baby_ending=my_beneficiary_option["baby_ending_age"],
                mutual=my_beneficiary_option["mutual_helpers"],
                optimistic=my_beneficiary_option["optimistic_choices"],
                time_now=time_now,
                peer=peer,
            )
        else:
            raise ValueError(
                "No such option to decide beneficiaries: {}".format(
                    self.beneficiary_option["method"]
                )
            )

        # update the contribution queue since it is the end of a calculation circle
        for neighbor in peer.peer_neighbor_mapping.values():
            neighbor.share_contribution.popleft()
            neighbor.share_contribution.append(0)

        return neighbors_selected

    def recommend_neighbors(
        self, requester: "Peer", base: Set["Peer"], target_number: int
    ) -> Set["Peer"]:
        """
        This method is run by the Simulator (or conceptually, centralized tracker).
        It is called by the method add_new_links_helper() in Simulator class.
        Upon request of increasing its neighbors, the tracker selects some peers from the base
        peer set, for the requesting peer to form neighborhoods.
        :param requester: the peer instance of the node who requests to increase its neighbor size
        :param base: the set of peer instances of other nodes that can be selected
        :param target_number: the targeted number of return set
        :return: a set of peer instances that are selected. Size is targeted at target_number,
        but might be smaller.
        """
        if self.rec_option["method"] == "Random":
            return engine_candidates.random_recommendation(
                requester, base, target_number
            )
        raise ValueError(
            "No such option to recommend neighbors: {}".format(
                self.rec_option["method"]
            )
        )
