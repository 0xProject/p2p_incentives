"""
This module defines code specific data types for Scenario, Engine, and Performance.
It also contains the definitions of self-defined data types.
"""

from typing import NamedTuple, List, Optional, Union, Dict
from mypy_extensions import TypedDict
from typing_extensions import Literal


# There are a number of TypedDict and NamedTuple data types defined in this module. They usually
# represent a data structure containing a finite and fixed set of keys, of type string (they are
# considered as attribute names if it is a NamedTuple), each associated with a value of a fixed
# date type. The advantages of using TypedDict or NamedTuple are:
# 1) The set of keys (or attribute names) is fixed, so later, if we miss the assignment to some
# of them, or we assign a value to a non-existing one, mypy will report an error; and
# 2) The data type of each value is also fixed, so there will be an error report if assigning a
# value of a different data type.
#
# The principle of choosing TypedDict and NamedTuple is as follows:
# 1) If it is possible to use NamedTuple, use it. It is a tuple so it is more efficient than a
# dictionary.
# 2) If we need (a) that the data type be mutable, or (b) to iterate over the keys, or (c) to
# inherit sub-types from a base type, then we can only use TypedDict.
# In what follows, we will explain the reason where we use a TypedDict, and will not provide
# extra explanation when using NamedTuple.


# ==================
# data types for Scenario
# ==================

# parameters, for Scenario. Parameters are values to represent the basic settings/assumptions of
# the systems.


class Distribution(NamedTuple):
    """
    Distribution is a tuple of floats, mean and variance. They can be used to generate a
    random variable following Gaussian distribution G(mean, var).
    """

    # note: this is a normal namedtuple. Written in this format in order to add type hints.

    mean: float
    var: float


class SettleProperty(TypedDict):
    """
    This data type is a part of an order type's property. It captures how this type of orders can
    be settled. Such data type contains "method" attribute that captures the way of implementing a
    settlement function (for example, "ConcaveSettle" represents that the settlement probability is
    a concavely increasing function with respect to the number of replicas of this order in Mesh.
    In respect to each method, there might be an inherited data type that contains additional
    attributes. For example, if the method is "ConcaveSettle", there are additional attributes
    "sensitivity" and "max_prob" that decide the settlement probability.
    """

    method: Literal["ConcaveProperty"]


class ConcaveProperty(SettleProperty):
    """
    Please refer to the above data type Docstring for explanation. However, please be noted that
    this data type is to capture an order type, not an order instance, so all parameters are in
    type of Dictionary so as to capture the heterogeneity of different orders of this type.
    """

    sensitivity: Distribution
    max_prob: Distribution


class SettleParameters(TypedDict):
    """
    This is similar to SettleProperty but is for a particular order instance.
    """

    method: Literal["ConcaveParameters"]


class ConcaveParameters(SettleParameters):
    """
    This is similar to ConcaveProperty but is for a particular order instance, so parameters are
    values not distributions.
    Given the values of sensitivity and max_prob, the probability of settling an order is
    prob = max_prob * (1 - math.exp(- sensitivity * len(order.holders))).
    """

    sensitivity: float
    max_prob: float


class CancelProperty(TypedDict):
    """
    This data type is a part of an order type's property. It is very similar to SettleProperty
    defined above. Now there are two sub-types: random-based cancellation and age-based cancellation
    """

    method: Literal["RandomProperty", "AgeBasedProperty"]


class RandomProperty(CancelProperty):
    """
    This is similar to ConcaveProperty.
    prob is the distribution of probability for an order to be canceled during any particular time
    slot.
    """

    prob: Distribution


class AgeBasedProperty(CancelProperty):
    """
    This is aga-based cancellation. It is very similar to ConcaveProperty.
    """

    sensitivity: Distribution
    max_prob: Distribution


class CancelParameters(TypedDict):
    """
    This is similar to SettleParameters. Now there are two sub-types: random-based cancellation
    and age-based cancellation.
    """

    method: Literal["RandomParameter", "AgeBasedParameters"]


class RandomParameter(CancelParameters):
    """
    This is similar to ConcaveParameters. prob is the probability for an order to be canceled
    during any particular time slot.
    """

    prob: float


