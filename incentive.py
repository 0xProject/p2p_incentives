'''
===========================
P2P Orderbook simulator

Weijie Wu
March 19, 2019

===========================

Purpose

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

- If this is the end of a batch period, a peer needs to do additionally:
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
        Invalid ones will be set Invalid and will be deleted.
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
- If neighbor departs or it is considered as lazy (score is too low) for a long time, neighborhood is cancelled.
    Procedure is: delete my neighbor - notify my neighbor (if he's still alive) to delete me too.

3. Order flows: arrival -> accept to pending table -> accept to local storage -> share it with others

3.1 Order arrival: two forms of arrival: internal and external.
    Internal: caused by a neighbor sharing an order. Can happen any time.
    External: caused by an external order arrival. Can also happen any time.
    If happend, the arrival will call the targeting peer's function receiveOrderInternal or receiveOrderExternal.

3.2 Order acceptance: The functions receiveOrderInternal or receiveOrderExternal can only be called by order sharing
    or external order arrival, at any time. These functions will determine whether or not to put the orders into the pending table.
    
3.3 Order storing: This function can only be called from the main function proactively. No other function calls it.
    It runs only at the end of a batch period. It will decide whether to put pending orders into the local storage.
    Pending table will be cleared.
    
3.4 Order sharing: This function can only be called from the main function proactively, following order storing function's execution.
    No other function calls it. It runs only at the end of a batch period.
    It will decide whether to share any stored order to any neighbor.
    It will call neighbor ranking function, which will first update neighbor scores.
    
Note: Peer init will directly put some orders into the local storage, without going through pending table.
    For new peers, the birthtime is the end of the 0th batch period, so order sharing will be called at birth.
    
    New neighbor establishment does not call any order-related operations.
    That being said, if I am an old peer but I am newly accepted by some other peer in the system as his neighbor,
    I need to wait till the end of batch period of the peer who accepted me, to receive his sharing;
    I will also wait till the end of my batch period, to share with him my orders.
         
===========================

Some Options:

- When an order is transmitted, we have an option "novelty" to indicate how may hops have this order been transmitted.
  If there is no fee sharing, we can disable this funtion since orders are not differentiable via hop numbers.
  If fee sharing is enabled, then enabling this feature will be useful (since some versions of a transmitted order can fill in
  a taker fee, some cannot).

- When a peer A deletes a neighbor B, we have an option for A to delete orders that are transmitted
    from B (in which case we call B is the order's previous owner).
  Normally we don't need to enable this feature, but if this neighbor is malicious, you may want to delete all ordes from it.

===========================
 
Limitations:

- In blockchain, the status of an order settlement is based on consensus, so it is in an asymptotic sense.
  There might be different beliefs/forks due to latency in P2P, but for now,
  we assume that there is some global grand truth for an order status.
  This simplification ignores races and may bring inaccuracy.

- Discrete time setting might be less accurate than event driven simulation.

- We do not model communication delay.

- Once there are more replicas of an order in the system, there is a better opportunity for settlement.
    This is not reflected.

- There is no namespacing (i.e., peers have particular interest in some trading pairs and only store/share these orders) right now.

- Neighborhood topology is totally random.
  
==========================
'''

import collections
import random
import statistics
import matplotlib.pyplot as plt
import numpy


'''
=======================
Parameters
=======================
'''

'''
SIMULATION_ROUNDS is the number of times the simulator is run.
This is NOT the time rounds of order propagation.
Instead, in each round of simulation, there will be certain time rounds where orders are created, propogated, and settled,
and we will run the whole process for SIMULATION_ROUNDS times.
The reason is there is some randomness in the simulator, so in order to smooth the
final result, we need to run the simulator multiple times and take the average.
'''

SIMULATION_ROUNDS = 40

''' Orders and peers '''

# order related parameters

ORDER_EXPIRATION_MEAN = 50 # time for an order to expire, mean
ORDER_EXPIRATION_VAR = 10 # time for an order to expire, variance

# peer related parameters

NEIGHBOR_MAX = 30 # neighborhood size, max
NEIGHBOR_MIN = 20 # neighborhood size, min. Only exception is the peer has tried all possibilities but can't reach this number.

LAZY_NEIGHBOR_CONTRI_THRESHOLD = 2 # If a neighbor's score is under this value, it is "lazy" in this batch
LAZY_NEIGHBOR_LENGTH_THRESHOLD = 6 # If a neighbor has been lazy for this number of batches, it is permanently lazy and kicked off from neighborhood.

BATCH_PERIOD = 10 # length of a batch period

ORDERBOOK_SIZE_MEAN = 6 # initial orderbook size when a peer is created, mean
ORDERBOOK_SIZE_VAR = 1 # initial orderbook size when a peer is created, variance

''' system dynamics '''

# init period

INIT_SIZE = 10 # number of peers joining the P2P at the very first beginning
BIRTH_TIME_SPAN = 20 # birth time of such peers is randomly distributed over [0,BIRTH_TIME_SPAN]

