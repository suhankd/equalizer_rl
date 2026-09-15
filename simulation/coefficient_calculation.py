import core
globals().update(vars(core))

from circuits.ctle import ctle
from circuits.channel import channel_section, channel

import numpy as np


def calculate_coefficient(
    W=99.6,
    L=0.15,
    Rs=50.5,
    Cs=3.3e-12,
    Rd=100,
    Ibias=1.25e-3,
    Vdd=1.8,
    temperature=27,
    corner='tt'
):

    # ---------------------------------------------------------
    # Parameters
    # ---------------------------------------------------------

    UI = 200e-12          # 5 Gb/s
    VCM = 1.2
    VIN_DIFF = 0.2

    # Clock sampling phase
    #
    # Rising edge at 200 ps, 400 ps, 600 ps...
    #
    # We put the isolated pulse BEFORE the first sampling edge,
    # so that the first sampling edge captures the main cursor.
    #
    # Pulse:
    #       0 ps -> 200 ps
    #
    # Samples:
    #       200 ps -> h0
    #       400 ps -> h1
    #
    SAMPLE_TIME = 200e-12

    circuit = Circuit("Channel + CTLE coefficient extraction")

    # ---------------------------------------------------------
    # SKY130 model
    # ---------------------------------------------------------

    circuit.raw_spice += f'.lib "{_PDK_LIB}" {corner}'

    # ---------------------------------------------------------
    # Subcircuits
    # ---------------------------------------------------------

    circuit.subcircuit(channel_section())
    circuit.subcircuit(channel(n_sections=8))

    circuit.subcircuit(
        ctle(
            W=W,
            L=L,
            Rs=Rs,
            Cs=Cs,
            Rd=Rd,
            Ibias=Ibias
        )
    )

    # ---------------------------------------------------------
    # Supply
    # ---------------------------------------------------------

    circuit.V(
        'dd',
        'vdd',
        circuit.gnd,
        Vdd @ u_V
    )

    # ---------------------------------------------------------
    # Channel input resistance
    # ---------------------------------------------------------

    circuit.R(
        'Pchannel_Rin',
        'SRCP',
        'Pchannel_INPUT',
        100
    )

    circuit.R(
        'Nchannel_Rin',
        'SRCN',
        'Nchannel_INPUT',
        100
    )

    # ---------------------------------------------------------
    # Channel output termination
    # ---------------------------------------------------------

    circuit.R(
        'Pchannel_Rout',
        'Pchannel_OUTPUT',
        circuit.gnd,
        100
    )

    circuit.R(
        'Nchannel_Rout',
        'Nchannel_OUTPUT',
        circuit.gnd,
        100
    )

    # ---------------------------------------------------------
    # Differential isolated pulse
    #
    # Clock:
    #
    #       |<------ UI ------>|
    #       0                 200 ps
    #                         ^
    #                         sampling edge
    #
    # Input pulse:
    #
    #       0 ──────────────── 1
    #       0 ps             200 ps
    #
    # Differential input:
    #
    #       VCM + 100mV
    #       VCM - 100mV
    #
    # After 200 ps, return to VCM.
    # ---------------------------------------------------------

    circuit.raw_spice += """
Vvin1 SRCP 0 PWL(
+ 0p      1.2
+ 1p      1.3
+ 199p    1.3
+ 200p    1.2
+ 1000p   1.2)

Vvin2 SRCN 0 PWL(
+ 0p      1.2
+ 1p      1.1
+ 199p    1.1
+ 200p    1.2
+ 1000p   1.2)

* 5 Gb/s clock
Vck ck 0 PULSE(
+ 0.6
+ 1.2
+ 0p
+ 10p
+ 10p
+ 90p
+ 200p)
"""

    # ---------------------------------------------------------
    # Differential channel
    # ---------------------------------------------------------

    circuit.X(
        'PCHANNEL',
        'channel',
        'Pchannel_INPUT',
        'Pchannel_OUTPUT'
    )

    circuit.X(
        'NCHANNEL',
        'channel',
        'Nchannel_INPUT',
        'Nchannel_OUTPUT'
    )

    circuit.X(
        'CTLE',
        'ctle',
        'Pchannel_OUTPUT',
        'Nchannel_OUTPUT',
        'voutp',
        'voutn',
        'vdd'
    )

    simulator = circuit.simulator(
        temperature=temperature,
        nominal_temperature=temperature
    )

    analysis = simulator.transient(
        step_time=0.2e-12,
        end_time=1e-9
    )

    t = np.array(analysis.time)

    voutp = np.array(analysis.voutp)
    voutn = np.array(analysis.voutn)

    vout_diff = voutp - voutn

    t_h0 = SAMPLE_TIME
    t_h1 = SAMPLE_TIME + UI

    i0 = np.argmin(np.abs(t - t_h0))
    i1 = np.argmin(np.abs(t - t_h1))

    h0 = vout_diff[i0]
    h1 = vout_diff[i1]

    coefficient = h1 / h0

    print(f"Sampling time       = {t[i0] * 1e12:.2f} ps")
    print(f"Main cursor h0      = {h0:.6f} V")

    print(f"Next sample time    = {t[i1] * 1e12:.2f} ps")
    print(f"Post-cursor h1      = {h1:.6f} V")

    print(f"DFE coefficient     = {coefficient:.6f}")

    return coefficient