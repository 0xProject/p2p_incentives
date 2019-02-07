'''
===========================
P2P Orderbook simulator

Weijie Wu
Feb 6, 2019

===========================

Purpose:

This simulator works for the P2P architecture of sharing orders under the 0x protocol.
Its initial aim is to facilitate the decision of key design choices in such system.
It is not constriant by any particular design choice, but works as a platform so that
any mechanism can be plug into the simulator.

===========================

Structure:

This simulator uses a discrete time based structure. Events happen only at any discrete time points.
Later, we call "at any discrete time points" simply as "at any time."
In the initialization, a given # of peers are created, each with a certain # of orders.

At each time point:

- (1) a given set of peers depart, (2) a given set of orders becomes invalid,
  (3) a number of new peers arrive, and (4) external orders arrive (added to peers' pending table)
  
- For any peer in the system, it needs to (1) update its local orderbook (delete invalid ones),
  (2) add neighbors if needed, and (3) decide order acceptance (updating its pending table).

- If this is the end of a batch period, a peer needs to do additinoally:
  (1) decide order storing, and (2) decide order sharing.


Classes:

- Class Peer represents peers in the system.
- Class Neighbor represents the neighbors of a particular peer.
    A neighbor is physically another peer, but with some extra local information.
- Class Order represents orders in the system.
- Class OrderInfo represents an order instance stored in a peer's local storage or pending table.
    It is physically an order, but with some local information, e.g., who transmitted at what time.

===========================

Design details:


1. Departure of orders and peers:

- Deletion of an order (settled, expired, or due to owner cancellation):
    - Each time, the system will update the status of all orders.
        Invalid ones will be set Invalid. In the next time of update, these invalid orders will be deleted.
    - Every peer will update local status for OrderInfo instances. Invalid ones will be deleted.

- Deletion of a peer:
    - Both peer and neighbor instances will be deleted immediately.
    
2. Neighborhood relationship:

- Any neighborhood relationships must to be bilateral.
- A peer will try to maintain the size of neighbors within a certain range
    (NEIGHBOR_MIN, NEIGHBOR_MAX), unless it is impossible.
- Each time, each peer will check if the # of neighbors is enough. If not
    (# < NEIGHBOR_MIN), it will call the system function addNewLinks() to add new neighbors.
- The only way to create new links is calling addNewLinks().
    Procedure is: random selection of peers -> send invitation to the other party -> Accepted?
        - Y: both sides add neighbors
        - N: nothing happens.
    Accept or reject: Always accept if # of my neighbor has not reached NEIGHBOR_MAX.
- If neighbor departs (or is scored too low for a long time, to be implemented), neighborhood is cancelled.
    Procedure is: delete my neighbor - notify my neighbor (if he's still alive) to delete me too.

3. Order flows: arrival -> accept to pending table -> accept to local storage -> share it with others

3.1 Order arrival: two forms of arrival: internal and external.
    Internal: caused by a neighbor sharing an order. Can happen any time.
    External: caused by an external order arrival. Can also happen any time.
    If happend, the arrival will call the targeting peer's function receiveOrderInternal or receiveOrderExternal.

3.2 Order acceptance: The functions receiveOrderInternal or receiveOrderExternal can only be called by order sharing
    or external order arrival, at any time. These functions will determine whether to put the orders into the pendint table.
    
3.3 Order storing: This function can only be called from the main function proactively. No other function calls it.
    It runs only at the end of a batch period. It will decide whether to put pending orders into the local storage.
    Pending table will be cleared.
    
3.4 Order sharing: This function can only be called from the main function proactively, following storing.
    No other function calls it. It runs only at the end of a batch period.
    It will decide whether to share any stored order to any neighbor.
    It will call neighbor ranking function, which will first update neighbor scores.
    
Note: Peer init will directly put some orders into the local storage, without going through pending table.
    For new peers, the birthtime is the end of the 0th batch period, so order sharing will be called at birth.
    
    New neighbor establishment does not call any order-related operations.
    If I am an old peer but I am newly accepted by some other peer in the system as his neighbor,
    I need to wait till the end of batch period of the peer who accepted me, to receive his sharing;
    I will also wait till the end of my batch period, to share with him my orders.
         
===========================

Some Options:

- When an order is transmitted, we have an option "novelty" to indicate how may hops have this order been transmitted.
  If there is no fee sharing, we can disable this funtion since orders are not differentiable via hop numbers.
  If fee sharing is enabled, then enabling this feature will be useful (since some versions of a transmitted order can fill in
  a taker fee, some cannot).

- When a peer departs from the system, we have an option to delete all orders it created.
  If a peer simply goes offline but are still intersted in the orders it makes, then this option should not be enabled.
  If a peer departs pamenantly (by cancelling all orders and taking away everything in wallet, then this option should be enabled.

- When a peer A deletes a neighbor B, we have an option for A to delete orders that are transmitted
    from B (in which case we call B is the order's previous owner).
  Normally we don't need to enable this feature, but if this neighbor is malicious, you may want to delete all ordes from it.

===========================
 
Limitations:

- In blockchain, the status of an order settlement is based on consensus, so it is in an asymptotic sense.
  There might be different beliefs/forks due to lantency in P2P, but for now,
  we assume that there is some global grand truth for an order status.
  This simplification ignores races and may bring inaccuracy.

- Descrete time setting might be less accurate than event driven simulation.

- We do not model communication delay.

- Once there are more replicas of an order in the system, there is a better opportunity for settlement.
    This is not reflected.

- There is no "interest of topic" right now.

- Topology is totally random.
  
==========================

'''

# order related parameters

ORDER_LIFETIME_MEAN = 80
ORDER_LIFETIME_VAR = 20

