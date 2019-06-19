0x Mesh Simulator
===

## Purpose

This simulator is meant to run simulations for 0x mesh.
Its initial aim is to facilitate the decision of key design choices in such system.
It is not constraint by any particular design choice, but works as a platform so that
any mechanism can be plug into the simulator.

## Structure

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


## Classes and modules

- Class Peer represents peers in the system.

- Class Neighbor represents the neighbors of a particular peer. A neighbor is physically another peer, 
but with some extra local information.

- Class Order represents orders in the system.
- Class OrderInfo represents an order instance stored in a peer's local storage or pending table.
    It is physically an order, but with some local information, e.g., who transmitted at what time.

- Class Scenario determines our basic assumptions of the system.
    Functions that implement assumptions are in module scenario_candidates.
- Class Engine determines a decision choice.
    Functions that implement decision choices are in module engine_candidates.
- Class Performance contains performance measures.
    Functions that implement performance evaluations are in module performance_candidates.
   
- Module data_processing contains some data processing functions that will be used by functions elsewhere.

- Class Simulator contains all system functions for the simulator to run.

- Class Execution contains functions that run the simulator in multi-processing manner and generates the result.

- Module example generates an example of the simulator input. It contains all testing points by constructing instances
 for Scenario, Engine, and Performance classes.

- Module run is the main file that runs the simulator. It gets inputs from Example, and runs the Execution for each 
input.

## Design details


1. Neighborhood relationship:

	- Any neighborhood relationship must to be bilateral.
	- A peer will try to maintain the size of its neighbors within a certain range
    (min, max), unless it is impossible.
	- Each round, the simulator will check that each peer has enough # of neighbors. If not
    (# < min), the simulator function add_new_links_helper() will be called to add new neighbors.
	- The only way to create new links is calling add_new_links_helper().
		- Procedure is: random selection of peers -> send invitation to the other party -> Accepted?
        	- Y: both sides add neighbors
        	- N: nothing happens.
        	- Accept or reject: Always accept if # of my neighbor has not reached the pre-set maximal value.
    - If neighbor departs or it is considered as lazy (score is too low) for a long time, neighborhood is cancelled.
   		- Procedure is: delete my neighbor -> notify my neighbor (if he's still alive) to delete me too.

2. Order flows: arrival -> accept to pending table -> accept to local storage -> share it with others

	- Order arrival: two forms of arrival: internal and external.
		- Internal: caused by a neighbor sharing an order. Can happen any time.
    	- External: caused by an external order arrival. Can also happen any time.
    	- If it happens, the arrival will call the targeting peer's function receive_order_internal() or 
    	receive_order_external().

	- Order acceptance: The functions receiveOrderInternal or receive_order_external() can only be called by order sharing
    or external order arrival, at any time. These functions will determine whether or not to put the orders into 
    the pending table.
    
	- Order storing: This function can only be called from the Simulator class proactively. No other function calls it.
    It runs only at the end of a batch period. It will decide whether to put pending orders into the local storage.
    Pending table will be cleared.
    
	- Order sharing: This function can only be called from the Simulator class proactively, following order storing.
    No other function calls it. It runs only at the end of a batch period.
    It will decide whether to share any stored order to any neighbor.
    It will call neighbor ranking function, which will first update neighbor scores.
    
3. Peer init will directly put some orders into the local storage, without going through pending table.
    For new peers, the birth time is the end of the 0th batch period, so order sharing will be called at birth.
    
4. New neighbor establishment does not call any order-related operations.
    - That being said, if I am an old peer but I am newly accepted by some other peer in the system as his neighbor,
    I need to wait until the end of batch period of the peer who accepted me, to receive his sharing;
    I will also wait until the end of my batch period, to share with him my orders.
         
## Some Options:

- When an order is transmitted, we have an option "novelty" to indicate how may hops have this order been transmitted.
  If there is no fee sharing, we can disable this function since orders are not differentiable via hop numbers.
  If fee sharing is enabled, then enabling this feature will be useful (since some versions of a transmitted order 
  can fill in a taker fee, some cannot).

- When a peer A deletes a neighbor B, we have an option for A to delete orders that are transmitted
    from B (in which case we call B is the order's previous owner). Normally we don't need to enable this feature, 
    but if this neighbor is malicious, you may want to delete all orders from it.

## Limitations

- In blockchain, the status of an order settlement is based on consensus, so it is in an asymptotic sense.
  There might be different beliefs/forks due to latency in the mesh network, but for now,
  we assume that there is some global grand truth for an order's status.
  This simplification ignores races and may bring inaccuracy.

- Discrete time setting might be less accurate than event driven simulation.

- We do not model communication delay.

- Once there are more replicas of an order in the system, there is a better opportunity for settlement.
    This is not reflected.

- There is no namespacing (i.e., peers have particular interest in some trading pairs and only store/share these orders)
 right now.

- Neighborhood topology is totally random.
  
