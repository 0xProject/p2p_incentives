'''
===========================
P2P Orderbook simulator

Weijie Wu
Dec 3, 2018

===========================

Purpose:

This simulator works for the P2P architecture of sharing orders under the 0x protocol.
Its initial aim is to facilitate the design of incentives in such system, but it can also be used to test other design issues.
It is not constriant by any particular incentives, but works as a platform so that any mechanism can be plug into the simulator.

===========================

Structure:

This simulator uses a descrete time based structure. In the initialization, a given # of peers are created, each with a certain # of
orders. In each time round, (1) a given set of peers depart, (2) a given set of orders are canceled, (3) a given set of orders are expired,
(4) a given # of orders are settled, (5) a number of new peers arrive, and (6) a set of orders are added to some exisiting peers.

For all peers in the system, in each time round, they need to (1) receive orders from internal sharing and external order arrival, (2) decide
which orders to be formally stored, and (3) for stored orders, decide whether to share each of them to each of its neighbors.


Classes:

- Class Peer represents peers in the system.
- Class Neighbor represents neighbors in a peer (called A)'s local storage (a neighbor is physically
another peer B, but peer A will store some local information of peer B as its neighbor, so we have a different class)
- Class Order represents orders in the system.
- Class OrderInfo represents an order instance stored in a peer's local storage (this is physically an order,
but a peer will have some local information of this order as well, e.g., who transmitted this order to me).

===========================

Design details:

1. Departure of orders and peers:

- Deletion of an order (settled, expired, or due to owner cancellation):
    - Order instance is still there, but valid is False.
    - OrderInfo instance will be deleted.

- Deletion of a peer:
    - Both peer and neighbor instances will be deleted.
    
2. Neighborhood relationship:

- Any neighborhood relationship needs to be bilateral, meaning that if A is a neighbor of B, then B must be a neighbor of A too.
- Note that this is not enforced in delNeighbor() function. Be careful to use delNeighbor() if it is not called by a peer departure.

3. Order receiving:
  
- There are four ways to receive orders: initialization, addNeighbor, receiveOrderExternal, receiveOrderInternal

    - 3.1. For Initialization, initial orders are directly put into the local storage (not through pending list).
    - 3.2. If you are added by some other peer as a neighbor (this includes your neighbors added during initialization),
            his shareNewNeighborDecision will be called, and this will input his public orders into your pending list.
    - 3.3. For receiveOrderExternal, it is called when a new order arrives (in the orderArrival function).
            This order will be put into the pending list.
    - 3.4. For receiveOrderInternal, it is called by the main function proactively in each round. When it is called, the peer looks at
            all its neighbors' order_id_revealing and add the orders into the pending list.
      
4. Order storing:

- Among the four ways that a peer can receive an order, 3.2 - 3.4 will first store an order into the pending list. In each round of the
    main function, storeOrderDecision() will be proactively called, so that certail orders will be moved from pending to local storage.
    
- For way 3.1, orders at the initialization will be directly stored in the local storage, so no function needs calling.

5. Order sharing:

- A peer will share its orders to only (1) existing neighbors, and (2) new neighbors.
     - For existing neighbors, a peer only needs to share its newly stored orders. Such newly stored orders must have been processed
         by storeOrderDecision() so as to be moved from pending list to local storage. Inside the function, shareOrderDecision() is called.
     - For new neighbors (including the initialization of this peer itself, when addNeighbor() is called), all orders in its local storage
         need to be considered sharing. Inside addNeighbor(), shareNewNeighborDecision() is called.
         
===========================

Some Options:

- When an order is transmitted, we have an option "noverty" to indicate how may hops have this order been transmitted.
If there's no fee sharing, we can disable this funtion since orders are not differentiable via hop numbers.
If fee sharing is enabled, then enabling this feature will be useful (since some versions of a transmitted order can fill in
a taker fee, some cannot).

- When a peer departs from the system, we have an option to delete all orders it created.
If a peer simply goes offline but are still intersted in the orders it makes, then this option should not be enabled.
If a peer departs pamenantly (by cancelling all orders and taking away everything in wallet, then this option should be enabled).

- When a peer A deletes a neighbor B (maybe because B departed or for some other reason), we have an option for A
to delete orders that are transmitted from B (in which case we call B is the order's previous owner).
If the incentive is designed such that the action of storing an order will only be credited by
its previous owner (but not its creator), then this feature should be enabled. Otherwise, don't enable this feature.

===========================

'''

FULL_SHARE_REWARD = 1.0 # reward for sharing with me an order that I never heard of.
PARTIAL_SHARE_REWARD = 0.5 # partial reward for sharing an order already in my pending list
LOWEST_SHARE_REWARD = 0.1 # lowest share reward for an order that I have accepted
SHARE_PENALTY = - 1.0 # penalty for intentionally sharing non-sense or duplicate information

STORAGE_REWARD = 1.0 # storage reward for storing my sharing
STORAGE_PENALTY = - 1.0 # penalty for being unwilling to store my orders