# topology related parameters

NEIGHBOR_MAX = 30
NEIGHBOR_MIN = 20

# init period

BIRTH_TIME_SPAN = 20
INIT_SIZE = 10

# growing period

GROWING_RATE = 3
GROWING_TIME = 30
PEER_EARLY_QUIT_RATE = 0

ORDER_EARLY_EXTERNAL_ARRIVAL_RATE = 15
ORDER_EARLY_DEPARTURE_RATE = 15

# stable period

SIMULATION_ROUND = 100
PEER_ARRIVAL_RATE = 2
PEER_DEPARTURE_RATE = 2

ORDER_EXTERNAL_ARRIVAL_RATE = 15
ORDER_DEPARTURE_RATE = 15

# order propagation

BATCH_PERIOD = 10
OLD_ORDER_SHARE_PROB = 0.5
MUTUAL_HELPERS = 5
OPTIMISTIC_CHOICES = 3

# peer init related parameters

ORDERBOOK_SIZE_MEAN = 6 # initial orderbook size when a peer is created, mean
ORDERBOOK_SIZE_VAR = 1 # initial orderbook size when a peer is created, variance

# incentive parameters

SHARE_REWARD_A = 0 # for sharing an order already in my local storage, shared by the same peer
SHARE_REWARD_B = 0 # for shairng an order already in my local storage, shared by a different peer
SHARE_REWARD_C = 0 # for sharing an order that I accepted to pending table, but don't store finally
SHARE_REWARD_D = 1 # for sharing an order I decide to store
SHARE_REWARD_E = 0 # for sharing an order I have multiple copies in the pending table and decided to store a copy from someone else

SHARE_PENALTY_A = -1 # for sharing an invalid order
SHARE_PENALTY_B = -1 # for sharing an idential and duplicate order within the same batch

STORAGE_REWARD = 0 # storage reward for storing my sharing
STORAGE_PENALTY = 0 # penalty for being unwilling to store my orders

CONTRIBUTION_LENGTH = 3 # length of the score queue

'''
=======================================
Classes
=======================================
'''

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
        # Only God knows that. But we track them for simulation convenience.
        self.num_replicas = 0 
        self.num_pending = 0
        
        # set of peers who put this order into their local storage/pending list.
        self.holders = set() # len() = num_replicas
        self.hesitators = set() # len() != num_pending since there might be multiple copies for one ID
        
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
    
    def updateValidness(self):
        if (self.num_replicas == 0 and self.num_pending == 0) or (self.expired is True) or (self.settled is True):
            self.setInvalid()
        return self.valid
            
# Each peer maintains a set of neighbors. Note, a neighbor physically is a peer, but a neighbor instance is not a peer instance;
# instead, it has specialized information from a peer's viewpoint.
# For general information about this node, refer to the global mapping table and find the corrosponding peer instance.

class Neighbor:
    
    def __init__(self, neighbor_id, est_time, preference = None):
        
        global global_id_peer_mapping_table
        if neighbor_id not in global_id_peer_mapping_table:
            raise KeyError('This peer does not exist in the system and hance cannot be my neighbor.')
        
        self.id = neighbor_id # same as peer id
        self.preference = preference # refers to my "observation" of the neighbor (e.g., friend or foe). 
        self.est_time = est_time # establishment time

        
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
    
    def setPreference(self, new_preference): # changes my preference to this peer
        self.preference = new_preference
        

# This class OrderInfo is similar to Neighbor: An instance of an orderinfo is an order from a peers viewpoint.
# Note, an order instance can have multiple OrderInfo instances stored by different peers.
# It contains specifit information about the novelty and property of the order, not included in Order class.

class OrderInfo:
    
    def __init__(self, order_id, arrival_time, local_property = None, prev_owner = None, novelty = 0):
    
        global global_id_order_mapping_table
        if order_id not in global_id_order_mapping_table or global_id_order_mapping_table[order_id].valid is False:
            raise KeyError('Orderinfo cannot be initicated since the order does not exist or is invalid.')
        
        self.id = order_id
        self.arrival_time = arrival_time
        self.prev_owner = prev_owner # previous owner, default is None (a new order)
        self.novelty = novelty # how many hops it has travalled. Default is 0. Leave design space for TEC.
        
        # if a local property of orderinfo is specified, then use it. Otherwise, use the order property.
        # it can represent trading pairs of tokens, or anything of interest.
        
        if local_property is not None:
            self.local_property = local_property
        else:
            self.local_property = global_id_order_mapping_table[order_id].order_property
        
        # storage_decision is to record whether this peer decides to put this order into the storage.
        # It seems redundant, but it is actually useful in storeOrders function.
        self.storage_decision = False
    

