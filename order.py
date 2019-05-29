'''
=======================================
Order, OrderInfo classes
=======================================
'''
# Order class, each instance being an order in the P2P system.

class Order:
    
    def __init__(self, scenario, seq, birthtime, creator, expiration = float('inf'), category = None):
        
        self.scenario = scenario # assumption. needed for updateSettledStatus().
        self.seq = seq # sequence number. Not in use now, reserved for possible future use
        self.birthtime = birthtime # will be decided by system clock
        self.creator = creator # the peer who creates this order
        self.expiration = expiration # maximum time for a peer to be valid, and will expire thereafter
        self.category = category # may refer to a trading pair label or something else
        
        # set of peers who put this order into their local storage.
        self.holders = set()
        
        # set of peers who put this order into their pending table but not local storage.
        # in order words, these peers are hesitating whether to store the orders.
        self.hesitators = set()
        
        self.is_settled = False # this order instance has not been taken and settled
        self.is_canceled = False # will change to True when the order departs proactively.
        
    # This function updates the settled status for this order
    def updateSettledStatus(self): 
        self.scenario.orderUpdateSettleStatus(self)
        
        
# An instance of an orderinfo is an order from a peer's viewpoint. It contains extra information to an Order instance.
# Note, an Order instance can have multiple OrderInfo instances stored by different peers.
# It contains specific information about the novelty and property of the order, not included in Order.

class OrderInfo:
    
    def __init__(self, engine, order, master, arrival_time, priority = None, prev_owner = None, novelty = 0):
    
        self.engine = engine # design choice. Needed for orderinfoSetPriority()
        self.arrival_time = arrival_time # arrival time of this orderinfo to my pending table
        self.prev_owner = prev_owner # previous owner, default is None (a new order)
        self.novelty = novelty # How many hops it has travalled. Default is 0. Leave design space for possible extensions in future.
        self.engine.orderinfoSetPriority(master, order, priority) # set up priority
        
        # storage_decision is to record whether this peer decides to put this order into the storage.
        # It seems redundant, but it will be useful in storeOrders function.
        self.storage_decision = False
        