class AgeBasedParameters(CancelParameters):
    """
    This is aga-based cancellation. It is very similar to ConcaveProperty.
    """

    sensitivity: float
    max_prob: float


class OrderProperty(NamedTuple):
    """
    This data type specifies the property of a particular order type.
    expiration is the distribution of expiration (mean and variance) of this type.
    """

    expiration: Distribution
    settlement: "SettleProperty"
    cancellation: "CancelProperty"


class PeerProperty(NamedTuple):
    """
    This data type specifies the property of a particular peer type.
    ratio is the portion of peers of this type in the Mesh.
    Note: Summing up the ratios of all peer types doesn't have to be 1; but their relative weights
    matter.
    initial_orderbook_size_dict: A dictionary. Keys can only be taken over OrderTypeName; values
    are of type Distribution. Each value is the distribution number of initial orders (mean and
    variance) of this type.
    Note: The relative weights of the initial orderbook sizes of different types of orders,
    represent the relative weights of order numbers in this type of peer as well. Later when new
    orders arrive, the relative weights of order numbers will still remain the same as the
    weights as the initial orderbook sizes.
    """

    ratio: float
    initial_orderbook_size_dict: Dict["OrderTypeName", Distribution]


# The following two data types are created to specify order/peer type names, and their
# characteristics.
# We use a TypedDict, not a NamedTuple. This is because we will need to iterate over them to get
# all keys. We can also do it by using a NamedTuple but have to access namedtuple_instance._fields.
# It doesn't seem good so we opt to use a TypedDict.


class OrderTypePropertyDict(TypedDict):
    """
    This data type is to specify all order type names and their properties.
    """

    default: OrderProperty
    nft: OrderProperty


class PeerTypePropertyDict(TypedDict):
    """
    This data type is to specify all peer type names and their properties.
    """

    normal: PeerProperty
    free_rider: PeerProperty


# The following are two Literal data types. If an instance belongs to this data type, then it can
# only take values specified in the data type.

# We manually make sure that OrderTypeName contains all keys in OrderRatio and OrderParameter,
# and similarly for PeerTypeName.

# pylint thinks they are constants but in fact they are types.
# We temporarily disable invalid-names

OrderTypeName = Literal["default", "nft"]  # pylint: disable=invalid-name
PeerTypeName = Literal["normal", "free_rider"]  # pylint: disable=invalid-name


# The following two data types are both NamedTuples, containing parameters to specify the system
# status in different stages.


class SystemInitialState(NamedTuple):
    """
    To specify initial system status: number of initial peers, and the span of their birth time.
    If the span is X, then the birth time of the initial peers are normally distributed over [0, X).
    """

    num_peers: int
    birth_time_span: int


class SystemEvolution(NamedTuple):
    """
    To specify system evolution parameters, including the total number of rounds, and rate of
    peers arrival, departure, orders arrival and cancellation in each of these rounds.
    Note that the last four attributes are not exact number of event happenings, but the rate to
    generate them (according to some random process). Depending on the manner we generate them,
    such data might be in different types (e.g., float for Poisson, or Tuple of floats for Hawkes).
    """

    rounds: int
    peer_arrival: "EventArrivalRate"
    peer_dept: "EventArrivalRate"
    order_arrival: "EventArrivalRate"


class ScenarioParameters(NamedTuple):
    """
    Putting all value parameters together and use a NamedTuple to represent all values for Scenario.
    """

    order_type_property: OrderTypePropertyDict
    peer_type_property: PeerTypePropertyDict
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
# Though we have only one entry "method" for EventOption and two entries for SettleOption right
# now, there is a chance we need to use inheritance in the future. Please refer to the Options in
# Engine to see how complicated it can be.


class EventOption(TypedDict):
    """
    Option for how to generate events. Now we have two implementations: according to a Poisson
    random process, or a Hawkes random process.
    """

    method: Literal["Poisson", "Hawkes"]


class ScenarioOptions(NamedTuple):
    """
    Putting all options together and use a NamedTuple to represent all options for Scenario.
    """

    event: EventOption


# ==================
# data types for Engine
# ==================

# parameters, for Engine. They are values we can set in the design space.


