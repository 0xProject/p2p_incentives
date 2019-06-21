"""
This module defines Order and OrderInfo classes
"""


class Order:
    """
    Order class, each instance being an order in the mesh system.
    """
    # pylint: disable=too-few-public-methods
    # Though order class has only one public method, it is still fine to use a class instead of
    # namedtuple, otherwise we won't be able to change the value of the parameters.

    # pylint: disable=too-many-instance-attributes
    # Fine to have many attributes.

    def __init__(self, scenario, seq, birth_time, creator, expiration=float('inf'), category=None):
        # pylint: disable=too-many-arguments
        # fine to have many arguments

        self.scenario = scenario  # assumption. needed for function update_settled_status().
        self.seq = seq  # sequence number. Not in use now, reserved for possible future use
        self.birth_time = birth_time  # will be decided by system clock
        self.creator = creator  # the peer who creates this order
        self.expiration = expiration  # maximum time for a peer to be valid
        self.category = category  # may refer to a trading pair label or something else

        # set of peers who put this order into their local storage.
        self.holders = set()

        # set of peers who put this order into their pending table but not local storage.
        # in order words, these peers are hesitating whether to store the orders.
        self.hesitators = set()

        self.is_settled = False  # this order instance has not been taken and settled
        self.is_canceled = False  # will change to True when the order departs proactively.

    def update_settled_status(self):
        """
        This method updates the settled status of this order.
        :return: None
        """
        self.scenario.update_orders_settled_status(self)


class OrderInfo:
    """
    Orderinfo class. An instance of OrderInfo is an order instance from a peer's viewpoint.
    However, it contains extra information to an Order instance.
    Note, an Order instance can have multiple OrderInfo instances stored by different peers.
    It contains specific information about the novelty and property of the order.
    Such information is not included in Order.
    """

    # pylint: disable=too-few-public-methods
    # Though orderinfo class does not have any public method, it is still fine to use a class
    # instead of namedtuple, otherwise we won't be able to change the value of the parameters.

    def __init__(self, engine, order, master, arrival_time, priority=None, prev_owner=None,
                 novelty=0):
        # pylint: disable=too-many-arguments
        # fine to have many arguments

        self.engine = engine  # design choice. Needed for function orderinfo_set_priority()
        self.arrival_time = arrival_time  # arrival time of this orderinfo to my pending table
        self.prev_owner = prev_owner  # previous owner, default is None (a new order)
        self.novelty = novelty  # How many hops it has travelled. Default is 0.
        self.engine.set_priority_for_orderinfo(master, order, priority)  # set up priority

        # storage_decision is to record whether this peer decides to put this order into storage.
        # It seems redundant, but it will be useful in store_orders function.
        self.storage_decision = False
