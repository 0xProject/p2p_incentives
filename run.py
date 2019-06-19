"""
This is the single main file that runs the simulator.
"""

import example
import execution

if __name__ == '__main__':
    for my_scenario in example.SCENARIOS:
        for my_engine in example.ENGINES:
            for my_performance in example.PERFORMANCES:
                execution.Execution(my_scenario, my_engine, my_performance, 20).run()
