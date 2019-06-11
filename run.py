"""
=====================================
Main file that runs the simulator
=====================================
"""

# This is the single main file that runs the simulator.


import example
import execution

if __name__ == "__main__":
    for myscenario in example.scenarios:
        for myengine in example.engines:
            for myperformance in example.performances:
                execution.Execution(
                    myscenario, myengine, myperformance, 20
                ).run()
