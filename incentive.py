'''
===========================
P2P Orderbook simulator

Weijie Wu
April 23, 2019

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

- Class Scenario is our basic assumptions of the system
- Class Engine is our decision choice
- Class Performance contains all peformance evaluation parameters and functions.
- Class Simulator contains all system functions for the simulator to run
- Class Execution contains functions that run the simulator in multi-processing manner and generates the figure

===========================

Design details:


1. Neighborhood relationship:

- Any neighborhood relationships must to be bilateral.
- A peer will try to maintain the size of neighbors within a certain range
    (min, max), unless it is impossible.
- Each time, The simualtor will check if each peer has enough # of neighbors. If not
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
    If happend, the arrival will call the targeting peer's function receiveOrderInternal or receiveOrderExternal.

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

        self.order_type_ratios = order_type_ratios # ratio vector for each type of orders
        self.peer_type_ratios = peer_type_ratios # ratio vector for each type of peers. The last element is the ratio for freeriders.
        
        self.order_parameter_list = list(order_par_list) # each element is (mean, var) of order expiration
        self.peer_parameter_list = list(peer_par_list) # each element is (mean, var) of the initial orderbook size of this peer
        
        # init period, init_size is number of peers joining the P2P at the very first beginning,
        # and the birth time of such peers is randomly distributed over [0,BIRTH_TIME_SPAN]
        (self.init_size, self.birth_time_span) = init_par
        
        # growing period (# of peers increases)
        # parameters are: # of time rounds for growth period, peer arrival rate,
        # peer dept rate, order arrival rate, order dept rate
        self.growth_par = growth_par
    
        # stable period (# of peers remains relatively stable)
        # parameters refer to: # of time rounds for stable period, peer arrival rate,
        # peer dept rate, order arrival rate, order dept rate
        # Theoretically, peer arrival rate ~= peer dept rate, order arrival rate ~= order dept rate.
        self.stable_par = stable_par
        
        # unpacking options
        # options will determine forms of function implementations that describe the system.
        # option_numEvent is an option on the peer/order's arrival pattern. Now only Poisson is implemented.
        # option_settle is an option on when order is settled. Now only "never settle" is implementd.
        (self.option_numEvent, self.option_settle) = options

    # This function generates a sample following a certain event happening pattern.
    # Input is the expected rate, output is a sample of number of incidents for this time slot.
    # Current implementation: Poisson process and Hawkes process.

    def numEvents(self, event_parameters):
        if self.option_numEvent == 'Poisson':
            return numpy.random.poisson(*event_parameters)
        elif self.option_numEvent == 'Hawkes':
            return ScenarioCandidates().Hawkes(*event_parameters)
        else:
            raise ValueError('No sucn option to generate events.')
    
    # This function updates the settle status for orders.
    def orderUpdateSettleStatus(self, order):
        if self.option_settle == 'Never':
            pass # never settles an order
        else:
            raise ValueError('No such option to change settle statues for orders.')

'''
====================
Candidates of Scenarios
====================
'''

# This class contains candidates to realize the functions in Scenario

class ScenarioCandidates():
    
    # This is the funciton to generate Hawkes process
    # The definition of the arrival rate is: 
    # \lambda(t) = a + (\lambda_0 - a ) \times e ^(-\delta \times t) + \sum_{T_i < t} \gamma e^{-\delta (t-T_i)}
    
    # This simulation method was proposed by Dassios and Zhao in a paper entitled 'Exact simulation of Hawkes process
    # with exponentially decaying intensity,' published in Electron. Commun. Probab. 18 (2013) no. 62, 1-13.
    # It is believed to be running faster than other methods.
    
    def Hawkes(self, variables, max_time):
        
        (a, lambda_0, delta, gamma) = variables

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
        
        # batch period
        self.batch = batch
        
        # topology parameters: maximal/minimal size of neighborhood
        (self.neighbor_max, self.neighbor_min) = topology
        
        # incentive related parameters: length of the score sheet, reward a-e, penality a-b
        # reward a-e:
        # a: sharing an order already in my local storage, shared by the same peer
        # b: shairng an order already in my local storage, shared by a different peer
        # c: sharing an order that I accepted to pending table, but I don't store finally
        # d: sharing an order I decide to store
        # e: for sharing an order I have multiple copies in the pending table and decided to store a copy from someone else
        # penalty a-b:
        # a: sharing an order that I have no interest to accept to the pending table
        # b: sharing an identical and duplicate order within the same batch
        
        (self.score_length, self.ra, self.rb, self.rc, self.rd, self.re, self.pa, self.pb) = incentive
        
        # Unpacking options. They specify a choice on a function impelementation.
        # Each option parameter is a tuple, with the first element being the name of the option,
        # followed by parameters specific to this option.
        # For example, share_option may look like ('TitForTat', 3, 1)
        # where 3 is # of mutual helpers and 1 is # of optimisitic choice.
        (self.preference_option, self.priority_option, self.exteral_option, self.internal_option, self.store_option,\
         self.share_option, self.score_option, self.beneficiary_option, self.fair_option, self.rec_option) = options
        
    # This function helps a peer to set a preference to one of its neighbor.
    # A preference represents this peer's attitute to this neighbor (e.g., friend or foe).
    # Parameters: Neighbor is the neighbor instance for this neighbor. Peer is the peer instance for this neighbor.
    # Master is the peer instance who wants to set the preference to the neighbor.
    # Preference is an optional argument in case the master node already has a value to set.
    # If he does not, then it is None by default and the function will decide the value to set based on other arguments.
    
    def neighborSetPreference(self, neighbor, peer, master, preference = None):
        if self.preference_option[0] == 'Passive':
            EngineCandidates().setPreferencePassive(neighbor, peer, master, preference)
        else:
            raise ValueError('No such option to set preference.')
            
    # This function sets a priority for an orderinfo instance.
    # A peer can call this function to manually set a priority value
    # to any orderinfo instance that is accepted into his pending table or local storage.
    # Parameters are similar to the above function.
    # This value can be utilized for order storing and sharing decisions.
    
    def orderinfoSetPriority(self, orderinfo, order, master, priority = None):
        if self.priority_option[0] == 'Passive':
            EngineCandidates().setPriorityPassive(orderinfo, order, master, priority)
        else:
            raise ValueError('No such option to set priority.')
            
    # This function determines whether to accept an external order into the pending table.
    def externalOrderAcceptance(self, receiver, order):
        if self.exteral_option[0] == 'Always':
            return True
        else:
            raise ValueError('No such option to recieve external orders.')
    
    # This function determines whether to accept an internal order into the pending table
    def internalOrderAcceptance(self, receiver, sender, order):
        if self.internal_option[0] == 'Always':
            return True
        else:
            raise ValueError('No such option to receive internal orders.')
    
    # This function is for a peer to determine whether to store each orderinfo
    # in the pending table to the local storage, or discard it.
    # Need to make sure that for each order, at most one orderinfo instance is stored.
    
    def orderStorage(self, peer):
        if self.store_option[0] == 'First':
            EngineCandidates().storeFirst(peer)
        else:
            raise ValueError('No such option to store orders.')
                
    # This function determins the set of orders to share for this peer.
    def ordersToShare(self, peer):
        if self.share_option[0] == 'AllNewSelectedOld':
            return EngineCandidates().shareAllNewSelectedOld(self.share_option, peer)
        else:
            raise ValueError('No such option to share orders.')
    
    # This function calculates the scores of a given peer, and delete a neighbor if necessary
    def scoringNeighbors(self, peer):
        if self.score_option[0] == 'Weighted':
            EngineCandidates().weightedSum(self.score_option, peer)
        else:
            raise ValueError('No such option to calculate scores.')
        
    # This function determines the set of neighboring nodes to share the orders in this batch.
    def neighborToShare(self, time_now, peer):
        if self.beneficiary_option[0] == 'TitForTat':
            return EngineCandidates().titForTat(self.beneficiary_option, time_now, peer)
        else:
            raise ValueError('No such option to decide beneficairies.')
        
    # This function calculates the fairness index for each peer
    # Right now, it is not implemented.
    def calFairness(self, peer):
        if self.fair_option[0] == 'Zero':
            return 0
        else:
            raise ValueError('No such option to calculate fairness index.')
    
    # This function selects some peers from the base peer set for the requester to form neighborhoods
    def neighborRec(self, requester, base, target_number):
        if self.rec_option[0] == 'Random':
            return EngineCandidates().randomRec(requester, base, target_number)
        else:
            raise ValueError('No such option to recommend neighbors.')


'''
====================
Candidates of design choices
====================
'''
# The class Candidates contains all possible realizations of functions in the Engine class.

class EngineCandidates:
    
    # This is a candidate design for setting preference for neighbors.
    # The choice is: set the value as "preference" if preference is not None, or set it as None otherwise.
    
    def setPreferencePassive(self, neighbor, peer, master, preference):
        neighbor.preference = preference
    
    # This is a candidate design for setting a priority for orderinfo.
    # The choice is: set the value as "priority" if priority is not None, or set it as None otherwise.
    
    def setPriorityPassive(self, orderinfo, order, master, priority):
        orderinfo.priority = priority
    
    # This is a candidate design for storing orders.
    # Note that there might be multiple orderinfo instances for a given order instance.
    # The design needs to make sure to store at most one of such orderinfo instances.
    # The choice is: store the first instance of orderinfo for every order.
    
    def storeFirst(self, peer):
        for pending_orderinfolist_of_same_id in peer.order_pending_orderinfo_mapping.values():
            pending_orderinfolist_of_same_id[0].storage_decision = True # first orderinfo is stored
            for orderinfo in pending_orderinfolist_of_same_id[1:]: # the rest (if any) are not stored
                orderinfo.storage_decision = False        
    
    # This is a candidate design for sharing orders.
    # The choice is: share min(max_to_share, # of new_peers) of new peers,
    # and share min(remaining_quota, [# of old peers] * prob) of old peers.
    
    def shareAllNewSelectedOld(self, option, peer):
        
        (_, max_to_share, old_prob) = option
        
        new_order_set = peer.new_order_set
        old_order_set = set(peer.order_orderinfo_mapping) - peer.new_order_set
        selected_order_set = set()
                      
        selected_order_set |= set(random.sample(new_order_set, min(max_to_share, len(new_order_set))))
        
        remaining_share_size = max(0, max_to_share - len(new_order_set))
        probability_selection_size = round(len(old_order_set) * old_prob)
        selected_order_set |= set(random.sample(old_order_set, min(remaining_share_size, probability_selection_size)))            
        return selected_order_set
    
    # This is a candidate design for calculating the scores of neighbors of a peer.
    # The choice is: (1) calculate the current score by a weight sum of all elements in the queue
    # (2) update the queue by moving one step forward and delete the oldest element, and
    # (3) delete a neighbor if it has been lazy for a long time.
 
    def weightedSum(self, option, peer):
        
        # If a neighbor's score is under self.lazy_contri, it is "lazy" in this batch;
        # If a neighbor has been lazy for self.lazy_length time, it is permanently lazy and gets kicked off.
        # discount elements are the weights to add each element of the score queue
        (_, lazy_contri, lazy_length, discount) = option
        
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
            
            # update the contribution queue since it is the end of a calculation circle
            neighbor.share_contribution.popleft()
            neighbor.share_contribution.append(0)
    
    
    # This is a candidate design to select beneficiaries from neighbors.
    # The choice is similar to tit-for-tat.
    # If this is a new peer (age <= baby_ending) and it does not know its neighbors well,
    # it shares to random neighbors (# = mutual + optimistic).
    # Otherwise, it shares to a number of "mutual" of highly-reputated neighbors, and
    # a number of "optimistic" of other random neighbors.
    # In the case where the # of neighbors with non-zero scores is less than "mutual", only
    # select the neithbors with non-zero scores as highly-reputated neighbors.
    # The number of other random neighbors is still "optimistic".
    
    def titForTat(self, option, time_now, peer):
        
        (_, baby_ending, mutual, optimistic) = option
        
        selected_peer_set = set() 
        if (time_now - peer.birthtime <= baby_ending): # This is a new peer. random select neighbors
            selected_peer_set |= set(\
                random.sample(list(peer.peer_neighbor_mapping),\
                              min(len(peer.peer_neighbor_mapping), mutual + optimistic)))
        else: # This is an old peer
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
    # The choice is to choose targe_number elements from the base in a totally random manner.
    # The current implementation does not take requester into consideration.
    
    def randomRec(self, requester, base, target_number):
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

class Performance:
    
    def __init__(self, performance_parameters, measure_options, measures_to_execute):

        # unpacking pamameters. This is design space.
        (max_age_to_track, adult_age, statistical_window) = performance_parameters
        
        # setting paramters
        
        self.max_age_to_track = max_age_to_track # the oldest age of orders to track
        self.adult_age = adult_age # the age beyond which a peer is considered an Adult. Only adult will be evaluated for satisfaction (because new peers receive limited orders)
        
        # this is the window length to aggregate orders for statistics.
        # All orders that falls into the same window will be considered in the same era for calculation.
        # The reason for this window is when order arrival rate is very low, then in many time slots there's no new arrived orders.
        # So it is better to aggregate the orders in the time horizon for such cases.
        self.statistical_window = statistical_window
                
        # unpacking measure options
        (spreading_measure_option, satisfaction_measure_option) = measure_options
        
        # setting options. Right now there is only one option.
        
        # how to measure the spreading pattern of orders (e.g., spreading ratio, spreading speed, etc.)
        self.spreading_measure_option = spreading_measure_option
        
        # how does a peer feel about its satisfaction based on the orders that it is aware of
        self.satisfaction_measure_option = satisfaction_measure_option
        
        # measurement to execute
        self.measures_to_execute = measures_to_execute
        
    # The following function returns some measurement for the spreading pattern of orders.
    # Currently we only implemented spreading ratio.
    
    def orderSpreadingMeasure(self, cur_time, peer_full_set, order_full_set):
        if self.spreading_measure_option == 'Ratio':
            return PerformanceCandidates().\
                   orderSpreadingRatioStat(cur_time, order_full_set, \
                                           peer_full_set, self.max_age_to_track, self.statistical_window)
        else:
            raise ValueError('No such option to evaluate order spreading.')
        
        
    # The following funciton returns some measurement for user satisfaction.
    # Currently, we only implemented a neutral evaluation on receiving any orders.
    # Refer to the comments of peerSatisfaction() function for details.
    
    def userSatisfactionMeasure(self, cur_time, set_of_peers_for_evaluation, order_full_set):
        return PerformanceCandidates().\
                   peerSatisfaction(self.satisfaction_measure_option, set_of_peers_for_evaluation, self.adult_age, \
                                cur_time, self.max_age_to_track, self.statistical_window, order_full_set)
    
    
    # This function runs performance evaluation.
    # It reads the strings in self.measures_to_execute to decide which evaluation functions to call, and returns
    # a list of results corresponding to each evaluation function.
    # If some function is not called, the correponding value is None.
    
    def run(self, cur_time, peer_full_set, normal_peer_set, free_rider_set, order_full_set):
        if 'orderSpreadingMeasure' in self.measures_to_execute:
            result_order_spreading = self.orderSpreadingMeasure(cur_time, peer_full_set, order_full_set)
        else:
            result_order_spreading = None
            
        if 'normalUserSatisfactionMeasure' in self.measures_to_execute:
            result_normal_user_satisfaction = self.userSatisfactionMeasure(cur_time, normal_peer_set, order_full_set)
        else:
            result_normal_user_satisfaction = None
            
        if 'freeRiderSatisfactionMeasure' in self.measures_to_execute:
            result_free_rider_satisfaction = self.userSatisfactionMeasure(cur_time, free_rider_set, order_full_set)
        else:
            result_free_rider_satisfaction = None
            
        result = [result_order_spreading, result_normal_user_satisfaction, result_free_rider_satisfaction]
        return result

'''
=================================
Candidates of performance evaluation
=================================
'''

class PerformanceCandidates:
    

    # The following function returns the spreading ratios of orders, arranged by their age.
    # The return value is a list, the index being the order age, and
    # each value being the spreading ratio of orders of that age.
    # the spreading ratio is defined as the # of peers holding this
    # order, over the total # of peers in the system at current time.
    # The maximal age of orders that we consider, is max_age_to_track.
    # In addition, we divide the orders into age intervals [n * statistical_interval, (n+1)* statistical_interval), n = 0, 1, ...
    # and all orders that falls into an interval are calculated on the same base.
    # if all orders of a particular age (< max age) are all invalid, then value for that entry is 'None'.
    
    def orderSpreadingRatioStat(self, cur_time, order_full_set, peer_full_set, max_age_to_track, statistical_window):
        
        num_active_peers = len(peer_full_set)
        
        order_spreading_ratio = [[] for _ in range(int((max_age_to_track - 1)/statistical_window) + 1)]
        
        for order in order_full_set:
            ratio = len(order.holders) / num_active_peers
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
    
    def orderNumStatOnAge(self, cur_time, max_age_to_track, statistical_window, order_full_set):
        
        num_orders_in_age_range = [0] * int(((max_age_to_track - 1)/statistical_window) + 1)
        for order in order_full_set:
            age = cur_time - order.birthtime
            if age < max_age_to_track:
                bin_num = int(age / statistical_window)
                num_orders_in_age_range[bin_num] += 1
        return num_orders_in_age_range
    
    # The following function is a helper function. It returns the aggregated number of orders that a particular peer
    # observes, based on statistical window of order ages.
    
    def peerInfoObservation(self, peer, cur_time, max_age_to_track, statistical_window):
        
        num_orders_this_peer_stores = [0] * int(((max_age_to_track - 1)/statistical_window) + 1)
        
        for order in peer.order_orderinfo_mapping:
            age = cur_time - order.birthtime
            if age < max_age_to_track:
                bin_num = int(age / statistical_window)
                num_orders_this_peer_stores[bin_num] += 1
                
        return num_orders_this_peer_stores


    # The following function is a helper function. It returns a vector of the ratios of orders it receives, w.r.t. the
    # total # of orders in the system in this catagory. THe catagory is based on age window. If there is no order in
    # the system in this window, the value for this entry is None.

    def singlePeerInfoRatio(self, cur_time, peer, max_age_to_track, statistical_window, order_full_set):
        
        def try_division(x, y):
            try:
                z = x/y
            except:
                z = None
            return z
        
        order_stat_based_on_age = self.orderNumStatOnAge\
                                  (cur_time, max_age_to_track, statistical_window, order_full_set)
        
        num_orders_this_peer_stores = self.peerInfoObservation\
                                      (peer, cur_time, max_age_to_track, statistical_window)
        
        peer_observation_ratio = list(map(try_division, num_orders_this_peer_stores, order_stat_based_on_age))
        
        return peer_observation_ratio
        
        
    # This function calculates a peer's satisfaction based on his info observation ratios
    # The neutral implementation is taking average of each element (neutral to every order), or return None of every element is None.
    
    def singlePeerSatisfactionNeutral(self, cur_time, peer, max_age_to_track, statistical_window, order_full_set):
        
        peer_observation_ratio = self.singlePeerInfoRatio(cur_time, peer, max_age_to_track, statistical_window, order_full_set)
        
        try:
            return statistics.mean(item for item in peer_observation_ratio if item is not None)
        except:
            return None # this peer does not have any orders


    # The following function calculates the peer experiences based on singlePeerSatisfactionNeutral()
    # w.r.t. all adult peers in the system. It returns a (non-fixed length) list of adult-peer satisfactions.
    # Currently we only implemented the option for Neutral (taking average of order receipt rate over all orders) 
    
    def peerSatisfaction(self, option, set_of_peers_for_evaluation, adult_age, \
                               cur_time, max_age_to_track, statistical_window, order_full_set):
        
        if option == 'Neutral':
            singleCalculation = self.singlePeerSatisfactionNeutral
        else:
            raise ValueError('No such option to evaluate peer satisfaction.')
        
        set_of_adult_peers_for_evaluation = set(peer for peer in set_of_peers_for_evaluation\
                                    if cur_time - peer.birthtime >= adult_age)
        
        satisfaction_list = [singleCalculation(cur_time, peer, max_age_to_track, statistical_window, order_full_set)\
                             for peer in set_of_adult_peers_for_evaluation]
        
        return satisfaction_list
    

'''
=======================================
Data processing tools
=======================================
'''
# The following class contains data processing tools (e.g., finding the max, min, average, frequency...)
# for performance evaluation results after running the simulator for multiple times.

class DataProcessing:
    
    # This function takes a sequence of equal-length lists and find the best and worst lists.
    # An element in the list is either a non-negative float/int or None.
    # the best/worst list is the one who's last entry is the largest/smallest among all lists given.
    # If any entry is None, it is ignored (not the best nor the worst).
    # If the last entry of all lists is None, then we look at the second last entry, up till
    # the first entry. If all entries of all lists are None, raise an exception.
    # For example, if list_1 = [0.1, 0.2, 0.3, None], list_2 = [0.29, 0.29, 0.29, None],
    # then list_1 is the best and list_2 is the worst.
    # For effeciency consideration, this function does not check validity of the argument
    # since it should have been guaranteed in the function that calls it.
    
    def findBestWorstLists(self, sequence_of_lists):
        
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
    
    # The following function takes a sequence of equal-length lists as input, and outputs
    # a list of the same length.
    # Each element in each input list is either a float/int or None.
    # Each element in the output list is the average of the values in the corresponding place
    # of all input lists, ignoring all None elements.
    # If all elements in a place of all input lists are None, then the output element is 0.
    
    def averagingLists(self, sequence_of_lists):
        
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
    # Each element in each list is a real value between [0,1).
    # It outputs the density distribution of such values. Each list/element is equally weighted.
    # In other words, one can merge all lists into one long list as the input.
    
    def densityOverAll(self, sequence_of_lists, division_unit = 0.01):
        
        total_points = sum(len(single_list) for single_list in sequence_of_lists)
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
        self.seq = seq # sequence number
        self.birthtime = birthtime # will be decided by system clock
        self.creator = creator # the peer who creates this order
        self.expiration = expiration # maximum time for a peer to be valid, and will expire thereafter.
        self.category = category # may refer to a trading pair lable or something else
        
        # set of peers who put this order into their local storage.
        self.holders = set()
        
        # set of peers who put this order into their pending table but not local storage.
        # in order words, these peers are hesitating whether to store the orders.
        self.hesitators = set()
        
        self.settled = False # this order instance has not been taken and settled
        self.canceled = False # will change to True when the order departs proactively.
        
    # This function updates the settled status for this order
    def updateSettledStatus(self): 
        self.scenario.orderUpdateSettleStatus(self)
        

# An instance of an orderinfo is an order from a peers viewpoint. It contains extra information to an order instance.
# Note, an order instance can have multiple OrderInfo instances stored by different peers.
# It contains specifit information about the novelty and property of the order, not included in Order class.

class OrderInfo:
    
    def __init__(self, engine, order, master, arrival_time, priority = None, prev_owner = None, novelty = 0):
    
        self.engine = engine # design choice
        self.arrival_time = arrival_time # arrival time of this orderinfo to my pending table
        self.prev_owner = prev_owner # previous owner, default is None (a new order)
        self.novelty = novelty # how many hops it has travalled. Default is 0. Leave design space for TEC.
        self.engine.orderinfoSetPriority(master, order, priority) # set up priority
        
        # storage_decision is to record whether this peer decides to put this order into the storage.
        # It seems redundant, but it will be useful in storeOrders function.
        self.storage_decision = False
            
# Each peer maintains a set of neighbors. Note, a neighbor physically is a peer, but a neighbor instance is not a peer instance;
# instead, it has specialized information from a peer's viewpoint.
# For general information about this node, refer to the global mapping table and find the corrosponding peer instance.

class Neighbor:
    
    def __init__(self, engine, peer, master, est_time, preference = None):
         
        self.engine = engine # design choice
        self.est_time = est_time # establishment time
        # "peer" is the peer instance of this neighbor
        # "master" is the peer instance of whom that regards me as a neighbor
        # the following function sets up the master node's preference to this neighbor
        self.engine.neighborSetPreference(peer, master, preference)
        
        # If peer A shares his info to peer B, we say peer A contributes to B.
        # Such contribution is recorded in peer B's local record, i.e., the neighbor instance for peer A in the local storage of peer B.
        # Formally, "share_contribution" is a queue to record a length of "contribution_length" of contributions in the previous rounds.
        # each round is defined as the interval of two contiguous executions of updateNeighborScore function.
        self.share_contribution = collections.deque()
        for _ in range(engine.score_length):
            self.share_contribution.append(0)
        
        self.score = 0 # the score to evaluate my neighbor.
        
        # lazy_round is over how many batch periods has this peer be regarded as a lazy neighbor.
        # A neighbor is regarded as lazy if its score in one batch period is below a certain value.
        # Default for lazy_round is 0. Increased by 1 if its score is below that certain value, or reset to 0 otherwise.
        self.lazy_round = 0
    
        
class Peer:

    # Note: initialization deals with initial orders, but does not establish neighborhood relationships.
    
    def __init__(self, engine, seq, birthtime, init_orders, namespacing = None, peer_type = None):
        
        self.local_clock = birthtime
        
        # simple parameter setting
        self.engine = engine
        self.seq = seq # sequence number
        self.birthtime = birthtime
        self.init_orderbook_size = len(init_orders)
        self.namespacing = namespacing # A peer's namespacing is its interest in certain trading groups. Currently we don't set it.
        
        self.peer_type = peer_type # Refers to a peer type (e.g., big/small relayer). Type 0 is free-rider.
        
        # This denotes if this peer is a free rider (no contribution to other peers)
        # A free rider sits in the system, listen to orders, and does nothing else.
        # It does not generate orders by itself.
        self.freerider = (peer_type == 0) 
        
        self.order_orderinfo_mapping = {} # mapping from the order instance to orderinfo instances that have been formally stored.
        self.peer_neighbor_mapping = {} # mapping from the peer instance to neighbor instance. Note, neighborhood relationship must be bilateral.
        self.new_order_set = set() # set of newly and formally-stored orders that have NEVER been shared out by this peer.
        
        # the following mapping maintains a table of pending orders, by recording their orderinfo instance.
        # note that an order can have multiple orderinfo instances, because it can be forwarded by different neighbors.
        self.order_pending_orderinfo_mapping = {}
        
        if self.freerider and init_orders:
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
    # or False if the cur # of neighbors already reaches the maximal.
    # Note, this function does not establish neighborhood relationship by itself. It accepts or rejects only.
    
    def acceptNeighborRequest(self, requester):
        
        if requester in self.peer_neighbor_mapping:
            raise ValueError('You are my neighbor. No need to request again.')
    
        return len(self.peer_neighbor_mapping) < self.engine.neighbor_min
    
    # The following function establishes a neighborhood relationship.
    # It can only be called by the Simulator function addNewLinksHelper.
        
    def addNeighbor(self, peer):
        
        # if this peer is already a neighbor, error with addNewLinks function.
        if peer in self.peer_neighbor_mapping:
            raise ValueError('The addNewLinksHelper() function is requesting me to add my current neighbor.')
                
        # create new neighbor in my local storage
        new_neighbor = Neighbor(self.engine, peer, self, self.local_clock)
        self.peer_neighbor_mapping[peer] = new_neighbor
        
    # This function defines what a peer will do if it's notified by someone for cancelling a neighborhood relationship.
    # It will always accept and deletes that peer from his neighbor.
    # Note that this is different from a real system that a peer simply drops a neighborhood relationship
    # without need to being accepted by the other side. This function is for simulation bookkeeping purpose only.
        
    def acceptNeighborCancellation(self, requester):
        # If I am removed as a neighbor by my neighbor, I will delete him as well.
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
    # return True if accepted or False otherwise
    
    def receiveOrderExternal(self, order):
        
        if order in self.order_pending_orderinfo_mapping:
            raise ValueError('Duplicated external order. This order is in my pending table.')
        if order in self.order_orderinfo_mapping:
            raise ValueError('Duplicated external order. This order is already in my local storage.')

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
                # my neighbor is sending me the same order again.
                # It may be due to randomness of sharing old orders.
                neighbor.share_contribution[-1] += self.engine.ra
            else:
                # I have this order in my local storage, but it was from someone else.
                # No need to store it anymore. Just update the reward for the uploader.
                neighbor.share_contribution[-1] += self.engine.rb
            return False
            
        # if this order has not been formally stored.
        # Need to write it into the pending table (even if there has been one with the same ID).            
        if novelty_update is True:
            order_novelty = peer.order_orderinfo_mapping[order].novelty + 1
        else:
            order_novelty = peer.order_orderinfo_mapping[order].novelty
                    
        # create an orderinfo instance
        new_orderinfo = OrderInfo(self.engine, order, self, self.local_clock, None, peer, order_novelty)
                    
        # if no such order in the pending list, create an entry for it
        if order not in self.order_pending_orderinfo_mapping: # order id not in the pending set 
            self.order_pending_orderinfo_mapping[order] = [new_orderinfo]
            order.hesitators.add(self)
            # put into the pending table. share reward will be updated when a storing decision is made.
            return True
                        
        # if there is such order in the pending list, check if this order is from the same prev_owner.    
        for existing_orderinfo in self.order_pending_orderinfo_mapping[order]:
            if peer == existing_orderinfo.prev_owner:
                # this neighbor is sending duplicates to me in a short period of time
                # Likely to be a malicious one.
                neighbor.share_contribution[-1] += self.engine.pb
                return False
       
        # my neighbor is honest, but he is late in sending me the message.
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
                      
            # sort the list of pending orderinfo with the same id, so that if
            # there is some order to be stored, it will be the first one.
            pending_orderinfolist_of_same_id.sort(key = lambda item: item.storage_decision, reverse = True)
            
            # update the order instance, e.g., number of pending orders, and remove the hesitator, in advance.
            order.hesitators.remove(self)
            
            # after sorting, for all pending orderinfo with the same id,
            # either (1) no one is to be stored, or (2) only the first one is stored
            
            if pending_orderinfolist_of_same_id[0].storage_decision is False: # if nothing is to be stored
                for pending_orderinfo in pending_orderinfolist_of_same_id:
                    # find the global instance of the sender, and update it.
                    if pending_orderinfo.prev_owner in self.peer_neighbor_mapping: # internal order, sender is still a neighbor
                        self.peer_neighbor_mapping[pending_orderinfo.prev_owner].share_contribution[-1] += self.engine.rc
            
            else: # the first element is to be stored
                first_pending_orderinfo = pending_orderinfolist_of_same_id[0]
                # find the global instance for the sender, and update it.
                if first_pending_orderinfo.prev_owner in self.peer_neighbor_mapping: # internal order, sender is still neighbor
                    self.peer_neighbor_mapping[first_pending_orderinfo.prev_owner].share_contribution[-1] += self.engine.rd
                # add the order into the local storage, and update the global order instance
                self.order_orderinfo_mapping[order] = first_pending_orderinfo
                self.new_order_set.add(order)
                order.holders.add(self)
                
                
                # for the rest pending orderinfo in the list, no need to store them, but may need to do other updates
                for pending_orderinfo in pending_orderinfolist_of_same_id[1:]:
                    
                    if pending_orderinfo.storage_decision is True:
                        raise ValueError('Should not store multiple orders. Wrong in storage decision process.')
                    
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
        if self.freerider is True:
            self.new_order_set.clear()
            return
        
        # Otherwise, this function has to go through order by order and neighbor by neighbor.
        
        # orders to share
        order_to_share_set = self.engine.ordersToShare(self)
        
        # peers to share
        peer_to_share_set = self.engine.neighborToShare(self.local_clock, self)
        
        # call receiver node to accept the orders
        for peer in peer_to_share_set:
            for order in order_to_share_set:
                peer.receiveOrderInternal(self, order)
            
        # clear the new order set. Every order becomes old.        
        self.new_order_set.clear()


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
        self.engine.scoringNeighbors(self)
        peer_list = list(self.peer_neighbor_mapping)
        peer_list.sort(key = lambda item: self.peer_neighbor_mapping[item].score, reverse = True)
        return peer_list
    
    
    # This function measures the fairness of the incentive scheme.
    # There is no implemetion for now, and it is called from nowhere.
    def fairnessIndex(self):
        return self.engine.calFairness(self)
 
 
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
        self.peer_full_set = set() # set of peers
        self.peer_type_set = [set() for _ in range(len(scenario.peer_type_ratios))] # list of set of peers
        
        self.cur_time = 0 # current system time
        self.latest_order_seq = 0 # sequence number for next order to use
        self.latest_peer_seq = 0 # sequence number for next peer to use
        
        self.scenario = scenario
        self.engine = engine
        self.performance = performance

    # This is the global initialization function for system status.
    # Construct a number of peers and a number of orders and maintain their references in two sets.
    # Sequence numbers of peers and neighbors begin from 0 and increase by 1 each time.
    # Right now there is no use for the sequence numbers but we keep them for potential future use.
    # We only consider one type of peers and one type of orders for now.
    
    def globalInit(self):
        
        order_seq = self.latest_order_seq # order sequence number should start from zero, but can be customized
        peer_seq = self.latest_peer_seq # same as above
        
        # determine the peer types
        peer_type_vector = random.choices(range(len(self.scenario.peer_type_ratios)),\
                                          weights = self.scenario.peer_type_ratios, k = self.scenario.init_size)
        
        # first create all peer instances with no neighbors
        
        for peer_type in peer_type_vector:
            
            # decide the birth time for this peer. Randomlized over [0, birth_time_span] to avoid sequentiality issue.
            birth_time = random.randint(0, self.scenario.birth_time_span - 1)
            
            # decide the number of orders for this peer
            num_orders = max(0, round(random.gauss(*self.scenario.peer_parameter_list[peer_type])))

            # create all order instances, and the initial orderbooks
            cur_order_set = set()
            
            for _ in range(num_orders):
                # decide the max expiration for this order
                expiration = max(0, round(random.gauss(*self.scenario.order_parameter_list[0])))
                
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
    # This function deals with normal (not free-riders) peer arrival.
    
    def peerArrival(self, peer_type, num_orders): 
        
        # decide this peer's sequence number
        peer_seq = self.latest_peer_seq

        # create the initial orders for this peer and update global order set
        cur_order_set = set()
        order_seq = self.latest_order_seq
        for _ in range(num_orders):
            expiration = max(0, round(random.gauss(*self.scenario.order_parameter_list[0])))
            # Now we initiate the new orders, whose creator should be the new peer.
            # But the new peer has not been initiated, so we set the creator to be None temporarily.
            # We will modify it when the peer is initiated.
            new_order = Order(self.scenario, order_seq, self.cur_time, None, expiration)
            self.order_full_set.add(new_order)
            cur_order_set.add(new_order)
            order_seq += 1
        
        # create the new peer, and add it to the table
        new_peer = Peer(self.engine, peer_seq, self.cur_time, cur_order_set, None, peer_type)
        self.peer_full_set.add(new_peer)
        self.peer_type_set[peer_type].add(new_peer)
        
        # update latest sequence numberes for peer and order
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
        
        # update the global peer set
        self.peer_full_set.remove(peer)
        self.peer_type_set[peer.peer_type].remove(peer)

     
    # This function initiates an external order arrival, whose creator is the "target_peer"
    
    def orderArrival(self, target_peer, expiration):
        
        # create a new order
        new_order_seq = self.latest_order_seq
        new_order = Order(self.scenario, new_order_seq, self.cur_time, target_peer, expiration)
        
        # update global info of this order
        self.order_full_set.add(new_order)
        self.latest_order_seq += 1
        
        # update the order info to the target peer
        target_peer.receiveOrderExternal(new_order)
    
    
    # This function takes a set of orders to depart as input,
    # deletes them, and deletes all other invalid orders
    # from both the global set and all peers' pending tables and storages.

    def updateGlobalOrderbook(self, order_dept_set = None):
        
        if order_dept_set is not None:
            for order in order_dept_set:
                order.canceled = True
            
        for order in list(self.order_full_set):
            if ((not order.holders) and (not order.hesitators)) \
               or (self.cur_time - order.birthtime >= order.expiration) \
               or (order.settled is True) or (order.canceled is True):
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
            raise ValueError('Wrong in requested number or range.')
        
        pool = self.peer_full_set - set([requester])
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

    def operationsInATimeRound(self, peer_arr_num, peer_dept_num, order_arr_num, order_dept_num):
        
        # peers leave
        for peer_to_depart in random.sample(self.peer_full_set, min(len(self.peer_full_set), peer_dept_num)):
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
            num_init_orders = max(0, round(random.gauss(*self.scenario.peer_parameter_list[peer_type])))
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
            expiration = max(0, round(random.gauss(*self.scenario.order_parameter_list[0])))    
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
    # It returns the spreading ratios of orders at the end of the simulator.
    
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
                    list(map(lambda x: self.scenario.numEvents((x, self.scenario.growth_par[0])), self.scenario.growth_par[1:]))
        numpy.random.seed()
        counts_stable =\
                    list(map(lambda x: self.scenario.numEvents((x, self.scenario.stable_par[0])), self.scenario.stable_par[1:]))
        peer_arrival_count, peer_dept_count, order_arrival_count, order_dept_count = \
                            map(lambda x,y: list(x) + list(y), counts_growth, counts_stable)
        
        # growth period and stable period
        self.cur_time = self.scenario.birth_time_span 
        for i in range(self.scenario.growth_par[0] + self.scenario.stable_par[0]):
            self.operationsInATimeRound(peer_arrival_count[i], peer_dept_count[i], order_arrival_count[i], order_dept_count[i])
            self.cur_time += 1
        
        # performance evaluation
        
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
# and y-axis is the average spreading ratio of that age over the multipel times of running the simulator.
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
            # performance_result_list = list(peformance_results in each run)
            performance_result_list = my_pool.map(self.make_run,
                          [(self.scenario, self.engine, self.performance) for _ in range(self.rounds)])
        
        # Unpacking and reorganizing the performance evaluation results such that
        # performance_measure[i] is the list of i-th performance result in all runs.
        
        performance_measure = [None for _ in range(len(performance_result_list[0]))]
 
        for measure_idx in range(len(performance_result_list[0])):
            performance_measure[measure_idx] = list(item[measure_idx] for item in performance_result_list)
            
        # process each performance result
        
        # processing spreading ratio, calculate best, worst, and average spreading ratios
        
        spreading_ratio_lists = performance_measure[0]
        
        (best_order_spreading_ratio, worst_order_spreading_ratio)\
                    = DataProcessing().findBestWorstLists(spreading_ratio_lists)
        average_order_spreading_ratio = DataProcessing().averagingLists(spreading_ratio_lists)
        
        
        print('spreading ratio is', average_order_spreading_ratio)
        
        plt.plot(average_order_spreading_ratio)
        plt.plot(worst_order_spreading_ratio)
        plt.plot(best_order_spreading_ratio)
        
        plt.legend(['average spreading', 'worst spreading', 'best spreading'], loc='upper left')
        plt.xlabel('age of orders')
        plt.ylabel('spreading ratio')
        plt.show()
        
        # processing user satisfaction. Normal peers first.
        normal_peer_satisfaction_lists = performance_measure[1]
        normal_satistaction_density = DataProcessing().densityOverAll(normal_peer_satisfaction_lists)
        print('density of normal peer satisfaction is', normal_satistaction_density)
        plt.plot(normal_satistaction_density)
        
        # processing user satisfaction. Free riders next.
        free_rider_satisfaction_lists = performance_measure[2]
        freerider_satistaction_density = DataProcessing().densityOverAll(free_rider_satisfaction_lists)
        print('density of free rider satisfaction is', freerider_satistaction_density)
        plt.plot(freerider_satistaction_density)
        
        plt.legend(['normal peer', 'free rider'], loc='upper left')
        plt.xlabel('satisfaction')
        plt.ylabel('density')
        plt.show()
        
'''
The following is one example of Scenario instance. 
'''
 
order_type_ratios = [1] # ratio of orders of each type
peer_type_ratios = [0.2, 0.8] # ratio of peers of each type
order_par_list = [(500,0)] # mean and var of order expiration
peer_par_list = [(0,0), (6,1)] # mean and var of init orderbook size
init_par = (10,20) # # of peers, birthtime span
growth_par = (30,3,0,15,15) # rounds, peer arrival/dept, order arrival/dept, for growth period
stable_par = (50,2,2,15,15) # same above, for stable period


growth_par_hawkes = (30, (1.5,1.5,1,0.5), (0,0,1,0.5), (7.5,7.5,1,0.5), (7.5,7.5,1,0.5))
stable_par_hawkes = (50, (1,1,1,0.5), (1,1,1,0.5), (7.5,7.5,1,0.5), (7.5,7.5,1,0.5))

s_parameters = (order_type_ratios, peer_type_ratios, order_par_list, \
                peer_par_list, init_par, growth_par, stable_par,)

s_parameters_hawkes = (order_type_ratios, peer_type_ratios, order_par_list, \
                peer_par_list, init_par, growth_par_hawkes, stable_par_hawkes)

s_options = ('Poisson', 'Never')
s_options_hawkes = ('Hawkes', 'Never')

myscenario = Scenario(s_parameters, s_options)
myscenario_hawkes = Scenario(s_parameters_hawkes, s_options_hawkes)


'''
The following is one example of Engine instance.
'''

batch = 10 # length of a batch period
topology = (30, 20) # max/min neighbor size
incentive = (3, 0, 0, 0, 1, 0, 0, -1) # length,reward a-e, penalty a-b
e_parameters = (batch, topology, incentive)

preference = ('Passive',)
priority = ('Passive',)
external = ('Always',)
internal = ('Always',)
store = ('First',)
share = ('AllNewSelectedOld', 5000, 0.5)
score = ('Weighted', 2, 6, [1,1,1])
beneficiary = ('TitForTat', 0, 3, 1)
fair = ('Zero',)
rec = ('Random',)
e_options = (preference, priority, external, internal, store, share, score, beneficiary, fair, rec)

myengine = Engine(e_parameters, e_options)

'''
The following is an example of Performance instance.
'''

max_age_to_track = 50
statistical_window = 5
adult_age = 30

performance_parameters = (max_age_to_track, adult_age, statistical_window, )
measure_options = ('Ratio', 'Neutral')
measures_to_execute = ('orderSpreadingMeasure', 'normalUserSatisfactionMeasure', 'freeRiderSatisfactionMeasure')
myperformance = Performance(performance_parameters, measure_options, measures_to_execute)

scenarios = [myscenario]#, myscenario_hawkes]
engines = [myengine]
performances = [myperformance]

if __name__ == '__main__':
    for myscenario in scenarios:
        for myengine in engines:
            Execution(myscenario, myengine, myperformance, 60).run()