class Topology(NamedTuple):
    """
    Topology represents the max and min number of neighbors that a peer would like to maintain.
    """

    max_neighbor_size: int
    min_neighbor_size: int


class Incentive(NamedTuple):
    """
    Incentive represents the length of history record taken into consideration, rewards and
    penalties that a neighbor receives for corresponding activities observed.
    """

    score_sheet_length: int  # length of the score sheet
    reward_a: float  # sharing an order already in my local storage, shared by the same peer
    reward_b: float  # sharing an order already in my local storage, shared by a different peer
    reward_c: float  # sharing an order that I accepted to pending table, but I don't store finally
    reward_d: float  # sharing an order I decide to store
    reward_e: float  # sharing an order I have multiple copies in the pending table and decided
    # to store a copy from someone else
    penalty_a: float  # sharing an order that I have no interest to accept to the pending table
    penalty_b: float  # sharing an identical and duplicate order within the same batch period


class EngineParameters(NamedTuple):
    """
    Putting all values together and use a NamedTuple to represent all value parameters for Engine.
    """

    batch_length: int
    topology: Topology
    incentive: Incentive


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
    """
    Option for a peer to set a preference for a neighbor.
    """

    method: Literal["Passive"]


class PriorityOption(TypedDict):
    """
    Option for a peer to set a priority for an OrderInfo instance.
    """

    method: Literal["Passive"]


class ExternalOption(TypedDict):
    """
    Option for a peer to decide whether to accept an external order (an order not shared by some
    other node in the mesh)
    """

    method: Literal["Always"]


class InternalOption(TypedDict):
    """
    Option for a peer to decide whether to accept an internal order shared by some other node in
    the mesh.
    """

    method: Literal["Always"]


class StoreOption(TypedDict):
    """
    Option for a peer to decide whether to store an accepted order.
    """

    method: Literal["First"]


class ShareOption(TypedDict):
    """
    Option for a peer to decide which orders to share with other nodes
    """

    method: Literal["AllNewSelectedOld"]
    max_to_share: int


class AllNewSelectedOld(ShareOption):
    """
    Sub-type of ShareOption where the strategy is share all new orders (those put into the local
    storage during the most recent batch) but selected old ones (the rest ones in local storage).
    The parameter old_share_prob is the probability of sharing any old order.
    """

    old_share_prob: float


class ScoreOption(TypedDict):
    """
    Option for calculating the score of a neighbor.
    """

    method: Literal["Weighted"]


class Weighted(ScoreOption):
    """
    Sub-type of ScoreOption where the strategy is to take a weighted average of all scores in the
    score sheet.
    """

    weights: List[float]  # the list of weights for summing up the scores in the sheet.


class RefreshOption(TypedDict):
    """
    Option for refreshing neighbors.
    """

    method: Literal["Never", "RemoveLazy"]


class RemoveLazy(RefreshOption):
    """
    Sub-type of RefreshOption where the strategy is to remove the lazy neighbors.
    """

    # if the contribution in this round is below this value, the neighbor is considered as lazy
    # in this round.
    lazy_contribution: float

    # if the contribution is below lazy_threshold for a continuum of lazy_length rounds,
    # it is considered as permanently lazy.
    lazy_length: int


class BeneficiaryOption(TypedDict):
    """
    Option for a peer to select the beneficiary nodes from neighbors to share orders.
    """

    method: Literal["TitForTat"]


class TitForTat(BeneficiaryOption):
    """
    Sub-type of BeneficiaryOption where the strategy is tit-for-tat.
    """

    # the following one is the threshold of age below which the peer is considered as a baby. For a
    # baby, random selection is adopted since there is no history for neighbors.
    baby_ending_age: int

    # Followings are number of highly-ranked and randomly-selected peers.
    mutual_helpers: int
    optimistic_choices: int


class RecommendationOption(TypedDict):
    """
    Option for the tracker to recommend new neighbors to a peer upon request.
    """

    method: Literal["Random"]


class EngineOptions(NamedTuple):
    """
    Putting all options together and use a NamedTuple to represent all options for Engine.
    """

    preference: PreferenceOption
    priority: PriorityOption
    external: ExternalOption
    internal: InternalOption
    store: StoreOption
    share: ShareOption
    score: ScoreOption
    refresh: RefreshOption
    beneficiary: BeneficiaryOption
    rec: RecommendationOption


