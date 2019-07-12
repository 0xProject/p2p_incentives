"""
This module contains one test case by generating a point in engine, scenario, and performance.
"""

from typing import Dict, Tuple, Any, List
from engine import Engine
from scenario import Scenario
from performance import Performance


# ======
# The following is one example of a Scenario instance.
# parameters

ORDER_TYPE_RATIOS: Dict[str, float] = {'default': 1.0}  # ratio of orders of each type
PEER_TYPE_RATIOS: Dict[str, float] = {'free-rider': 0.1,
                                      'normal': 0.9
                                      }  # ratio of peers of each type

# In what follows we use dictionary to generate parameters for a scenario instance.
# One needs to follow the format. No change on the dictionary keys. Change values only.

# The following dictionary specifies an order type (which is the only type we have right now).
# The parameters are the mean and variance of order expiration.

ORDER_DEFAULT_TYPE: Dict[str, float] = {'mean': 500.0,
                                        'var': 0.0
                                        }

# right now, only one order type
ORDER_PAR_DICT: Dict[str, Dict[str, float]] = {'default': ORDER_DEFAULT_TYPE}

# The following dictionaries specify various peer types.
# The parameters are the mean and variance of the initial orderbook size of the peer.

PEER_FREE_RIDER: Dict[str, float] = {'mean': 0.0,
                                     'var': 0.0
                                     }

PEER_NORMAL: Dict[str, float] = {'mean': 6.0,
                                 'var': 1.0
                                 }

PEER_PAR_DICT: Dict[str, Dict[str, float]] = {'free-rider': PEER_FREE_RIDER,
                                              'normal': PEER_NORMAL
                                              }

# The following dictionary specifies the parameters for the system's initial status.

INIT_PAR: Dict[str, int] = {'num_peers': 10,
                            'birth_time_span': 20
                            }

# The following dictionary specifies the parameters for the system's grwoth period
# when the # of peers keeps increasing.

GROWTH_PAR: Dict[str, float] = {'rounds': 30,
                                'peer_arrival': 3.0,
                                'peer_dept': 0.0,
                                'order_arrival': 15.0,
                                'order_cancel': 15.0
                                }

# The following dictionary specifies the parameters for the system's stable period
# when the # of peers keeps stable.

STABLE_PAR: Dict[str, float] = {'rounds': 50,
                                'peer_arrival': 2.0,
                                'peer_dept': 2.0,
                                'order_arrival': 15.0,
                                'order_cancel': 15.0
                                }

S_PARAMETERS: Tuple[Dict[str, float], Dict[str, float], Dict[str, Dict[str, float]],
                    Dict[str, Dict[str, float]], Dict[str, int], Dict[str, float],
                    Dict[str, float]] \
    = (ORDER_TYPE_RATIOS, PEER_TYPE_RATIOS, ORDER_PAR_DICT, PEER_PAR_DICT, INIT_PAR, GROWTH_PAR,
       STABLE_PAR)

# options

# event arrival pattern
EVENT_ARRIVAL: Dict[str, str] = {'method': 'Poisson'}

# how an order's is_settled status is changed
CHANGE_SETTLE_STATUS: Dict[str, str] = {'method': 'Never'}

S_OPTIONS: Tuple[Dict[str, str], Dict[str, str]] = (EVENT_ARRIVAL, CHANGE_SETTLE_STATUS)

MY_SCENARIO: Scenario = Scenario(S_PARAMETERS, S_OPTIONS)


# =====
# The following is one example of Engine instance.
# parameters

BATCH: int = 10  # length of a batch period

# This dictionary describes neighbor-related parameters.
# Similar to creating a Scenario instance, please follow the format and do not change the key.
# Only value can be changed.

TOPOLOGY: Dict[str, int] = {'max_neighbor_size': 30,
                            'min_neighbor_size': 20
                            }

# This dictionary describes the incentive score parameters.