CONTRIBUTION_LENGTH = 3 # number of rounds of share/storage contribution to consider in the neighbors' history

ROUND = 4 # total round of simulations
NUM_PEERS = 10 # total number of peers in the simulation system

ORDERBOOK_SIZE_MEAN = 6 # mean number of initial orderbook size for peers
ORDERBOOK_SIZE_VAR = 0 # variance of intial orderbook size for peers

CONNECTIVITY_MEAN = 0.2 # mean of [total number of your neighbors divided by the total number of peers]
CONNECTIVITY_VAR = 0 # var of [ ... ]

ORDER_DURATION_MEAN = 10  # mean of order duration (maximal lifetime)
ORDER_DURATION_VAR = 0 # var of order duration (maximal lifetime)

import collections
import random

class Order:
    
    def __init__(self, idx, birthtime, creator, lifetime = float('inf'), order_property = None):
        self.id = idx
        self.birthtime = birthtime # will be decided by system clock
        self.creator = creator # the ID of its original owner (a peer ID)
        self.lifetime = lifetime # maximal lifetime allowed, specified by the creation of the order instance
        self.order_property = order_property # refers to some property so that a peer can be interested in/evading this order.
        
        # the following two properties are the numbers of stored/pending replicas in the whole system, held by all peers.
        # no one really knows such information except from the God's view. But we track them for simulation convenience.
        self.num_replicas = 0 
        self.num_pending = 0
        
        self.expired = False # this order instance has not been expired.
        self.settled = False # this order instance has not been taken and settled
        self.valid = True # this order is still valid. Once it is false, it should be removed.
    
    def updateExpiredStatus(self): # too old, expire.
        global cur_time
        if cur_time - self.birthtime >= self.lifetime:
            self.expired = True
            
    def updateSettledStatus(self):
        if not True:
            self.setSettled()
    
        '''
        =======================
        Design space in here!

        probability = ??? # need to fix the parameters, related to age, num of replicas, etc.
        temp = random.random()
        if temp < probability:
            self.settled = True
        =======================
        '''        
    
    def setSettled(self):
        self.settled = True
    
    def setInvalid(self): 
        self.valid = False
    
    def setProperty(self, my_property):
        self.order_property = my_property
    
    def updateValidness(self):
        if (self.num_replicas == 0 and self.num_pending == 0) or (self.expired is True) or (self.settled is True):
            self.setInvalid()
            return False
        return True
            
# Each peer maintains a set of neighbors. Note, a neighbor physically is a peer, but a neighbor instance is not a peer instance;
# instead, it has limited and specialized information from a peer's viewpoint.
# For other information about this node, refer to the global mapping table and find the corrosponding peer instance.

class Neighbor:
    
    def __init__(self, neighbor_id, preference = None):
        
        global global_id_peer_mapping_table
        if neighbor_id not in global_id_peer_mapping_table:
            raise KeyError('This peer does not exist in the system and hance cannot be my neighbor.')
        
        self.id = neighbor_id
        self.preference = preference
        
        # this is the order IDs that a peer is willing to share with one of its neighbor.
        # This set can differ for its various neighbors.
        self.order_id_revealing = set()
        
        # If peer A shares his info with peer B, or stores info shared by peer B, we say peer A contributes to B.
        # Such contribution is recorded in peer B's local record, i.e., the neighbor instance of peer A in the local storage of peer B.
        # Formally, "share_contribution/storage_contribution" are two queues to record a length of
        # "contribution_length" of contributions in the previous rounds.
        # each round is defined as the interval of two contiguous executions of updateNeighborScore function.
        
        # share_contribution is the contribution of my neighbor for sharing his information to me.
        self.share_contribution = collections.deque()
        for _ in range(CONTRIBUTION_LENGTH):
            self.share_contribution.append(0)
        self.total_share_contribution = 0 # sum of all entry values in the queue
        
        # storage_contribution is the contribution of my neighbor for storing my information shared to him.
        self.storage_contribution = collections.deque()
        for _ in range(CONTRIBUTION_LENGTH):
            self.storage_contribution.append(0)
        self.total_storage_contribution = 0 # sum of all entry values in the queue.
        
        self.score = 0 # scores to evaluate my neighbor. 
        

# This class OrderInfo is similar to Neighbor: An instance of an orderinfo is an order from a peers viewpoint.
# Note, an order instance can have multiple OrderInfo instances stored by different peers.
# It contains specifit information about the noverty and property of the order, not included in Order class.

class OrderInfo:
    
    def __init__(self, order_id, local_property = None, prev_owner = None, noverty = 0):
    
        global global_id_order_mapping_table
        if order_id not in global_id_order_mapping_table or global_id_order_mapping_table[order_id].valid is False:
            raise KeyError('Orderinfo cannot be initicated since the order does not exist or is invalid.')
        
        self.id = order_id
        self.prev_owner = prev_owner # previous owner, default is None (a new order)
        self.noverty = noverty # how many hops it has travalled. Default is 0. We can increase it by 1 once transmitted.
        
        # if a local property of orderinfo is specified, then use it. Otherwise, use the order property.
        if local_property is not None:
            self.local_property = local_property
        else:
            self.local_property = global_id_order_mapping_table[order_id].order_property
        
        # storage_decision is to record whether this peer decides to put this order into the storage.
        # It seems redundant, but it is actually useful in storeOrderDecision function.
        self.storage_decision = False