# ==================
# data types for Performance
# ==================


class PerformanceParameters(NamedTuple):
    """
    parameters, for Performance. They are the value parameters to be passed to performance
    evaluation functions so that they know who/how/how long to track the performance.
    """

    max_age_to_track: int
    adult_age: int
    statistical_window: int


# options, for Performance. They specify the ways that performance evaluation functions are
# implemented. Reason of using TypedDict is similar to above.


class SpreadingOption(TypedDict):
    """
    Option to evaluate order spreading performance over the Mesh.
    """

    method: Literal["Ratio"]


class SatisfactionOption(TypedDict):
    """
    Option to evaluate user satisfactory performance over the Mesh.
    Neutral means a user treats every order received as equal (neutral to freshness of orders).
    This is obviously impractical but serve as a simplest one.
    """

    method: Literal["Neutral"]


class FairnessOption(TypedDict):
    """
    Option to evaluate the system level fairness.
    """

    method: Literal["Dummy"]


class PerformanceOptions(NamedTuple):
    """
    Putting options together for performance option.
    """

    spreading_option: SpreadingOption
    satisfaction_option: SatisfactionOption
    fairness_option: FairnessOption


class PerformanceExecutions(NamedTuple):
    """
    This is new: It is a namedtuple with all values being a boolean variable, indicating whether
    a performance evaluation execution is to perform or not.
    A performance evaluation execution is different from a performance option. For each base
    option we are dealing with one kind of performance metric. For example, SatisfactionOption
    refers to how to evaluate satisfaction of a group of peers. However, in PerformanceExecution,
    we do have choices on whether to perform a satisfaction evaluation on normal peers,
    and another satisfaction evaluation on free riders.
    Later if new executions come into our mind, we should add them into this tuple, even if we
    don't want to run them immediately. In such a case we can set its value to be False.
    """

    order_spreading: bool
    normal_peer_satisfaction: bool
    free_rider_satisfaction: bool
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


# Result, for Performance. They are data types to record performance evaluation result in single
# and multiple runs of the simulator. Used by execution module to receive and process data,
# and plot figures based on such data.


class SingleRunPerformanceResult(NamedTuple):
    """
    This is a NamedTuple to record performance evaluation record when the simulator runs once.
    Its keys are exactly the same as in PerformanceExecutions. For each key, if the evaluation is
    executed, record the result in its corresponding data type; otherwise, a None is put in that
    position.
    """

    order_spreading: Optional[OrderSpreading]
    normal_peer_satisfaction: Optional[UserSatisfaction]
    free_rider_satisfaction: Optional[UserSatisfaction]
    fairness: Optional[Fairness]


class MultiRunPerformanceResult(TypedDict):
    """
    This is a TypedDict to record performance evaluation record after the simulator run multiple.
    Its keys are exactly the same as in PerformanceExecutions. For each key, if the evaluation is
    executed, record the result in a list of its corresponding data type; otherwise, an empty
    list is in that position.
    """

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
    """
    This data type is to pass parameters to function scenario_candidates.hawkes()
    Variable names are set the same as in the paper that invented the method.
    """

    # Fine to violate naming regulations temporarily in "a".
    a: float  # pylint: disable=invalid-name
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


class BestAndWorstLists(NamedTuple):
    """
    # A NamedTuple for best and worst lists, serve for the data type of the return value of
    find_best_worst_lists() in data_processing module.
    """

    best: SpreadingRatio
    worst: SpreadingRatio


class InvalidInputError(ValueError):
    """
    Self defined error class in use of performance evaluation functions and data processing
    functions. Raise such an error when the input set of orders/peers are empty such that the
    evaluation cannot be done, or the number of lists is 0 so data processing cannot be done.
    Don't need anything in the class.
    """


class InvalidOrdersStat(TypedDict):
    """
    This is a data type to record the counts of various types of invalid orders in history. This
    will gives the information on how they became invalid (expired, settled, canceled, or missing).
    """

    expired_count: int
    settled_count: int
    canceled_count: int
    missing_count: int
