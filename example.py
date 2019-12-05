"""
This module contains one test case by generating a point in engine, scenario, and performance.
"""

from typing import List
import numpy
from engine import Engine
from scenario import Scenario
from performance import Performance
from data_types import (
    Distribution,
    OrderProperty,
    ConcaveProperty,
    RandomProperty,
    AgeBasedProperty,
    PeerProperty,
    OrderTypePropertyDict,
    PeerTypePropertyDict,
    SystemInitialState,
    SystemEvolution,
    ScenarioParameters,
    EventOption,
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
    RemoveLazy,
    TitForTat,
    RecommendationOption,
    LoopOption,
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

# On-chain verification speed
ON_CHAIN_SPEED = Distribution(mean=numpy.log(6.7), var=0.0)

# ratio and property of orders of each type.
# If an additional type is added, remember to modify OrderTypePropertyDict in data_types

# order property for type "default".
ORDER_DEFAULT_PROPERTY = OrderProperty(
    expiration=Distribution(mean=510.0, var=0.0),
    settlement=ConcaveProperty(
        method="ConcaveProperty",
        sensitivity=Distribution(mean=1.0, var=0.0),
        max_prob=Distribution(mean=0.0, var=0.0),
    ),
    cancellation=AgeBasedProperty(
        method="AgeBasedProperty",
        sensitivity=Distribution(mean=1.0, var=0.0),
        max_prob=Distribution(mean=0.01, var=0.0),
    ),
)

# order property for type "nft".
ORDER_NFT_PROPERTY = OrderProperty(
    expiration=Distribution(mean=600.0, var=0.0),
    settlement=ConcaveProperty(
        method="ConcaveProperty",
        sensitivity=Distribution(mean=2.0, var=0.0),
        max_prob=Distribution(mean=0.0, var=0.0),
    ),
    cancellation=RandomProperty(
        method="RandomProperty", prob=Distribution(mean=0.01, var=0.0)
    ),
)

# order type and property dictionary.
ORDER_TYPE_PROPERTY_DICT = OrderTypePropertyDict(
    default=ORDER_DEFAULT_PROPERTY, nft=ORDER_NFT_PROPERTY
)

# ratio and property of peers of each type.
# If an additional type is added, remember to modify PeerTypePropertyDict in data_types

# peer property for type "normal"
PEER_NORMAL_PROPERTY = PeerProperty(
    ratio=0.9,
    initial_orderbook_size_dict={
        "default": Distribution(mean=3.0, var=0.0),
        "nft": Distribution(mean=3.0, var=0.0),
    },
)

# peer property for type "free rider"
PEER_FREE_RIDER_PROPERTY = PeerProperty(
    ratio=0.1,
    initial_orderbook_size_dict={
        "default": Distribution(mean=0.0, var=0.0),
        "nft": Distribution(mean=0.0, var=0.0),
    },
)

# peer type and property dictionary. Now we have normal peers and free riders.
PEER_TYPE_PROPERTY_DICT = PeerTypePropertyDict(
    normal=PEER_NORMAL_PROPERTY, free_rider=PEER_FREE_RIDER_PROPERTY
)

# The following namedtuple specifies the parameters for the system's initial status.

INIT_PAR = SystemInitialState(num_peers=10, birth_time_span=20)

# The following namedtuple specifies the parameters for the system's growth period
# when the number of peers keeps increasing.

GROWTH_PAR = SystemEvolution(
    rounds=30, peer_arrival=3.0, peer_dept=0.0, order_arrival=15.0
)

# The following namedtuple specifies the parameters for the system's stable period
# when the number of peers keeps stable.

STABLE_PAR = SystemEvolution(
    rounds=50, peer_arrival=2.0, peer_dept=2.0, order_arrival=15.0
)

# Create scenario parameters, in type of a namedtuple.

S_PARAMETERS = ScenarioParameters(
    on_chain_verification=ON_CHAIN_SPEED,
    order_type_property=ORDER_TYPE_PROPERTY_DICT,
    peer_type_property=PEER_TYPE_PROPERTY_DICT,
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

# creating scenario options, in type of a namedtuple.
S_OPTIONS = ScenarioOptions(EVENT_ARRIVAL)

# create MY_SCENARIO instance, in type of a namedtuple.
MY_SCENARIO = Scenario(S_PARAMETERS, S_OPTIONS)


# =====
# The following is one example of Engine instance.
# parameters

# This namedtuple describes neighbor-related parameters.
# Similar to creating a Scenario instance, please follow the format and do not change the key.
# Only value can be changed.

TOPOLOGY = Topology(max_neighbor_size=30, min_neighbor_size=20)

# This namedtuple describes the incentive score parameters.
# The physical meaning of parameters like reward_a, ... reward_e are in the definition of the data
# types in date_types.py.

INCENTIVE = Incentive(
    score_sheet_length=3,
    reward_a=0.0,
    reward_b=0.0,
    reward_c=0.0,
    reward_d=1.0,
    reward_e=0.0,
    penalty_a=0.0,
    penalty_b=-1.0,
)

# creating engine parameters, in type of a namedtuple.
E_PARAMETERS = EngineParameters(TOPOLOGY, INCENTIVE)

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
    method="Weighted", weights=[1.0, 1.0, 1.0]
)  # must be of the same length as incentive

# This TypedDict describes when to remove a neighbor
REFRESH = RemoveLazy(method="RemoveLazy", lazy_contribution=2, lazy_length=6)

# This TypedDict describes how to determine the neighbors that receive my orders.

BENEFICIARY = TitForTat(
    method="TitForTat", baby_ending_age=0, mutual_helpers=0, optimistic_choices=10
)

# how to recommendation neighbors when a peer asks for more.
# Right now, we only implemented a random recommendation.

REC = RecommendationOption(method="Random")

# How to decide the next loop starting time


LOOP = LoopOption(method="FollowPrevious")


# creating engine option, in type of a namedtuple

E_OPTIONS = EngineOptions(
    PREFERENCE,
    PRIORITY,
    EXTERNAL,
    INTERNAL,
    STORE,
    SHARE,
    SCORE,
    REFRESH,
    BENEFICIARY,
    REC,
    LOOP,
)

# creating MY_ENGINE, an instance of Engine, in type pf a namedtuple.
MY_ENGINE = Engine(E_PARAMETERS, E_OPTIONS)


# ======
# The following is an example of Performance instance.

# creating performance parameters, in type of a namedtuple.

PERFORMANCE_PARAMETERS = PerformanceParameters(
    max_age_to_track=80, adult_age=30, statistical_window=5
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

MEASURES_TO_EXECUTE = PerformanceExecutions(
    order_spreading=True,
    normal_peer_satisfaction=True,
    free_rider_satisfaction=True,
    system_fairness=False,
)

# create MY_PERFORMANCE instance, in type of a namedtuple.

MY_PERFORMANCE = Performance(
    PERFORMANCE_PARAMETERS, MEASURE_OPTIONS, MEASURES_TO_EXECUTE
)

# Putting the instances into lists

SCENARIOS: List[Scenario] = [MY_SCENARIO]
ENGINES: List[Engine] = [MY_ENGINE]
PERFORMANCES: List[Performance] = [MY_PERFORMANCE]
