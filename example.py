"""
This module contains one test case by generating a point in engine, scenario, and performance.
"""

from typing import List
from engine import Engine
from scenario import Scenario
from performance import Performance
from data_types import (
    OrderRatio,
    PeerRatio,
    Distribution,
    OrderParameter,
    PeerParameter,
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

# ratio of orders of each type.
# If an additional type is added, remember to modify OrderRatio and OrderParameter in data_types

ORDER_TYPE_RATIOS: OrderRatio = OrderRatio(default=1.0)

# ratio of peers of each type
# If an additional type is added, remember to modify PeerRatio and PeerParameter in data_types

PEER_TYPE_RATIOS: PeerRatio = PeerRatio(free_rider=0.1, normal=0.9)

# Order parameter distribution: a namedtuple consisting of the mean and variance of order
# expiration. An order's real expiration follows a Normal distribution given this mean and variance.

ORDER_DEFAULT: Distribution = Distribution(mean=500.0, var=0.0)

# Order parameter dictionary: the type OrderParameter a TypedDict, key is the name of order
# type (str), value is the order parameter distribution.

ORDER_PAR_DICT: OrderParameter = OrderParameter(default=ORDER_DEFAULT)


# Peer parameter distribution: a namedtuple consisting of the mean and variance of order
# expiration. A peer's initial orderbook size follows a Normal distribution given this mean and
# variance.

PEER_FREE_RIDER: Distribution = Distribution(mean=0.0, var=0.0)
PEER_NORMAL: Distribution = Distribution(mean=6.0, var=0.0)

# Peer parameter dictionary: similar as above. In this example we have two types of peers: free
# riders and normal peers.

PEER_PAR_DICT: PeerParameter = PeerParameter(
    free_rider=PEER_FREE_RIDER, normal=PEER_NORMAL
)

# The following namedtuple specifies the parameters for the system's initial status.

NUM_PEERS: int = 10
BIRTH_TIME_SPAN: int = 20
INIT_PAR: SystemInitialState = SystemInitialState(
    num_peers=NUM_PEERS, birth_time_span=BIRTH_TIME_SPAN
)

# The following namedtuple specifies the parameters for the system's growth period
# when the # of peers keeps increasing.

GROWTH_ROUND: int = 30
GROWTH_PEER_ARRIVAL: float = 3.0
GROWTH_PEER_DEPT: float = 0.0
GROWTH_ORDER_ARRIVAL: float = 15.0
GROWTH_ORDER_CANCEL: float = 15.0
GROWTH_PAR: SystemEvolution = SystemEvolution(
    rounds=GROWTH_ROUND,
    peer_arrival=GROWTH_PEER_ARRIVAL,
    peer_dept=GROWTH_PEER_DEPT,
    order_arrival=GROWTH_ORDER_ARRIVAL,
    order_cancel=GROWTH_ORDER_CANCEL,
)

# The following namedtuple specifies the parameters for the system's stable period
# when the # of peers keeps stable.

STABLE_ROUND: int = 50
STABLE_PEER_ARRIVAL: float = 2.0
STABLE_PEER_DEPT: float = 2.0
STABLE_ORDER_ARRIVAL: float = 15.0
STABLE_ORDER_CANCEL: float = 15.0
STABLE_PAR: SystemEvolution = SystemEvolution(
    rounds=STABLE_ROUND,
    peer_arrival=STABLE_PEER_ARRIVAL,
    peer_dept=STABLE_PEER_DEPT,
    order_arrival=STABLE_ORDER_ARRIVAL,
    order_cancel=STABLE_ORDER_CANCEL,
)

# Create scenario parameters, in type of a namedtuple.

S_PARAMETERS: ScenarioParameters = ScenarioParameters(
    order_ratios=ORDER_TYPE_RATIOS,
    peer_ratios=PEER_TYPE_RATIOS,
    order_parameters=ORDER_PAR_DICT,
    peer_parameters=PEER_PAR_DICT,
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
EVENT_ARRIVAL: EventOption = EventOption(method="Poisson")
# how an order's is_settled status is changed
CHANGE_SETTLE_STATUS: SettleOption = SettleOption(method="Never")

# creating scenario options, in type of a namedtuple.
S_OPTIONS: ScenarioOptions = ScenarioOptions(EVENT_ARRIVAL, CHANGE_SETTLE_STATUS)

# create MY_SCENARIO instance, in type of a namedtuple.
MY_SCENARIO: Scenario = Scenario(S_PARAMETERS, S_OPTIONS)


# =====
# The following is one example of Engine instance.
# parameters

BATCH: int = 10  # length of a batch period

# This namedtuple describes neighbor-related parameters.
# Similar to creating a Scenario instance, please follow the format and do not change the key.
# Only value can be changed.

MAX_NEIGHBOR_SIZE: int = 30
MIN_NEIGHBOR_SIZE: int = 20
TOPOLOGY: Topology = Topology(
    max_neighbor_size=MAX_NEIGHBOR_SIZE, min_neighbor_size=MIN_NEIGHBOR_SIZE
)

# This namedtuple describes the incentive score parameters.

LENGTH: int = 3
REWARD_A: float = 0.0
REWARD_B: float = 0.0
REWARD_C: float = 0.0
REWARD_D: float = 1.0
REWARD_E: float = 0.0
PENALTY_A: float = 0.0
PENALTY_B: float = -1.0

INCENTIVE: Incentive = Incentive(
    length=LENGTH,
    reward_a=REWARD_A,
    reward_b=REWARD_B,
    reward_c=REWARD_C,
    reward_d=REWARD_D,
    reward_e=REWARD_E,
    penalty_a=PENALTY_A,
    penalty_b=PENALTY_B,
)

# creating engine parameters, in type of a namedtuple.
E_PARAMETERS: EngineParameters = EngineParameters(BATCH, TOPOLOGY, INCENTIVE)

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
PREFERENCE: PreferenceOption = PreferenceOption(method="Passive")

# set priority for orders
PRIORITY: PriorityOption = PriorityOption(method="Passive")

# accepting an external order or not
EXTERNAL: ExternalOption = ExternalOption(method="Always")

# accepting an internal order or not
INTERNAL: InternalOption = InternalOption(method="Always")

# storing an order or not
STORE: StoreOption = StoreOption(method="First")

# This TypedDict describes how to determine the orders to share with neighbors.
# Now we only implemented 'all_new_selected_old'.

SHARE: AllNewSelectedOld = AllNewSelectedOld(
    method="AllNewSelectedOld", max_to_share=5000, old_share_prob=0.5
)

# This TypedDict describes how to determine neighbor scoring system.

SCORE: Weighted = Weighted(
    method="Weighted",
    lazy_contribution_threshold=2,
    lazy_length_threshold=6,
    weights=[1.0, 1.0, 1.0],
)  # must be of the same length as incentive


# This TypedDict describes how to determine the neighbors that receive my orders.

BENEFICIARY: TitForTat = TitForTat(
    method="TitForTat", baby_ending_age=0, mutual_helpers=3, optimistic_choices=1
)

# how to recommendation neighbors when a peer asks for more.
# Right now, we only implemented a random recommendation.

REC: RecommendationOption = RecommendationOption(method="Random")

# creating engine option, in type of a namedtuple

E_OPTIONS: EngineOptions = EngineOptions(
    PREFERENCE, PRIORITY, EXTERNAL, INTERNAL, STORE, SHARE, SCORE, BENEFICIARY, REC
)

# creating MY_ENGINE, an instance of Engine, in type pf a namedtuple.
MY_ENGINE: Engine = Engine(E_PARAMETERS, E_OPTIONS)


# ======
# The following is an example of Performance instance.
# parameters

MAX_AGE_TO_TRACK: int = 50
ADULT_AGE: int = 30
STATISTICAL_WINDOW: int = 5

# creating performance parameters, in type of a namedtuple.

PERFORMANCE_PARAMETERS: PerformanceParameters = PerformanceParameters(
    max_age_to_track=MAX_AGE_TO_TRACK,
    adult_age=ADULT_AGE,
    statistical_window=STATISTICAL_WINDOW,
)

# options

SPREADING_OPTION: SpreadingOption = SpreadingOption(method="Ratio")

SATISFACTION_OPTION: SatisfactionOption = SatisfactionOption(method="Neutral")

FAIRNESS_OPTION: FairnessOption = FairnessOption(method="Dummy")

# creating performance options, in type of a namedtuple.

MEASURE_OPTIONS: PerformanceOptions = PerformanceOptions(
    SPREADING_OPTION, SATISFACTION_OPTION, FAIRNESS_OPTION
)

# executions, in type of a namedtuple.
# If one wants to add more execution possibilities, modify the definition of
# PerformanceExecutions (in type of a namedtuple) first in data_types module.

ORDER_SPREADING: bool = True
NORMAL_PEER_SATISFACTION: bool = True
FREE_RIDER_SATISFACTION: bool = True
SYSTEM_FAIRNESS: bool = False


MEASURES_TO_EXECUTE: PerformanceExecutions = PerformanceExecutions(
    order_spreading_measure=ORDER_SPREADING,
    normal_peer_satisfaction_measure=NORMAL_PEER_SATISFACTION,
    free_rider_satisfaction_measure=FREE_RIDER_SATISFACTION,
    system_fairness=SYSTEM_FAIRNESS,
)

# create MY_PERFORMANCE instance, in type of a namedtuple.

MY_PERFORMANCE: Performance = Performance(
    PERFORMANCE_PARAMETERS, MEASURE_OPTIONS, MEASURES_TO_EXECUTE
)

# Putting the instances into lists

SCENARIOS: List[Scenario] = [MY_SCENARIO]
ENGINES: List[Engine] = [MY_ENGINE]
PERFORMANCES: List[Performance] = [MY_PERFORMANCE]