class Peer:
        
    def __init__(self, idx, birthtime, init_order_ids, init_neighbor_ids, preference = None):
        
        global global_id_order_mapping_table
        global global_id_peer_mapping_table
        
        # simple parameter setting
        self.id = idx
        self.birthtime = birthtime
        self.preference = preference # A peers preference (e.g., deals in particular orders). May impact the storage decision.
        self.id_orderinfo_mapping = {} # mapping from id to orderinfo instances that have been formally stored.
        self.id_neighbor_mapping = {} # mapping from id to neighbor instance. Note, neighborhood relationship must be bilateral.
        
        # the following mapping maintains a table of pending orders, by recording their orderinfo instance.
        # note that an order can have multiple orderinfo instances here, because it can be forwarded by different neighbors.
        # in such a case, the IDs of the instances are the same, but local local_property, prev_owner and noverty might be different.
        self.pending_id_orderinfo_mapping = {}
        
        # initiate orders
        for order_id in init_order_ids: # inital orders will directly be stored without going through the storage decison.

            if order_id not in global_id_order_mapping_table:
                raise KeyError('Peer init: Some order ID does not exist.')
            
            # check if this order is still valid, and add only valid ones.
            if global_id_order_mapping_table[order_id].valid is True:
                '''
                ====================================
                Design space in here!
                chance of defining the local_property,
                or leave it None (use the Order property)
                ====================================
                '''
                local_property = None
                new_orderinfo = OrderInfo(order_id, local_property)
                self.id_orderinfo_mapping[order_id] = new_orderinfo
                new_orderinfo.storage_decision = True
                global_id_order_mapping_table[order_id].num_replicas += 1
        
        # initiate neighbors
        for neighbor_id in init_neighbor_ids: # add neighbors
            if neighbor_id not in global_id_peer_mapping_table:
                raise KeyError('Peer init: Some neighbor ID does not exist.')
            self.addNeighbor(neighbor_id)
        
    # for each peer in each round, before executing anything, call this function to update the local orderinfo list.
    # for the local mapping, if an order is not valid any more, delete OrderInfo instance from the mapping.
    # however, note that the Order instance may still be there (but is invalid).
    
    def updateOrderinfoValidity(self):
        
        global global_id_order_mapping_table
        
        for order_id in list(self.id_orderinfo_mapping):
            if order_id not in global_id_order_mapping_table:
                raise KeyError('updateOrderinfoValidity: Non-existance order.')
            if global_id_order_mapping_table[order_id].valid is False:
                del self.id_orderinfo_mapping[order_id]
        
        for order_id in list(self.pending_id_orderinfo_mapping):
            if order_id not in global_id_order_mapping_table:
                raise KeyError('updateOrderinfoValidity: Non-existance order.')
            if global_id_order_mapping_table[order_id].valid is False: 
                del self.pending_id_orderinfo_mapping[order_id]
        
    def addNeighbor(self, neighbor_id):
        
        global global_id_peer_mapping_table
        
        # the neighbor must exists as a peer first.
        if neighbor_id not in global_id_peer_mapping_table:
            raise KeyError('No such peer.')
        
        # if this peer is already a neighbor, ignore. Otherwise, add it.
        if neighbor_id not in self.id_neighbor_mapping:
            # create new neighbor in my local storage
            new_neighbor = Neighbor(neighbor_id)
            self.id_neighbor_mapping[neighbor_id] = new_neighbor
            
            # share my current orders with this new neighbor
            self.shareNewNeighborDecision(neighbor_id)
        
    def delNeighbor(self, neighbor_id, remove_order = False):
        
        # this function deletes a neighbor. If remove_order is True, then all orderinfo instances with the
        # prev_owner being this neighbor will also be deleted (order instances are still there).
        # It is allowed to delete a neighbor if it is no longer a valid peer now.
        
        if neighbor_id not in self.id_neighbor_mapping:
            raise KeyError('This peer is not my neighbor. Unable to delete.')
        
        # if remove_order is True, delete all orders whose previous owner is this neighbor
        if remove_order is True:
            global global_id_order_mapping_table
            for order_id, orderinfo in self.id_orderinfo_mapping.items():
                if orderinfo.prev_owner == neighbor_id:
                    order_instance = global_id_order_mapping_table[order_id]
                    if order_instance.valid is True:
                        order_instance.num_replicas -= 1
                    del self.id_orderinfo_mapping[order_id]
            for order_id, orderinfolist in self.pending_id_orderinfo_mapping.values():
                for idx, orderinfo in enumerate(orderinfolist):
                    if orderinfo.prev_owner == neighbor_id:
                        order_instance = global_id_order_mapping_table[orderinfo.id]
                        if order_instance.valid is True:
                            order_instance.num_pending -= 1
                        del orderinfolist[idx]
                if orderinfolist == []: # need to delete this entry
                    del self.pending_id_orderinfo_mapping[order_id]
        
        # delete this neighbor
        del self.id_neighbor_mapping[neighbor_id] # delete from the mapping (the dictionary)
    

    # receiveOrderExternal() is called when receiving some order from external sources (or created by itself).
    # OrderInfo instance will be put into the pending list.
    
    def receiveOrderExternal(self, order_id):
        
        if order_id in self.pending_id_orderinfo_mapping:
            raise KeyError('This order is now pending for storing decision.')
        if order_id in self.id_orderinfo_mapping:
            raise KeyError('This order is already in my local order list.')
        
        global global_id_order_mapping_table
        if order_id not in global_id_order_mapping_table:
            raise KeyError('This order does not exist.')
        
        if global_id_order_mapping_table[order_id].valid is True:
            
            # create the orderinfo instance and add it into the local pending mapping table
            new_orderinfo = OrderInfo(order_id)
            self.pending_id_orderinfo_mapping[order_id] = [new_orderinfo]
            
            # update the number of pending replicas for this order
            global_id_order_mapping_table[order_id].num_pending += 1

    # receiveOrderInternal() is called when receiving some order from internal share by neighbor[neighbor_id].
    # OrderInfo instance will be in the pending list.
    # when noverty_update is True, its count will increase by one once transmitted.
    
    def receiveOrderInternal(self, neighbor_id, noverty_update = True):     
        global global_id_peer_mapping_table
        global global_id_order_mapping_table
        
        # find the global peer instance for my neighbor
        cur_neighbor_as_a_peer_instance = global_id_peer_mapping_table[neighbor_id]
        
        # neighbor_id and me must be bilateral neighbors.
        if self.id not in cur_neighbor_as_a_peer_instance.id_neighbor_mapping \
           or neighbor_id not in self.id_neighbor_mapping:
            raise KeyError('Order transmission cannot be peformed between non-neighbors.')
        
        # find the instance of myself in the storage of my neighbor as his neighbor
        myself_as_a_neighbor_instance = cur_neighbor_as_a_peer_instance.id_neighbor_mapping[self.id]
        
        # this is the total share reward that i should give to my neighbor
        total_reward = 0.0
        
        # all orders that my neighbor wants to share with me, are in the instance's order_id_revealing space.
        for order_id in myself_as_a_neighbor_instance.order_id_revealing:
            if order_id not in global_id_order_mapping_table:
                raise KeyError('This order does not exist.')
            
            order_instance = global_id_order_mapping_table[order_id]
            
            # if this order is already invalid, or nonsense, don't add it but give my neighbor a penalty
            '''
            ============================
            Design space in here!
            check non-sense orders. To be added, or we can leave it blank assuming all are honest.
            ============================
            '''
            def nonsenseOrders(order_instance):
                return False
            
            if order_instance.valid is False or nonsenseOrders(order_instance) is True:
                total_reward += SHARE_PENALTY
                continue

            else: # this is a valid order
                # This order has not been formally stored.
                # Need to write it into the pending table (even if there has been one with the same ID).            
                if order_id not in self.id_orderinfo_mapping:
                    if noverty_update is True:
                        order_noverty = cur_neighbor_as_a_peer_instance.id_orderinfo_mapping[order_id].noverty + 1
                    else:
                        order_noverty = cur_neighbor_as_a_peer_instance.id_orderinfo_mapping[order_id].noverty
                    # create an orderinfo instance and add to the pending table
                    new_orderinfo = OrderInfo(order_id, None, neighbor_id, order_noverty)
                    
                    # if not in the pending list, add it to the pending_id_orderinfo_mapping
                    if order_id not in self.pending_id_orderinfo_mapping: # order id not in the pending set 
                        self.pending_id_orderinfo_mapping[order_id] = [new_orderinfo]
                        global_id_order_mapping_table[order_id].num_pending += 1
                        total_reward += FULL_SHARE_REWARD
                        
                    # if already in the pending list, check if this order is from the same prev_owner.    
                    else: 
                        for existing_orderinfo in self.pending_id_orderinfo_mapping[order_id]:
                            if neighbor_id == existing_orderinfo.prev_owner:
                                # this neighbor is sending non-sense duplicates to me. 
                                total_reward += SHARE_PENALTY
                                break
                        else:
                            # my neighbor is honest, but he is late in sending me the message.
                            # Add it to the pending list anyway since later, his order might be selected.
                            self.pending_id_orderinfo_mapping[order_id].append(new_orderinfo)
                            global_id_order_mapping_table[order_id].num_pending += 1
                            total_reward += PARTIAL_SHARE_REWARD
                            
                # This order has been formally stored.
                else: 
                    # check if it was from the same previous owner.
                    if self.id_orderinfo_mapping[order_id].prev_owner == neighbor_id:
                        # my neighbor is sending me the same order again...
                        total_reward += SHARE_PENALTY
                    else:
                        # received it from someone else. No need to store it anymore. Just update the reward for the uploader.
                        total_reward += LOWEST_SHARE_REWARD
            
        # update the contribution of my neighbor record
        self.id_neighbor_mapping[neighbor_id].share_contribution[-1] += total_reward
        
        # update myself_as_a_neighbor_instance's order id revealing set
        myself_as_a_neighbor_instance.order_id_revealing.clear()
    
    # Given any orderinfo, shareOrderDecision() decides for each of my neighbors,
    # whether to share this order with him or not.
    # This function will be called immediately after formally storing an order.

    def shareOrderDecision(self, orderinfo):
        
        def shareDecisionHelper(my_preference, my_neighbor, orderinfo, order_instance):
            '''
            ======================
            Design space in here!!!
            return True or False
            ======================
            '''
            
            '''
            Below is a naive design that shares everything.
            '''
            
            if order_instance.valid is True:
                return True
            else:
                return False
            
            '''
            Naive design ends here.
            '''
        
        global global_id_order_mapping_table
        global global_id_peer_mapping_table
        
        order_id = orderinfo.id
        
        if order_id not in global_id_order_mapping_table:
            raise KeyError('This order does not exist.')
        
        order_instance = global_id_order_mapping_table[order_id]
        
        for my_neighbor_id, my_neighbor in self.id_neighbor_mapping.items():
            
            my_neighbor_as_a_peer_instance = global_id_peer_mapping_table[my_neighbor_id]
            
            if self.id not in my_neighbor_as_a_peer_instance.id_neighbor_mapping:
                raise KeyError('Neighborhood relationship is not bi-directional.')
            
            if shareDecisionHelper(self.preference, my_neighbor, orderinfo, order_instance) is True:
                my_neighbor.order_id_revealing.add(order_id)
                
    # This function decides which orders in my local storage to share with a particular new neighbor.
    # This function will be called right after the addition of a new neighbor.
  
    def shareNewNeighborDecision(self, neighborid):

        def shareNewNeighborHelper(my_preference, my_neighbor, orderinfo, order_instance):
            '''
            ======================
            Design space in here!!!
            return True or False
            ======================
            '''
            
            '''
            Below is a naive sharing mechanism that shares everything.
            '''
            
            if order_instance.valid is True:
                return True
            else:
                return False
            
            '''
            Naive desisn ends here.
            '''
        
        global global_id_order_mapping_table
        global global_id_peer_mapping_table
        
        neighbor_instance = self.id_neighbor_mapping[neighborid]
        
        for order_id, orderinfo in self.id_orderinfo_mapping.items():
            if order_id not in global_id_order_mapping_table:
                raise KeyError('This order does not exist.')

            my_neighbor_as_a_peer_instance = global_id_peer_mapping_table[neighborid]        
            order_instance = global_id_order_mapping_table[order_id]
            
            if shareNewNeighborHelper(self.preference, neighborid, orderinfo, order_instance) is True: # share it with the new neighbor
                neighbor_instance.order_id_revealing.add(order_id)

                    
    def storeOrderDecision(self):
        
        global global_id_order_mapping_table
        global global_id_peer_mapping_table
    
        '''
        ===========================
        design space begins here.
        change instance.storage_decision to True if you would like to store this order.
        Later part of this function will take care of such orders and write them into the local storage.
        This decision process must make sure that for the set of pending orders
        with the same id, at most one will be selected.
        ===========================
        '''
        
        '''
        below is a naive one that labels the first entry of each pending orderinfolist as True.
        '''
        for idx, pending_orderinfolist_of_same_id in self.pending_id_orderinfo_mapping.items():
            if global_id_order_mapping_table[idx].valid is False:
                for orderinfo in pending_orderinfolist_of_same_id:
                    orderinfo.storage_decision = False
            else: # it is a valid order
                pending_orderinfolist_of_same_id[0].storage_decision = True
                for orderinfo in pending_orderinfolist_of_same_id[1:]:
                    orderinfo.storage_decision = False
        '''            
        Naive design ends here.
        '''
        
        for idx, pending_orderinfolist_of_same_id in self.pending_id_orderinfo_mapping.items():
            
            if idx not in global_id_order_mapping_table:
                raise KeyError('This order does not exist.')
            
            # sort the list of pending orderinfo with the same id, so that if
            # there is some order to be stored, it will be the first one.
            pending_orderinfolist_of_same_id.sort(key = lambda item: item.storage_decision, reverse = True)
            
            # find the global order instance for all orderinfo in this list, and update its number of pending orders in advance
            pending_orderinfo_as_an_order_instance = global_id_order_mapping_table[idx]
            pending_orderinfo_as_an_order_instance.num_pending -= len(pending_orderinfolist_of_same_id)
            
            # after sorting, for all pending orderinfo with the same id,
            # either (1) no one is to be stored, or (2) only the first one is stored
            
            if pending_orderinfolist_of_same_id[0].storage_decision is False: # if nothing is to be stored
                for pending_orderinfo in pending_orderinfolist_of_same_id:
                    # find the global instance of the sender, and update it.
                    if pending_orderinfo.prev_owner is not None:
                        sender_as_a_peer_instance = global_id_peer_mapping_table[pending_orderinfo.prev_owner]
                        sender_as_a_peer_instance.id_neighbor_mapping[self.id].storage_contribution[-1] += STORAGE_PENALTY
            
            else: # the first element is to be stored
                first_pending_orderinfo = pending_orderinfolist_of_same_id[0]
                # find the global instance for the sender, and update it.
                if first_pending_orderinfo.prev_owner is not None: # This is not a new order
                    first_sender_as_a_peer_instance = global_id_peer_mapping_table[first_pending_orderinfo.prev_owner]
                    first_sender_as_a_peer_instance.id_neighbor_mapping[self.id].storage_contribution[-1] += STORAGE_REWARD
                # add the order into the local storage, and update the global order instance
                self.id_orderinfo_mapping[idx] = first_pending_orderinfo
                pending_orderinfo_as_an_order_instance.num_replicas += 1
                
                # decide whether to share this order to my neighbors
                self.shareOrderDecision(first_pending_orderinfo)
                
                # for the rest pending orderinfo in the list, no need to store them, but may need to do other updates
                for pending_orderinfo in pending_orderinfolist_of_same_id[1:]:
                    
                    if pending_orderinfo.storage_decision is True:
                        raise ValueError('Should not store multiple orders. Wrong in storage decision process.')
                    
                    if pending_orderinfo.prev_owner is not None: # not a new order
                        # find the global instance for the sender
                        sender_as_a_peer_instance = global_id_peer_mapping_table[pending_orderinfo.prev_owner]
                        # if their noverties are the same, then they are indistinguishable.
                        # so you can just pretend that you're storing the order for the sender (though you're storing it for someone else)
                        if pending_orderinfo.noverty == first_pending_orderinfo.noverty:
                            # update the sender instance
                            sender_as_a_peer_instance.id_neighbor_mapping[self.id].storage_contribution[-1] += STORAGE_REWARD
                        else:
                            # the orders are distinguishable. No way to take advantage. Update the sender instance.
                            sender_as_a_peer_instance.id_neighbor_mapping[self.id].storage_contribution[-1] += STORAGE_PENALTY
                        
        # clear the pending mapping table                
        self.pending_id_orderinfo_mapping.clear()
     
    # this function deletes a certain orderinfo instance, even if it is still a valid order in the system.
    # for the case where an order becomes invalid, the function updateOrderinfoValidity() will delete it.
    
    def delOrder(self, order_id):
        
        global global_id_order_mapping_table
        if order_id not in global_id_order_mapping_table:
            raise KeyError('This order does not exist.')

        global_order_instance = global_id_order_mapping_table[order_id]
        
        # check if this order is in the pending list
        if order_id in self.pending_id_orderinfo_mapping:
            global_order_instance.num_pending -= len(self.pending_id_orderinfo_mapping[order_id])
            del self.pending_id_orderinfo_mapping[order_id]
        
        # check if this order is in the stored order table
        if order_id in self.id_orderinfo_mapping:
            global_order_instance.num_replicas -= 1
            del self.id_orderinfo_mapping[order_id]
            
            
    def updateNeighborScore(self):
        # update the scores of the neighbors.
        # For the curerent version I didn't use this function. But it is designed to decide sharing/storing order decisions.
        '''
        ============================
        design space:
        how to decide a neighbors score?
        Below we simply return 1.0 for all neighbors.
        ============================
        '''
        def scoreCalculator(share, storage):
            return 1.0
        
        global cur_time
        
        for neighbor in self.id_neighbor_mapping.values():
            
            neighbor.total_share_contribution = sum(partial for partial in neighbor.share_contribution) 
            neighbor.total_storage_contribution = sum(partial for partial in neighbor.storage_contribution)
            
            neighbor.score = scoreCalculator(neighbor.total_share_contribution, neighbor.total_storage_contribution)
            
            # update the contribution queue since it is the end of a calculation circle
            
            neighbor.share_contribution.popleft()
            neighbor.share_contribution.append(0) 
            
            neighbor.storage_contribution.popleft()
            neighbor.storage_contribution.append(0)
        
    def rankNeighbors(self):
        neighbor_list = list(self.id_neighbor.mapping.values())
        neighbor_list.sort(key = lambda item: item.score, reverse = True)
        return neighbor_list
    
    def fairnessIndex(self):
        
        '''
        ============================
        design space:
        how to decide a neighbors fairness index?
        ============================
        '''
        pass
 