class Peer:

    # Note: initialization deals with initial orders, but does not establish neighborhood relationships.
    
    def __init__(self, idx, birthtime, init_order_ids, max_neighbors, min_neighbors, preference = None):
        
        global global_id_order_mapping_table
        global global_id_peer_mapping_table
        global cur_time
        
        # simple parameter setting
        self.id = idx
        self.birthtime = birthtime
        self.preference = preference # A peers preference (e.g., deals in particular orders). May impact the storage decision.
        self.min_neighbors = min_neighbors # minimal # of neighbors to have
        self.max_neighbors = max_neighbors # max # of neighbors to have
        
        self.id_orderinfo_mapping = {} # mapping from id to orderinfo instances that have been formally stored.
        self.id_neighbor_mapping = {} # mapping from id to neighbor instance. Note, neighborhood relationship must be bilateral.
        
        self.new_order_id_set = set() # set of ids of newly and formally-stored orders that have NEVER been shared out by this peer.
        
        # the following mapping maintains a table of pending orders, by recording their orderinfo instance.
        # note that an order can have multiple orderinfo instances here, because it can be forwarded by different neighbors.
        # in such a case, the IDs of the instances are the same, but local local_property, prev_owner and novelty might be different.
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
                new_orderinfo = OrderInfo(order_id, cur_time, local_property)
                self.id_orderinfo_mapping[order_id] = new_orderinfo
                self.new_order_id_set.add(order_id)
                
                new_orderinfo.storage_decision = True # not sure if this is useful. Just keep it here to keep consistency.
                
                global_id_order_mapping_table[order_id].num_replicas += 1
                global_id_order_mapping_table[order_id].holders.add(self.id)
        
        
    # for each peer in each round, before executing anything, call this function to update the local orderinfo list.
    # for the local mapping, if an order is not valid any more, delete OrderInfo instance from the mapping.
    
    def updateOrderinfoValidity(self):
        
        global global_id_order_mapping_table
        
        for order_id in list(self.id_orderinfo_mapping):
            if order_id not in global_id_order_mapping_table:
                raise KeyError('updateOrderinfoValidity: Non-existance order.')
            if global_id_order_mapping_table[order_id].valid is False:
                del self.id_orderinfo_mapping[order_id]
                self.new_order_id_set.discard(order_id)
        
        for order_id in list(self.pending_id_orderinfo_mapping):
            if order_id not in global_id_order_mapping_table:
                raise KeyError('updateOrderinfoValidity: Non-existance order.')
            if global_id_order_mapping_table[order_id].valid is False: 
                del self.pending_id_orderinfo_mapping[order_id]
                
                
    # this function requests to add neighbors if the number of neighbors is not enough.
    # it aims at adding up to demand_num neighbors, but is fine if added up to min_num, or all possibilities have been tried.
    # The function returns the size of neighbors after update.
    # This function needs to be proactively and periodically called.
    
    def checkAddingNeighbor(self):
        cur_neighbor_size = len(self.id_neighbor_mapping)
        if cur_neighbor_size < self.min_neighbors:
            links_added = addNewLinks(self.id, self.max_neighbors - cur_neighbor_size, \
                                      self.min_neighbors - cur_neighbor_size)
        else:
            links_added = 0
            
        return cur_neighbor_size + links_added
            
    # This function is called when a request of establishing a neighborhood relationship is
    # called from another peer. This peer, which is requested, will return True for agreement by default,
    # or False if the cur # of neighbors already reaches the maximal.
    # Note, this function does not establish neighborhood relationship by itself. It accepts or rejects only.
    
    def acceptNeighborRequest(self, requester_id):
        
        if requester_id in self.id_neighbor_mapping:
            raise KeyError('You are my neighbor already. How come you request a connection again?')
        
        return len(self.id_neighbor_mapping) < self.max_neighbors
    
    
    # The following function establishes a neighborhood relationship.
    # It can only be called by the global function addNewLinks, where bilateral relationship is ganranteed.
        
    def addNeighbor(self, neighbor_id):
        
        global global_id_peer_mapping_table
        global cur_time
        
        # the neighbor must exists as a peer first.
        if neighbor_id not in global_id_peer_mapping_table:
            raise KeyError('No such peer.')
        
        # if this peer is already a neighbor, error with addNewLinks function.
        if neighbor_id in self.id_neighbor_mapping:
            raise KeyError('The addNewLinks function is requesting me to add my current neighbor.')
        
        # create new neighbor in my local storage
        new_neighbor = Neighbor(neighbor_id, cur_time)
        self.id_neighbor_mapping[neighbor_id] = new_neighbor
        
    # This function defines what to do if I am notified by someone for cancelling a neighborhood relationship.
    # Normally, I accept and deletes him from my neighbor.
        
    def acceptNeighborCancellation(self, requester_id, remove_order = False):
        
        global global_id_peer_mapping_table
        
        if requester_id not in global_id_peer_mapping_table:
            raise KeyError('I am receiving cancellation notification from someone non-existing.')
        
        if requester_id in self.id_neighbor_mapping:
            self.delNeighbor(requester_id, remove_order, False)
        
        
    # this function deletes a neighbor. If remove_order is True, then all orderinfo instances with the
    # prev_owner being this neighbor will also be deleted (order instances are still there).
    # It is allowed to delete a neighbor if it is no longer a valid peer now.
    # notification: whether to notify the other party to cancel neighborhood.
    
    def delNeighbor(self, neighbor_id, remove_order = False, notification = True): 
        
        global global_id_peer_mapping_table
        
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
                        order_instance.holders.remove(self.id)
                    self.new_order_id_set.discard(order_id)
                    del self.id_orderinfo_mapping[order_id]
                    
            for order_id, orderinfolist in self.pending_id_orderinfo_mapping.values():
                order_instance = global_id_order_mapping_table[order_id]
                for idx, orderinfo in enumerate(orderinfolist):
                    if orderinfo.prev_owner == neighbor_id:
                        if order_instance.valid is True:
                            order_instance.num_pending -= 1
                        del orderinfolist[idx]
                if orderinfolist == []: # no pending order under this id. need to delete this entry
                    order_instance.hesitators.remove(self.id) 
                    del self.pending_id_orderinfo_mapping[order_id]
        
        # if this neighbor is still an active peer, notify him to delete me as well.
        if notification is True:
            if neighbor_id in global_id_peer_mapping_table:
                global_id_peer_mapping_table[neighbor_id].acceptNeighborCancellation(self.id, False)
        
        # delete this neighbor
        del self.id_neighbor_mapping[neighbor_id] 
    
    # receiveOrderExternal() is called by orderArrval function.
    # OrderInfo will be put into pending table (just to keep consistent with receive_internal,
    # though most likely it will be accepted).
    # return True if accept or False otherwise
    
    def receiveOrderExternal(self, order_id):
        
        def storeExtHelper(ext_order):
            '''
            Design space begins here.
            Naive implementation:
            return True for all.
            '''
            return ext_order.valid
        
        if order_id in self.pending_id_orderinfo_mapping:
            raise KeyError('Abnormal external order. This order is now pending for storing decision.')
        if order_id in self.id_orderinfo_mapping:
            raise KeyError('Abnormal external order. This order is already in my local order list.')
        
        global global_id_order_mapping_table
        global cur_time
        
        if order_id not in global_id_order_mapping_table:
            raise KeyError('This order does not exist.')
        order_instance = global_id_order_mapping_table[order_id]
        
        if storeExtHelper(order_instance) is True:
            
            # create the orderinfo instance and add it into the local mapping table
            new_orderinfo = OrderInfo(order_id, cur_time)
            self.pending_id_orderinfo_mapping[order_id] = [new_orderinfo]
            
            # update the number of replicas for this order and hesitator of this order
            global_id_order_mapping_table[order_id].num_pending += 1
            global_id_order_mapping_table[order_id].hesitators.add(self.id)
            
            return True
        
        return False

    # receiveOrderInternal() is called by shareOrder function. It will immediately decide whether
    # to put order_id shared from neighbor_id into the pending table.
    # when novelty_update is True, its count will increase by one once transmitted.
    # Return True if accept and False otherwise.
    
    def receiveOrderInternal(self, neighbor_id, order_id, novelty_update = False):
        
        global global_id_peer_mapping_table
        global global_id_order_mapping_table
        global cur_time
        
        if neighbor_id not in global_id_peer_mapping_table:
            raise KeyError('Neighbor peer not found.')
        if order_id not in global_id_order_mapping_table:
            raise KeyError('Order not found.')
        
        # find the global peer instance for my neighbor
        cur_neighbor_as_a_peer_instance = global_id_peer_mapping_table[neighbor_id]
        
        # find the order instance
        order_instance = global_id_order_mapping_table[order_id]
        
        # neighbor_id and self must be neighbors of each other
        if self.id not in cur_neighbor_as_a_peer_instance.id_neighbor_mapping \
           or neighbor_id not in self.id_neighbor_mapping:
            raise KeyError('Order transmission cannot be peformed between non-neighbors.')
        
        # the instance for the neighbor sending this order.
        neighbor_instance = self.id_neighbor_mapping[neighbor_id]
        
        # the neighbor instance of myself stored by the sender
        myself_as_a_neighbor_instance = cur_neighbor_as_a_peer_instance.id_neighbor_mapping[self.id]
        
        if order_instance.valid is False:
            # update the contribution of my neighbor for his sharing
            neighbor_instance.share_contribution[-1] += SHARE_PENALTY_A
            # update my neighbor's record of me for my storage contribution
            myself_as_a_neighbor_instance.storage_contribution[-1] += STORAGE_PENALTY
            return False
        
        if order_id in self.id_orderinfo_mapping: # no need to store again
            if self.id_orderinfo_mapping[order_id].prev_owner == neighbor_id:
                # I have this order in my local storage.
                # my neighbor is sending me the same order again.
                # It may be due to randomness of sharing old orders.
                # no need to update storage contribution since the order is there.
                neighbor_instance.share_contribution[-1] += SHARE_REWARD_A
            else:
                # I have this order in my local storage, but it was from someone else.
                # No need to store it anymore. Just update the reward for the uploader.
                neighbor_instance.share_contribution[-1] += SHARE_REWARD_B
                myself_as_a_neighbor_instance.storage_contribution[-1] += STORAGE_PENALTY
            return False
            
        # if this order has not been formally stored.
        # Need to write it into the pending table (even if there has been one with the same ID).            
        if novelty_update is True:
            order_novelty = cur_neighbor_as_a_peer_instance.id_orderinfo_mapping[order_id].novelty + 1
        else:
            order_novelty = cur_neighbor_as_a_peer_instance.id_orderinfo_mapping[order_id].novelty
                    
        # create an orderinfo instance and add to the pending table
        new_orderinfo = OrderInfo(order_id, cur_time, None, neighbor_id, order_novelty)
                    
        # if not in the pending list, need to add it to the pending_id_orderinfo_mapping
        if order_id not in self.pending_id_orderinfo_mapping: # order id not in the pending set 
            self.pending_id_orderinfo_mapping[order_id] = [new_orderinfo]
            global_id_order_mapping_table[order_id].num_pending += 1
            global_id_order_mapping_table[order_id].hesitators.add(self.id)
            # put into the pending table. share/storage reward will be updated when a storing decision is made.
            return True
                        
        # if already in the pending list, check if this order is from the same prev_owner.    
        for existing_orderinfo in self.pending_id_orderinfo_mapping[order_id]:
            if neighbor_id == existing_orderinfo.prev_owner:
                # this neighbor is sending duplicates to me in a short period of time
                # Likely to be a malicious one.
                # neighbor does not need to update storage contirbution
                neighbor_instance.share_contribution[-1] += SHARE_PENALTY_B
                return False
                
        # my neighbor is honest, but he is late in sending me the message.
        # Add it to the pending list anyway since later, his version of the order might be selected.
        self.pending_id_orderinfo_mapping[order_id].append(new_orderinfo)
        global_id_order_mapping_table[order_id].num_pending += 1
        
        # no need to add hesitator since I am already a hesitator.
        # share reward will be updated when a storing decision is made.
        
        return True
                            
        
    def storeOrders(self):
        
        global cur_time
        
        if (cur_time - self.birthtime) % BATCH_PERIOD != 0:
            raise RuntimeError('Store order decision should not be called at this time.')
        
        global global_id_order_mapping_table
        global global_id_peer_mapping_table
    
        '''
        ===========================
        design space begins here.
        change instance.storage_decision to True if you would like to store this order.
        Later part of this function will take care of such orders and write them into the local storage.
        This decision process must make sure that for the set of pending orders
        with the same id, at most one will be selected.
        below is a naive one that labels the first entry of each pending orderinfolist as True.
        ===========================
        '''
        
        for idx, pending_orderinfolist_of_same_id in self.pending_id_orderinfo_mapping.items():
            if global_id_order_mapping_table[idx].valid is False:
                for orderinfo in pending_orderinfolist_of_same_id:
                    orderinfo.storage_decision = False
            else: # it is a valid order
                pending_orderinfolist_of_same_id[0].storage_decision = True # first orderinfo of idx is stored
                for orderinfo in pending_orderinfolist_of_same_id[1:]: # the rest (if any) are not stored
                    orderinfo.storage_decision = False
                    
        # Now store an order if necessary
        
        for idx, pending_orderinfolist_of_same_id in self.pending_id_orderinfo_mapping.items():
            
            if idx not in global_id_order_mapping_table:
                raise KeyError('This order does not exist.')
            
            # sort the list of pending orderinfo with the same id, so that if
            # there is some order to be stored, it will be the first one.
            pending_orderinfolist_of_same_id.sort(key = lambda item: item.storage_decision, reverse = True)
            
            # find the global order instance for all orderinfo in this list,
            # update its number of pending orders, and remove the hesitator, in advance.
            
            pending_orderinfo_as_an_order_instance = global_id_order_mapping_table[idx]
            pending_orderinfo_as_an_order_instance.num_pending -= len(pending_orderinfolist_of_same_id)
            pending_orderinfo_as_an_order_instance.hesitators.remove(self.id)
            
            # after sorting, for all pending orderinfo with the same id,
            # either (1) no one is to be stored, or (2) only the first one is stored
            
            if pending_orderinfolist_of_same_id[0].storage_decision is False: # if nothing is to be stored
                for pending_orderinfo in pending_orderinfolist_of_same_id:
                    # find the global instance of the sender, and update it.
                    if pending_orderinfo.prev_owner in self.id_neighbor_mapping: # internal order, sender is still a neighbor
                        sender_as_a_peer_instance = global_id_peer_mapping_table[pending_orderinfo.prev_owner]
                        sender_as_a_peer_instance.id_neighbor_mapping[self.id].storage_contribution[-1] += STORAGE_PENALTY
                        self.id_neighbor_mapping[pending_orderinfo.prev_owner].share_contribution[-1] += SHARE_REWARD_C
            
            else: # the first element is to be stored
                first_pending_orderinfo = pending_orderinfolist_of_same_id[0]
                # find the global instance for the sender, and update it.
                if first_pending_orderinfo.prev_owner in self.id_neighbor_mapping: # internal order, sender is still neighbor
                    first_sender_as_a_peer_instance = global_id_peer_mapping_table[first_pending_orderinfo.prev_owner]
                    first_sender_as_a_peer_instance.id_neighbor_mapping[self.id].storage_contribution[-1] += STORAGE_REWARD
                    self.id_neighbor_mapping[first_pending_orderinfo.prev_owner].share_contribution[-1] += SHARE_REWARD_D
                # add the order into the local storage, and update the global order instance
                self.id_orderinfo_mapping[idx] = first_pending_orderinfo
                self.new_order_id_set.add(idx)
                pending_orderinfo_as_an_order_instance.num_replicas += 1
                pending_orderinfo_as_an_order_instance.holders.add(self.id)
                
                
                # for the rest pending orderinfo in the list, no need to store them, but may need to do other updates
                for pending_orderinfo in pending_orderinfolist_of_same_id[1:]:
                    
                    if pending_orderinfo.storage_decision is True:
                        raise ValueError('Should not store multiple orders. Wrong in storage decision process.')
                    
                    if pending_orderinfo.prev_owner in self.id_neighbor_mapping: # internal order, sender is still neighbor
                        # update the share contribution
                        self.id_neighbor_mapping[pending_orderinfo.prev_owner].share_contribution[-1] += SHARE_REWARD_E
                        # find the global instance for the sender
                        sender_as_a_peer_instance = global_id_peer_mapping_table[pending_orderinfo.prev_owner]
                        # if their novelties are the same, then they are indistinguishable.
                        # so you can just pretend that you're storing the order for the sender (though you're storing it for someone else)
                        if pending_orderinfo.novelty == first_pending_orderinfo.novelty:
                            # update the sender instance
                            sender_as_a_peer_instance.id_neighbor_mapping[self.id].storage_contribution[-1] += STORAGE_REWARD
                        else:
                            # the orders are distinguishable. No way to take advantage. Update the sender instance.
                            sender_as_a_peer_instance.id_neighbor_mapping[self.id].storage_contribution[-1] += STORAGE_PENALTY
                        
        # clear the pending mapping table                
        self.pending_id_orderinfo_mapping.clear()
        
        
    # shareOrders() function determines which orders to be shared to which neighbors.
    # It will call internal order receiving function of the receiver peer.
    # This function is only called by the main function at the end of a batch period.

    def shareOrders(self):
        
        # this function has to go through order by order and neighbor by neighbor.
        global cur_time
        
        if ( cur_time - self.birthtime ) % BATCH_PERIOD != 0:
            raise RuntimeError('Share order decision should not be called at this time.')
        
        global global_id_order_mapping_table
        global global_id_peer_mapping_table
        
        new_order_id_set = self.new_order_id_set
        old_order_id_set = set(self.id_orderinfo_mapping.keys()) - self.new_order_id_set
        
        '''
        The following funtion defines what orders to share with a particular neighbor.
        Default setting: share every new order and randomly select some old orders to share.
        '''
        
        def shareOrdersToSingleNeighbor(neighbor_id):
            
            neighbor_as_a_peer_instance = global_id_peer_mapping_table[neighbor_id]
            
            for order_id in new_order_id_set:
                if order_id not in global_id_order_mapping_table\
                   or global_id_order_mapping_table[order_id].valid is False:
                    raise ValueError('Invalid order to be shared.')
                
                neighbor_as_a_peer_instance.receiveOrderInternal(self.id, order_id)
                
            for order_id in old_order_id_set:
                if order_id not in global_id_order_mapping_table\
                   or global_id_order_mapping_table[order_id].valid is False:
                    raise ValueError('Invalid order to be shared.')
                
                random_number = random.random()
                if random_number < OLD_ORDER_SHARE_PROB:
                    neighbor_as_a_peer_instance.receiveOrderInternal(self.id, order_id)
                    
        '''
        The following function decides the set of neighbors to share with.
        This is the design space.
        Default: If I am new, share to random ones (# = MUTUAL_HELP + OPTIMISTIC_CHOICES).
        If I am old, share to MUTUAL_HELP highly-reputated neighbors, and OPTIMISTIC_CHOICES random low-reputated neighbors.
        '''
        
        def selectNeighborsToShare():
            
            set_neighbor_id_to_share = set()
            
            if ( cur_time == self.birthtime): # This is a new peer. random select neighbors
                for neighbor_id in random.sample(self.id_neighbor_mapping.keys(), \
                                                 min(len(self.id_neighbor_mapping.keys()), MUTUAL_HELPERS + OPTIMISTIC_CHOICES)):
                    set_neighbor_id_to_share.add(neighbor_id)
            else: # This is an old peer
                ranked_id_list_of_neighbors = self.rankNeighbors()
                highly_ranked_neighbors_list = ranked_id_list_of_neighbors[:MUTUAL_HELPERS]
                lowly_ranked_neighbors_list = ranked_id_list_of_neighbors[MUTUAL_HELPERS:]
                for neighbor_id in highly_ranked_neighbors_list:
                    set_neighbor_id_to_share.add(neighbor_id)
                for neighbor_id in random.sample(lowly_ranked_neighbors_list, min(len(lowly_ranked_neighbors_list), OPTIMISTIC_CHOICES)):
                    set_neighbor_id_to_share.add(neighbor_id)
                    
            for neighbor_id in set_neighbor_id_to_share:
                if neighbor_id not in global_id_peer_mapping_table:
                    raise ValueError('Non-existant neighbor was seleted.')
                
            return set_neighbor_id_to_share
        
        # share every order to every correct peer:
        
        for neighbor_id in selectNeighborsToShare():   
            shareOrdersToSingleNeighbor(neighbor_id)
            
        # clear the new order set. Every order becomes old.        
        self.new_order_id_set.clear()
    
     
    # this function deletes a valid orderinfo instance. Now, it is not called anywhere in the simulator.
    # We just put it here for future use.
    # for the case where an order becomes invalid, updateOrderinfoValidity() will delete it.
    
    def delOrder(self, order_id):
        
        global global_id_order_mapping_table
        if order_id not in global_id_order_mapping_table:
            raise KeyError('This order does not exist.')

        global_order_instance = global_id_order_mapping_table[order_id]
        
        # check if this order is in the pending table
        if order_id in self.pending_id_orderinfo_mapping:
            global_order_instance.num_pending -= len(self.pending_id_orderinfo_mapping[order_id])
            global_order_instance.hesitators.remove(self.id)
            del self.pending_id_orderinfo_mapping[order_id]
        
        # check if this order is in the local storage
        if order_id in self.id_orderinfo_mapping:
            global_order_instance.num_replicas -= 1
            global_order_instance.holders.remove(self.id)
            self.new_order_id_set.discard(order_id)
            del self.id_orderinfo_mapping[order_id]
            
    # This function updates neighbor score, by (1) calculating the current score according to the queue
    # and (2) update the queue by moving one step forward and delete the oldest element.
    # It is called by rankNeighbor function.
    
    def updateNeighborScore(self):
        
        '''
        ============================
        design space:
        how to decide a neighbors score?
        how to decide the discount factor?
        Below we simply return scores of share and storage, where storage score is 0.
        Discounts are all 1.
        ============================
        '''
        
        discount_share = [0.7, 0.8, 1]
        discount_storage = [0.7, 0.8, 1]
        
        def scoreCalculator(share, storage):
            return share
        
        global cur_time
        
        for neighbor in self.id_neighbor_mapping.values():
            
            neighbor_total_share_contribution = sum(a * b for a, b in zip(neighbor.share_contribution, discount_share))
            neighbor_total_storage_contribution = sum(a * b for a, b in zip(neighbor.storage_contribution, discount_storage))
            
            #neighbor_total_share_contribution = sum(share for share in neighbor.share_contribution)
            #neighbor_total_storage_contribution = sum (store for store in neighbor.storage_contribution)
            
            neighbor.score = scoreCalculator(neighbor.total_share_contribution, neighbor.total_storage_contribution)
            
            # update the contribution queue since it is the end of a calculation circle
            
            neighbor.share_contribution.popleft()
            neighbor.share_contribution.append(0) 
            
            neighbor.storage_contribution.popleft()
            neighbor.storage_contribution.append(0)
    
    # This function ranks neighbors according to their scores. It is called by shareOrders function
    # It returns a list of neighbor IDs with the highest score in the front.
    
    def rankNeighbors(self):
        
        self.updateNeighborScore()
        
        neighbor_list = list(self.id_neighbor_mapping.values())
        neighbor_list.sort(key = lambda item: item.score, reverse = True)
        return [item.id for item in neighbor_list]
    
    
    # This function measures the fairness of the incentive scheme.
    # There is no implemetion for now, and it is called from nowhere.
    
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


