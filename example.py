"""
This module contains one test case by generating a point in engine, scenario, and performance.
"""

from typing import List
from engine import Engine
from scenario import Scenario
from performance import Performance
from data_types import (
    Distribution,
    OrderFeature,
    PeerFeature,
    OrderTypeFeatureDict,
    PeerTypeFeatureDict,
    SystemInitialState,
    SystemEvolution,
    ScenarioParameters,
    EventOption,
    SettleOption,
    ScenarioOptions,
    Topology,
    Incentive,
    EngineParameters,
    ExternalOption,
    InternalOption,
    PreferenceOption,
    PriorityOption,
    StoreOption,
    AllNewSelectedOld,
    Weighted,
    TitForTat,
    RecommendationOption,
    EngineOptions,
    PerformanceParameters,
    SpreadingOption,
    SatisfactionOption,
    FairnessOption,
    PerformanceOptions,
    PerformanceExecutions,
)


# ======
# The following is one example of a Scenario instance.
# parameters

# ratio and feature of orders of each type.
# If an additional type is added, remember to modify OrderTypeFeatureDict in data_types

# order feature for type "default".
ORDER_DEFAULT_FEATURE = OrderFeature(
    ratio=1.0, expiration=Distribution(mean=500.0, var=0.0)
)

# order type and feature dictionary. Only one type in this example.
ORDER_TYPE_FEATURE_DICT = OrderTypeFeatureDict(default=ORDER_DEFAULT_FEATURE)

# ratio and feature of peers of each type.
# If an additional type is added, remember to modify PeerTypeFeatureDict in data_types

# peer feature for type "normal"
PEER_NORMAL_FEATURE = PeerFeature(
    ratio=0.9, initial_orderbook_size=Distribution(mean=6.0, var=0.0)
)

# peer feature for type "free rider"
PEER_FREE_RIDER_FEATURE = PeerFeature(
    ratio=0.1, initial_orderbook_size=Distribution(0, 0)
)

# peer type and feature dictionary. Now we have normal peers and free riders.
PEER_TYPE_FEATURE_DICT = PeerTypeFeatureDict(
    normal=PEER_NORMAL_FEATURE, free_rider=PEER_FREE_RIDER_FEATURE
)

# The following namedtuple specifies the parameters for the system's initial status.

NUM_PEERS: int = 10
BIRTH_TIME_SPAN: int = 20
INIT_PAR = SystemInitialState(num_peers=NUM_PEERS, birth_time_span=BIRTH_TIME_SPAN)

# The following namedtuple specifies the parameters for the system's growth period
# when the number of peers keeps increasing.

GROWTH_ROUND: int = 30
GROWTH_PEER_ARRIVAL: float = 3.0
GROWTH_PEER_DEPT: float = 0.0
GROWTH_ORDER_ARRIVAL: float = 15.0
GROWTH_ORDER_CANCEL: float = 15.0
GROWTH_PAR = SystemEvolution(
    rounds=GROWTH_ROUND,
    peer_arrival=GROWTH_PEER_ARRIVAL,
    peer_dept=GROWTH_PEER_DEPT,
    order_arrival=GROWTH_ORDER_ARRIVAL,
    order_cancel=GROWTH_ORDER_CANCEL,
)

# The following namedtuple specifies the parameters for the system's stable period
# when the number of peers keeps stable.

STABLE_ROUND: int = 50
STABLE_PEER_ARRIVAL: float = 2.0
STABLE_PEER_DEPT: float = 2.0
STABLE_ORDER_ARRIVAL: float = 15.0
STABLE_ORDER_CANCEL: float = 15.0
STABLE_PAR = SystemEvolution(
    rounds=STABLE_ROUND,
    peer_arrival=STABLE_PEER_ARRIVAL,
    peer_dept=STABLE_PEER_DEPT,
    order_arrival=STABLE_ORDER_ARRIVAL,
    order_cancel=STABLE_ORDER_CANCEL,
)

# Create scenario parameters, in type of a namedtuple.

S_PARAMETERS = ScenarioParameters(
    order_type_feature=ORDER_TYPE_FEATURE_DICT,
    peer_type_feature=PEER_TYPE_FEATURE_DICT,
    init_state=INIT_PAR,
    growth_period=GROWTH_PAR,
    stable_period=STABLE_PAR,
)

# options.

# Note that the data types for options, EventOption and SettleOption, are both TypedDict.
# They both have only one key-value pair where key == "method".
# If another method is created with additional parameters (e.g., "Hawkes"), then first create a
# data type for it (e.g., HawkesEventOption) inheriting from the base type (e.g., EventOption),
# with additional definitions on the parameters.
# One can refer to the options in Engine for examples of additional parameters.

# event arrival pattern.
EVENT_ARRIVAL = EventOption(method="Poisson")
# how an order's is_settled status is changed
CHANGE_SETTLE_STATUS = SettleOption(method="Never")

# creating scenario options, in type of a namedtuple.
S_OPTIONS = ScenarioOptions(EVENT_ARRIVAL, CHANGE_SETTLE_STATUS)

# create MY_SCENARIO instance, in type of a namedtuple.
MY_SCENARIO = Scenario(S_PARAMETERS, S_OPTIONS)


# =====
# The following is one example of Engine instance.
# parameters

BATCH: int = 10  # length of a batch period

# This namedtuple describes neighbor-related parameters.
# Similar to creating a Scenario instance, please follow the format and do not change the key.
# Only value can be changed.

