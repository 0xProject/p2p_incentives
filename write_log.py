"""
This module contains functions that write logs.
"""
import csv

def store_log(from_node, to_node, order, timestamp):
    with open('store_order_logs.csv', 'a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([from_node, to_node, order, timestamp])


def receive_log(from_node, to_node, order, timestamp):
    with open('receive_order_logs.csv', 'a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([from_node, to_node, order, timestamp])