'''
====================
Design Space
====================
'''

# The class Engine describes the design space. By choosing a specific option we refer to a particular design choice.
# They include our possible choices on neighbor establishment, order operations and incentives, scoring system, etc.
# Such choices are viable, and one can change any/some of them to test the performance.
# Later the Simulator class will call functions from this Engine class for a particular realization of implementation.

import engine_candidates

class Engine:
    
    # set up parameters for decision choices
    
    def __init__(self, parameters, options):
        
        # unpacking parameters
        (batch, topology, incentive) = parameters
        
        # length of batch period.
        # Recall that a peer runs its order storing and sharing algorithms only at the end of a batch period.
        # A batch period contains multiple time rounds.
        
        self.batch = batch
        
        # topology parameters: maximal/minimal size of neighborhood
        self.neighbor_max = topology['max_neighbor_size']
        self.neighbor_min = topology['min_neighbor_size']
        
        # incentive related parameters: length of the score sheet, reward a-e, penality a-b
        # reward a-e:
        # a: sharing an order already in my local storage, shared by the same peer
        # b: sharing an order already in my local storage, shared by a different peer
        # c: sharing an order that I accepted to pending table, but I don't store finally
        # d: sharing an order I decide to store
        # e: for sharing an order I have multiple copies in the pending table and decided to store a copy from someone else
        # penalty a-b:
        # a: sharing an order that I have no interest to accept to the pending table
        # b: sharing an identical and duplicate order within the same batch period
        
        self.score_length = incentive['length']
        self.ra = incentive['reward_a']
        self.rb = incentive['reward_b']
        self.rc = incentive['reward_c']
        self.rd = incentive['reward_d']
        self.re = incentive['reward_e']
        self.pa = incentive['penalty_a']
        self.pb = incentive['penalty_b']
        
        # Unpacking options. They specify a choice on a function implementation.
        # Each option parameter is a dictionary. It must contain a key 'method' to specify
        # which function to call. For example, if beneficiary_option['method'] == 'TitForTat',
        # then tit-for-tat algorithm is called for neighbor selection.
        # If a particular funciton realization needs more parameters, their values are specified by
        # other keys in the dictionary.
        # In what follows, the methods in this class will check 'method' first to decide
        # which funtion in engine_candidates to call, and then pass the rest parameters to the function called.
        
        (self.preference_option, self.priority_option, self.external_option,\
         self.internal_option, self.store_option, self.share_option, \
         self.score_option, self.beneficiary_option, self.rec_option) = options
        
    # This function helps a peer to set a preference to one of its neighbor.
    # A preference represents this peer's attitude towards this neighbor (e.g., friend or foe).
    # Parameters: Neighbor is the neighbor instance for this neighbor. Peer is the peer instance for this neighbor.
    # Master is the peer instance who wants to set the preference to the neighbor.
    # Preference is an optional argument in case the master node already knows the value to set.
    # If preference is not given, it is None by default and the function will decide the value to set based on other arguments.
    
    def neighborSetPreference(self, neighbor, peer, master, preference = None):
        if self.preference_option['method'] == 'Passive':
            engine_candidates.setPreferencePassive(neighbor, peer, master, preference)
        else:
            raise ValueError('No such option to set preference: {}'.\
                             format(self.preference_option['method']))
            
    # This function sets a priority for an orderinfo instance.
    # A peer can call this function to manually set a priority value
    # to any orderinfo instance that is accepted into his pending table or stored in the local storage.
    # Parameters are similar to the above function neighborSetPreference().
    # The priority value can be utilized for order storing and sharing decisions.
    
    def orderinfoSetPriority(self, orderinfo, order, master, priority = None):
        if self.priority_option['method'] == 'Passive':
            engine_candidates.setPriorityPassive(orderinfo, order, master, priority)
        else:
            raise ValueError('No such option to set priority: {}'.\
                             format(self.priority_option['method']))
            
    # This function determines whether to accept an external order into the pending table.
    def externalOrderAcceptance(self, receiver, order):
        if self.external_option['method'] == 'Always':
            return True
        else:
            raise ValueError('No such option to recieve external orders: {}'.\
                             format(self.external_option['method']))
    
    # This function determines whether to accept an internal order into the pending table
    def internalOrderAcceptance(self, receiver, sender, order):
        if self.internal_option['method'] == 'Always':
            return True
        else:
            raise ValueError('No such option to receive internal orders: {}'.\
                             format(self.internal_option['method']))
    
    # This function is for a peer to determine whether to store each orderinfo
    # in the pending table to the local storage, or discard it.
    # Need to make sure that for each order, at most one orderinfo instance is stored.
    
    def orderStorage(self, peer):
        if self.store_option['method'] == 'First':
            engine_candidates.storeFirst(peer)
        else:
            raise ValueError('No such option to store orders: {}'.\
                             format(self.store_option['method']))
                
    # This function determines the set of orders to share for this peer.
    def ordersToShare(self, peer):
        if self.share_option['method'] == 'AllNewSelectedOld':
            return engine_candidates.shareAllNewSelectedOld\
                   (self.share_option['max_to_share'], \
                    self.share_option['old_share_prob'], peer)
        else:
            raise ValueError('No such option to share orders: {}'.\
                             format(self.share_option['method']))
    
    # This function calculates the scores of a given peer, and deletes a neighbor if necessary.
    def scoreNeighbors(self, peer):
        if self.score_option['method'] == 'Weighted':
            return engine_candidates.\
                   weightedSum(self.score_option['lazy_contribution_threshold'], \
                               self.score_option['lazy_length_threshold'], \
                               self.score_option['weights'], peer)
        else:
            raise ValueError('No such option to calculate scores: {}'.\
                             format(self.score_option['method']))
      
    # This function determines the set of neighboring nodes to share the orders in this batch.
    def neighborsToShare(self, time_now, peer):
        
        if self.beneficiary_option['method'] == 'TitForTat':
            neighbors_selected = engine_candidates.titForTat(self.beneficiary_option['baby_ending_age'],\
                                        self.beneficiary_option['mutual_helpers'],\
                                        self.beneficiary_option['optimistic_choices'],\
                                        time_now, peer)
        else:
            raise ValueError('No such option to decide beneficairies: {}'.\
                             format(self.beneficiary_option['method']))
        
        # update the contribution queue since it is the end of a calculation circle
        for neighbor in peer.peer_neighbor_mapping.values():
            neighbor.share_contribution.popleft()
            neighbor.share_contribution.append(0)
        
        return neighbors_selected
           
    # This function selects some peers from the base peer set for the requester to form neighborhoods
    def neighborRec(self, requester, base, target_number):
        if self.rec_option['method'] == 'Random':
            return engine_candidates.randomRec(requester, base, target_number)
        else:
            raise ValueError('No such option to recommend neighbors: {}'.\
                             format(self.rec_option['method']))

