'''
=======================================
Peer, Neighbor classes
=======================================
'''

from order import OrderInfo
import collections

# Each peer maintains a set of neighbors. Note, a neighbor physically is a peer,
# but a neighbor instance is not a peer instance; instead, it has specialized information
# from a peer's viewpoint. For information stored in the Peer instance,
# refer to the mapping table in the Simulator and find the corrosponding Peer instance.


class Neighbor:
    
    def __init__(self, engine, peer, master, est_time, preference = None):
         
        self.engine = engine # design choice
        self.est_time = est_time # establishment time
        # "peer" is the peer instance of this neighbor
        # "master" is the peer instance of whom that regards me as a neighbor
        # the following function sets up the master node's preference to this neighbor
        self.engine.neighborSetPreference(peer, master, preference)
        
        # If peer A shares his info to peer B, we say peer A contributes to B.
        # Such contribution is recorded in peer B's local record, i.e.,
        # the neighbor instance for peer A in the local storage of peer B.
        # Formally, "share_contribution" is a queue to record a length of "score_length"
        # of contributions, each corresponding to the score in one of the previous batches.
        self.share_contribution = collections.deque()
        for _ in range(engine.score_length):
            self.share_contribution.append(0)
        
        self.score = 0 # the score to evaluate my neighbor.
        
        # lazy_round is over how many batches has this peer be regarded as a lazy neighbor.
        # A neighbor is regarded as lazy if its score in one batch is below a certain value.
        # Default for lazy_round is 0. Increased by 1 if its score is below that certain value, or reset to 0 otherwise.
        self.lazy_round = 0

# Peer class, each peer instance being a node in the P2P system. 
        
