"""
This is the single main file that runs the simulator.
"""

import example
import execution
import plot

if __name__ == "__main__":
    for my_scenario in example.SCENARIOS:
        for my_engine in example.ENGINES:
            for my_performance in example.PERFORMANCES:
                multi_run_result = execution.MultiRunInParallel(
                    scenario=my_scenario,
                    engine=my_engine,
                    performance=my_performance,
                    rounds=20,
                ).parallel_run()
                plot.plot_performance(my_performance, multi_run_result)
