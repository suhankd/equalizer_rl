import core
globals().update(vars(core))

from circuits.ctle import ctle

from simulation.frequency_response import *
from simulation.hd3_analysis import *
from simulation.eye_analysis import *
from simulation.noise_analysis import *

PROCESS_CORNERS = ["tt", "ss", "ff", "sf", "fs"]
VDD_VALUES = [1.71, 1.80, 1.89]
TEMPERATURES = list(range(0,126,25))

def pvt_analysis(
    W, L, Rs, Cs, Rd, Ibias
):

    results = []

    for corner in PROCESS_CORNERS:
        for vdd in VDD_VALUES:
            for temperature in TEMPERATURES:

                print(
                    f"\nPVT: {corner} | "
                    f"VDD={vdd:.2f} V | "
                    f"T={temperature} C"
                )

                freq = frequency_response(
                    W=W,
                    L=L,
                    Rs=Rs,
                    Cs=Cs,
                    Rd=Rd,
                    Ibias=Ibias,
                    corner=corner,
                    Vdd=vdd,
                    temperature=temperature)

                hd3 = hd3_analysis(
                    W=W,
                    L=L,
                    Rs=Rs,
                    Cs=Cs,
                    Rd=Rd,
                    Ibias=Ibias,
                    corner=corner,
                    Vdd=vdd,
                    temperature=temperature)

                noise = input_referred_noise(
                    W=W,
                    L=L,
                    Rs=Rs,
                    Cs=Cs,
                    Rd=Rd,
                    Ibias=Ibias,
                    corner=corner,
                    Vdd=vdd,
                    temperature=temperature)

                result = {
                    "corner": corner,
                    "vdd": vdd,
                    "temperature": temperature,
                    "dc_gain": freq["dc_gain"],
                    "boost_db": freq["boost_db"],
                    "peak_freq": freq["peak_freq"],
                    "hd3_db": hd3,
                    "noise_rms": noise,
                }

                result["pass"] = (
                    3 <= freq["boost_db"] <= 12
                    and 1.25e9 <= freq["peak_freq"] <= 2.5e9
                    and hd3 < -30
                    and noise < 1.5e-3
                )

                results.append(result)

                print(
                    f"  DC gain : {freq['dc_gain']:.2f} dB\n"
                    f"  Boost   : {freq['boost_db']:.2f} dB\n"
                    f"  Peak    : {freq['peak_freq']/1e9:.2f} GHz\n"
                    f"  HD3     : {hd3:.2f} dB\n"
                    f"  Noise   : {noise*1e3:.3f} mV RMS\n"
                    f"  PASS    : {result['pass']}"
                )

    return results