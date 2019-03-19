# The Engine class contains all variable strategies in the P2P simulation
import random

class Engine:
    
    # This function updates the settle status for orders
    def orderUpdateSettleStatus(self, order):
        pass
    
    # This function sets preference to a neighbor
    def neighborSetPreference(self, neighbor, peer, master, preference):
        if preference is not None:
            neighbor.preference = preference
        else:
            neighbor.preference = None
            
    # This function sets priority for an orderinfo instance        
    def orderinfoSetPriority(self, orderinfo, master, order, priority):
        if priority is not None:
            self.priority = priority
        else: # may need to depend on the master node's namespacing, and category of this order
            self.priority = None
            
    # This function determines whether to accept an external order into the pending table
    def externalOrderAcceptance(self, receiver, order):
        return True
    
    # This function determines whether to accept an internal order into the pending table
    def internalOrderAcceptance(self, receiver, sender, order):
        return True
    
    # This function is for a peer to determine whether to store each order
    # in the pending table to the local storage, or discard it.
    # Right now, the implementation is: Set the first orderinfo of each order as "store,"
    # and the rest ones as "not to store."
    # Need to make sure that for each order, at most one orderinfo instance is stored.
    def orderStorage(self, peer):
        for order, pending_orderinfolist_of_same_id in peer.order_pending_orderinfo_mapping.items():
            pending_orderinfolist_of_same_id[0].storage_decision = True # first orderinfo is stored
            for orderinfo in pending_orderinfolist_of_same_id[1:]: # the rest (if any) are not stored
                orderinfo.storage_decision = False
                
    # This function determins the set of orders to share for this peer
    # Right now, the implementation is:
    # share min(max_to_share, size_of_new_peers) new peers,
    # and share min(remaining_quota, size_of_old_peers * prob) old peers.
    
    def orderToShare(self, peer, old_order_share_prob):
        new_order_set = peer.new_order_set
        old_order_set = set(peer.order_orderinfo_mapping) - peer.new_order_set
        selected_order_set = set()
                      
        selected_order_set |= set(random.sample(new_order_set, min(peer.max_to_share, len(new_order_set))))
        
        remaining_share_size = max(0, peer.max_to_share - len(new_order_set))
        probability_selection_size = round(len(old_order_set) * old_order_share_prob)
        selected_order_set |= set(random.sample(old_order_set, min(remaining_share_size, probability_selection_size)))            
        return selected_order_set
    
    # This function determines the set of neighboring nodes to share the order in this batch.
    # Right now the strategy is: If I am a new peer and do not know my neighbors well,
    # share to random ones (# = MUTUAL_HELP + OPTIMISTIC_CHOICES).
    # Otherwise, share to MUTUAL_HELP highly-reputated neighbors, and
    # OPTIMISTIC_CHOICES random low-reputated neighbors.
    
    def neighborToShare(self, cur_time, peer, baby_ending_time, mutual_helpers, optimistic_choices):
        
        selected_peer_set = set() 
        if (cur_time - peer.birthtime <= baby_ending_time): # This is a new peer. random select neighbors
            selected_peer_set |= set(\
                random.sample(list(peer.peer_neighbor_mapping),\
                              min(len(peer.peer_neighbor_mapping), mutual_helpers + optimistic_choices)))
        else: # This is an old peer
            ranked_list_of_peers = peer.rankNeighbors()
            highly_ranked_peers_list = ranked_list_of_peers[:mutual_helpers]
            lowly_ranked_peers_list = ranked_list_of_peers[mutual_helpers:]
            selected_peer_set |= set(highly_ranked_peers_list)
            selected_peer_set |= set(\
                random.sample(lowly_ranked_peers_list,\
                                                   min(len(lowly_ranked_peers_list), optimistic_choices)))            
        return selected_peer_set
    
    # This function calculates the fairness index for each peer
    # Right now, it is not implemented.
    def calFairness(self, peer):
        return 0
    
    # This function selects some peers from the base peer set for the requester to form neighborhoods
    # Current versio: random. No differentiation accross requesters.
    def neighborRec(self, requester, base, target_number):
        if not base or not target_number:
            raise ValueError('Base set is empty or target number is zero.')
        
        # if the target number is larger than the set size, output the whole set.
        return set(random.sample(base, min(target_number, len(base))))
 
    
    
        
        