def globalInit(init_size_peer, birth_time_span):
    
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
    peer_index = latest_peer_id # same thing as above
    
    # first create all peer instances with no neighbors
    
    for _ in range(init_size_peer):
        
        # decide the birth time for this peer
        birth_time = random.randint(0, birth_time_span - 1)
        
        # decide the number of orders for this peer
        num_orders = max(0, round(random.gauss(ORDERBOOK_SIZE_MEAN, ORDERBOOK_SIZE_VAR)))

        # create all order instances, and the initial orderbooks
        beginning_order_index = order_index
        
        for _ in range(num_orders):
            # decide the max lifetime for this order
            duration = max(0, round(random.gauss(ORDER_LIFETIME_MEAN, ORDER_LIFETIME_VAR)))
            
            # create the order. Order's birth time is cur_time, different from peer's birthtime.
            new_order = Order(order_index, cur_time, peer_index, duration)
            global_id_order_mapping_table[order_index] = new_order
            order_index += 1
        
        order_id_set = set(range(beginning_order_index, order_index))
        
        # create the peer instance. Neighbor set is empty.
        new_peer = Peer(peer_index, birth_time, order_id_set, NEIGHBOR_MAX, NEIGHBOR_MIN)
        
        global_id_peer_mapping_table[peer_index] = new_peer
        peer_index += 1
        
    # update the latest order id and latest peer id
    latest_order_id = order_index
    latest_peer_id = peer_index
        
    # add neighbors to the peers. Use shuffle function to avoid preference of forming neighbors for
    # peers with small id.
    keys = list(global_id_peer_mapping_table.keys())
    random.shuffle(keys)
    
    for peer_id in keys:
        peer = global_id_peer_mapping_table[peer_id]
        peer.checkAddingNeighbor()
        
    
