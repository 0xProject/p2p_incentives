"""
This module defines code specific data types for Scenario, Engine, and Performance.
It also contains the definitions of self-defined data types.
"""

# pylint: disable=missing-docstring
# Classes in this module are to define data types. Fine to omit docstring.

from typing import NamedTuple, List, Optional, Union
from mypy_extensions import TypedDict
from typing_extensions import Literal

# ==================
# data types for Scenario
# ==================

# parameters, for Scenario. Parameters are values to represent the basic settings/assumptions of
# the systems.

# Distribution is a tuple of floats, mean and variance. They can be used to generate a random
# variable following Gaussian distribution G(mean, var).


class Distribution(NamedTuple):
    # note: this is a normal namedtuple. Written in this format in order to
    # add type hints.
    mean: float
    var: float


# The following four data types are created to specify order/peer type names, ratios for each
# type in the whole set of orders/peers, and corresponding parameters.
# We use a TypedDict, not a NamedTuple. This is because we will need to iterate over them to get
# all keys. We can also do it by using a NamedTuple but have to access namedtuple_instance._fields.
# It doesn't seem good so we opt to use a TypedDict.

# Note: OrderRatio and OrderParameter can be definitely merged into one data type, and so for
# PeerRatio and PeerParameter. This will change a number of logic in the code anyway, so I leave
# it to be done in the next PR.
# This comment should be deleted in the next PR.


class OrderRatio(TypedDict):
    default: float


class PeerRatio(TypedDict):
    normal: float
    free_rider: float


class OrderParameter(TypedDict):
    default: Distribution


class PeerParameter(TypedDict):
    normal: Distribution
    free_rider: Distribution


# The following are two Literal data types. If an instance belongs to this data type, then it can
# only take values specified in the data type.

# We manually make sure that OrderTypeName contains all keys in OrderRatio and OrderParameter,
# and similarly for PeerTypeName.

# pylint thinks they are constants but in fact they are types.
# We temporarily disable invalid-names

OrderTypeName = Literal["default"]  # pylint: disable=invalid-name
PeerTypeName = Literal["normal", "free_rider"]  # pylint: disable=invalid-name


# The following two data types are both NamedTuples, containing parameters to specify the system
# status in different stages.


class SystemInitialState(NamedTuple):
    num_peers: int
    birth_time_span: int


class SystemEvolution(NamedTuple):
    rounds: int
    peer_arrival: float
    peer_dept: float
    order_arrival: float
    order_cancel: float


# Putting all value parameters together and use a NamedTuple to represent all values for Scenario.


class ScenarioParameters(NamedTuple):
    order_ratios: OrderRatio
    peer_ratios: PeerRatio
    order_parameters: OrderParameter
    peer_parameters: PeerParameter
    init_state: SystemInitialState
    growth_period: SystemEvolution
    stable_period: SystemEvolution


# options, for Scenario. Options are to specify ways of implementing functions that specify the
# feature of the system, for example, to specify a function implementation method that describes
# event happening pattern (e.g., peer arrival & departure), we have Poisson and Hawkes which are
# two different random processes.
#
# In general, such Option data type can contain a method name, and associated parameters. Here is
# a little bit special:
# - For EventOption, it only specifies the kind of random process but not the
# happening rate. The reason is there are many random processes and the rate parameters are
# specified in scenario.parameters but not here.
# - For SettleOption, we only have one implementation which is "Never", and it does not need
# additional parameters. For future implementations, additional parameters may be needed (e.g.,
# probability of an order being settled).
#
# Given the possibility of need to generalization, we use a TypedDict to represent an Option.
# Though we have only one entry "method" for each of them right now, we do have a chance of need
# of using inheritance in future. Please refer to the Options in Engine to see how complicated it
# can be.


class EventOption(TypedDict):
    method: Literal["Poisson", "Hawkes"]


class SettleOption(TypedDict):
    method: Literal["Never"]


# Putting all options together and use a NamedTuple to represent all options for Scenario.


class ScenarioOptions(NamedTuple):
    event: EventOption
    settle: SettleOption


# ==================
# data types for Engine
# ==================

# parameters, for Engine. They are values we can set in the design space.


# Topology represents the max and min # of neighbors that a peer would like to maintain.


class Topology(NamedTuple):
    max_neighbor_size: int
    min_neighbor_size: int


# Incentive represents the length of history record taken into consideration, rewards and
# penalties that a neighbor receives for corresponding activities observed. Please refer to
# module engine for their specific meanings.


class Incentive(NamedTuple):
    length: int
    reward_a: float
    reward_b: float
    reward_c: float
    reward_d: float
    reward_e: float
    penalty_a: float
    penalty_b: float