INCENTIVE: Dict[str, float] = {'length': 3,
                               'reward_a': 0.0,
                               'reward_b': 0.0,
                               'reward_c': 0.0,
                               'reward_d': 1.0,
                               'reward_e': 0.0,
                               'penalty_a': 0.0,
                               'penalty_b': -1.0
                               }

E_PARAMETERS: Tuple[int, Dict[str, int], Dict[str, float]] = (BATCH, TOPOLOGY, INCENTIVE)

# options

# Any option choice is a dictionary. It must contain a key "method," to specify which
# implementation function to call. The rest entries, if any, are the parameters specific to this
# implementation that will be passed to the function.

PREFERENCE: Dict[str, str] = {'method': 'Passive'}  # set preference for neighbors
PRIORITY: Dict[str, str] = {'method': 'Passive'}  # set priority for orders
EXTERNAL: Dict[str, str] = {'method': 'Always'}  # accepting an external order or not
INTERNAL: Dict[str, str] = {'method': 'Always'}  # accepting an internal order or not
STORE: Dict[str, str] = {'method': 'First'}  # storing an order or not

# This dictionary describes how to determine the orders to share with neighbors.
# 'method' refers to the implementation choice. Now we only implemented 'all_new_selected_old'.
# The rest entries are parameters specific to this implementation choice and will be passed
# to the implementation function.

SHARE: Dict[str, Any] = {'method': 'AllNewSelectedOld',
                         'max_to_share': 5000,
                         'old_share_prob': 0.5}

# This dictionary describes how to determine neighbor scoring system.

SCORE: Dict[str, Any] = {'method': 'Weighted',
                         'lazy_contribution_threshold': 2,
                         'lazy_length_threshold': 6,
                         'weights': [1.0, 1.0, 1.0]  # must be of the same length as incentive
                         }

# This dictionary describes how to determine the neighbors that receive my orders.

BENEFICIARY: Dict[str, Any] = {'method': 'TitForTat',
                               'baby_ending_age': 0,
                               'mutual_helpers': 3,
                               'optimistic_choices': 1
                               }

# This dictionary describes neighbor recommendation manner when a peer asks for more neighbors.
# Right now, we only implemented a random recommendation.

REC: Dict[str, Any] = {'method': 'Random'}


E_OPTIONS: Tuple[Dict[str, Any], ...] = (PREFERENCE, PRIORITY, EXTERNAL, INTERNAL, STORE, SHARE,
                                         SCORE, BENEFICIARY, REC)

MY_ENGINE: Engine = Engine(E_PARAMETERS, E_OPTIONS)


# ======
# The following is an example of Performance instance.
# parameters

PERFORMANCE_PARAMETERS: Dict[str, int] = {'max_age_to_track': 50,
                                          'adult_age': 30,
                                          'statistical_window': 5
                                          }

# options

SPREADING_OPTION: Dict[str, str] = {'method': 'Ratio'}
SATISFACTION_OPTION: Dict[str, str] = {'method': 'Neutral'}
FAIRNESS_OPTION: Dict[str, str] = {'method': 'Dummy'}
MEASURE_OPTIONS: Tuple[Dict[str, str], ...] = (SPREADING_OPTION, SATISFACTION_OPTION,
                                               FAIRNESS_OPTION)

# executions

MEASURES_TO_EXECUTE: Dict[str, bool] = {'order_spreading_measure': True,
                                        'normal_peer_satisfaction_measure': True,
                                        'free_rider_satisfaction_measure': True,
                                        'fairness': False
                                        }

MY_PERFORMANCE: Performance = \
    Performance(PERFORMANCE_PARAMETERS, MEASURE_OPTIONS, MEASURES_TO_EXECUTE)

# Putting the instances into lists

SCENARIOS: List[Scenario] = [MY_SCENARIO]
ENGINES: List[Engine] = [MY_ENGINE]
PERFORMANCES: List[Performance] = [MY_PERFORMANCE]