'''
===========================================
System functions begin here.
===========================================
'''

def globalInit(num_peers):
    
    # construct a number of peers and a number of orders
    # also, construct a global mapping table from peer id to the peer instances
    # and a global mapping table from order id to order instances
    # track the next IDs for order and peer
    
    global global_id_order_mapping_table # mapping from order ID to order instance
    global global_id_peer_mapping_table # mapping from peer ID to peer instance
    global cur_time # current system time
    global latest_order_id # id for next order to use
    global latest_peer_id # id for next peer to use
    
    order_index = latest_order_id # should start from zero, but can be customized
    peer_index = latest_peer_id # samething as above
    
    # first create all peer instances with no neighbors
    
    for _ in range(num_peers):
        
        # decide the number of orders for this peer
        num_orders = max(0, round(random.gauss(ORDERBOOK_SIZE_MEAN, ORDERBOOK_SIZE_VAR)))

        # create all order instances, and the initial orderbooks
        beginning_order_index = order_index
        
        for _ in range(num_orders):
            # decide the max lifetime for this order
            duration = max(0, round(random.gauss(ORDER_DURATION_MEAN, ORDER_DURATION_VAR)))
            
            # create the order
            new_order = Order(order_index, cur_time, peer_index, duration)
            global_id_order_mapping_table[order_index] = new_order
            order_index += 1
        
        order_id_set = set(range(beginning_order_index, order_index))
            
        # create the peer instance. Neighbor set is empty.
        new_peer = Peer(peer_index, cur_time, order_id_set, set())
        global_id_peer_mapping_table[peer_index] = new_peer
        peer_index += 1
        
    # update the latest order id and latest peer id
    latest_order_id = order_index
    latest_peer_id = peer_index
        
    # add neighbors to the peers
    
    set_of_all_peer_id = set(global_id_peer_mapping_table.keys())
    num_peers = len(global_id_peer_mapping_table)
        
    for peer_index, peer_instance in global_id_peer_mapping_table.items():
        # decide the set of neighbors
        base_set = set_of_all_peer_id - set([peer_index]) - set(peer_instance.id_neighbor_mapping.keys())
        size_set = max(0, min(round(num_peers * random.gauss(CONNECTIVITY_MEAN, CONNECTIVITY_VAR)), len(base_set)))
        num_remaining = max(0, size_set - len(peer_instance.id_neighbor_mapping))
        selected_set = set(random.sample(base_set, num_remaining))
        
        # add neighborhood
        for neighbor_id in selected_set:
            peer_instance.addNeighbor(neighbor_id)
            global_id_peer_mapping_table[neighbor_id].addNeighbor(peer_index)