# growing period (# of peers increases)

GROWING_TIME = 30 # number of time rounds of the growth period
GROWING_RATE = 3 # number of peers joining the P2P system in each time round
PEER_EARLY_QUIT_RATE = 0 # number of peers leaving the P2P system in each time round

ORDER_EARLY_EXTERNAL_ARRIVAL_RATE = 15 # number of new orders created during each time round
ORDER_EARLY_DEPARTURE_RATE = 15 # number of orders canceled during each time round

# stable period (# of peers remain relatively stable)

STABLE_ROUND = 50 # number of time rounds of the stable period
PEER_ARRIVAL_RATE = 2 # number of peers joining the P2P system in each time round
PEER_DEPARTURE_RATE = 2 # number of peers leaving the P2P system in each time round (should be the same or close to PEER_ARRIVAL_RATE)

ORDER_EXTERNAL_ARRIVAL_RATE = 15 # number of new orders created during each time round
ORDER_DEPARTURE_RATE = 15 # number of orders canceled during each time round

''' incentives '''

# scoring system

CONTRIBUTION_LENGTH = 3 # length of the score queue
DISCOUNT_FACTOR_VECTOR = [1] * CONTRIBUTION_LENGTH

# score change

SHARE_REWARD_A = 0 # for sharing an order already in my local storage, shared by the same peer
SHARE_REWARD_B = 0 # for shairng an order already in my local storage, shared by a different peer
SHARE_REWARD_C = 0 # for sharing an order that I accepted to pending table, but don't store finally
SHARE_REWARD_D = 1 # for sharing an order I decide to store
SHARE_REWARD_E = 0 # for sharing an order I have multiple copies in the pending table and decided to store a copy from someone else

SHARE_PENALTY_A = 0 # for sharing an order that I have no interest
SHARE_PENALTY_B = -1 # for sharing an identical and duplicate order within the same batch

# sharing mechanics

MAX_SHARE = 5000 # maximal number of orders to share in each sharing event
OLD_ORDER_SHARE_PROB = 0.5 # probability for an old order to be shared again
MUTUAL_HELPERS = 3 # number of mutual helpers (who ranked high in the neighborhood)
OPTIMISTIC_CHOICES = 1 # number of randomly selected neighbors
# if a peer joins the system for no more than this time, it is considered a "baby peer" without enough
# knowledge about its neighbor and will randomly choose beneficiaries.
BABY_ENDING_TIME = 0

'''
====================
Design choices
====================
'''

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
    
    # This function generates a sample following a certain event happening pattern.
    # Input is the expected rate, output is a sample of number of incidents for this time slot.
    # Current implementation: Poisson process. May want to consider Hawkes process later.
    
    def numEvents(self, rate):
        return numpy.random.poisson(rate)
 
'''
=======================================
Simulation codes begin.
To change a strategy or parameter, modify lines above,
but not supposed to modify lines below.
=======================================
'''

myengine = Engine()

'''
=======================================
Classes
=======================================
'''

class Order:
    
    def __init__(self, seq, birthtime, creator, expiration = float('inf'), category = None):
        self.seq = seq # sequence number
        self.birthtime = birthtime # will be decided by system clock
        self.creator = creator # the peer who creates this order
        self.expiration = expiration # maximum time for a peer to be valid, and will expire thereafter.
        self.category = category # may refer to a trading pair lable or something else
        
        # the following two properties are the numbers of stored/pending replicas in the whole system, held by all peers.
        # Only God knows that. But we track them for simulation convenience.
        self.num_replicas = 0 
        self.num_pending = 0
        
        # set of peers who put this order into their local storage.
        self.holders = set() # len() = num_replicas
        
        # set of peers who put this order into their pending table but not local storage.
        # in order words, these peers are hesitating whether to store the orders.
        self.hesitators = set() # len() != num_pending since there might be multiple copies for one ID
        
        self.settled = False # this order instance has not been taken and settled
        self.canceled = False # will change to True when the order departs proactively.
    
    # This function updates the settled status for this order
    def updateSettledStatus(self): 
        myengine.orderUpdateSettleStatus(self)
            
# Each peer maintains a set of neighbors. Note, a neighbor physically is a peer, but a neighbor instance is not a peer instance;
# instead, it has specialized information from a peer's viewpoint.
# For general information about this node, refer to the global mapping table and find the corrosponding peer instance.

class Neighbor:
    
    def __init__(self, peer, master, est_time, preference = None):
         
        self.est_time = est_time # establishment time
        self.setPreference(peer, master, preference) # setup the master node's preference to this neighbor

        # If peer A shares his info to peer B, we say peer A contributes to B.
        # Such contribution is recorded in peer B's local record, i.e., the neighbor instance for peer A in the local storage of peer B.
        # Formally, "share_contribution" is a queue to record a length of "contribution_length" of contributions in the previous rounds.
        # each round is defined as the interval of two contiguous executions of updateNeighborScore function.
        
        self.share_contribution = collections.deque()
        for _ in range(CONTRIBUTION_LENGTH):
            self.share_contribution.append(0)
        
        self.score = 0 # the score to evaluate my neighbor.
        
        # indicator for the lazyness of this neighbor.
        # Default is 0. Increased by 1 if its score is below THRESHOLD, and reset to 0 if beyond.
        self.lazy_round = 0
    
    def setPreference(self, peer, master, preference):
        # determine the master node's preference to this neighbor
        myengine.neighborSetPreference(self, peer, master, preference)
        

