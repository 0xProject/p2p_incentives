"""
This module contains the class Engine only.
"""

import engine_candidates


class Engine:

    """
    The class Engine describes the design space. By choosing a specific option we refer to a particular design choice.
    They include our possible choices on neighbor establishment, order operations and incentives, scoring system, etc.
    Such choices are viable, and one can change any/some of them to test the performance.
    Later the Simulator class will call methods from this Engine class for a particular realization of implementation.
    """

    # pylint: disable=too-many-instance-attributes
    # It is fine to have many instance attributes here.

    def __init__(self, parameters, options):

        # unpacking parameters
        (batch, topology, incentive) = parameters

        # length of a batch period.
        # Recall that a peer runs its order storing and sharing algorithms only at the end of a batch period.
        # A batch period contains multiple time rounds.

        self.batch = batch

        # topology parameters: maximal/minimal size of neighborhood
        self.neighbor_max = topology['max_neighbor_size']
        self.neighbor_min = topology['min_neighbor_size']

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

        self.score_length = incentive['length']
        self.reward_a = incentive['reward_a']
        self.reward_b = incentive['reward_b']
        self.reward_c = incentive['reward_c']
        self.reward_d = incentive['reward_d']
        self.reward_e = incentive['reward_e']
        self.penalty_a = incentive['penalty_a']
        self.penalty_b = incentive['penalty_b']

        # Unpacking options. They specify a choice on a function implementation.
        # Each option parameter is a dictionary. It must contain a key 'method' to specify
        # which function to call. For example, if beneficiary_option['method'] == 'tit_for_tat',
        # then tit-for-tat algorithm is called for neighbor selection.
        # If a particular function realization needs more parameters, their values are specified by
        # other keys in the dictionary.
        # In what follows, the methods in this class will check 'method' first to decide
        # which function in engine_candidates to call, and then pass the rest parameters to the function called.

        (self.preference_option, self.priority_option, self.external_option, self.internal_option,
         self.store_option, self.share_option, self.score_option, self.beneficiary_option, self.rec_option) = options

    def set_preference_for_neighbor(self, neighbor, peer, master, preference=None):
        """
        This method helps a peer to set a preference to one of its neighbor.
        A preference represents this peer's attitude towards this neighbor (e.g., friend or foe).
        :param neighbor: the neighbor instance for this neighbor
        :param peer: the peer instance for this neighbor
        :param master: the peer instance who wants to set the preference to the neighbor
        :param preference: an optional argument in case the master node already knows the value to set.
        If preference is not given, it is None by default and the method will decide the
        value to set based on other arguments.
        :return: None
        """
        if self.preference_option['method'] == 'Passive':
            engine_candidates.set_preference_passive(neighbor, peer, master, preference)
        else:
            raise ValueError('No such option to set preference: {}'.format(self.preference_option['method']))

    def set_priority_for_orderinfo(self, orderinfo, order, master, priority=None):
        """
        This method sets a priority for an orderinfo instance.
        A peer can call this function to manually set a priority value to any orderinfo
        instance that is accepted into his pending table or stored in the local storage.
        :param orderinfo: the orderinfo instance of the order to be set a priority
        :param order: the order instance of the order to be set a priority
        :param master: the peer instance who wants to set the priority
        :param priority: an optional argument in case the master node already knows the value to set.
        If priority is not given, it is None by default and the method will decide the
        value to set based on other arguments.
        :return: None
        """
        if self.priority_option['method'] == 'Passive':
            engine_candidates.set_priority_passive(orderinfo, order, master, priority)
        else:
            raise ValueError('No such option to set priority: {}'.format(self.priority_option['method']))

    def should_accept_external_order(self, _receiver, _order):
        """
        This method determines whether to accept an external order into the pending table.
        :param _receiver: the peer instance of the node who is supposed to receive this order
        :param _order: the order instance
        :return: True if the node accepts this order, or False otherwise
        Note: right now, we only have a naive implementation that accepts everything, so the input
        arguments are not useful so they start with an underline. Later, one may need to delete the underline.
        """
        if self.external_option['method'] == 'Always':
            return True
        raise ValueError('No such option to receive external orders: {}'.format(self.external_option['method']))

    def should_accept_internal_order(self, _receiver, _sender, _order):
        """
        This method determines whether to accept an internal order into the pending table.
        :param _receiver: same as the above method
        :param _sender: the peer instance of the node who wants to send this order
        :param _order: same as the above method
        :return: same as the above method
        Note: Underline issue same as the above method.
        """
        if self.internal_option['method'] == 'Always':
            return True
        raise ValueError('No such option to receive internal orders: {}'.format(self.internal_option['method']))

    def store_or_discard_orders(self, peer):
        """
        This method is for a peer to determine whether to store each orderinfo
        in the pending table to the local storage, or discard it.
        Need to make sure that for each order, at most one orderinfo instance is stored.
        However, there is no self-check for this condition in the method itself.
        The check will be done in the Peer's method store_orders().
        :param peer: the peer to make the decision
        :return: None. The decision is recorded in Orderinfo.storage_decision.
        """
        if self.store_option['method'] == 'First':
            engine_candidates.store_first(peer)
        else:
            raise ValueError('No such option to store orders: {}'.format(self.store_option['method']))

    def find_orders_to_share(self, peer):
        """
        This method determines the set of orders to share for this peer.
        :param peer: the peer to make the decision
        :return: the set of orders to share
        """
        if self.share_option['method'] == 'AllNewSelectedOld':
            return engine_candidates.share_all_new_selected_old(self.share_option['max_to_share'],
                                                                self.share_option['old_share_prob'], peer)
        raise ValueError('No such option to share orders: {}'.format(self.share_option['method']))

    def score_neighbors(self, peer):
        """
        This method calculates the scores of a given peer, and deletes a neighbor if necessary.
        :param peer: the peer whose neighbors are to be scored
        :return: None. Results of the scores are recorded in neighbor.score.
        """
        if self.score_option['method'] == 'Weighted':
            engine_candidates.weighted_sum(self.score_option['lazy_contribution_threshold'],
                                           self.score_option['lazy_length_threshold'],
                                           self.score_option['weights'],
                                           peer)
        else:
            raise ValueError('No such option to calculate scores: {}'.
                             format(self.score_option['method']))

    def find_neighbors_to_share(self, time_now, peer):
        """
        This method determines the set of neighboring nodes to share the orders in this batch.
        :param time_now: the current time
        :param peer: the peer who is making the decision
        :return: the set of peer instances of neighboring nodes that are selected as beneficiaries.
        """
        if self.beneficiary_option['method'] == 'TitForTat':
            neighbors_selected = engine_candidates.tit_for_tat(self.beneficiary_option['baby_ending_age'],
                                                               self.beneficiary_option['mutual_helpers'],
                                                               self.beneficiary_option['optimistic_choices'],
                                                               time_now, peer)
        else:
            raise ValueError('No such option to decide beneficiaries: {}'.format(self.beneficiary_option['method']))

        # update the contribution queue since it is the end of a calculation circle
        for neighbor in peer.peer_neighbor_mapping.values():
            neighbor.share_contribution.popleft()
            neighbor.share_contribution.append(0)

        return neighbors_selected

    def recommend_neighbors(self, requester, base, target_number):
        """
        This method is run by the Simulator (or conceptually, centralized tracker).
        It is called by the method add_new_links_helper() in Simulator class.
        Upon request of increasing its neighbors, the tracker selects some peers from the base peer set,
        for the requesting peer to form neighborhoods.
        :param requester: the peer instance of the node who requests to increase its neighbor size
        :param base: the set of peer instances of other nodes that can be selected
        :param target_number: the targeted number of return set
        :return: a set of peer instances that are selected. Size is targeted at target_number, but might be smaller.
        """
        if self.rec_option['method'] == 'Random':
            return engine_candidates.random_recommendation(requester, base, target_number)
        raise ValueError('No such option to recommend neighbors: {}'.format(self.rec_option['method']))
