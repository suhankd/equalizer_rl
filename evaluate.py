import core
globals().update(vars(core))
from evaluation.params import *

from circuits.ctle import ctle
from simulation.frequency_response import *
from simulation.hd3_analysis import *
from simulation.eye_analysis import *
from simulation.noise_analysis import *
from simulation.pvt_analysis import *
from simulation.coefficient_calculation import *

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

# x = pvt_analysis(
    # W = CTLEParams.W,
    # L = CTLEParams.L,
    # Rs = CTLEParams.Rs,
    # Cs = CTLEParams.Cs,
    # Rd = CTLEParams.Rd,
    # Ibias = CTLEParams.Ibias)

# print(calculate_coefficient(
#     W = CTLEParams.W,
#     L = CTLEParams.L,
#     Rs = CTLEParams.Rs,
#     Cs = CTLEParams.Cs,
#     Rd = CTLEParams.Rd,
#     Ibias = CTLEParams.Ibias)
# )

result = eye_opening(
    W = CTLEParams.W,
    L = CTLEParams.L,
    Rs = CTLEParams.Rs,
    Cs = CTLEParams.Cs,
    Rd = CTLEParams.Rd,
    Ibias = CTLEParams.Ibias,
    save_path = 'eye_diagram.png')

print()
print(f"Eye width:  {result['eye_width']:.3f} UI")
print(f"Eye height: {result['eye_height']*1e3:.1f} mV")
print(f"Eye width spec:   {'PASS' if result['eye_width_pass'] else 'FAIL'}")
print(f"Eye height spec:  {'PASS' if result['eye_height_pass'] else 'FAIL'}")
print(f"Overall eye spec: {'PASS' if result['passed'] else 'FAIL'}")