# This class OrderInfo is similar to Neighbor: An instance of an orderinfo is an order from a peers viewpoint.
# Note, an order instance can have multiple OrderInfo instances stored by different peers.
# It contains specifit information about the novelty and property of the order, not included in Order class.

class OrderInfo:
    
    def __init__(self, order, master, arrival_time, priority = None, prev_owner = None, novelty = 0):
    
        self.arrival_time = arrival_time
        self.prev_owner = prev_owner # previous owner, default is None (a new order)
        self.novelty = novelty # how many hops it has travalled. Default is 0. Leave design space for TEC.
        self.setPriority(master, order, priority) # set up priority
        
        # storage_decision is to record whether this peer decides to put this order into the storage.
        # It seems redundant, but it is actually useful in storeOrders function.
        self.storage_decision = False
        
    # this function sets the priority for this orderinfo.
    def setPriority(self, master, order, priority): 
        myengine.orderinfoSetPriority(self, master, order, priority)

class Peer:

    # Note: initialization deals with initial orders, but does not establish neighborhood relationships.
    
    def __init__(self, seq, birthtime, init_orders, max_neighbors, min_neighbors, max_to_share, namespacing = None):
        
        global cur_time
        
        # simple parameter setting
        self.seq = seq # sequence number
        self.birthtime = birthtime
        self.namespacing = namespacing # A peers namespacing is its interest in certain trading groups. Currently we don't set it.
        self.min_neighbors = min_neighbors # minimal # of neighbors 
        self.max_neighbors = max_neighbors # maximum # of neighbors 
        self.max_to_share = max_to_share # maximum # of orders to share in each share decision
        
        self.order_orderinfo_mapping = {} # mapping from the order instance to orderinfo instances that have been formally stored.
        self.peer_neighbor_mapping = {} # mapping from the peer instance to neighbor instance. Note, neighborhood relationship must be bilateral.
        self.new_order_set = set() # set of newly and formally-stored orders that have NEVER been shared out by this peer.
        
        # the following mapping maintains a table of pending orders, by recording their orderinfo instance.
        # note that an order can have multiple orderinfo instances, because it can be forwarded by different neighbors.
        self.order_pending_orderinfo_mapping = {}
        
        # initiate orders
        for order in init_orders: # inital orders will directly be stored without going through the storage decison.
     
            # if this order is created by this peer, but in the peer initialization,
            # it was unable to define the creator as this peer since the peer has not been created.
            # there we defined the creator as None, and we will modify here.
            if order.creator is None:
                order.creator = self
                    
            priority = None # we don't set the priority for now
            new_orderinfo = OrderInfo(order, self, birthtime, priority)
            self.order_orderinfo_mapping[order] = new_orderinfo
            self.new_order_set.add(order)
                
            new_orderinfo.storage_decision = True # not sure if this is useful. Just keep it here to keep consistency.
                
            order.num_replicas += 1
            order.holders.add(self)
            
                    
    # this function requests to add neighbors if the number of neighbors is not enough.
    # it aims at adding up to demand_num neighbors, but is fine if added up to min_num, or all possibilities have been tried.
    # The function returns the size of neighbors after update.
    # This function needs to be proactively and periodically called.
    
    def checkAddingNeighbor(self):
        cur_neighbor_size = len(self.peer_neighbor_mapping)
        if cur_neighbor_size < self.min_neighbors:
            links_added = addNewLinks(self, self.max_neighbors - cur_neighbor_size, \
                                      self.min_neighbors - cur_neighbor_size)
        else:
            links_added = 0
            
        return cur_neighbor_size + links_added
            
    # This function is called when a request of establishing a neighborhood relationship is
    # called from another peer. This peer, which is requested, will return True for agreement by default,
    # or False if the cur # of neighbors already reaches the maximal.
    # Note, this function does not establish neighborhood relationship by itself. It accepts or rejects only.
    
    def acceptNeighborRequest(self, requester):
        
        if requester in self.peer_neighbor_mapping:
            raise ValueError('You are my neighbor. No need to request again.')
    
        return len(self.peer_neighbor_mapping) < self.max_neighbors
    
    # The following function establishes a neighborhood relationship.
    # It can only be called by the global function addNewLinks, where bilateral relationship is ganranteed.
        
    def addNeighbor(self, peer):
        
        global cur_time
        
        # if this peer is already a neighbor, error with addNewLinks function.
        if peer in self.peer_neighbor_mapping:
            raise ValueError('The addNewLinks function is requesting me to add my current neighbor.')
                
        # create new neighbor in my local storage
        new_neighbor = Neighbor(peer, self, cur_time)
        self.peer_neighbor_mapping[peer] = new_neighbor
        
    # This function defines what a peer will do if it's notified by someone for cancelling a neighborhood relationship.
    # Normally, it will accept and deletes that peer from his neighbor.
    # Note that this is different from real system that a peer simply drops a neighborhood relationship
    # without need to being accepted by the other side. This function is for simulation bookkeeping purpose only.
        
    def acceptNeighborCancellation(self, requester):
        # If I got removed as a neighbor by my neighbor, I will delete him as well.
        # But I will not remove orders from him, and I don't need to inform him to delete me.
        if requester in self.peer_neighbor_mapping:
            self.delNeighbor(requester, False, False) 
        
    # this function deletes a neighbor. If remove_order is True, then all orderinfo instances with the
    # prev_owner being this neighbor will also be deleted (order instances are still there).
    # notification: whether to notify the other party to cancel neighborhood.
    
    def delNeighbor(self, peer, remove_order = False, notification = True): 
   
        if peer not in self.peer_neighbor_mapping:
            raise ValueError('This peer is not my neighbor. Unable to delete.')
        
        # if remove_order is True, delete all orders whose previous owner is this neighbor
        if remove_order is True:
            
            for order, orderinfo in self.order_orderinfo_mapping.items():
                if orderinfo.prev_owner == peer:
                    order.num_replicas -= 1
                    order.holders.remove(self)
                    self.new_order_set.discard(order)
                    del self.order_orderinfo_mapping[order]
                    
            for order, orderinfolist in self.order_pending_orderinfo_mapping.items():
                for idx, orderinfo in enumerate(orderinfolist):
                    if orderinfo.prev_owner == peer:
                        order.num_pending -= 1
                        del orderinfolist[idx]
                if orderinfolist == []: # no pending orderinfo for this order. need to delete this entry
                    order.hesitators.remove(self) 
                    del self.order_pending_orderinfo_mapping[order]
        
        # if this neighbor is still an active peer, notify him to delete me as well.
        if notification is True:
            peer.acceptNeighborCancellation(self)
        
        # delete this neighbor
        del self.peer_neighbor_mapping[peer]
    
    # receiveOrderExternal() is called by orderArrival function.
    # OrderInfo will be put into pending table (just to keep consistent with receive_internal,
    # though most likely it will be accepted).
    # return True if accepted or False otherwise
    
    def receiveOrderExternal(self, order):
        
        if order in self.order_pending_orderinfo_mapping:
            raise ValueError('Abnormal external order. This order is in my pending table.')
        if order in self.order_orderinfo_mapping:
            raise ValueError('Abnormal external order. This order is already in my local storage.')

        global cur_time
        
        if myengine.externalOrderAcceptance(self, order) is True:
            
            # create the orderinfo instance and add it into the local mapping table
            new_orderinfo = OrderInfo(order, self, cur_time)
            self.order_pending_orderinfo_mapping[order] = [new_orderinfo]
            
            # update the number of replicas for this order and hesitator of this order
            order.num_pending += 1
            order.hesitators.add(self) # a peer is a hesitator of an order if this order is in its pending table
            return True
        
        return False

    # receiveOrderInternal() is called by shareOrder function. It will immediately decide whether
    # to put the order from the peer (who is my neighbor) into my pending table.
    # when novelty_update is True, its count will increase by one once transmitted.
    # Return True if accepted or False otherwise.
    
    def receiveOrderInternal(self, peer, order, novelty_update = False):
        
        global cur_time
        
        if self not in peer.peer_neighbor_mapping or peer not in self.peer_neighbor_mapping:
            raise ValueError('Order transmission cannot be peformed between non-neighbors.')
        
        neighbor = self.peer_neighbor_mapping[peer]
                
        if myengine.internalOrderAcceptance(self, peer, order) is False:
            # update the contribution of my neighbor for his sharing
            neighbor.share_contribution[-1] += SHARE_PENALTY_A
            return False
        
        if order in self.order_orderinfo_mapping: # no need to store again
            orderinfo = self.order_orderinfo_mapping[order]
            if orderinfo.prev_owner == peer:
                # I have this order in my local storage.
                # my neighbor is sending me the same order again.
                # It may be due to randomness of sharing old orders.
                neighbor.share_contribution[-1] += SHARE_REWARD_A
            else:
                # I have this order in my local storage, but it was from someone else.
                # No need to store it anymore. Just update the reward for the uploader.
                neighbor.share_contribution[-1] += SHARE_REWARD_B
            return False
            
        # if this order has not been formally stored.
        # Need to write it into the pending table (even if there has been one with the same ID).            
        if novelty_update is True:
            order_novelty = peer.order_orderinfo_mapping[order].novelty + 1
        else:
            order_novelty = peer.order_orderinfo_mapping[order].novelty
                    
        # create an orderinfo instance
        new_orderinfo = OrderInfo(order, self, cur_time, None, peer, order_novelty)
                    
        # if no such order in the pending list, create an entry for it
        if order not in self.order_pending_orderinfo_mapping: # order id not in the pending set 
            self.order_pending_orderinfo_mapping[order] = [new_orderinfo]
            order.num_pending += 1
            order.hesitators.add(self)
            # put into the pending table. share reward will be updated when a storing decision is made.
            return True
                        
        # if there is such order in the pending list, check if this order is from the same prev_owner.    
        for existing_orderinfo in self.order_pending_orderinfo_mapping[order]:
            if peer == existing_orderinfo.prev_owner:
                # this neighbor is sending duplicates to me in a short period of time
                # Likely to be a malicious one.
                neighbor.share_contribution[-1] += SHARE_PENALTY_B
                return False
       
        # my neighbor is honest, but he is late in sending me the message.
        # Add it to the pending list anyway since later, his version of the order might be selected.
        self.order_pending_orderinfo_mapping[order].append(new_orderinfo)
        order.num_pending += 1
        
        return True
    
    # storeOrders() function determines which orders to store and which to discard, for all orders
    # in the pending table. It is proactively called in the main function by each peer, when the time is
    # the end of a batch period.
        
    def storeOrders(self):
        
        global cur_time
        
        if (cur_time - self.birthtime) % BATCH_PERIOD != 0:
            raise RuntimeError('Store order decision should not be called at this time.')
        
        # change instance.storage_decision to True if you would like to store this order.
        myengine.orderStorage(self)
               
        # Now store an order if necessary
        
        for order, pending_orderinfolist_of_same_id in self.order_pending_orderinfo_mapping.items():
                      
            # sort the list of pending orderinfo with the same id, so that if
            # there is some order to be stored, it will be the first one.
            pending_orderinfolist_of_same_id.sort(key = lambda item: item.storage_decision, reverse = True)
            
            # update the order instance, e.g., number of pending orders, and remove the hesitator, in advance.
            order.num_pending -= len(pending_orderinfolist_of_same_id)
            order.hesitators.remove(self)
            
            # after sorting, for all pending orderinfo with the same id,
            # either (1) no one is to be stored, or (2) only the first one is stored
            
            if pending_orderinfolist_of_same_id[0].storage_decision is False: # if nothing is to be stored
                for pending_orderinfo in pending_orderinfolist_of_same_id:
                    # find the global instance of the sender, and update it.
                    if pending_orderinfo.prev_owner in self.peer_neighbor_mapping: # internal order, sender is still a neighbor
                        self.peer_neighbor_mapping[pending_orderinfo.prev_owner].share_contribution[-1] += SHARE_REWARD_C
            
            else: # the first element is to be stored
                first_pending_orderinfo = pending_orderinfolist_of_same_id[0]
                # find the global instance for the sender, and update it.
                if first_pending_orderinfo.prev_owner in self.peer_neighbor_mapping: # internal order, sender is still neighbor
                    self.peer_neighbor_mapping[first_pending_orderinfo.prev_owner].share_contribution[-1] += SHARE_REWARD_D
                # add the order into the local storage, and update the global order instance
                self.order_orderinfo_mapping[order] = first_pending_orderinfo
                self.new_order_set.add(order)
                order.num_replicas += 1
                order.holders.add(self)
                
                
                # for the rest pending orderinfo in the list, no need to store them, but may need to do other updates
                for pending_orderinfo in pending_orderinfolist_of_same_id[1:]:
                    
                    if pending_orderinfo.storage_decision is True:
                        raise ValueError('Should not store multiple orders. Wrong in storage decision process.')
                    
                    if pending_orderinfo.prev_owner in self.peer_neighbor_mapping: # internal order, sender is still neighbor
                        # update the share contribution
                        self.peer_neighbor_mapping[pending_orderinfo.prev_owner].share_contribution[-1] += SHARE_REWARD_E
                        
        # clear the pending mapping table                
        self.order_pending_orderinfo_mapping.clear()
        
        
    # shareOrders() function determines which orders to be shared to which neighbors.
    # It will call internal order receiving function of the receiver peer.
    # This function is only called by the main function at the end of a batch period.

    def shareOrders(self):
        
        # this function has to go through order by order and neighbor by neighbor.
        global cur_time
        
        if ( cur_time - self.birthtime ) % BATCH_PERIOD != 0:
            raise RuntimeError('Share order decision should not be called at this time.')
        
        # orders to share
        order_to_share_set = myengine.orderToShare(self, OLD_ORDER_SHARE_PROB)
        
        # peers to share
        peer_to_share_set = myengine.neighborToShare(cur_time, self, BABY_ENDING_TIME, MUTUAL_HELPERS, OPTIMISTIC_CHOICES)
        
        # sharing event
        for peer in peer_to_share_set:
            for order in order_to_share_set:
                peer.receiveOrderInternal(self, order)
            
        # clear the new order set. Every order becomes old.        
        self.new_order_set.clear()


    # This function deletes all orderinfo instances of a particular order.
    
    def delOrder(self, order):
        
        global order_full_set
        
        # check if this order is in the pending table
        if order in self.order_pending_orderinfo_mapping:
            if order in order_full_set:
                order.num_pending -= len(self.order_pending_orderinfo_mapping[order])
                order.hesitators.remove(self)
            del self.order_pending_orderinfo_mapping[order]
        
        # check if this order is in the local storage
        if order in self.order_orderinfo_mapping:
            self.new_order_set.discard(order)
            del self.order_orderinfo_mapping[order]
            if order in order_full_set:
                order.num_replicas -= 1
                order.holders.remove(self)
            
    # This function updates neighbor score, by (1) calculating the current score according to the queue
    # and (2) update the queue by moving one step forward and delete the oldest element.
    # It is called by rankNeighbor function.
    
    def updateNeighborScore(self):
        
        for peer in list(self.peer_neighbor_mapping):
            
            neighbor = self.peer_neighbor_mapping[peer]
            
            # update laziness
            if neighbor.share_contribution[-1] <=  LAZY_NEIGHBOR_CONTRI_THRESHOLD:
                neighbor.lazy_round += 1
            else:
                neighbor.lazy_round = 0
                
            # delete neighbor if necessary
            if neighbor.lazy_round >= LAZY_NEIGHBOR_LENGTH_THRESHOLD:
                self.delNeighbor(peer)
                continue
            
            neighbor.score = sum(a * b for a, b in zip(neighbor.share_contribution, DISCOUNT_FACTOR_VECTOR))
            
            # update the contribution queue since it is the end of a calculation circle
            neighbor.share_contribution.popleft()
            neighbor.share_contribution.append(0) 

    
    # This function ranks neighbors according to their scores. It is called by shareOrders function.
    # It returns a list peers ranked by the scores of their corresponding neighbor instances.
    
    def rankNeighbors(self):
        
        self.updateNeighborScore()
        
        peer_list = list(self.peer_neighbor_mapping)
        peer_list.sort(key = lambda item: self.peer_neighbor_mapping[item].score, reverse = True)
        return peer_list
    
    # This function measures the fairness of the incentive scheme.
    # There is no implemetion for now, and it is called from nowhere.
    
    def fairnessIndex(self):
        return myengine.calFairness(self)
 
 
