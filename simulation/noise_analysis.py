import core
globals().update(vars(core))

from circuits.ctle import ctle


def input_referred_noise(
    W=99.6,
    L=0.15,
    Rs=50.5,
    Cs=3.3e-12,
    Rd=100,
    Ibias=1.25e-3,
    Vdd = 1.8,
    temperature = 27,
    corner = 'tt'
):

    circuit = Circuit("CTLE Noise")

    circuit.raw_spice += f'.lib "{_PDK_LIB}" {corner}'

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

    circuit.V(
        'dd',
        'vdd',
        circuit.gnd,
        Vdd @ u_V
    )

    circuit.X(
        'CTLE',
        'ctle',
        'vinp',
        'vinn',
        'voutp',
        'voutn',
        'vdd'
    )

    circuit.R('Rloadp', 'voutp', '0', 1e3)
    circuit.R('Rloadn', 'voutn', '0', 1e3)

    circuit.raw_spice += """
Vcm vinp 0 DC 1.2
Vdiff vinn vinp DC 0 AC 1
"""

    simulator = circuit.simulator(
        temperature=temperature,
        nominal_temperature=27
    )

    analysis = simulator.noise(
        output_node='voutp',
        ref_node='voutn',
        src='Vdiff',
        variation='dec',
        points=50,
        start_frequency=10e6,
        stop_frequency=5e9
    )

    noise_rms = np.array(
        analysis.nodes['inoise_total']
    )[0]

    print(
        f"Input-referred noise = "
        f"{noise_rms * 1e3:.3f} mV RMS"
    )

    return noise_rms