# The following function helps the peer with requester_id to add neighbors.
# It targets at adding demand_num neighbors, but is fine if the final added #
# is in the range [min_num, demand_num], or stop when all possible links are added.
# This function will call the corresponding peers' functions to add the neighbors, respectively.
# finally, this function will output the # of links established.

def addNewLinks(requester_id, demand, minimum):
    
    '''
    ============================
    Design space:
    How to perform the selection. Right now: random.
    ============================
    '''
    
    # this function is a helper function to addNewLinks. It takes in a base set and a targeted number,
    # and outputs a subset of the base set whose size is targeted number, or all items are selected.
    
    def selectionFromBase(base, target_number):
        
        if not base or not target_number:
            raise ValueError('Base set is empty or target number is zero.')
        
        # if the target number is larger than the set size, output the whole set.
        try:
            return_set = set(random.sample(base, min(target_number, len(base))))
        except ValueError:
            print(len(base), target_number)
        
        return return_set
             
    if requester_id not in global_id_peer_mapping_table:
        raise KeyError('Request from a non-existance peer.')
    if demand <= 0 or minimum < 0 or demand < minimum:
        raise ValueError('Wrong in requested number or range.')
    
    requester_instance = global_id_peer_mapping_table[requester_id]
    pool = set(global_id_peer_mapping_table.keys()) - set([requester_id])
    selection_size = demand
    links_added = 0
    
    while links_added < minimum and pool:
        
        links_added_this_round = 0
        
        selected_peer_id_set = selectionFromBase(pool, selection_size)
        
        for candidate_id in selected_peer_id_set:
            
            if candidate_id not in global_id_peer_mapping_table:
                raise KeyError('Some non-existance peer was selected. Wrong.')
            candidate_instance = global_id_peer_mapping_table[candidate_id]
            
            # if this peer_id is already the requester's neighbor, ignore.
            if candidate_id not in requester_instance.id_neighbor_mapping:
                # check if the candidate is willing to add the requester.
                if candidate_instance.acceptNeighborRequest(requester_id) is True:
                    # mutual add neighbors
                    candidate_instance.addNeighbor(requester_id)
                    requester_instance.addNeighbor(candidate_id)
                    links_added += 1
                    links_added_this_round += 1
                    
        pool -= selected_peer_id_set
        selection_size -= links_added_this_round
    
    return links_added

        
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
        duration = max(0, round(random.gauss(ORDER_LIFETIME_MEAN, ORDER_LIFETIME_VAR)))
        new_order = Order(order_index, cur_time, peer_id, duration)
        global_id_order_mapping_table[order_index] = new_order
        order_index += 1
    
    init_orderIDs = set(range(latest_order_id, order_index))
    
    # create the new peer, and add it to the table
    new_peer = Peer(peer_id, cur_time, init_orderIDs, NEIGHBOR_MAX, NEIGHBOR_MIN)
    global_id_peer_mapping_table[peer_id] = new_peer
    
    # add neighbors
    new_peer.checkAddingNeighbor()
    
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
        global_id_order_mapping_table[order_id].holders.remove(peer_id)
    
    for order_id, pending_orderlist in peer_instance.pending_id_orderinfo_mapping.items():
        global_id_order_mapping_table[order_id].num_pending -= len(pending_orderlist)
        global_id_order_mapping_table[order_id].hesitators.remove(peer_id)
    
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

 
# This function creates external order arrival

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
    
    
# This function proactively invalidate an order.