'''
===========================================
System functions begin here.
===========================================
'''

# This is the initialization function.
# Construct a number of peers and a number of orders and maintain their references in two sets.
# Sequence numbers of peers and neighbors begin from 0 and increase by 1 each time.
    
def globalInit(init_size_peer, birth_time_span):
    

    global order_full_set # set of orders
    global peer_full_set # set of peers
    global cur_time # current system time
    global latest_order_seq # sequence number for next order to use
    global latest_peer_seq # sequence number for next peer to use
    
    order_seq = latest_order_seq # order sequence number should start from zero, but can be customized
    peer_seq = latest_peer_seq # same as above
    
    # first create all peer instances with no neighbors
    
    for _ in range(init_size_peer):
        
        # decide the birth time for this peer. Randomlized over [0, birth_time_span] to avoid sequentiality issue.
        birth_time = random.randint(0, birth_time_span - 1)
        
        # decide the number of orders for this peer
        num_orders = max(0, round(random.gauss(ORDERBOOK_SIZE_MEAN, ORDERBOOK_SIZE_VAR)))

        # create all order instances, and the initial orderbooks
        cur_order_set = set()
        
        for _ in range(num_orders):
            # decide the max expiration for this order
            expiration = max(0, round(random.gauss(ORDER_EXPIRATION_MEAN, ORDER_EXPIRATION_VAR)))
            
            # create the order. Order's birth time is cur_time, different from peer's birthtime.
            # Order's creator is set to be None since the peer is not initiated, but will be changed
            # in the peer's initiation function.
            new_order = Order(order_seq, cur_time, None, expiration)
            order_full_set.add(new_order)
            cur_order_set.add(new_order)
            order_seq += 1
        
        # create the peer instance. Neighbor set is empty.
        new_peer = Peer(peer_seq, birth_time, cur_order_set, NEIGHBOR_MAX, NEIGHBOR_MIN, MAX_SHARE)
        peer_full_set.add(new_peer)
        peer_seq += 1
        
    # update the latest order sequence number and latest peer sequence number
    latest_order_seq = order_seq
    latest_peer_seq = peer_seq
        
    # add neighbors to the peers. Use shuffle function to avoid preference of forming neighbors for
    # peers with small sequence number.
    peer_list = list(peer_full_set)
    random.shuffle(peer_list)
    
    for peer in peer_list:
        peer.checkAddingNeighbor()
        
    
