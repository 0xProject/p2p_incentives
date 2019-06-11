"""
========================
Generating a test case
========================
"""
# This module contains one test case by generating a point in engine, scenario, and performance

from engine import Engine
from scenario import Scenario
from performance import Performance


"""
The following is one example of a Scenario instance. 
"""
"""
parameters
"""

order_type_ratios = {"default": 1}  # ratio of orders of each type
peer_type_ratios = {
    "free-rider": 0.1,
    "normal": 0.9,
}  # ratio of peers of each type

# In what follows we use dictionary to generate parameters for a scenario instance.
# One needs to follow the format. No change on the dictionary keys. Change values only.

# The following dictionary specifies an order type (which is the only type we have right now).
# The paramters are the mean and variance of order expirations.

order_default_type = {"mean": 500, "var": 0}

order_par_dict = {
    "default": order_default_type
}  # right now, only one order type

# The following dictionaries specify various peer types.
# The paramters are the mean and variance of the initial orderbook size of the peer.

peer_free_rider = {"mean": 0, "var": 0}

peer_normal = {"mean": 6, "var": 1}

peer_par_dict = {"free-rider": peer_free_rider, "normal": peer_normal}

# The following dictionary specifies the paramters for the system's initial status.

init_par = {"num_peers": 10, "birth_time_span": 20}

# The following dictionary specifies the paramters for the system's grwoth period
# when the # of peers keeps increasing.

growth_par = {
    "rounds": 30,
    "peer_arrival": 3,
    "peer_dept": 0,
    "order_arrival": 15,
    "order_dept": 15,
}

# The following dictionary specifies the paramters for the system's stable period
# when the # of peers keeps stable.

stable_par = {
    "rounds": 50,
    "peer_arrival": 2,
    "peer_dept": 2,
    "order_arrival": 15,
    "order_dept": 15,
}

s_parameters = (
    order_type_ratios,
    peer_type_ratios,
    order_par_dict,
    peer_par_dict,
    init_par,
    growth_par,
    stable_par,
)


"""
options
"""

# event arrival pattern
event_arrival = {"method": "Poisson"}

# how an order's is_settled status is changed
change_settle_status = {"method": "Never"}

s_options = (event_arrival, change_settle_status)

myscenario = Scenario(s_parameters, s_options)


"""
The following is one example of Engine instance.  
"""
"""
parameters
"""

batch = 10  # length of a batch period

# This dictionary describes neighbor-related parameters.
# Similar to creating a Scenario instance, please follow the format and do not change the key.
# Only value can be changed.

topology = {"max_neighbor_size": 30, "min_neighbor_size": 20}

# This dictionary descrives the incentive score paramters.

incentive = {
    "length": 3,
    "reward_a": 0,
    "reward_b": 0,
    "reward_c": 0,
    "reward_d": 1,
    "reward_e": 0,
    "penalty_a": 0,
    "penalty_b": -1,
}

e_parameters = (batch, topology, incentive)

"""
options
"""

# Any option choice is a dictionary. It must contain a key "method," to specify which
# implementation function to call. The rest entries, if any, are the parameters specific to this
# implementation that will be passed to the function.

preference = {"method": "Passive"}  # set preference for neighbors
priority = {"method": "Passive"}  # set priority for orders
external = {
    "method": "Always"
}  # how to determine accepting an external order or not
internal = {
    "method": "Always"
}  # how to determine accepting an internal order or not
store = {"method": "First"}  # how to determine storing an order or not

# This dictionary describes how to determine the orders to share with neighbors.
# 'method' refers to the implementation choice. Now we only implemented 'AllNewSelectedOld'.
# The rest entries are parameters specific to this implemention choice and will be passed
# to the implementation function.
share = {
    "method": "AllNewSelectedOld",
    "max_to_share": 5000,
    "old_share_prob": 0.5,
}

# This dictionary describes how to determine neighbor scoring system.

score = {
    "method": "Weighted",
    "lazy_contribution_threshold": 2,
    "lazy_length_threshold": 6,
    "weights": [1, 1, 1],  # must be of the same length as incentive['length']
}

# This dictionary describes how to determine the neighbors that receive my orders.

beneficiary = {
    "method": "TitForTat",
    "baby_ending_age": 0,
    "mutual_helpers": 3,
    "optimistic_choices": 1,
}

# This dictionary describes neighbor recommendation manner when a peer asks for more neighbors.
# Right now, we only implemented a random recommendation.
rec = {"method": "Random"}


e_options = (
    preference,
    priority,
    external,
    internal,
    store,
    share,
    score,
    beneficiary,
    rec,
)

myengine = Engine(e_parameters, e_options)

"""
The following is an example of Performance instance.
"""
"""
parameters
"""

performance_parameters = {
    "max_age_to_track": 50,
    "adult_age": 30,
    "statistical_window": 5,
}

"""
options
"""

spreading_option = {"method": "Ratio"}
satisfaction_option = {"method": "Neutral"}
fairness_option = {"method": "Dummy"}
measure_options = (spreading_option, satisfaction_option, fairness_option)

"""
executions
"""
measures_to_execute = {
    "order_spreading_measure": True,
    "normal_peer_satisfaction_measure": True,
    "free_rider_satisfaction_measure": True,
    "fairness": False,
}

myperformance = Performance(
    performance_parameters, measure_options, measures_to_execute
)

"""
Putting the instances into lists
"""

scenarios = [myscenario]  # , myscenario_hawkes]
engines = [myengine]
performances = [myperformance]
