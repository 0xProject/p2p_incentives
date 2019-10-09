"""
This module contains the class Engine only.
"""

from typing import Set, TYPE_CHECKING, cast, List
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
    RefreshOption,
    BeneficiaryOption,
    RecommendationOption,
    LoopOption,
    AllNewSelectedOld,
    Weighted,
    TitForTat,
    Preference,
    Priority,
    RemoveLazy,
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
    Later the SingleRun class will call methods from this Engine class for a particular
    realization of implementation.
    """

    def __init__(self, parameters: EngineParameters, options: EngineOptions) -> None:

        # unpacking parameters

        # topology parameters: maximal/minimal size of neighborhood
        self.neighbor_max: int = parameters.topology.max_neighbor_size
        self.neighbor_min: int = parameters.topology.min_neighbor_size

        # please refer to class Incentive definition in date_types module for their explanation.

        self.score_length: int = parameters.incentive.score_sheet_length
        self.reward_a: float = parameters.incentive.reward_a
        self.reward_b: float = parameters.incentive.reward_b
        self.reward_c: float = parameters.incentive.reward_c
        self.reward_d: float = parameters.incentive.reward_d
        self.reward_e: float = parameters.incentive.reward_e
        self.penalty_a: float = parameters.incentive.penalty_a
        self.penalty_b: float = parameters.incentive.penalty_b

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

        self.preference_option: PreferenceOption = options.preference
        self.priority_option: PriorityOption = options.priority
        self.external_option: ExternalOption = options.external
        self.internal_option: InternalOption = options.internal
        self.store_option: StoreOption = options.store
        self.share_option: ShareOption = options.share
        self.score_option: ScoreOption = options.score
        self.refresh_option: RefreshOption = options.refresh
        self.beneficiary_option: BeneficiaryOption = options.beneficiary
        self.rec_option: RecommendationOption = options.rec
        self.loop_option: LoopOption = options.loop

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
        to set. If preference is not given, the method will decide the value to set based on
        other arguments.
        :return: None
        """
        if self.preference_option["method"] == "Passive":
            engine_candidates.set_preference_passive(neighbor, peer, master, preference)
        else:
            raise ValueError(
                f"No such option to set preference: {self.preference_option['method']}"
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
        If priority is not given, the method will decide the value to set based on other arguments.
        :return: None
        """
        if self.priority_option["method"] == "Passive":
            engine_candidates.set_priority_passive(orderinfo, order, master, priority)
        else:
            raise ValueError(
                f"No such option to set priority: {self.priority_option['method']}"
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
            f"No such option to receive external orders: {self.external_option['method']}"
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
            f"No such option to receive internal orders: {self.internal_option['method']}"
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
                f"No such option to store orders: {self.store_option['method']}"
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
            f"No such option to share orders: {self.share_option['method']}"
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
            # input argument check
            if self.score_length != len(my_score_option["weights"]):
                raise ValueError("Wrong length in weights.")
            engine_candidates.weighted_sum(
                discount=my_score_option["weights"], peer=peer
            )
        else:
            raise ValueError(
                f"No such option to calculate scores: {self.score_option['method']}"
            )

    def neighbor_refreshment(self, peer: "Peer") -> None:
        """
        This method refreshes neighborhood for a peer by deleting some unwanted neighbors.
        :param peer: the peer whose neighborhood is to be refreshed.
        :return: None
        """
        if self.refresh_option["method"] == "RemoveLazy":
            my_refresh_option: RemoveLazy = cast(RemoveLazy, self.refresh_option)
            neighbor_to_remove: List["Peer"] = engine_candidates.remove_lazy_neighbors(
                lazy_contribution=my_refresh_option["lazy_contribution"],
                lazy_length=my_refresh_option["lazy_length"],
                peer=peer,
            )
            for neighbor in neighbor_to_remove:
                peer.del_neighbor(neighbor)
        elif self.refresh_option["method"] == "Never":
            # don't delete any one
            pass
        else:
            raise ValueError(
                f"No such option to refresh neighbors: {self.refresh_option['method']}"
            )

    def find_neighbors_to_share(
        self, time_now: int, peer: "Peer", time_start: int
    ) -> Set["Peer"]:
        """
        This method determines the set of neighboring nodes to share the orders in this batch.
        :param time_now: the current time
        :param peer: the peer who is making the decision
        :param time_start: the starting time of a peer. Usually birth_time, but for initial peers
        in the simulator, this time is scenario.birth_time_span - 1.
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
                time_start=time_start,
                peer=peer,
            )
        else:
            raise ValueError(
                f"No such option to decide beneficiaries: {self.beneficiary_option['method']}"
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
        This method is run by the SingleRun instance (or conceptually, centralized tracker).
        It is called by the method add_new_links_helper() in SingleRun class.
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
            f"No such option to recommend neighbors: {self.rec_option['method']}"
        )

    def should_a_peer_start_a_new_loop(
        self, peer: "Peer", time_now: int, init_birth_span
    ) -> bool:
        """
        This method return True if the given peer should start a new loop, or False otherwise.
        :param peer: the given peer
        :param time_now: Mesh system time.
        :param init_birth_span: max (birth time + 1 for birth time of the system's initial orders)
        :return: True or False.
        """
        if self.loop_option["method"] == "FollowPrevious":
            return engine_candidates.after_previous(peer, time_now, init_birth_span)
        raise ValueError(
            f"No such option to start a new loop: {self.loop_option['method']}"
        )