# The following function helps the requester peer to add neighbors.
# It targets at adding demand_num neighbors, but is fine if the final added number
# is in the range [min_num, demand_num], or stops when all possible links are added.
# This function will call the corresponding peers' functions to add the neighbors, respectively.
# Finally, this function will output the # of links established.

def addNewLinks(requester, demand, minimum):
             
    if demand <= 0 or minimum < 0 or demand < minimum:
        raise ValueError('Wrong in requested number or range.')
    
    pool = peer_full_set - set([requester])
    selection_size = demand
    links_added = 0
    
    while links_added < minimum and pool:
        
        links_added_this_round = 0
        selected_peer_set = myengine.neighborRec(requester, pool, selection_size)
        for candidate in selected_peer_set: 
            # if this peer is already the requester's neighbor, ignore.
            if candidate not in requester.peer_neighbor_mapping:
                # check if the candidate is willing to add the requester.
                if candidate.acceptNeighborRequest(requester) is True:
                    # mutual add neighbors
                    candidate.addNeighbor(requester)
                    requester.addNeighbor(candidate)
                    links_added += 1
                    links_added_this_round += 1
                    
        pool -= selected_peer_set
        selection_size -= links_added_this_round
    
    return links_added

        
# when a new peer arrives, it may already have a set of orders. It only needs to specify the number of initial orders, 
# the function will specify the sequence numbers for the peers and orders.