def orderDeparture(order_id):
    
    global global_id_order_mapping_table
    
    if order_id not in global_id_order_mapping_table:
        raise KeyError('Order ID is not found.')
    
    if global_id_order_mapping_table[order_id].valid is False:
        raise KeyError('An invalid order cannot depart again.')

    # set the order to be invalid so that it will be deleted by the updateGlobalOrderbook function.
    global_id_order_mapping_table[order_id].setInvalid()

# Invalidate expired or settled orders and delete them if appropriate.
# Return the set of valid order IDs.

def updateGlobalOrderbook():
    
    global global_id_order_mapping_table
    
    #num_active = 0
    cur_active_order_id_set = set()
    
    for idx in list(global_id_order_mapping_table):
        order = global_id_order_mapping_table[idx]
        
        # delete invalid orders, labeled in the last round.
        # so that new invalid orders are still there for one round, to avoid KeyError.
        if order.valid is False:
            del global_id_order_mapping_table[idx]
                
        # update expired and settled status
        order.updateExpiredStatus()
        order.updateSettledStatus()
        
        # update validity
        if order.updateValidness() is True:
            cur_active_order_id_set.add(idx)
            
    return cur_active_order_id_set

# the following function prints out the spreading ratio of orders in the same age.
# printout is a list, each element being the spreading ratio of orders of the same age (starting from 0 till the maximal age)
# if all orders of a particular age (smaller than max age) are all invalid, then string 'None' is printed.
# the spreading ratio is defined as the # of peers holding this order, over the total # of peers in the system at cur time.