# when a new peer arrives, it will bring a new set of orders. It only needs to specify the number of initial orders, 
# the function will specify the order IDs and the peer ID, which are the next integers to use, respectively.

def peerArrival(num_orders): 

    global global_id_peer_mapping_table
    global global_id_order_mapping_table
    global cur_time
    global latest_peer_id
    global latest_order_id
    
    # decide this peer's ID
    peer_id = latest_peer_id

    # create the initial orders for this peer and update global info for orders
    order_index = latest_order_id
    for _ in range(num_orders):
        duration = max(0, round(random.gauss(ORDER_DURATION_MEAN, ORDER_DURATION_VAR)))
        new_order = Order(order_index, cur_time, peer_id, duration)
        global_id_order_mapping_table[order_index] = new_order
        order_index += 1
    
    init_orderIDs = set(range(latest_order_id, order_index))

    # decide the neighbors for this new peer
    num_peers = len(global_id_peer_mapping_table)
    num_neighbors = max(0, min(num_peers, round(num_peers * random.gauss(CONNECTIVITY_MEAN, CONNECTIVITY_VAR))))    
    neighbor_id_set = random.sample(set(global_id_peer_mapping_table.keys()), num_neighbors)
    
    # create the new peer, and add it to the table
    new_peer = Peer(peer_id, cur_time, init_orderIDs, neighbor_id_set) # addNeighbor will be called through init
    global_id_peer_mapping_table[peer_id] = new_peer
    
    # for all its neighbors, add it to the neighbor list as well
    for neighbor_id in neighbor_id_set:
        neighbor_as_a_peer_instance = global_id_peer_mapping_table[neighbor_id]
        neighbor_as_a_peer_instance.addNeighbor(peer_id)

    # update latest IDs for peer and order
    latest_peer_id += 1
    latest_order_id = order_index
    