# Putting all values together and use a NamedTuple to represent all value parameters for Engine.


class EngineParameters(NamedTuple):
    batch_parameter: int
    topology_parameters: Topology
    incentive_parameters: Incentive


# options, for Engine. They are TypedDict data types representing possible ways to implement
# functions in the design space. They are similar to options in Scenario but more complicated.

# We use TypedDict, not NamedTuple, to allow inheritance.
# For each function, there is a base class where there must be only one key "method". This
# element refers to the manner that a related function is implemented. For example,
# if "method" of an instance of PreferenceOption is "Passive", It means a peer implements the
# set_preference in a passive manner (in here, it means the peer does not set a preference to a
# neighbor unless the preference has been specified in the function argument.
# The data type for the value of "method" is a Literal containing all possible names of the methods.
#
# There are two possibilities to represent a real choice of function implementation:
# (1) If the implementation only needs to know "method" and does not need any other parameter,
# then create an instance of this TypedDict by giving a value to "method", then use this instance
# to represent the option of implementation. For example, to represent the option of implementing
# set_preference function passively, one needs to create an instance of PreferenceOption by
# giving method the value "Passive." So One example would be:
# preference_option: PreferenceOption = PreferenceOption(method="Passive").
#
# (2) If the implementation needs to know the method and other parameters, first create
# another data type, which is also a TypedDict, inheriting from the base type and adding
# additional key-value pairs. Then create an instance of this inherited type, by giving the value
# for key "method" exactly the same characters as the data type name, and giving extra proper
# values in the additional key-value pairs. For example, to represent the option of implementation
# "tit-for-tat" mechanisms for selecting beneficiaries, one needs to create a new TypedDict,
# named TitForTat, inherited from BeneficiaryOption type. The new type also contains other
# attributes (e.g., baby_ending_time, mutual_helpers, and optimistic_choice). Then create an
# instance of this new type, by giving the value for "method" exactly the word "TitForTat",
# the same as the name of the new type itself, and giving proper values to additional attributes.
# One example would be:
# BENEFICIARY: TitForTat = TitForTat(
#     method="TitForTat", baby_ending_age=0, mutual_helpers=3, optimistic_choices=1
# )
#
# The reason of having the duplicated information in the sub-type name and the "method" attribute
# is tricky. When the option for choosing beneficiaries is passed to the corresponding
# function, there is no way for the function to know the option parameter is of any
# sub-type. It can only judge if it is of type BeneficiaryOption. If yes, then it need to
# further judge which sub-type it is. There is no implementation of isinstance() function
# for TypedDict, so there is no way but check the "method" attribute of the instance. Once we
# know it is TItForTat, the code will need to cast the type of this instance from
# BeneficiaryOption to the sub-type TitForTat and further pass it to a detailed implementation.
# Having to use cast is not perfect but this is the best way in our mind now.


class PreferenceOption(TypedDict):
    method: Literal["Passive"]


class PriorityOption(TypedDict):
    method: Literal["Passive"]


class ExternalOption(TypedDict):
    method: Literal["Always"]


class InternalOption(TypedDict):
    method: Literal["Always"]


class StoreOption(TypedDict):
    method: Literal["First"]


class ShareOption(TypedDict):
    method: Literal["AllNewSelectedOld"]
    max_to_share: int


class AllNewSelectedOld(ShareOption):
    old_share_prob: float


class ScoreOption(TypedDict):
    method: Literal["Weighted"]


class Weighted(ScoreOption):
    lazy_contribution_threshold: int
    lazy_length_threshold: int
    weights: List[float]


class BeneficiaryOption(TypedDict):
    method: Literal["TitForTat"]


class TitForTat(BeneficiaryOption):
    baby_ending_age: int
    mutual_helpers: int
    optimistic_choices: int


class RecommendationOption(TypedDict):
    method: Literal["Random"]


# Putting all options together and use a NamedTuple to represent all options for Engine.


class EngineOptions(NamedTuple):
    preference_option: PreferenceOption
    priority_option: PriorityOption
    external_option: ExternalOption
    internal_option: InternalOption
    store_option: StoreOption
    share_option: ShareOption
    score_option: ScoreOption
    beneficiary_option: BeneficiaryOption
    rec_option: RecommendationOption


# ==================
# data types for Performance
# ==================

# parameters, for Performance. They are the value parameters to be passed to performance
# evaluation functions so that they know who/how/how long to track the performance.


class PerformanceParameters(NamedTuple):
    max_age_to_track: int
    adult_age: int
    statistical_window: int


# options, for Performance. They specify the ways that performance evaluation functions are
# implemented. Reason of using TypedDict is similar to above.


class SpreadingOption(TypedDict):
    method: Literal["Ratio"]


