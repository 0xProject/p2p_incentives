'''
===========================
P2P Orderbook simulator

Weijie Wu
May 2, 2019

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

- Class Scenario determines our basic assumptions of the system.
    Functions that implement assumptions are in class ScenarioCandidates.
    I will delete this class and put functions into a separate module later.
- Class Engine determines a decision choice.
    Functions that implement decision choices are in class EngineCandidate.
    I will delete this class and put functions into a separate module later.
- Class Performance contains performance measures.
    Functions that implement performance evaluations are in class PerformanceCandidates.
    I will delete this class and put functions into a separate module later.
- Class DataProcessing contains some data processing functions that will be used by functions elsewhere.
    I will delete this class and put functions into a separate module later.
- Class Simulator contains all system functions for the simulator to run.
- Class Execution contains functions that run the simulator in multi-processing manner and generates the result.

===========================

Design details:


1. Neighborhood relationship:

- Any neighborhood relationship must to be bilateral.
- A peer will try to maintain the size of its neighbors within a certain range
    (min, max), unless it is impossible.
- Each round, the simualtor will check that each peer has enough # of neighbors. If not
    (# < min), the simulator function addNewLinksHelper() will be called to add new neighbors.
- The only way to create new links is calling addNewLinksHelper().
    Procedure is: random selection of peers -> send invitation to the other party -> Accepted?
        - Y: both sides add neighbors
        - N: nothing happens.
    Accept or reject: Always accept if # of my neighbor has not reached NEIGHBOR_MAX.
- If neighbor departs or it is considered as lazy (score is too low) for a long time, neighborhood is cancelled.
    Procedure is: delete my neighbor -> notify my neighbor (if he's still alive) to delete me too.

2. Order flows: arrival -> accept to pending table -> accept to local storage -> share it with others

2.1 Order arrival: two forms of arrival: internal and external.
    Internal: caused by a neighbor sharing an order. Can happen any time.
    External: caused by an external order arrival. Can also happen any time.
    If it happens, the arrival will call the targeting peer's function receiveOrderInternal or receiveOrderExternal.

2.2 Order acceptance: The functions receiveOrderInternal or receiveOrderExternal can only be called by order sharing
    or external order arrival, at any time. These functions will determine whether or not to put the orders into the pending table.
    
2.3 Order storing: This function can only be called from the Simulator class proactively. No other function calls it.
    It runs only at the end of a batch period. It will decide whether to put pending orders into the local storage.
    Pending table will be cleared.
    
2.4 Order sharing: This function can only be called from the Simulator class proactively, following order storing.
    No other function calls it. It runs only at the end of a batch period.
    It will decide whether to share any stored order to any neighbor.
    It will call neighbor ranking function, which will first update neighbor scores.
    
Note: Peer init will directly put some orders into the local storage, without going through pending table.
    For new peers, the birthtime is the end of the 0th batch period, so order sharing will be called at birth.
    
    New neighbor establishment does not call any order-related operations.
    That being said, if I am an old peer but I am newly accepted by some other peer in the system as his neighbor,
    I need to wait until the end of batch period of the peer who accepted me, to receive his sharing;
    I will also wait until the end of my batch period, to share with him my orders.
         
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
  we assume that there is some global grand truth for an order's status.
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
import pickle
from multiprocessing import Pool
import math
import itertools

'''
====================
System Assumptions
====================
'''
# The class Scenario describes our assumptions on the system setting.
# For examples, peer and order parameters, system evolving dynamics, event arrival pattern, etc.
# They describe the feature of the system, but is NOT part of our design space.

class Scenario:
    
    def __init__(self, parameters, options):
        
        # unpacking parameters
        (order_type_ratios, peer_type_ratios, order_par_list, peer_par_list, \
         init_par, growth_par, stable_par) = parameters

        self.order_type_ratios = order_type_ratios # ratios of each type of orders
        self.peer_type_ratios = peer_type_ratios # ratios for each type of peers. The first element is the ratio for freeriders.
        
        self.order_parameter_list = order_par_list # each element is (mean, var) of order expirations of this order type
        self.peer_parameter_list = peer_par_list # each element is (mean, var) of the initial orderbook size of this peer type
        
        # init period, init_size is number of peers joining the P2P at the very beginning,
        # and the birth time of such peers is randomly distributed over [0,birth_time_span]
        self.init_size = init_par['num_peers']
        self.birth_time_span = init_par['birth_time_span']
        
        # growing period (when # of peers increases)
        # parameters are: # of time rounds for growth period
        # peer arrival rate, peer dept rate, order arrival rate, order dept rate.
        # An event (peer/order arrival/departure) happens according to some random process
        # (e.g., Poisson or Hawkes) that takes the rate as an input parameter(s).
        
        '''
        # please be noted that, the order dept rate refers to the rate that an order is proactively
        # canceled. This is a poor naming. In reality, an order departs when it is (1) canceled, (2) expired, or (3) settled.
        # So the real departure rate of an order is larger than the order dept rate we define here.
        # I remain the name here just to reduce the difference for this PR review. Will probably change the name
        # to order_cancel in the next version.
        '''
        
        self.growth_rounds = growth_par['rounds']
        self.growth_rates = [growth_par['peer_arrival'], growth_par['peer_dept'], \
                             growth_par['order_arrival'], growth_par['order_dept']]
        
        # stable period (# of peers and # of orders remain relatively stable)
        # parameters refer to: # of time rounds, 
        # peer arrival rate, peer dept rate, order arrival rate, order dept rate.
        
        # We should choose the parameters such that peer arrival rate is approximately equal to peer departure rate,
        # and that order arrival rate is appoximately equal to the total order departure rate
        # (due to cancellation, settlement, or expiration).
        
        self.stable_rounds = stable_par['rounds']
        self.stable_rates = [stable_par['peer_arrival'], stable_par['peer_dept'], \
                             stable_par['order_arrival'], stable_par['order_dept']]
        
        # unpacking and setting options
        # options will determine the forms of implementations for functions in this class.
        # option_numEvent determines event happening (peer/order arrival/dept) pattern.
        # Poisson and Hawkes processes are implemented.
        # option_settle determines when an order is settled. Now only "never settle" is implementd.
        (self.option_numEvent, self.option_settle) = options

    # This function generates event happening events according to some pattern.
    # It reads option_numEvent['method'] to determine the pattern,
    # takes the expected rate (could be a value or a tuple of values)
    # and the length of time slots as input, and
    # outputs the number of incidents in each time slot.
    # Current pattern implementations: Poisson process and Hawkes process.

    def numEvents(self, rate, max_time):
        if self.option_numEvent['method'] == 'Poisson':
            return numpy.random.poisson(rate, max_time)
        elif self.option_numEvent['method'] == 'Hawkes':
            # note that the rate parameter for Hawkes is a tuple of variables.
            # They are explained in Hawkes function implementation.
            return ScenarioCandidates.Hawkes(rate, max_time)
        else:
            raise ValueError('No such option to generate events: {}'.\
                             format(self.option_numEvent['method']))
    
    # This function updates the is_settled status for orders.
    def orderUpdateSettleStatus(self, order):
        if self.option_settle['method'] == 'Never':
            return ScenarioCandidates.settleDummy(order)
        else:
            raise ValueError('No such option to change settlement status for orders: {}'.\
                             format(self.option_settle['method']))

'''
====================
Candidates of Scenarios
====================
'''

# This class contains contains all possible realizations for functions in Scenario.
'''
Please be noted that this will be changed to individual functions in a module later.
'''

class ScenarioCandidates:
    
    # This is the funciton to generate Hawkes process.
    # The definition of the arrival rate is: 
    # \lambda(t) = a + (\lambda_0 - a ) \times e ^(-\delta \times t) +
    # \sum_{T_i < t} \gamma e^{-\delta (t-T_i)}
    
    # It takes parameters (a, lambda_0, delta, gamma) from rate, and max time slots as input,
    # and outputs a random realization of event happening counts over time slots [0, max_time].
    
    # This simulation method was proposed by Dassios and Zhao in a paper
    # entitled 'Exact simulation of Hawkes process
    # with exponentially decaying intensity,' published in Electron.
    # Commun. Probab. 18 (2013) no. 62, 1-13.
    # It is believed to be running faster than other methods.
    
    @staticmethod
    def Hawkes(rate, max_time):
        
        (a, lambda_0, delta, gamma) = rate
        # check paramters
        if not (a >= 0 and lambda_0 >= a and delta > 0 and gamma >= 0):
            raise ValueError('Parameter setting is incorrect for the Hawkes process.')
        
        T = [0]
        lambda_minus = lambda_0
        lambda_plus= lambda_0
        
        while T[-1] < max_time:
            u0 = random.random()
            try:
                s0 = - 1/a * math.log(u0)
            except:
                s0 = float('inf')
            u1 = random.random()
            try:
                d = 1 + delta * math.log(u1) / (lambda_plus - a)
            except:
                d = float('-inf')
            if d > 0:
                try:
                    s1 = (-1 / delta) * math.log(d)
                except:
                    s1 = float('inf')
                tau = min(s0, s1)
            else:
                tau = s0
            T.append(T[-1] + tau)
            lambda_minus = (lambda_plus - a)* math.exp(-delta * tau) + a
            lambda_plus = lambda_minus + gamma
        
        num_events = [0] * (max_time)
        for t in T[1:-1]:
            num_events[int(t)] += 1
            
        return num_events
    
    
    # The following function determines to change an order's is_settled status or not.
    # This is a dummy implementation that never changes the status.
    
    @staticmethod
    def settleDummy(order):
        pass

'''
====================
Design Space
====================
'''
# The class Engine describes the design space. By choosing a specific option we refer to a particular design choice.
# They include our possible choices on neighbor establishment, order operations and incentives, scoring system, etc.
# Such choices are viable, and one can change any/some of them to test the performance.
# Later the Simulator class will call functions from this Engine class for a particular realization of implementation.

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
        # which funtion in EngineCandidates to call, and then pass the rest parameters to the function called.
        
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
            EngineCandidates.setPreferencePassive(neighbor, peer, master, preference)
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
            EngineCandidates.setPriorityPassive(orderinfo, order, master, priority)
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
            EngineCandidates.storeFirst(peer)
        else:
            raise ValueError('No such option to store orders: {}'.\
                             format(self.store_option['method']))
                
    # This function determines the set of orders to share for this peer.
    def ordersToShare(self, peer):
        if self.share_option['method'] == 'AllNewSelectedOld':
            return EngineCandidates.shareAllNewSelectedOld\
                   (self.share_option['max_to_share'], \
                    self.share_option['old_share_prob'], peer)
        else:
            raise ValueError('No such option to share orders: {}'.\
                             format(self.share_option['method']))
    
    # This function calculates the scores of a given peer, and deletes a neighbor if necessary.
    def scoreNeighbors(self, peer):
        if self.score_option['method'] == 'Weighted':
            return EngineCandidates.\
                   weightedSum(self.score_option['lazy_contribution_threshold'], \
                               self.score_option['lazy_length_threshold'], \
                               self.score_option['weights'], peer)
        else:
            raise ValueError('No such option to calculate scores: {}'.\
                             format(self.score_option['method']))
      
    # This function determines the set of neighboring nodes to share the orders in this batch.
    def neighborsToShare(self, time_now, peer):
        
        if self.beneficiary_option['method'] == 'TitForTat':
            neighbors_selected = EngineCandidates.titForTat(self.beneficiary_option['baby_ending_age'],\
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
            return EngineCandidates.randomRec(requester, base, target_number)
        else:
            raise ValueError('No such option to recommend neighbors: {}'.\
                             format(self.rec_option['method']))


'''
====================
Candidates of design choices
====================
'''
# The class Candidates contains all possible realizations of functions in the Engine class.
'''
Please be noted that this will be changed to individual functions in a module later.
'''

class EngineCandidates:
    
    # This is a candidate design for setting preference of a neighbor instance.
    # The choice is: set the value as "preference" if preference is not None, or set it as None otherwise.
    
    @staticmethod
    def setPreferencePassive(neighbor, peer, master, preference):
        neighbor.preference = preference
    
    # This is a candidate design for setting a priority of an orderinfo instance.
    # The choice is: set the value as "priority" if priority is not None, or set it as None otherwise.
    
    @staticmethod
    def setPriorityPassive(orderinfo, order, master, priority):
        orderinfo.priority = priority
    
    # This is a candidate design for storing orders.
    # Note that there might be multiple orderinfo instances for a given order instance.
    # The design needs to make sure to store at most one of such orderinfo instances.
    # The choice is: store the first instance of orderinfo for every order.
    
    @staticmethod
    def storeFirst(peer):
        for pending_orderinfolist_of_same_id in peer.order_pending_orderinfo_mapping.values():
            pending_orderinfolist_of_same_id[0].storage_decision = True # first orderinfo is stored
            for orderinfo in pending_orderinfolist_of_same_id[1:]: # the rest (if any) are not stored
                orderinfo.storage_decision = False        
    
    # This is a candidate design for sharing orders.
    # The choice is: share min(max_to_share, # of new_orders) of new orders,
    # and share min(remaining_quota, [# of old peers] * old_prob) of old orders,
    # where remaining_quota = max(0, max_to_share minus #_of_new_orders_selected).
    
    @staticmethod
    def shareAllNewSelectedOld(max_to_share, old_prob, peer):
        
        new_order_set = peer.new_order_set
        old_order_set = set(peer.order_orderinfo_mapping) - peer.new_order_set
        selected_order_set = set()
                      
        selected_order_set |= set(random.sample(new_order_set, min(max_to_share, len(new_order_set))))
        
        remaining_share_size = max(0, max_to_share - len(new_order_set))
        probability_selection_size = round(len(old_order_set) * old_prob)
        selected_order_set |= set(random.sample(old_order_set, \
                                                min(remaining_share_size, probability_selection_size)))            
        return selected_order_set
    
    # This is a candidate design for calculating the scores of neighbors of a peer.
    # The choice is: (1) calculate the current score by a weighted sum of all elements in the queue
    # (2) update the queue by moving one step forward and delete the oldest element, and
    # (3) delete a neighbor if it has been lazy for a long time.

    @staticmethod
    def weightedSum(lazy_contri, lazy_length, discount, peer):
        
        # If a neighbor's score is under self.lazy_contri, it is "lazy" in this batch;
        # If a neighbor has been lazy for self.lazy_length batches,
        # it is permanently lazy and gets kicked off.
        # Discount is a list of weights weights for each element of the score queue.
        # Usually recent elements are of higher weights.
        
        for neighboring_peer in list(peer.peer_neighbor_mapping): # neighboring_peer is the peer instance for a neighbor
            
            neighbor = peer.peer_neighbor_mapping[neighboring_peer] # neighbor is the neighbor instance for a neighbor
            # update laziness
            if neighbor.share_contribution[-1] <=  lazy_contri:
                neighbor.lazy_round += 1
            else:
                neighbor.lazy_round = 0  
            # delete neighbor if necessary
            if neighbor.lazy_round >= lazy_length:
                peer.delNeighbor(neighboring_peer)
                continue
        
            neighbor.score = sum(a * b for a, b in zip(neighbor.share_contribution, discount))

    # This is a candidate design to select beneficiaries from neighbors.
    # The choice is similar to tit-for-tat.
    # If this is a new peer (age <= baby_ending) so it does not know its neighbors well,
    # it shares to random neighbors (# = mutual + optimistic).
    # Otherwise, it shares to (# = "mutual") highly-reputated neighbors, and
    # (# = "optimistic") of other random neighbors.
    # In the case fewer than (# = "mutual") neighbors have positive scores, only
    # select the neithbors with positive scores as highly-reputated neighbors.
    # The number of other random neighbors is still "optimistic"
    # (i.e., the quota for beneficiaries is wasted in such a case).
    
    @staticmethod
    def titForTat(baby_ending, mutual, optimistic, time_now, peer):
        
        selected_peer_set = set() 
        if (time_now - peer.birthtime <= baby_ending): # This is a new peer. Random select neighbors.
            selected_peer_set |= set(\
                random.sample(list(peer.peer_neighbor_mapping),\
                              min(len(peer.peer_neighbor_mapping), mutual + optimistic)))
        else: # This is an old peer
            # ranked_list_of_peers is a list of peer instances who are my neighbors
            # and they are ranked according to their scores that I calculate.
            ranked_list_of_peers = peer.rankNeighbors()
            mutual = min(mutual, len(ranked_list_of_peers))
            while mutual > 0 and peer.peer_neighbor_mapping\
                  [ranked_list_of_peers[mutual - 1]].score == 0:
                mutual -= 1
                
            highly_ranked_peers_list = ranked_list_of_peers[:mutual]
            lowly_ranked_peers_list = ranked_list_of_peers[mutual:]
            selected_peer_set |= set(highly_ranked_peers_list)
            selected_peer_set |= set(\
                random.sample(lowly_ranked_peers_list,\
                              min(len(lowly_ranked_peers_list), optimistic)))            
        return selected_peer_set
    
    # This is a candidate design for neighbor recommendation.
    # The choice is to choose (# = targe_number) elements from the base in a totally random manner.
    # The current implementation does not take requester into consideration.
    
    @staticmethod
    def randomRec(requester, base, target_number):
        if not base or not target_number:
            raise ValueError('Base set is empty or target number is zero.')
        
        # if the target number is larger than the set size, output the whole set.
        return set(random.sample(base, min(target_number, len(base))))

'''
=================================
Performance evaluation 
=================================
'''

# The following class contains paramters, measures, and methods to carry out peformance evaluation.
# Functions in this class will call realization from PerformanceCandidates.

class Performance:
    
    def __init__(self, parameters, options, executions):

        # unpacking and setting pamameters
        
        # the oldest age of orders to track
        self.max_age_to_track = parameters['max_age_to_track'] 
        
        # the age beyond which a peer is considered an Adult.
        # Only adults will be evaluated for user satisfaction
        # (because new peers receive limited orders only).
        self.adult_age = parameters['adult_age']
        
        # This is the window length to aggregate orders for statistics.
        # All orders that falls into the same window will be considered in the same era for calculation.
        # For example if statistical_window = 10, then orders whose ages are between 0 and 9 will be
        # put into the same category for statistics.
        # The reason for this window is when order arrival rate is very low, then in many time slots
        # there's no new arrived orders. So it is better to aggregate the orders for statistics.
        self.statistical_window = parameters['statistical_window']
        
        # unpacking and setting options.
        
        # "spreading_option" is how to measure the spreading pattern of orders
        # (e.g., spreading ratio, spreading speed, etc.)
        
        # "satisfaction_option" is how a peer evaluates
        # its satisfaction based on the orders that it receives.
        
        # "fairness_option" is how to evaluate the fairness for a group of peers.
        # Currenly we have no implementation yet.
        (self.spreading_option, self.satisfaction_option, self.fairness_option) = options
        
        # measurement to execute, i.e., which measurement functions to execute.
        self.measures_to_execute = measures_to_execute
        
    # In what follows we have performance evaluation functions.
    # In most of these functions they take peers_to_evaluate and orders_to_evaluate as input.
    # The reason is to add flexibility in considering evaluating over reasonable peers and reasonable
    # orders only (given that there are possibly free riders and wash trading orders).
        
    # The following function returns some measurement on the spreading pattern of orders.
    
    def orderSpreadingMeasure(self, cur_time, peers_to_evaluate, orders_to_evaluate):
        
        if not len(peers_to_evaluate) or not len(orders_to_evaluate):
            raise ValueError('Invalid to measure the spreading based on no orderd or no peers.')
        
        # Currently we only implemented spreading ratio. In future we may also want to investigate
        # new orders spreading rate, etc.
        
        if self.spreading_option['method'] == 'Ratio':
            return PerformanceCandidates.\
                   orderSpreadingRatioStat(cur_time, orders_to_evaluate, peers_to_evaluate,\
                                           self.max_age_to_track, self.statistical_window)
        else:
            raise ValueError('No such option to evaluate order spreading: {}'.\
                             format(self.spreading_option['method']))
        
        
    # The following function takes in a set of peers and a set of orders,
    # calculates every adult peer's satisfaction on the # of orders received.
    # It returns a (non-fixed length) list of satisfactions of every adult peer.
    # These values are simply put in a list without specifying which peer they correspond to.
    # Functions in DataProcessing will perform statistics over these data.
   
    def userSatisfactionMeasure(self, cur_time, peers_to_evaluate, orders_to_evaluate):
   
        if not len(peers_to_evaluate) or not len(orders_to_evaluate):
            raise ValueError('Invalid to evalute user satisfaction if there are no peers or no orders.')
        
        # A "neutral" implementation refers to that a peer regards each order as equally important.
        # This is a naive implementation only. Later we will need to consider new orders as more important.
        
        if self.satisfaction_option['method'] == 'Neutral':
            singleCalculation = PerformanceCandidates.singlePeerSatisfactionNeutral
        else:
            raise ValueError('No such option to evaluate peer satisfaction: {}'.\
                             format(self.satisfaction_option['method']))
        
        set_of_adult_peers_to_evaluate = set(peer for peer in peers_to_evaluate\
                                    if cur_time - peer.birthtime >= self.adult_age)
        
        satisfaction_list = [singleCalculation(cur_time, peer, self.max_age_to_track,\
                                               self.statistical_window, orders_to_evaluate)\
                             for peer in set_of_adult_peers_to_evaluate]
        
        return satisfaction_list
    
    # The following function measures fairness index for a given set of peers and a
    # given set of orders. Now we don't have a real implementation.
    
    def fairnessMeasure(self, peers_to_evaluate, orders_to_evaluate):
        
        if not len(peers_to_evaluate):
            raise ValueError('Invalid to evalute fairness for an empty set of peers.')
        
        if self.fairness_option['method'] == 'Dummy':
            return PerformanceCandidates.fairnessDummy(peers_to_evaluate, orders_to_evaluate)
        else:
            raise ValueError('No such option to evaluate fairness: {}'.\
                             format(self.fairness_option['method']))
    
    # This function runs performance evaluation.
    # It reads self.measures_to_execute dictionary to decide which evaluation
    # measures are required to run, and returns a list of results.
    # If some measure is not run, or it is infeasible to generate any result for that measure,
    # the correponding value in the return list is None.
    
    def run(self, cur_time, peer_full_set, normal_peer_set, free_rider_set, order_full_set):
        
        # Generate order spreading measure for all orders over all peers
        if self.measures_to_execute['order_spreading_measure']:
            try:
                result_order_spreading = self.orderSpreadingMeasure(cur_time, peer_full_set, order_full_set)
            except:
                result_order_spreading = None
        else:
            result_order_spreading = None
        
        # Generate normal peer satisfaction measure over all orders
        if self.measures_to_execute['normal_peer_satisfaction_measure']:
            try:
                result_normal_peer_satisfaction = self.userSatisfactionMeasure(cur_time, normal_peer_set, order_full_set)
            except:
                result_normal_peer_satisfaction = None
        else:
            result_normal_peer_satisfaction = None
         
        # Generate free rider satisfaction measure over all orders
        if self.measures_to_execute['free_rider_satisfaction_measure']:
            try:
                result_free_rider_satisfaction = self.userSatisfactionMeasure(cur_time, free_rider_set, order_full_set)
            except:
                result_free_rider_satisfaction = None
        else:
            result_free_rider_satisfaction = None
        
        # Generate system fairness measure over all peers and all orders
        if self.measures_to_execute['fairness']:
            try:
                result_fairness = self.fairnessMeasure(peer_full_set, order_full_set)
            except:
                result_fairness = None
        else:
            result_fairness = None
         
        # Organize the results in a list 
        result = {'order_spreading': result_order_spreading,
                  'normal_peer_satisfaction': result_normal_peer_satisfaction,
                  'free_rider_satisfaction': result_free_rider_satisfaction,
                  'fairness': result_fairness
                  }
        return result

'''
=================================
Candidates of performance evaluation
=================================
'''

# This class contains possible implementations for performance measurement functions.
'''
Please be noted that this will be changed to individual functions in a module later. 
'''

class PerformanceCandidates:

    
    # The following function returns the spreading ratios of orders, arranged by statistical windows.
    # The return value is a list, the index being the i-th statistical window, and
    # each value being the spreading ratio of orders of that window.
    
    # Statistical window: We divide the orders into age intervals
    # [n * statistical_interval, (n+1)* statistical_interval), n = 0, 1, ...,
    # and all orders that falls into an interval are all in this window.
    
    # The spreading ratio of an order, is defined as the # of peers holding this
    # order, over the total # of peers in the peer set.
    # The spreading ratio of a statistical window, is the average spreading ratio
    # of all orders in this window.
    
    # The maximal age of orders that we consider, is max_age_to_track.
    
    # The return value is a list of order spreading ratios, corresponding to each statistical window.
    # if all orders of a window are all invalid, then value for that entry is 'None'.
    
    @staticmethod
    def orderSpreadingRatioStat(cur_time, order_set, peer_set, max_age_to_track, statistical_window):
        
        num_active_peers = len(peer_set)
        order_spreading_ratio = [[] for _ in range(int((max_age_to_track - 1)/statistical_window) + 1)]
        
        for order in order_set:
            num_peers_holding_order = len(list(item for item in order.holders if item in peer_set))
            ratio = num_peers_holding_order / num_active_peers
            age = cur_time - order.birthtime
            if age < max_age_to_track:
                order_spreading_ratio[int(age/statistical_window)].append(ratio)
            
        for idx, sublist in enumerate(order_spreading_ratio):
            if sublist != []:
                order_spreading_ratio[idx] = statistics.mean(sublist) # sum(item for item in sublist) / len(sublist)
            else:
                order_spreading_ratio[idx] = None       
        return order_spreading_ratio
    
    # The following function is a helper function. It returns a vector,
    # each value being the # of orders whose age falls into
    # [k * statistical_window, (k+1) * statistical_window).
    
    @staticmethod
    def orderNumStatOnAge(cur_time, max_age_to_track, statistical_window, order_set):
        
        num_orders_in_age_range = [0] * int(((max_age_to_track - 1)/statistical_window) + 1)
        for order in order_set:
            age = cur_time - order.birthtime
            if age < max_age_to_track:
                bin_idx = int(age / statistical_window)
                num_orders_in_age_range[bin_idx] += 1
        return num_orders_in_age_range
    
    # The following function is a helper function. It returns the aggregated number
    # of orders in the set order_set, that falls into each statistical window, that a particular peer observes.
     
    @staticmethod
    def peerInfoObservation(peer, cur_time, max_age_to_track, statistical_window, order_set):
        
        num_orders_this_peer_stores = [0] * int(((max_age_to_track - 1)/statistical_window) + 1)
        
        for order in peer.order_orderinfo_mapping:
            age = cur_time - order.birthtime
            if age < max_age_to_track and order in order_set:
                bin_num = int(age / statistical_window)
                num_orders_this_peer_stores[bin_num] += 1
                
        return num_orders_this_peer_stores


    # The following function is a helper function. It returns a list of the ratios of orders that this peer
    # receives, each ratio is calculated based on the total # of orders of this window.
    # If there is no order in this window, the value for this entry is None.

    @classmethod
    def singlePeerInfoRatio(cls, cur_time, peer, max_age_to_track, statistical_window, order_set):
        
        def try_division(x, y):
            try:
                z = x/y
            except:
                z = None
            return z
        
        order_stat_based_on_age = cls.orderNumStatOnAge\
                                  (cur_time, max_age_to_track, statistical_window, order_set)
        
        num_orders_this_peer_stores = cls.peerInfoObservation\
                                      (peer, cur_time, max_age_to_track, statistical_window, order_set)
        
        peer_observation_ratio = list(map(try_division, num_orders_this_peer_stores, order_stat_based_on_age))
        
        return peer_observation_ratio
        
        
    # This function calculates a peer's satisfaction based on his info observation ratios
    # The neutral implementation is taking average of each observation ratio
    # (neutral to every order), or return None of every element is None.
    
    @classmethod
    def singlePeerSatisfactionNeutral(cls, cur_time, peer, max_age_to_track,\
                                      statistical_window, order_set):
        
        peer_observation_ratio = cls.singlePeerInfoRatio\
                                 (cur_time, peer, max_age_to_track, \
                                  statistical_window, order_set)
        
        try:
            return statistics.mean(item for item in peer_observation_ratio if item is not None)
        except:
            return None # this peer does not have any orders


    # This function calculates the fairness index for all peers
    # Right now, it is not implemented.
    
    @staticmethod
    def fairnessDummy(peer_set, order_set):
        return 0
  


'''
=======================================
Data processing tools
=======================================
'''
# The following class contains data processing tools (e.g., finding the max, min, average, frequency...)
# to work on performance evaluation results, possibly for results of running the simulator multiple times.

'''
Please be noted that this will be changed to individual functions in a module later. 
'''

class DataProcessing:
    
    # This function takes a sequence of equal-length lists and find the best and worst lists.
    # An element in the list is either a non-negative value or None.
    # the best/worst list is the one who's last entry is the largest/smallest among all lists given.
    # If any entry is None, it is ignored (neither the best nor the worst).
    # If the last entries of all lists are all None, then we look at the second last entry, etc.,
    # up till the first entry. If all entries of all lists are None, raise an exception.
    # For example, if list_1 = [0.1, 0.2, 0.3, None], list_2 = [0.29, 0.29, 0.29, None],
    # then list_1 is the best and list_2 is the worst.
    # For effeciency consideration, this function does not check validity of the argument (same length)
    # since it should have been guaranteed in the function that calls it.
    
    @staticmethod
    def findBestWorstLists(sequence_of_lists):
        
        last_effective_idx = -1
        while last_effective_idx >= -len(sequence_of_lists[0]):
            if any(item[last_effective_idx] is not None for item in sequence_of_lists):
                break
            last_effective_idx -= 1
        
        if last_effective_idx == -len(sequence_of_lists[0]) - 1:
            raise ValueError('All entries are None. Invalid to compare.')

        it1, it2 = itertools.tee((item for item in sequence_of_lists if item[last_effective_idx] is not None), 2)
        best_list = max(it1, key = lambda x: x[last_effective_idx])
        worst_list = min(it2, key = lambda x: x[last_effective_idx])
        
        return (best_list, worst_list)
    
    # The following function takes a sequence of equal-length lists as input,
    # and outputs a list of the same length.
    # Each element in each input list is either a value or None.
    # Each element in the output list is the average of the values in the corresponding place
    # of all input lists, ignoring all None elements.
    # If all elements in a place of all input lists are None, then the output element in that place is 0.
    
    @staticmethod
    def averagingLists(sequence_of_lists):
        
        average_list = [None for _ in range(len(sequence_of_lists[0]))]
        
        for idx in range(len(average_list)):
            try:
                average_list[idx] = statistics.mean\
                                    (any_list[idx] for any_list in sequence_of_lists\
                                     if any_list[idx] is not None)
            except:
                average_list[idx] = 0
                
        return average_list
    
    # The following function takes a sequence of lists, and a division unit, as input.
    # Each element in each list is a real value over [0,1).
    # It outputs the density distribution of such values. Each list/element is equally weighted.
    # In other words, one can imagine merging all lists into one long list as the input,
    # and the result is the density of elements in that long list.
    
    @staticmethod
    def densityOverAll(sequence_of_lists, division_unit = 0.01):
        
        total_points = sum(len(single_list) for single_list in sequence_of_lists)
        
        if total_points == 0:
            raise ValueError('Invalid to calculate density for nothing.')
        
        largest_index = int(1/division_unit)
        density_list = [0 for _ in range(largest_index + 1)]
        
        for single_list in sequence_of_lists:
            for value in single_list:
                density_list[int(value/division_unit)] += 1
        
        density_list = [value/total_points for value in density_list]
            
        return density_list
            
        
'''
=======================================
Order, Peer, OrderInfo, Neighbor classes
=======================================
'''
# The following classes represent the main players in the system: orders and peers.
# We will explain why we will need two extra classes (OrderInfo and Neighbor).

class Order:
    
    def __init__(self, scenario, seq, birthtime, creator, expiration = float('inf'), category = None):
        
        self.scenario = scenario # assumption. needed for updateSettledStatus().
        self.seq = seq # sequence number. Not in use now, reserved for possible future use
        self.birthtime = birthtime # will be decided by system clock
        self.creator = creator # the peer who creates this order
        self.expiration = expiration # maximum time for a peer to be valid, and will expire thereafter
        self.category = category # may refer to a trading pair lable or something else
        
        # set of peers who put this order into their local storage.
        self.holders = set()
        
        # set of peers who put this order into their pending table but not local storage.
        # in order words, these peers are hesitating whether to store the orders.
        self.hesitators = set()
        
        self.is_settled = False # this order instance has not been taken and settled
        self.is_canceled = False # will change to True when the order departs proactively.
        
    # This function updates the settled status for this order
    def updateSettledStatus(self): 
        self.scenario.orderUpdateSettleStatus(self)
        
        
# An instance of an orderinfo is an order from a peer's viewpoint. It contains extra information to an Order instance.
# Note, an Order instance can have multiple OrderInfo instances stored by different peers.
# It contains specific information about the novelty and property of the order, not included in Order.

class OrderInfo:
    
    def __init__(self, engine, order, master, arrival_time, priority = None, prev_owner = None, novelty = 0):
    
        self.engine = engine # design choice. Needed for orderinfoSetPriority()
        self.arrival_time = arrival_time # arrival time of this orderinfo to my pending table
        self.prev_owner = prev_owner # previous owner, default is None (a new order)
        self.novelty = novelty # How many hops it has travalled. Default is 0. Leave design space for possible extensions in future.
        self.engine.orderinfoSetPriority(master, order, priority) # set up priority
        
        # storage_decision is to record whether this peer decides to put this order into the storage.
        # It seems redundant, but it will be useful in storeOrders function.
        self.storage_decision = False
            
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
        
        self.peer_type = peer_type # Refers to a peer type (e.g., big/small relayer). Type 0 is a free-rider.
        
        # This denotes if this peer is a free rider (no contribution to other peers)
        # This is a redundant variable, for better readability only.
        # A free rider sits in the system, listen to orders, and does nothing else.
        # It does not generate orders by itself.
        self.is_freerider = (peer_type == 0) 
        
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
        
    def addNeighbor(self, peer):
        
        # if this peer is already a neighbor, there is an error with addNewLinks function.
        if peer in self.peer_neighbor_mapping:
            raise ValueError('The addNewLinksHelper() function is requesting me to add my current neighbor.')
                
        # create new neighbor in my local storage
        new_neighbor = Neighbor(self.engine, peer, self, self.local_clock)
        self.peer_neighbor_mapping[peer] = new_neighbor
        
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
        if remove_order is True:
            
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
        if notification is True:
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

        if self.engine.externalOrderAcceptance(self, order) is True:
            
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
                
        if self.engine.internalOrderAcceptance(self, peer, order) is False:
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
        
        if novelty_update is True:
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
        
        for order, pending_orderinfolist_of_same_id in self.order_pending_orderinfo_mapping.items():
                      
            # Sort the list of pending orderinfo with the same id, so that if
            # there is some order to be stored, it will be the first one.
            pending_orderinfolist_of_same_id.sort(key = lambda item: item.storage_decision, reverse = True)
            
            # Update the order instance, e.g., number of pending orders, and remove the hesitator, in advance.
            order.hesitators.remove(self)
            
            # After sorting, for all pending orderinfo with the same id,
            # either (1) no one is to be stored, or (2) only the first one is stored
            
            if pending_orderinfolist_of_same_id[0].storage_decision is False: # if nothing is to be stored
                for pending_orderinfo in pending_orderinfolist_of_same_id:
                    # Find the global instance of the sender, and update it.
                    if pending_orderinfo.prev_owner in self.peer_neighbor_mapping: # internal order, sender is still a neighbor
                        self.peer_neighbor_mapping[pending_orderinfo.prev_owner].share_contribution[-1] += self.engine.rc
            
            else: # the first element is to be stored
                first_pending_orderinfo = pending_orderinfolist_of_same_id[0]
                # Find the global instance for the sender, and update it.
                if first_pending_orderinfo.prev_owner in self.peer_neighbor_mapping: # internal order, sender is still neighbor
                    self.peer_neighbor_mapping[first_pending_orderinfo.prev_owner].share_contribution[-1] += self.engine.rd
                # Add the order into the local storage, and update the global order instance
                self.order_orderinfo_mapping[order] = first_pending_orderinfo
                self.new_order_set.add(order)
                order.holders.add(self)
                
                
                # For the rest pending orderinfo in the list, no need to store them, but may need to do other updates
                for pending_orderinfo in pending_orderinfolist_of_same_id[1:]:
                    
                    if pending_orderinfo.storage_decision is True:
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
        if self.is_freerider is True:
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
    
 
'''
===========================================
Simulator functions.
===========================================
'''
# The Simulator class contains all function that is directly called by the simulator.
# For example, global initilization of the system, and operations in each time round.

class Simulator:
    
    def __init__(self, scenario, engine, performance):
        
        self.order_full_set = set() # set of orders
        # list of order sets, each containing all orders of a particular type.
        self.order_type_set = [set() for _ in range(len(scenario.order_type_ratios))]
        
        self.peer_full_set = set() # set of peers
        # list of peer sets, each containing all peers of a particular type.
        self.peer_type_set = [set() for _ in range(len(scenario.peer_type_ratios))] 
        
        self.cur_time = 0 # current system time
        self.latest_order_seq = 0 # sequence number for next order to use
        self.latest_peer_seq = 0 # sequence number for next peer to use
        
        self.scenario = scenario # assumptions
        self.engine = engine # design choices
        self.performance = performance # performance evaluation measures

    # This is the global initialization function for system status.
    # Construct a number of peers and a number of orders and maintain their references in two sets.
    # Sequence numbers of peers and neighbors begin from 0 and increase by 1 each time.
    # Right now there is no use for the sequence numbers but we keep them for potential future use.
    # We only consider one type of orders for now. However, we do consider multiple peer types.
    '''
    In current implementation we assume there is only one order type.
    There is a hard-coded line of creating orders of type 0,
    where we create the initial orderbooks for initial peers.
    '''
    
    def globalInit(self):
        
        order_seq = self.latest_order_seq # order sequence number should start from zero, but can be customized
        peer_seq = self.latest_peer_seq # same as above
        
        # determine the peer types
        peer_type_vector = random.choices(range(len(self.scenario.peer_type_ratios)),\
                                          weights = self.scenario.peer_type_ratios, \
                                          k = self.scenario.init_size)
        
        # first create all peer instances with no neighbors
        
        for peer_type in peer_type_vector:
            
            # decide the birth time for this peer.
            # Randomized over [0, birth_time_span] to avoid sequentiality issue.
            birth_time = random.randint(0, self.scenario.birth_time_span - 1)
            
            # decide the number of orders for this peer
            num_orders = max(0, round(random.gauss(self.scenario.peer_parameter_list[peer_type]['mean'],\
                                                   self.scenario.peer_parameter_list[peer_type]['var'])))

            # create all order instances, and the initial orderbooks
            cur_order_set = set()
            
            for _ in range(num_orders):
                # decide the max expiration for this order
                expiration = max(0, round(random.gauss(self.scenario.order_parameter_list[0]['mean'],\
                                                       self.scenario.order_parameter_list[0]['var'])))
                
                # create the order. Order's birth time is cur_time, different from peer's birthtime.
                # Order's creator is set to be None since the peer is not initiated, but will be changed
                # in the peer's initiation function.
                new_order = Order(self.scenario, order_seq, self.cur_time, None, expiration)
                self.order_full_set.add(new_order)
                cur_order_set.add(new_order)
                order_seq += 1
            
            # create the peer instance. Neighbor set is empty.
            new_peer = Peer(self.engine, peer_seq, birth_time, cur_order_set, None, peer_type)
            new_peer.local_clock = self.scenario.birth_time_span - 1
            self.peer_full_set.add(new_peer)
            self.peer_type_set[peer_type].add(new_peer)
            peer_seq += 1
            
        # update the latest order sequence number and latest peer sequence number
        self.latest_order_seq = order_seq
        self.latest_peer_seq = peer_seq
            
        # add neighbors to the peers. Use shuffle function to avoid preference of forming neighbors for
        # peers with small sequence number.
        peer_list = list(self.peer_full_set)
        random.shuffle(peer_list)
        self.checkAddingNeighbor()
            
            
    # when a new peer arrives, it may already have a set of orders. It only needs to specify the number of initial orders, 
    # and the function will specify the sequence numbers for the peers and orders.
    '''
    In current implementation we assume there is only one order type.
    There is a hard-coded line of creating orders of type 0,
    where we create the initial orderbook for this peer.
    '''
    
    def peerArrival(self, peer_type, num_orders): 
        
        # decide this peer's sequence number
        peer_seq = self.latest_peer_seq

        # create the initial orders for this peer and update global order set
        cur_order_set = set()
        order_seq = self.latest_order_seq
        for _ in range(num_orders):
            expiration = max(0, round(random.gauss(self.scenario.order_parameter_list[0]['mean'],\
                                                   self.scenario.order_parameter_list[0]['var'])))
            # Now we initiate the new orders, whose creator should be the new peer.
            # But the new peer has not been initiated, so we set the creator to be None temporarily.
            # We will modify it when the peer is initiated.
            # This is tricky and informal, but I don't have a better way of doing it right now.
            new_order = Order(self.scenario, order_seq, self.cur_time, None, expiration)
            self.order_full_set.add(new_order)
            cur_order_set.add(new_order)
            order_seq += 1
        
        # create the new peer, and add it to the table
        new_peer = Peer(self.engine, peer_seq, self.cur_time, cur_order_set, None, peer_type)
        self.peer_full_set.add(new_peer)
        self.peer_type_set[peer_type].add(new_peer)
        
        # update latest sequence numbers for peer and order
        self.latest_peer_seq += 1
        self.latest_order_seq = order_seq
    
   
    # This peer departs from the system.
    
    def peerDeparture(self, peer):
        
        # update number of replicas of all stored/pending orders with this peer
        for order in peer.order_orderinfo_mapping:
            order.holders.remove(peer)
        for order in peer.order_pending_orderinfo_mapping:
            order.hesitators.remove(peer)
        
        # update existing peers
        for other_peer in self.peer_full_set:
            if peer in other_peer.peer_neighbor_mapping:
                other_peer.delNeighbor(peer)
        
        # update the peer set of the Simulator
        self.peer_full_set.remove(peer)
        self.peer_type_set[peer.peer_type].remove(peer)

     
    # This function initiates an external order arrival, whose creator is the "target_peer"
    
    def orderArrival(self, target_peer, expiration):
        
        # create a new order
        new_order_seq = self.latest_order_seq
        new_order = Order(self.scenario, new_order_seq, self.cur_time, target_peer, expiration)
        
        # update the set of orders for the Simulator
        self.order_full_set.add(new_order)
        self.latest_order_seq += 1
        
        # update the order info to the target peer
        target_peer.receiveOrderExternal(new_order)
    
    
    # This function takes a set of orders to depart as input,
    # deletes them, and deletes all other invalid orders
    # from both order set of Simulator, and all peers' pending tables and storages.

    def updateGlobalOrderbook(self, order_dept_set = None):
        
        if order_dept_set is not None:
            for order in order_dept_set:
                order.is_canceled = True
            
        for order in list(self.order_full_set):
            if ((not order.holders) and (not order.hesitators)) \
               or (self.cur_time - order.birthtime >= order.expiration) \
               or (order.is_settled is True) or (order.is_canceled is True):
                for peer in list(order.holders):
                    peer.delOrder(order)
                for peer in list(order.hesitators):
                    peer.delOrder(order)
                self.order_full_set.remove(order)
                
        return self.order_full_set       
    
    # The following function helps the requester peer to add neighbors, and is called only by checkAddingNeighbor().
    # It targets at adding demand neighbors, but is fine if the final added number
    # is in the range [mininum, demand], or stops when all possible links are added.
    # This function will call the corresponding peers' functions to add the neighbors, respectively.

    def addNewLinksHelper(self, requester, demand, minimum):
                 
        if demand <= 0 or minimum < 0 or demand < minimum:
            raise ValueError('Wrong in requested number(s) or range for adding neighbors.')
        
        candidates_pool = self.peer_full_set - set([requester])
        selection_size = demand
        links_added = 0
        
        while links_added < minimum and candidates_pool:
            
            links_added_this_round = 0
            selected_peer_set = self.engine.neighborRec(requester, candidates_pool, selection_size)
            for candidate in selected_peer_set: 
                # if this peer is already the requester's neighbor, if not,
                # check if the candidate is willing to add the requester.
                if candidate not in requester.peer_neighbor_mapping \
                   and candidate.acceptNeighborRequest(requester):
                    # mutual add neighbors
                    candidate.addNeighbor(requester)
                    requester.addNeighbor(candidate)
                    links_added += 1
                    links_added_this_round += 1
                        
            candidates_pool -= selected_peer_set
            selection_size -= links_added_this_round

    # This function checks for all peers if they need to add neighbors,
    # if the number of neighbors is not enough.
    # It aims at adding up to neighbor_max neighbors, but is fine if
    # added up to neighbor_min, or all possibilities have been tried.
    # This function needs to be proactively called every time round.
    
    def checkAddingNeighbor(self):
        for peer in self.peer_full_set:
            cur_neighbor_size = len(peer.peer_neighbor_mapping)
            if cur_neighbor_size < self.engine.neighbor_min:
                self.addNewLinksHelper(peer, self.engine.neighbor_max - cur_neighbor_size, \
                                          self.engine.neighbor_min - cur_neighbor_size)
                
    
    # The following function runs normal operations at a particular time point.
    # It includes peer/order dept/arrival, order status update,
    # and peer's order acceptance, storing, and sharing.
    # This is a temparaty version. In the next PR, mode will not exist. Please ignore the missing of
    # explanation of "mode" for now.

    def operationsInATimeRound(self, peer_arr_num, peer_dept_num, order_arr_num, order_dept_num):
        
        # peers leave
        for peer_to_depart in random.sample\
            (self.peer_full_set, min(len(self.peer_full_set), peer_dept_num)):
            self.peerDeparture(peer_to_depart)
           
        # existing peers adjust clock
        for peer in self.peer_full_set:
            peer.local_clock += 1
            if peer.local_clock != self.cur_time:
                raise RuntimeError('Clock system in a mass.')
            
        # new peers come in
        peer_type_vector = random.choices(range(len(self.scenario.peer_type_ratios)),\
                                          weights = self.scenario.peer_type_ratios, k = peer_arr_num)
        
        for peer_type in peer_type_vector:
            
            # assuming there is only one type of peers, so taking [0]. Subject to change later.
            num_init_orders = max(0, round(random.gauss(self.scenario.peer_parameter_list[peer_type]['mean'],\
                                                        self.scenario.peer_parameter_list[peer_type]['var'])))
            self.peerArrival(peer_type, num_init_orders)

        # Now, if the system does not have any peers, stop operations in this round.
        # The simulator can still run, hoping that in the next round peers will appear.

        if not self.peer_full_set:
            return
        
        # if there are only free-riders, then there will be no new order arrival.
        # However, other operations will continue.
        
        if self.peer_full_set == self.peer_type_set[0]: # all peers are free-riders
            order_arr_num = 0
            
        # external orders arrival
        
        # Decide which peers to hold these orders.
        # The probablity for any peer to get an order is proportional to its init orderbook size.
        # Free riders will not be candidates since they don't have init orderbook.
        candidate_peer_list = list(self.peer_full_set)
        peer_capacity_weight = list(item.init_orderbook_size for item in candidate_peer_list)
        
        target_peer_list = random.choices(candidate_peer_list, weights = peer_capacity_weight, k = order_arr_num)
            
        for target_peer in target_peer_list:
            # decide the max expiration for this order. Assuming there is only one type of orders, so taking [0]. Subject to change later.
            expiration = max(0, round(random.gauss(self.scenario.order_parameter_list[0]['mean'],\
                                                   self.scenario.order_parameter_list[0]['var'])))    
            self.orderArrival(target_peer, expiration)
            
        # existing orders depart, orders settled, and global orderbook updated
        order_to_depart = random.sample(self.order_full_set, min(len(self.order_full_set), order_dept_num))
    
        for order in self.order_full_set:
            order.updateSettledStatus()
            
        self.updateGlobalOrderbook(order_to_depart)
            
        # peer operations
        self.checkAddingNeighbor()
        for peer in self.peer_full_set:
            if (self.cur_time - peer.birthtime ) % self.engine.batch == 0:
                peer.storeOrders()
                peer.shareOrders()
           
    # This is the function that runs the simulator, including the initilization, and growth and stable periods.
    # It returns performance evaluation results.
    
    def run(self):

        self.cur_time = 0 # the current system time
        self.latest_order_seq = 0 # the next order ID that can be used
        self.latest_peer_seq = 0 # the next peer ID that can be used
        self.peer_full_set.clear() # for each round of simulation, clear everything
        self.peer_type_set = [set() for _ in range(len(self.scenario.peer_type_ratios))]
        self.order_full_set.clear()
        
        # Initialization, orders are only held by creators
        # Peers do not exchange orders at this moment.
        self.globalInit()
        self.updateGlobalOrderbook()
        
        # initiate vectors of each event happening count in each time round
        numpy.random.seed() # this is very important since numpy.random is not multiprocessing safe (when we call Hawkes process)
        counts_growth =\
                    list(map(lambda x: self.scenario.numEvents(x, self.scenario.growth_rounds),\
                             self.scenario.growth_rates))
        numpy.random.seed()
        counts_stable =\
                    list(map(lambda x: self.scenario.numEvents(x, self.scenario.stable_rounds),\
                             self.scenario.stable_rates))
        peer_arrival_count, peer_dept_count, order_arrival_count, order_dept_count = \
                            map(lambda x,y: list(x) + list(y), counts_growth, counts_stable)
        
        # growth period and stable period
        self.cur_time = self.scenario.birth_time_span 
        for i in range(self.scenario.growth_rounds + self.scenario.stable_rounds):
            self.operationsInATimeRound(peer_arrival_count[i], peer_dept_count[i],\
                                        order_arrival_count[i], order_dept_count[i])
            self.cur_time += 1
        
        # performance evaluation
        # input arguments are: time, peer set, normal peer set, free rider set, order set
        performance_result = self.performance.run(self.cur_time, self.peer_full_set, self.peer_type_set[1],\
                                  self.peer_type_set[0], self.order_full_set)
        
        return performance_result
        
 
'''
======================
Multiprocessing execution
======================
'''

# This class contains functions that runs the simulator multiple times, using a multiprocessing manner,
# and finally, average the spreading ratio and output a figure, where x-axis is the age of orders
# and y-axis is the average spreading ratio of that age over the multiple times of running the simulator.
# The need of running the simulator multiple times comes from randomness. Due to randomness, each time the
# simulator is run, the result can be quite different, and the increase of spreading ratio w.r.t age
# is not smooth. Due to the fact that each time the simulator running is totally independent,
# we use multiprocessing to reduce execution time.

class Execution:
    
    def __init__(self, scenario, engine, performance, rounds = 40, multipools = 32):
        self.scenario = scenario # assumption
        self.engine = engine # design choice
        self.performance = performance # performance evaluation method
        
        self.rounds = rounds # how many times the simulator is run. Typtically 40.
        self.multipools = multipools # how many processes we have. Typically 16 or 32.

    def make_run(self, args):
        return Simulator(*args).run()

    def run(self):
        with Pool(self.multipools) as my_pool:
            performance_result_list = my_pool.map(self.make_run,
                          [(self.scenario, self.engine, self.performance) for _ in range(self.rounds)])
        
        # Unpacking and re-organizing the performance evaluation results such that
        # performance_measure[i] is the list of i-th performance result in all runs.
        performance_measure = dict()#[None for _ in range(len(performance_result_list[0]))]
 
        for measure_key in performance_result_list[0].keys():
            performance_measure[measure_key] = list\
                    (item[measure_key] for item in \
                     performance_result_list if item[measure_key] is not None)
            
        # process each performance result
        
        # processing spreading ratio, calculate best, worst, and average spreading ratios
        spreading_ratio_lists = performance_measure['order_spreading']
        if spreading_ratio_lists:
            (best_order_spreading_ratio, worst_order_spreading_ratio)\
                        = DataProcessing.findBestWorstLists(spreading_ratio_lists)
            average_order_spreading_ratio = DataProcessing.averagingLists(spreading_ratio_lists)
            
            plt.plot(average_order_spreading_ratio)
            plt.plot(worst_order_spreading_ratio)
            plt.plot(best_order_spreading_ratio)
            
            plt.legend(['average spreading', 'worst spreading', 'best spreading'], loc='upper left')
            plt.xlabel('age of orders')
            plt.ylabel('spreading ratio')
            plt.show()
        
        legend_label = []
        # processing user satisfaction if it exists. Normal peers first.
        normal_peer_satisfaction_lists = performance_measure['normal_peer_satisfaction']
        if normal_peer_satisfaction_lists:
            legend_label.append('normal peer')
            normal_satistaction_density = DataProcessing.\
                                          densityOverAll(normal_peer_satisfaction_lists)
            plt.plot(normal_satistaction_density)
        
        # processing user satisfaction if it exists. Free riders next.
        free_rider_satisfaction_lists = performance_measure['free_rider_satisfaction']
        if free_rider_satisfaction_lists:
            legend_label.append('free rider')
            freerider_satistaction_density = DataProcessing.\
                                             densityOverAll(free_rider_satisfaction_lists)
            plt.plot(freerider_satistaction_density)
        
        # plot normal peers and free riders satisfactions in one figure.
        if legend_label != []:
            plt.legend(legend_label, loc='upper left')
            plt.xlabel('satisfaction')
            plt.ylabel('density')
            plt.show()
        
        # processing fairness index if it exists. Now it is dummy.
        system_fairness = performance_measure['fairness']
        try:
            system_fairness_density = DataProcessing.densityOverAll\
                                      ([[item for item in system_fairness if item is not None]])
        except:
            raise RuntimeError('Seems wrong somewhere since there is no result for fairness in any run.')
        else:
            plt.plot(system_fairness_density)
            plt.legend(['fairness density'], loc='upper left')
            plt.xlabel('fairness')
            plt.ylabel('density')
            plt.show()
               
'''
The following is one example of a Scenario instance. 
'''

'''
parameters
'''
 
'''
parameters
'''

order_type_ratios = [1] # ratio of orders of each type
peer_type_ratios = [0.1, 0.9] # ratio of peers of each type

# In what follows we use dictionary to generate parameters for a scenario instance.
# One needs to follow the format. No change on the dictionary keys. Change values only.

# The following dictionary specifies an order type (which is the only type we have right now).
# The paramters are the mean and variance of order expirations.

order_default_type = {
    'mean': 500,
    'var': 0
    }

order_par_list = [order_default_type] # right now, only one order type

# The following dictionaries specify various peer types.
# The paramters are the mean and variance of the initial orderbook size of the peer.

peer_free_rider = {
    'mean': 0,
    'var': 0
    }

peer_normal = {
    'mean': 6,
    'var': 1
    }

peer_par_list = [peer_free_rider, peer_normal] # right now, only one peer type

# The following dictionary specifies the paramters for the system's initial status.

init_par = {
    'num_peers': 10,
    'birth_time_span': 20
    }

# The following dictionary specifies the paramters for the system's grwoth period
# when the # of peers keeps increasing.

growth_par = {
    'rounds': 30,
    'peer_arrival': 3,
    'peer_dept': 0,
    'order_arrival': 15,
    'order_dept': 15
    }

# The following dictionary specifies the paramters for the system's stable period
# when the # of peers keeps stable. 

stable_par = {
    'rounds': 50,
    'peer_arrival': 2,
    'peer_dept': 2,
    'order_arrival': 15,
    'order_dept': 15
    }

s_parameters = (order_type_ratios, peer_type_ratios, order_par_list, \
                peer_par_list, init_par, growth_par, stable_par)


'''
options
'''

# event arrival pattern
event_arrival = {
    'method': 'Poisson'
    }

# how an order's is_settled status is changed
change_settle_status = {
    'method': 'Never'
    }

s_options = (event_arrival, change_settle_status)

myscenario = Scenario(s_parameters, s_options)


'''
The following is one example of Engine instance. 
'''

batch = 10 # length of a batch period

# This dictionary describes neighbor-related parameters.
# Similar to creating a Scenario instance, please follow the format and do not change the key.
# Only value can be changed.

topology = {
    'max_neighbor_size': 30,
    'min_neighbor_size': 20}

# This dictionary descrives the incentive score paramters.

incentive = {
    'length': 3,
    'reward_a': 0,
    'reward_b': 0,
    'reward_c': 0,
    'reward_d': 1,
    'reward_e': 0,
    'penalty_a': 0,
    'penalty_b': -1}

e_parameters = (batch, topology, incentive)

'''
options
'''

# Any option choice is a dictionary. It must contain a key "method," to specify which
# implementation function to call. The rest entries, if any, are the parameters specific to this
# implementation that will be passed to the function.

preference = {'method': 'Passive'} # set preference for neighbors
priority = {'method': 'Passive'} # set priority for orders
external = {'method': 'Always'} # how to determine accepting an external order or not
internal = {'method': 'Always'} # how to determine accepting an internal order or not
store = {'method': 'First'} # how to determine storing an order or not

# This dictionary describes how to determine the orders to share with neighbors.
# 'method' refers to the implementation choice. Now we only implemented 'AllNewSelectedOld'.
# The rest entries are parameters specific to this implemention choice and will be passed
# to the implementation function.
share = {
    'method': 'AllNewSelectedOld',
    'max_to_share': 5000,
    'old_share_prob': 0.5
    }

# This dictionary describes how to determine neighbor scoring system.

score = {
    'method': 'Weighted',
    'lazy_contribution_threshold': 2,
    'lazy_length_threshold': 6,
    'weights': [1,1,1] # must be of the same length as incentive['length']
    }

# This dictionary describes how to determine the neighbors that receive my orders.

beneficiary = {
    'method': 'TitForTat',
    'baby_ending_age': 0,
    'mutual_helpers': 3,
    'optimistic_choices': 1
    }

# This dictionary describes neighbor recommendation manner when a peer asks for more neighbors.
# Right now, we only implemented a random recommendation.
rec = {'method': 'Random'}


e_options = (preference, priority, external, internal, store, share, score, beneficiary, rec)

myengine = Engine(e_parameters, e_options)

'''
The following is an example of Performance instance.
'''

'''
parameters
'''

performance_parameters = {'max_age_to_track': 50,
                          'adult_age': 30,
                          'statistical_window': 5
                          }

'''
options
'''

spreading_option = {'method': 'Ratio'}
satisfaction_option = {'method': 'Neutral'}
fairness_option = {'method': 'Dummy'}
measure_options = (spreading_option, satisfaction_option, fairness_option)

'''
executions
'''
measures_to_execute = {'order_spreading_measure': True,
                       'normal_peer_satisfaction_measure': True,
                       'free_rider_satisfaction_measure': True,
                       'fairness': True
                       }

myperformance = Performance(performance_parameters, measure_options, measures_to_execute)

scenarios = [myscenario]#, myscenario_hawkes]
engines = [myengine]
performances = [myperformance]

if __name__ == '__main__':
    for myscenario in scenarios:
        for myengine in engines:
            Execution(myscenario, myengine, myperformance, 20).run()