def printOrderSpreadingRatio():
    
    global global_id_order_mapping_table
    global cur_time
    
    num_active_peers = len(global_id_peer_mapping_table)
    max_age = cur_time - min(order.birthtime for order in global_id_order_mapping_table.values() if order.valid is True)
    order_spreading_ratio = [[] for _ in range(max_age + 1)]

    for order in global_id_order_mapping_table.values():
        if order.valid is True:
            ratio = order.num_replicas / num_active_peers
            order_spreading_ratio[cur_time - order.birthtime].append(ratio)
        
    for index, sublist in enumerate(order_spreading_ratio):
        if sublist != []:
            order_spreading_ratio[index] = sum(item for item in sublist) / len(sublist)
        else:
            order_spreading_ratio[index] = None

    print(order_spreading_ratio)

# The following function runs normal operations at a particular time point.
# It includes peer/order dept/arrival, order status update,
# and peer's order acceptance, storing, and sharing.

def operationsInATimeRound(peer_dept_rate, peer_arr_rate, order_dept_rate, order_arr_rate):
    
    global cur_time
        
    # peers leave
    
    peer_ids_to_depart = random.sample(set(global_id_peer_mapping_table.keys()), peer_dept_rate)
    for peer_id_to_depart in peer_ids_to_depart:
        peerDeparture(peer_id_to_depart)
    
    # new peers come in
    
    for _ in range(peer_arr_rate):
        num_init_orders = max(0, round(random.gauss(ORDERBOOK_SIZE_MEAN, ORDERBOOK_SIZE_VAR)))
        peerArrival(num_init_orders)
          
    # external order arrival
    
    for _ in range(order_arr_rate):
        # decide which peer to hold this order
        target_peer_idx = random.sample(set(global_id_peer_mapping_table.keys()), 1)
        # decide the max lifetime for this order
        duration = max(0, round(random.gauss(ORDER_LIFETIME_MEAN, ORDER_LIFETIME_VAR)))    
        orderArrival(target_peer_idx[0], duration)
    
    # system update of order validity
    active_order_id_set = updateGlobalOrderbook()
    
    # existing orders depart
    
    order_ids_to_depart = random.sample(active_order_id_set, order_dept_rate)
    for order_id_to_depart in order_ids_to_depart:
        orderDeparture(order_id_to_depart)
        
    # peer operations
    for peer in global_id_peer_mapping_table.values():
        peer.checkAddingNeighbor()
            
    for peer in global_id_peer_mapping_table.values():
        peer.updateOrderinfoValidity()
            
    for peer in global_id_peer_mapping_table.values():
        if (cur_time - peer.birthtime ) % BATCH_PERIOD == 0:
            peer.storeOrders()
            peer.shareOrders()

        
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

# initialization, orders are only held by creators

globalInit(INIT_SIZE, BIRTH_TIME_SPAN)

updateGlobalOrderbook()

# growth period [BIRTH_TIME_SPAN, BIRTH_TIME_SPAN + GROWING_TIME]

for time in range(BIRTH_TIME_SPAN, BIRTH_TIME_SPAN + GROWING_TIME):
    cur_time = time
    operationsInATimeRound(PEER_EARLY_QUIT_RATE, GROWING_RATE, ORDER_EARLY_DEPARTURE_RATE, ORDER_EARLY_EXTERNAL_ARRIVAL_RATE)

# from round 1 and onward, we allow peer departure, order departure, peer arrival, and order arrival.

for time in range(BIRTH_TIME_SPAN + GROWING_TIME, BIRTH_TIME_SPAN + GROWING_TIME + SIMULATION_ROUND):
    cur_time = time
    operationsInATimeRound(PEER_DEPARTURE_RATE, PEER_ARRIVAL_RATE, ORDER_DEPARTURE_RATE, ORDER_EXTERNAL_ARRIVAL_RATE)
    
printOrderSpreadingRatio()
 