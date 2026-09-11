import core
globals().update(vars(core))
from evaluation.params import *

from circuits.ctle import ctle
from simulation.frequency_response import *
from simulation.hd3_analysis import *
from simulation.eye_analysis import *
from simulation.noise_analysis import *
from simulation.pvt_analysis import *

params = CTLEParams()

print(params)

# frequency_response(
#     W = CTLEParams.W,
#     L = CTLEParams.L,
#     Rs = CTLEParams.Rs,
#     Cs = CTLEParams.Cs,
#     Rd = CTLEParams.Rd,
#     Ibias = CTLEParams.Ibias)

# print(hd3_analysis(
#     W = CTLEParams.W,
#     L = CTLEParams.L,
#     Rs = CTLEParams.Rs,
#     Cs = CTLEParams.Cs,
#     Rd = CTLEParams.Rd,
#     Ibias = CTLEParams.Ibias)
# )

# print(input_referred_noise(
#     W = CTLEParams.W,
#     L = CTLEParams.L,
#     Rs = CTLEParams.Rs,
#     Cs = CTLEParams.Cs,
#     Rd = CTLEParams.Rd,
#     Ibias = CTLEParams.Ibias
#     ))

x = pvt_analysis(
    W = CTLEParams.W,
    L = CTLEParams.L,
    Rs = CTLEParams.Rs,
    Cs = CTLEParams.Cs,
    Rd = CTLEParams.Rd,
    Ibias = CTLEParams.Ibias)

print(pvt_analysis)