def peerArrival(num_orders): 

    global peer_full_set
    global order_full_set
    global cur_time
    global latest_peer_seq
    global latest_order_seq
    
    # decide this peer's sequence number
    peer_seq = latest_peer_seq

    # create the initial orders for this peer and update global order set
    cur_order_set = set()
    order_seq = latest_order_seq
    for _ in range(num_orders):
        duration = max(0, round(random.gauss(ORDER_EXPIRATION_MEAN, ORDER_EXPIRATION_VAR)))
        new_order = Order(order_seq, cur_time, None, duration) # creator of the order temp set to be None
        order_full_set.add(new_order)
        cur_order_set.add(new_order)
        order_seq += 1
    
    # create the new peer, and add it to the table
    new_peer = Peer(peer_seq, cur_time, cur_order_set, NEIGHBOR_MAX, NEIGHBOR_MIN, MAX_SHARE)
    peer_full_set.add(new_peer)
    
    # add neighbors
    new_peer.checkAddingNeighbor()
    
    # update latest sequence numberes for peer and order
    latest_peer_seq += 1
    latest_order_seq = order_seq
    
# this peer departs from the system.

def peerDeparture(peer):

    # update number of replicas of all stored/pending orders with this peer
    for order in peer.order_orderinfo_mapping:
        order.num_replicas -= 1
        order.holders.remove(peer)
    
    for order, pending_orderlist in peer.order_pending_orderinfo_mapping.items():
        order.num_pending -= len(pending_orderlist)
        order.hesitators.remove(peer)
    
    # update existing peers
    for other_peer in peer_full_set:
        if peer in other_peer.peer_neighbor_mapping:
            other_peer.delNeighbor(peer)
    
    # update the global peer set
    peer_full_set.remove(peer)

 