# this peer departs from the system.
# There is an option to cancel all orders it creats, by setting cancel_orders to be True.

def peerDeparture(peer_id, cancel_orders = False):
    global global_id_peer_mapping_table
    global global_id_order_mapping_table
    
    if peer_id not in global_id_peer_mapping_table:
        raise KeyError('Peer ID is not found.')
    
    # update number of replicas of all stored/pending orders with this peer

    peer_instance = global_id_peer_mapping_table[peer_id]
    for order_id in peer_instance.id_orderinfo_mapping.keys():
        global_id_order_mapping_table[order_id].num_replicas -= 1
        if global_id_order_mapping_table[order_id].num_replicas < 0:
            raise ValueError('Order replica number should not be negative. Something wrong.')
    
    for order_id, pending_orderlist in peer_instance.pending_id_orderinfo_mapping.keys():
        global_id_order_mapping_table[order_id].num_pending -= len(pending_orderlist)
        if global_id_order_mapping_table[order_id].num_pending < 0:
            raise ValueError('Order pending number should not be negative. Something wrong.')
    
    # update existing peers
    for other_peer in global_id_peer_mapping_table.values():
        if peer_id in other_peer.id_neighbor_mapping:
            other_peer.delNeighbor(peer_id)
            
    # disactivate all orders it created, optional
    if cancel_orders is True:
        for order in global_id_order_mapping_table.values():
            if order.creator == peer_id:
                order.setInvalid()
    
    # update peer global mapping table
    del global_id_peer_mapping_table[peer_id]

    