class SatisfactionOption(TypedDict):
    method: Literal["Neutral"]


class FairnessOption(TypedDict):
    method: Literal["Dummy"]


class PerformanceOptions(NamedTuple):
    spreading_option: SpreadingOption
    satisfaction_option: SatisfactionOption
    fairness_option: FairnessOption


# executions, for Performance.
# This is new: It is a namedtuple with all values being a boolean variable, indicating whether a
# performance evaluation execution is to perform or not.
# A performance evaluation execution is different from a performance option. For each base option
# we are dealing with one kind of performance metric. For example, SatisfactionOption refers to
# how to evaluate satisfaction of a group of peers. However, in PerformanceExecution, we do have
# choices on whether to perform a satisfaction evaluation on normal peers, and another
# satisfaction evaluation on free riders.
# Later if new executions come into our mind, we should add them into this tuple, even if we
# don't want to run them immediately. In such a case we can set its value to be False.


class PerformanceExecutions(NamedTuple):
    order_spreading_measure: bool
    normal_peer_satisfaction_measure: bool
    free_rider_satisfaction_measure: bool
    system_fairness: bool


# Aliases for performance metrics

# Spreading ratio. Its explanation can be found in the string doc of
# data_processing.find_best_worst_lists().

SpreadingRatio = List[Optional[float]]

# The following data types capture types of OrderSpreading, Fairness and UserSatisfaction results.
# We use a Union here and now only put in current possibilities, but in future, if there is a new
# metric for such performance measures and it is of a different type (for example, we use some
# kind of quickness rather than spreading ratio to evaluate order spreading), simply put it
# into Union (e.g., OrderSpreading = Union[SpreadingRatio, SpreadingQuickness].
#
# However, note that in execution module, such results are passed to data processing. In case new
# types are added, make sure there is a function to deal with it.

# can include more types for new metrics for order spreading
OrderSpreading = Union[SpreadingRatio]

# can include more types if new metrics for fairness is added
Fairness = Union[float]

# can include more types if new metrics for satisfaction is added
UserSatisfaction = List[float]


# result, for Performance. They are data types to record performance evaluation result in single
# and multiple runs of the simulator. Used by execution module to receive and process data,
# and plot figures based on such data.


# This is a NamedTuple to record performance evaluation record when the simulator runs once. Its
# keys are exactly the same as in PerformanceExecutions. For each key, if the evaluation is
# executed, record the result in its corresponding data type; otherwise, a None is put in that
# position.


class SingleRunPerformanceResult(NamedTuple):
    order_spreading: Optional[OrderSpreading]
    normal_peer_satisfaction: Optional[UserSatisfaction]
    free_rider_satisfaction: Optional[UserSatisfaction]
    fairness: Optional[Fairness]


# This is a TypedDict to record performance evaluation record after the simulator run multiple. Its
# keys are exactly the same as in PerformanceExecutions. For each key, if the evaluation is
# executed, record the result in a list of its corresponding data type; otherwise, an empty list
# is in that position.


class MultiRunPerformanceResult(TypedDict):
    order_spreading: List[OrderSpreading]
    normal_peer_satisfaction: List[UserSatisfaction]
    free_rider_satisfaction: List[UserSatisfaction]
    fairness: List[Fairness]


# ===================
# Others
# ===================

# Event happening rate types. There are currently two types of event happening: Poisson and
# Hawkes. For Poisson, the rate is a float. For Hawkes, the rate is a namedtuple of four floats,
# specifying how the current rate is related to past events. Please refer to the docstring inside
# scenario_candidates.hawkes() for details.

PoissonArrivalRate = float


class HawkesArrivalRate(NamedTuple):
    # pylint: disable=invalid-name
    # This data type is to pass parameters to function scenario_candidates.hawkes()
    # Variable names are set the same as in the paper that invented the method.
    # Fine to violate naming regulations temporarily in this data type.
    a: float
    lambda_0: float
    delta: float
    gamma: float


# A union of all possible event happening rate data types. To judge if a parameter passing to
# scenario.generate_event_counts_over_time() function is correct.

EventArrivalRate = Union[PoissonArrivalRate, HawkesArrivalRate]

# We haven't implemented namespacing, preference, priority, and category attributes in
# Neighbor/Peer and Order/OrderInfo.
# We now specify their types to be int, but they are subject to change when implemented in future.

NameSpacing = Optional[int]
Preference = Optional[int]
Priority = Optional[int]
Category = Optional[int]

# A NamedTuple for best and worst lists, serve for the data type of the return value of
# find_best_worst_lists() in data_processing module.


class BestAndWorstLists(NamedTuple):
    best: SpreadingRatio
    worst: SpreadingRatio
