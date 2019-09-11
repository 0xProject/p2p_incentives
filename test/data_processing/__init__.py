"""
tests for data_processing.py
This init file contains input data for the unit tests.
"""

from typing import List
from data_types import SpreadingRatio

#  constructing input data

RATIO_LIST: List[SpreadingRatio] = [[] for _ in range(15)]

RATIO_LIST[0] = [0.1, 0.2, 0.3, 0.4]
RATIO_LIST[1] = [0.1, 0.2, 0.3, 0.5]
RATIO_LIST[2] = [0.3, 0.5, 0.8, 0.9]
RATIO_LIST[3] = [None, None, None, None]
RATIO_LIST[4] = [0.1, 0.2, None, 0.6]
RATIO_LIST[5] = [0.1, 0.1, 1.0, None]
RATIO_LIST[6] = [None, 0.3, 0.5, 1.0]
RATIO_LIST[7] = [0.3, 0.5, 0.8, None]
RATIO_LIST[8] = [0.3, 0.5, 0.7, None]
RATIO_LIST[9] = [0.3, 0.5, None, None]
RATIO_LIST[10] = [0.2, 0.6, None, None]
RATIO_LIST[11] = [1.0, 0.1, None, None]
RATIO_LIST[12] = [None, None, None, None]
RATIO_LIST[13] = [None, None, None, None]
RATIO_LIST[14] = [0.1, 0.4, 0.9]

SATISFACTORY_LIST: List[List[float]] = [[] for _ in range(5)]

SATISFACTORY_LIST[0] = [0.88, 0.25, 0.67, 0.83]
SATISFACTORY_LIST[1] = [0.99, 0.13, 0.22, 0.01, 1.00]
SATISFACTORY_LIST[2] = []
SATISFACTORY_LIST[3] = [0.45]
SATISFACTORY_LIST[4] = [2]