def orderArrival(target_peer_id, duration_time):
    global global_id_order_mapping_table
    global global_id_peer_mapping_table
    
    global cur_time
    global latest_order_id

    if target_peer_id not in global_id_peer_mapping_table:
        raise KeyError('The targeted peer does not exist.')
    
    # create a new order
    new_order_id = latest_order_id
    new_order = Order(new_order_id, cur_time, target_peer_id, duration_time)
    
    # update global info of this order
    global_id_order_mapping_table[new_order_id] = new_order
    latest_order_id += 1
    
    # update the order info to the target peer
    global_id_peer_mapping_table[target_peer_id].receiveOrderExternal(new_order_id)
    
def orderDeparture(order_id):
    global global_id_order_mapping_table
    
    if order_id not in global_id_order_mapping_table:
        raise KeyError('Order ID is not found.')

    # set the order to be invalid so that it will be deleted by the updateGlobalOrderbook function.
    global_id_order_mapping_table[order_id].setInvalid()

# the option deletion is False by default, where when an order is invalid, it is still in the mapping table.
# If the option is True, then the system will delete it from the global mapping table.
# in the current version, please use deletion = False. Otherwise, there might be some KeyError in execution.

def updateGlobalOrderbook(deletion = False):
    
    global global_id_order_mapping_table
    num_active = 0
    
    for idx in list(global_id_order_mapping_table):
        order = global_id_order_mapping_table[idx]
        
        # do deletion in the beginning so that newly deleted orders are still there for one round, to avoid KeyError.
        if deletion is True:
            # delete the order it is invalid
            if order.valid is False:
                del global_id_order_mapping_table[idx]
                
        # update expired and settled status
        order.updateExpiredStatus()
        order.updateSettledStatus()
        # update validity
        if order.updateValidness() is True:
            num_active += 1
            
    return num_active
        
