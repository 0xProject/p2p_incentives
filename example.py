"""
This module contains one test case by generating a point in engine, scenario, and performance.
"""

from engine import Engine
from scenario import Scenario
from performance import Performance


# ======
# The following is one example of a Scenario instance.
# parameters

ORDER_TYPE_RATIOS = {'default': 1.0}  # ratio of orders of each type
PEER_TYPE_RATIOS = {'free-rider': 0.1,
                    'normal': 0.9
                    }  # ratio of peers of each type

# In what follows we use dictionary to generate parameters for a scenario instance.
# One needs to follow the format. No change on the dictionary keys. Change values only.

# The following dictionary specifies an order type (which is the only type we have right now).
# The parameters are the mean and variance of order expiration.

ORDER_DEFAULT_TYPE = {
    'mean': 500.0,
    'var': 0.0
    }

ORDER_PAR_DICT = {'default': ORDER_DEFAULT_TYPE}  # right now, only one order type

# The following dictionaries specify various peer types.
# The parameters are the mean and variance of the initial orderbook size of the peer.

PEER_FREE_RIDER = {
    'mean': 0.0,
    'var': 0.0
    }

PEER_NORMAL = {
    'mean': 6.0,
    'var': 1.0
    }

PEER_PAR_DICT = {'free-rider': PEER_FREE_RIDER,
                 'normal': PEER_NORMAL
                 }

# The following dictionary specifies the parameters for the system's initial status.

INIT_PAR = {
    'num_peers': 10,
    'birth_time_span': 20
    }

# The following dictionary specifies the parameters for the system's grwoth period
# when the # of peers keeps increasing.

GROWTH_PAR = {
    'rounds': 30,
    'peer_arrival': 3.0,
    'peer_dept': 0.0,
    'order_arrival': 15.0,
    'order_cancel': 15.0
    }

# The following dictionary specifies the parameters for the system's stable period
# when the # of peers keeps stable.

STABLE_PAR = {
    'rounds': 50,
    'peer_arrival': 2.0,
    'peer_dept': 2.0,
    'order_arrival': 15.0,
    'order_cancel': 15.0
    }

S_PARAMETERS = (ORDER_TYPE_RATIOS, PEER_TYPE_RATIOS, ORDER_PAR_DICT, PEER_PAR_DICT, INIT_PAR,
                GROWTH_PAR, STABLE_PAR)

# options

# event arrival pattern
EVENT_ARRIVAL = {
    'method': 'Poisson'
    }

# how an order's is_settled status is changed
CHANGE_SETTLE_STATUS = {
    'method': 'Never'
    }

S_OPTIONS = (EVENT_ARRIVAL, CHANGE_SETTLE_STATUS)

MY_SCENARIO = Scenario(S_PARAMETERS, S_OPTIONS)


# =====
# The following is one example of Engine instance.
# parameters

BATCH = 10  # length of a batch period

# This dictionary describes neighbor-related parameters.
# Similar to creating a Scenario instance, please follow the format and do not change the key.
# Only value can be changed.

TOPOLOGY = {
    'max_neighbor_size': 30,
    'min_neighbor_size': 20}

# This dictionary describes the incentive score parameters.

INCENTIVE = {
    'length': 3,
    'reward_a': 0.0,
    'reward_b': 0.0,
    'reward_c': 0.0,
    'reward_d': 1.0,
    'reward_e': 0.0,
    'penalty_a': 0.0,
    'penalty_b': -1.0}

E_PARAMETERS = (BATCH, TOPOLOGY, INCENTIVE)

# options

# Any option choice is a dictionary. It must contain a key "method," to specify which
# implementation function to call. The rest entries, if any, are the parameters specific to this
# implementation that will be passed to the function.

PREFERENCE = {'method': 'Passive'}  # set preference for neighbors
PRIORITY = {'method': 'Passive'}  # set priority for orders
EXTERNAL = {'method': 'Always'}  # how to determine accepting an external order or not
INTERNAL = {'method': 'Always'}  # how to determine accepting an internal order or not
STORE = {'method': 'First'}  # how to determine storing an order or not

# This dictionary describes how to determine the orders to share with neighbors.
# 'method' refers to the implementation choice. Now we only implemented 'all_new_selected_old'.
# The rest entries are parameters specific to this implementation choice and will be passed
# to the implementation function.

SHARE = {
    'method': 'AllNewSelectedOld',
    'max_to_share': 5000,
    'old_share_prob': 0.5
    }

# This dictionary describes how to determine neighbor scoring system.

SCORE = {
    'method': 'Weighted',
    'lazy_contribution_threshold': 2,
    'lazy_length_threshold': 6,
    'weights': [1.0, 1.0, 1.0]  # must be of the same length as incentive['length']
    }

# This dictionary describes how to determine the neighbors that receive my orders.

BENEFICIARY = {
    'method': 'TitForTat',
    'baby_ending_age': 0,
    'mutual_helpers': 3,
    'optimistic_choices': 1
    }

# This dictionary describes neighbor recommendation manner when a peer asks for more neighbors.
# Right now, we only implemented a random recommendation.

REC = {'method': 'Random'}


E_OPTIONS = (PREFERENCE, PRIORITY, EXTERNAL, INTERNAL, STORE, SHARE, SCORE, BENEFICIARY, REC)

MY_ENGINE = Engine(E_PARAMETERS, E_OPTIONS)


# ======
# The following is an example of Performance instance.
# parameters

PERFORMANCE_PARAMETERS = {'max_age_to_track': 50,
                          'adult_age': 30,
                          'statistical_window': 5
                          }

# options

SPREADING_OPTION = {'method': 'Ratio'}
SATISFACTION_OPTION = {'method': 'Neutral'}
FAIRNESS_OPTION = {'method': 'Dummy'}
MEASURE_OPTIONS = (SPREADING_OPTION, SATISFACTION_OPTION, FAIRNESS_OPTION)

# executions

MEASURES_TO_EXECUTE = {'order_spreading_measure': True,
                       'normal_peer_satisfaction_measure': True,
                       'free_rider_satisfaction_measure': True,
                       'fairness': False
                       }

MY_PERFORMANCE = Performance(PERFORMANCE_PARAMETERS, MEASURE_OPTIONS, MEASURES_TO_EXECUTE)

# Putting the instances into lists

SCENARIOS = [MY_SCENARIO]
ENGINES = [MY_ENGINE]
PERFORMANCES = [MY_PERFORMANCE]