# This function creates an external order arrival

def orderArrival(target_peer, expiration):
    
    global cur_time
    global latest_order_seq
    
    # create a new order
    new_order_seq = latest_order_seq
    new_order = Order(new_order_seq, cur_time, target_peer, expiration)
    
    # update global info of this order
    order_full_set.add(new_order)
    latest_order_seq += 1
    
    # update the order info to the target peer
    target_peer.receiveOrderExternal(new_order)
    
    
# This function takes a set of orders to depart as input,
# deletes them, updates all other order status. and deletes invalid ones
# from both the global set and all peers' pending tables and storages.

def updateGlobalOrderbook(order_dept_set):
    
    global order_full_set
    
    for order in order_dept_set:
        order.canceled = True
        
    for order in list(order_full_set):
        if (order.num_replicas == 0 and order.num_pending == 0) \
           or (cur_time - order.birthtime >= order.expiration) \
           or (order.settled is True) or (order.canceled is True):
            for peer in list(order.holders):
                peer.delOrder(order)
            for peer in list(order.hesitators):
                peer.delOrder(order)
            order_full_set.remove(order)
            
    return order_full_set       
            

# The following function returns the spreading ratio of orders of the same age.
# The return value is a list, each element being the spreading ratio of orders of the same age (starting from 0)
# if all orders of a particular age are all invalid, then that entry is 'None'.
# the spreading ratio is defined as the # of peers holding this order, over the total # of peers in the system at cur time.

def orderSpreadingRatioStat():
    
    global cur_time
    
    num_active_peers = len(peer_full_set)
    cur_active_order_set = updateGlobalOrderbook(set())
    max_age = cur_time - min(order.birthtime for order in cur_active_order_set)
    order_spreading_ratio = [[] for _ in range(max_age + 1)]

    for order in cur_active_order_set:
        ratio = order.num_replicas / num_active_peers
        order_spreading_ratio[cur_time - order.birthtime].append(ratio)
        
    for idx, sublist in enumerate(order_spreading_ratio):
        if sublist != []:
            order_spreading_ratio[idx] = sum(item for item in sublist) / len(sublist)
        else:
            order_spreading_ratio[idx] = None

    return order_spreading_ratio