class Peer:

    # Note: initialization deals with initial orders, but does not establish neighborhood relationships.
    
    def __init__(self, engine, seq, birthtime, init_orders, namespacing = None, peer_type = None):
        
        self.local_clock = birthtime
        
        # simple parameter setting
        self.engine = engine # design choice
        self.seq = seq # sequence number. Not in use now, for reserve purpose only.
        self.birthtime = birthtime
        self.init_orderbook_size = len(init_orders)
        self.namespacing = namespacing # A peer's namespacing is its interest in certain trading groups. Currently we don't set it.
        
        self.peer_type = peer_type # Refers to a peer type (e.g., big/small relayer). Its value is a string (or None by default).
        
        # This denotes if this peer is a free rider (no contribution to other peers)
        # This is a redundant variable, for better readability only.
        # A free rider sits in the system, listens to orders, and does nothing else.
        # It does not generate orders by itself.
        self.is_freerider = (peer_type == 'free-rider') 
        
        self.order_orderinfo_mapping = {} # mapping from the order instance to orderinfo instances that have been formally stored.
        self.peer_neighbor_mapping = {} # mapping from the peer instance to neighbor instance. Note, neighborhood relationship must be bilateral.
        self.new_order_set = set() # set of newly and formally-stored orders that have NEVER been shared out by this peer.
        
        # The following mapping maintains a table of pending orders, by recording their orderinfo instance.
        # Note that an order can have multiple orderinfo instances, because it can be forwarded by different neighbors.
        self.order_pending_orderinfo_mapping = {}
        
        if self.is_freerider and init_orders:
            raise ValueError('Free riders should not have their own orders.')
        
        # initiate orderinfos
        for order in init_orders: # inital orders will directly be stored without going through the storage decison.
     
            # if this order is created by this peer, but in the peer initialization,
            # it was unable to define the creator as this peer since the peer has not been created.
            # there we defined the creator as None, and we will modify here.
            if order.creator is None:
                order.creator = self
                    
            priority = None # we don't set the priority for now
            new_orderinfo = OrderInfo(engine, order, self, birthtime, priority)
            self.order_orderinfo_mapping[order] = new_orderinfo
            self.new_order_set.add(order)
                
            new_orderinfo.storage_decision = True # not sure if this is useful. Just keep it here to keep consistency.
            order.holders.add(self)
            
                    
    # This function is called when a request of establishing a neighborhood relationship is
    # called from another peer. This peer, which is requested, will return True for agreement by default,
    # or False if the current # of neighbors already reaches the maximal.
    # Note, this function does not establish neighborhood relationship by itself.
    # It accepts or rejects the request only.
    
    def acceptNeighborRequest(self, requester):
        
        if requester in self.peer_neighbor_mapping:
            raise ValueError('You are my neighbor. No need to request again.')
    
        return len(self.peer_neighbor_mapping) < self.engine.neighbor_min
    
    # The following function establishes a neighborhood relationship.
    # It can only be called by the Simulator function addNewLinksHelper.
    # Return False if peer is already my neighbor, or True otherwise. 
        
    def addNeighbor(self, peer):
        
        if peer in self.peer_neighbor_mapping:
            return False
                
        # create new neighbor in my local storage
        new_neighbor = Neighbor(self.engine, peer, self, self.local_clock)
        self.peer_neighbor_mapping[peer] = new_neighbor
        
        return True
        
    # This function defines what a peer will do if it's notified by someone for cancelling a neighborhood relationship.
    # It will always accept the cancellation, and delete that peer from his neighbor.
    # Note that this is different from a real system that a peer simply drops a neighborhood relationship
    # without need of being accepted by the other side. This function is for simulation bookkeeping purpose only.
        
    def acceptNeighborCancellation(self, requester):
        # If I am removed as a neighbor by my neighbor, I will delete him as well.
        # But I will not remove orders from him, and I don't need to inform him to delete me.
        if requester in self.peer_neighbor_mapping:
            self.delNeighbor(requester, False, False) 
        
    # This function deletes a neighbor. If remove_order is True, then all orderinfo instances with the
    # prev_owner being this neighbor will also be deleted (order instances are still there).
    # notification: whether to notify the other party to cancel neighborhood.
    
    def delNeighbor(self, peer, remove_order = False, notification = True): 
   
        if peer not in self.peer_neighbor_mapping:
            raise ValueError('This peer is not my neighbor. Unable to delete.')
        
        # if remove_order is True, delete all orders whose previous owner is this neighbor
        if remove_order:
            
            for order, orderinfo in self.order_orderinfo_mapping.items():
                if orderinfo.prev_owner == peer:
                    order.holders.remove(self)
                    self.new_order_set.discard(order)
                    del self.order_orderinfo_mapping[order]
                    
            for order, orderinfolist in self.order_pending_orderinfo_mapping.items():
                for idx, orderinfo in enumerate(orderinfolist):
                    if orderinfo.prev_owner == peer:
                        del orderinfolist[idx]
                if orderinfolist == []: # no pending orderinfo for this order. need to delete this entry
                    order.hesitators.remove(self) 
                    del self.order_pending_orderinfo_mapping[order]
        
        # if this neighbor is still an active peer, notify him to delete me as well.
        if notification:
            peer.acceptNeighborCancellation(self)
        
        # delete this neighbor
        del self.peer_neighbor_mapping[peer]
    
    # receiveOrderExternal() is called by orderArrival function.
    # OrderInfo will be put into pending table (just to keep consistent with receive_internal,
    # though most likely it will be accepted).
    # return True if accepted or False otherwise.
    
    def receiveOrderExternal(self, order):
        
        if order in self.order_pending_orderinfo_mapping:
            raise ValueError('Duplicated external order. This order is in my pending table.')
        if order in self.order_orderinfo_mapping:
            raise ValueError('Duplicated external order. This order is in my local storage.')

        if self.engine.externalOrderAcceptance(self, order):
            
            # create the orderinfo instance and add it into the local mapping table
            new_orderinfo = OrderInfo(self.engine, order, self, self.local_clock)
            self.order_pending_orderinfo_mapping[order] = [new_orderinfo]
            
            # update the number of replicas for this order and hesitator of this order
            order.hesitators.add(self) # a peer is a hesitator of an order if this order is in its pending table
            return True
        
        return False

    # receiveOrderInternal() is called by shareOrder function. It will immediately decide whether
    # to put the order from the peer (who is my neighbor) into my pending table.
    # When novelty_update is True, its count will increase by one once transmitted.
    # Return True if accepted or False otherwise.
    
    def receiveOrderInternal(self, peer, order, novelty_update = False):
    
        if self not in peer.peer_neighbor_mapping or peer not in self.peer_neighbor_mapping:
            raise ValueError('Order transmission cannot be peformed between non-neighbors.')
        
        neighbor = self.peer_neighbor_mapping[peer]
                
        if not self.engine.internalOrderAcceptance(self, peer, order):
            # update the contribution of my neighbor for his sharing
            neighbor.share_contribution[-1] += self.engine.pa
            return False
        
        if order in self.order_orderinfo_mapping: # no need to store again
            orderinfo = self.order_orderinfo_mapping[order]
            if orderinfo.prev_owner == peer:
                # I have this order in my local storage.
                # My neighbor is sending me the same order again.
                # It may be due to randomness of sharing old orders.
                neighbor.share_contribution[-1] += self.engine.ra
            else:
                # I have this order in my local storage, but it was from someone else.
                # No need to store it anymore. Just update the reward for the uploader.
                neighbor.share_contribution[-1] += self.engine.rb
            return False
            
        # If this order has not been formally stored:
        # Need to write it into the pending table (even if there has been one with the same ID).            
        
        if novelty_update:
            order_novelty = peer.order_orderinfo_mapping[order].novelty + 1
        else:
            order_novelty = peer.order_orderinfo_mapping[order].novelty
                    
        # create an orderinfo instance
        new_orderinfo = OrderInfo(self.engine, order, self, self.local_clock, None, peer, order_novelty)
                    
        # If no such order in the pending list, create an entry for it
        if order not in self.order_pending_orderinfo_mapping: # order id not in the pending set 
            self.order_pending_orderinfo_mapping[order] = [new_orderinfo]
            order.hesitators.add(self)
            # Put into the pending table. Share reward will be updated when a storing decision is made.
            return True
                        
        # If there is such order in the pending list, check if this order is from the same prev_owner.    
        for existing_orderinfo in self.order_pending_orderinfo_mapping[order]:
            if peer == existing_orderinfo.prev_owner:
                # This neighbor is sending duplicates to me in a short period of time
                # Likely to be a malicious one.
                neighbor.share_contribution[-1] += self.engine.pb
                return False
       
        # My neighbor is honest, but he is late in sending me the message.
        # Add it to the pending list anyway since later, his version of the order might be selected.
        self.order_pending_orderinfo_mapping[order].append(new_orderinfo)
        
        return True
    
    # storeOrders() function determines which orders to store and which to discard, for all orders
    # in the pending table. It is proactively called by each peer at the end of a batch period.
        
    def storeOrders(self):
        
        if (self.local_clock - self.birthtime) % self.engine.batch != 0:
            raise RuntimeError('Store order decision should not be called at this time.')
        
        # change orderinfo.storage_decision to True if you would like to store this order.
        self.engine.orderStorage(self)
               
        # Now store an orderinfo if necessary
               
        for order, pending_orderinfolist_for_same_order in self.order_pending_orderinfo_mapping.items():
                      
            # Sort the list of pending orderinfo with the same id, so that if
            # there is some order to be stored, it will be the first one.
            pending_orderinfolist_for_same_order.sort(key = lambda item: item.storage_decision, reverse = True)
            
            # Update the order instance, e.g., number of pending orders, and remove the hesitator, in advance.
            order.hesitators.remove(self)
            
            # After sorting, for all pending orderinfo with the same id,
            # either (1) no one is to be stored, or (2) only the first one is stored
            
            if not pending_orderinfolist_for_same_order[0].storage_decision: # if nothing is to be stored
                for pending_orderinfo in pending_orderinfolist_for_same_order:
                    # Find the global instance of the sender, and update it.
                    if pending_orderinfo.prev_owner in self.peer_neighbor_mapping: # internal order, sender is still a neighbor
                        self.peer_neighbor_mapping[pending_orderinfo.prev_owner].share_contribution[-1] += self.engine.rc
            
            else: # the first element is to be stored
                first_pending_orderinfo = pending_orderinfolist_for_same_order[0]
                # Find the global instance for the sender, and update it.
                if first_pending_orderinfo.prev_owner in self.peer_neighbor_mapping: # internal order, sender is still neighbor
                    self.peer_neighbor_mapping[first_pending_orderinfo.prev_owner].share_contribution[-1] += self.engine.rd
                # Add the order into the local storage, and update the global order instance
                self.order_orderinfo_mapping[order] = first_pending_orderinfo
                self.new_order_set.add(order)
                order.holders.add(self)
                
                
                # For the rest pending orderinfo in the list, no need to store them, but may need to do other updates
                for pending_orderinfo in pending_orderinfolist_for_same_order[1:]:
                    
                    if pending_orderinfo.storage_decision:
                        raise ValueError('Should not store multiple orders. Wrong in order store decision process.')
                    
                    if pending_orderinfo.prev_owner in self.peer_neighbor_mapping: # internal order, sender is still neighbor
                        # update the share contribution
                        self.peer_neighbor_mapping[pending_orderinfo.prev_owner].share_contribution[-1] += self.engine.re
                        
        # clear the pending mapping table                
        self.order_pending_orderinfo_mapping.clear()
        
        
    # shareOrders() function determines which orders to be shared to which neighbors.
    # It will call internal order receiving function of the receiver peer.
    # This function is only called by each peer proactively at the end of a batch period.

    def shareOrders(self):
        
        if (self.local_clock - self.birthtime) % self.engine.batch != 0:
            raise RuntimeError('Share order decision should not be called at this time.')
       
        # free riders do not share any order.
        if self.is_freerider:
            self.new_order_set.clear()
            return
        
        # Otherwise, this function has to go through order by order and neighbor by neighbor.
        
        # orders to share
        order_to_share_set = self.engine.ordersToShare(self)
        
        # clear self.new_order_set for future use
        self.new_order_set.clear()
        
        # peers to share
        peer_to_share_set = self.engine.neighborsToShare(self.local_clock, self)
        
        # call receiver node to accept the orders
        for peer in peer_to_share_set:
            for order in order_to_share_set:
                peer.receiveOrderInternal(self, order)


    # This function deletes all orderinfo instances of a particular order.
    def delOrder(self, order):
        # check if this order is in the pending table
        if order in self.order_pending_orderinfo_mapping:
            order.hesitators.remove(self)
            del self.order_pending_orderinfo_mapping[order]
        # check if this order is in the local storage
        if order in self.order_orderinfo_mapping:
            self.new_order_set.discard(order)
            del self.order_orderinfo_mapping[order]
            order.holders.remove(self)
                
    
    # This function ranks neighbors according to their scores. It is called by shareOrders function.
    # It returns a list peers ranked by the scores of their corresponding neighbor instances.
    def rankNeighbors(self):
        self.engine.scoreNeighbors(self)
        peer_list = list(self.peer_neighbor_mapping)
        peer_list.sort(key = lambda item: self.peer_neighbor_mapping[item].score, reverse = True)
        return peer_list
    
 