MAX_NEIGHBOR_SIZE: int = 30
MIN_NEIGHBOR_SIZE: int = 20
TOPOLOGY = Topology(
    max_neighbor_size=MAX_NEIGHBOR_SIZE, min_neighbor_size=MIN_NEIGHBOR_SIZE
)

# This namedtuple describes the incentive score parameters.
# The physical meaning of parameters like reward_a, ... reward_e are in the definition of the data
# types in date_types.py.

LENGTH: int = 3
REWARD_A: float = 0.0
REWARD_B: float = 0.0
REWARD_C: float = 0.0
REWARD_D: float = 1.0
REWARD_E: float = 0.0
PENALTY_A: float = 0.0
PENALTY_B: float = -1.0

INCENTIVE = Incentive(
    score_sheet_length=LENGTH,
    reward_a=REWARD_A,
    reward_b=REWARD_B,
    reward_c=REWARD_C,
    reward_d=REWARD_D,
    reward_e=REWARD_E,
    penalty_a=PENALTY_A,
    penalty_b=PENALTY_B,
)

# creating engine parameters, in type of a namedtuple.
E_PARAMETERS = EngineParameters(BATCH, TOPOLOGY, INCENTIVE)

# options

# Note that the data types for all the options (e.g., PreferenceOption) are both TypedDict.
# They all have only one key-value pair where key == "method" which specifies how the function
# should be really implemented.
# If a method is created with additional parameters (e.g., "TitForTat"), then first create a
# data type for it (e.g., TitForTat) inheriting from the base type (e.g., BeneficiaryOption),
# where "method" = "TitForTat", and with additional definitions on the parameters (e.g.,
# baby_ending_age: int, mutual_helpers: int, and optimistic_choices: int), so they can be passed
# to the function implementation.

# set preference for neighbors
PREFERENCE = PreferenceOption(method="Passive")

# set priority for orders
PRIORITY = PriorityOption(method="Passive")

# accepting an external order or not
EXTERNAL = ExternalOption(method="Always")

# accepting an internal order or not
INTERNAL = InternalOption(method="Always")

# storing an order or not
STORE = StoreOption(method="First")

# This TypedDict describes how to determine the orders to share with neighbors.
# Now we only implemented 'all_new_selected_old'.

SHARE = AllNewSelectedOld(
    method="AllNewSelectedOld", max_to_share=5000, old_share_prob=0.5
)

# This TypedDict describes how to determine neighbor scoring system.

SCORE = Weighted(
    method="Weighted",
    lazy_contribution_threshold=2,
    lazy_length_threshold=6,
    weights=[1.0, 1.0, 1.0],
)  # must be of the same length as incentive


# This TypedDict describes how to determine the neighbors that receive my orders.

BENEFICIARY = TitForTat(
    method="TitForTat", baby_ending_age=0, mutual_helpers=3, optimistic_choices=1
)

# how to recommendation neighbors when a peer asks for more.
# Right now, we only implemented a random recommendation.

REC = RecommendationOption(method="Random")

# creating engine option, in type of a namedtuple

E_OPTIONS = EngineOptions(
    PREFERENCE, PRIORITY, EXTERNAL, INTERNAL, STORE, SHARE, SCORE, BENEFICIARY, REC
)

# creating MY_ENGINE, an instance of Engine, in type pf a namedtuple.
MY_ENGINE = Engine(E_PARAMETERS, E_OPTIONS)


# ======
# The following is an example of Performance instance.
# parameters

MAX_AGE_TO_TRACK: int = 50
ADULT_AGE: int = 30
STATISTICAL_WINDOW: int = 5

# creating performance parameters, in type of a namedtuple.

PERFORMANCE_PARAMETERS = PerformanceParameters(
    max_age_to_track=MAX_AGE_TO_TRACK,
    adult_age=ADULT_AGE,
    statistical_window=STATISTICAL_WINDOW,
)

# options

SPREADING = SpreadingOption(method="Ratio")

SATISFACTION = SatisfactionOption(method="Neutral")

FAIRNESS = FairnessOption(method="Dummy")

# creating performance options, in type of a namedtuple.

MEASURE_OPTIONS = PerformanceOptions(SPREADING, SATISFACTION, FAIRNESS)

# executions, in type of a namedtuple.
# If one wants to add more execution possibilities, modify the definition of
# PerformanceExecutions (in type of a namedtuple) first in data_types module.

ORDER_SPREADING: bool = True
NORMAL_PEER_SATISFACTION: bool = True
FREE_RIDER_SATISFACTION: bool = True
SYSTEM_FAIRNESS: bool = False


MEASURES_TO_EXECUTE = PerformanceExecutions(
    order_spreading=ORDER_SPREADING,
    normal_peer_satisfaction=NORMAL_PEER_SATISFACTION,
    free_rider_satisfaction=FREE_RIDER_SATISFACTION,
    system_fairness=SYSTEM_FAIRNESS,
)

# create MY_PERFORMANCE instance, in type of a namedtuple.

MY_PERFORMANCE = Performance(
    PERFORMANCE_PARAMETERS, MEASURE_OPTIONS, MEASURES_TO_EXECUTE
)

# Putting the instances into lists

SCENARIOS: List[Scenario] = [MY_SCENARIO]
ENGINES: List[Engine] = [MY_ENGINE]
PERFORMANCES: List[Performance] = [MY_PERFORMANCE]