'''
========================================================
Main simulation begins here.
========================================================
'''
cur_time = 0 # the current system time

latest_order_id = 0 # the next order ID that can be used
latest_peer_id = 0 # the next peer ID that can be used

global_id_peer_mapping_table = {} # mapping table from ID to peer instance
global_id_order_mapping_table = {} # mapping table from ID to order instance

# initialization
globalInit(NUM_PEERS)

for peer in global_id_peer_mapping_table.values():
    print('This is peer', peer.id, 'My orderbook size is', len(set(peer.id_orderinfo_mapping.keys())), 'and my neighbor size is', len(set(peer.id_neighbor_mapping.keys())))


for time in range(ROUND):
    
    cur_time = time
    print('round', time)
    
    # existing peers depart, sample from current peers
    peer_ids_to_depart = random.sample(set(global_id_peer_mapping_table.keys()), 1)
    
    for peer_id_to_depart in peer_ids_to_depart:
        peerDeparture(peer_id_to_depart)
     
    # existing orders depart, sample of current orders
    order_ids_to_depart = random.sample(set(global_id_order_mapping_table.keys()), 1)
    for order_id_to_depart in order_ids_to_depart:
        orderDeparture(order_id_to_depart)
      
    # new peers coming in, random process
    peerArrival(5)
        
    # new orders coming into pending list of peers
    target_peer_idx = random.sample(set(global_id_peer_mapping_table.keys()), 1)[0]
    orderArrival(target_peer_idx, ORDER_DURATION_MEAN)
    
    # system update of order validity
    updateGlobalOrderbook()
    
    # for each peer: (1) pull internal sharing orders into pending list,
    # (2) local order validity update, (3) storage decision (pending -> local storage),
    # and (4) sharing decision (local storage -> neighbor.order_id_revealing_set)

    for peer in global_id_peer_mapping_table.values():
        for neighbor_index in peer.id_neighbor_mapping:
            peer.receiveOrderInternal(neighbor_index)
            
    for peer in global_id_peer_mapping_table.values():
        peer.updateOrderinfoValidity()
            
    for peer in global_id_peer_mapping_table.values():
        peer.storeOrderDecision()
        
    for peer in global_id_peer_mapping_table.values():
        print('This is peer', peer.id, 'My orderbook size is', \
              len(set(peer.id_orderinfo_mapping.keys())), \
              'and my neighbor size is', len(set(peer.id_neighbor_mapping.keys())))

 