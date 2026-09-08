import core
globals().update(vars(core))

from circuits.ctle import ctle
from simulation.frequency_response import *
from simulation.hd3_analysis import *

import time

t1 = time.perf_counter()

hd3_analysis()

t2 = time.perf_counter()

print("HD3 analysis took:", t2 - t1, "seconds")