# The following function runs normal operations at a particular time point.
# It includes peer/order dept/arrival, order status update,
# and peer's order acceptance, storing, and sharing.

def operationsInATimeRound(peer_dept_rate, peer_arr_rate, order_dept_rate, order_arr_rate):
    
    global cur_time
    global order_full_set
    
    # peers leave
    peer_dept_num = myengine.numEvents(peer_dept_rate)
    for peer_to_depart in random.sample(peer_full_set, peer_dept_num):
        peerDeparture(peer_to_depart)
    
    # new peers come in
    peer_arr_num = myengine.numEvents(peer_arr_rate)
    for _ in range(peer_arr_num):
        num_init_orders = max(0, round(random.gauss(ORDERBOOK_SIZE_MEAN, ORDERBOOK_SIZE_VAR)))
        peerArrival(num_init_orders)
          
    # external order arrival
    order_arr_num = myengine.numEvents(order_arr_rate)
    for _ in range(order_arr_num):
        # decide which peer to hold this order
        target_peer = random.sample(peer_full_set, 1)
        # decide the max expiration for this order
        expiration = max(0, round(random.gauss(ORDER_EXPIRATION_MEAN, ORDER_EXPIRATION_VAR)))    
        orderArrival(target_peer[0], expiration)
        
    # existing orders depart
    order_dept_num = myengine.numEvents(order_dept_rate)
    order_to_depart = random.sample(order_full_set, order_dept_num)
    updateGlobalOrderbook(order_to_depart)
        
    # peer operations
    for peer in peer_full_set:
        peer.checkAddingNeighbor()
        
    for peer in peer_full_set:
        if (cur_time - peer.birthtime ) % BATCH_PERIOD == 0:
            peer.storeOrders()
            peer.shareOrders()
       
'''
========================================================
Main simulation begins here.
========================================================
'''

max_age_to_track = ORDER_EXPIRATION_MEAN # will track spreading ratio of orders between age 0 and max_age_to_track - 1
average_order_spreading_ratio = [[] for _ in range(max_age_to_track)] # this is our performance metrics

cur_time = 0
latest_order_seq = 0
latest_peer_seq = 0
peer_full_set = set()
order_full_set = set()

for i in range(SIMULATION_ROUNDS):

    cur_time = 0 # the current system time

    latest_order_seq = 0 # the next order ID that can be used
    latest_peer_seq = 0 # the next peer ID that can be used
    peer_full_set.clear() # for each round of simulation, clear everything
    order_full_set.clear()
    
    # Initialization, orders are only held by creators
    # Peers do not exchange orders at this moment.
    globalInit(INIT_SIZE, BIRTH_TIME_SPAN)
    updateGlobalOrderbook(set())

    # growth period [BIRTH_TIME_SPAN, BIRTH_TIME_SPAN + GROWING_TIME]
    # more peer coming in than leaving
    for time in range(BIRTH_TIME_SPAN, BIRTH_TIME_SPAN + GROWING_TIME):
        cur_time = time
        # All the following rates can be fractional. The real numbers of events follow a Poisson process.
        operationsInATimeRound(PEER_EARLY_QUIT_RATE, GROWING_RATE, ORDER_EARLY_DEPARTURE_RATE, ORDER_EARLY_EXTERNAL_ARRIVAL_RATE)
    
    # steady state, we allow peer departure, order departure, peer arrival, and order arrival.
    # The # of peers remains a constant.
    for time in range(BIRTH_TIME_SPAN + GROWING_TIME, BIRTH_TIME_SPAN + GROWING_TIME + STABLE_ROUND):
        cur_time = time
        # All the following rates can be fractional. The real numbers of events follow a Poisson process.
        operationsInATimeRound(PEER_DEPARTURE_RATE, PEER_ARRIVAL_RATE, ORDER_DEPARTURE_RATE, ORDER_EXTERNAL_ARRIVAL_RATE)
    
    # we use the status of order spreading at the last time point, as an appoximation of the steady state status    
    order_spreading_ratio_this_time = orderSpreadingRatioStat()
    
    # add the values into order spreading ratio table
    for ratio_idx, ratio_value in enumerate(order_spreading_ratio_this_time[:max_age_to_track]):
        if ratio_value is not None:
            average_order_spreading_ratio[ratio_idx].append(ratio_value)
            
for ratio_idx, ratio_value_list in enumerate(average_order_spreading_ratio):
    if ratio_value_list == []:
        average_order_spreading_ratio[ratio_idx] = 0
    else:
        average_order_spreading_ratio[ratio_idx] = statistics.mean(ratio_value_list)
           
plt.plot(average_order_spreading_ratio)
plt.xlabel('age of orders')
plt.ylabel('spreading ratio')
plt.show()     
