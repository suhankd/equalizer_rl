import core
globals().update(vars(core))

from circuits.ctle import ctle

def frequency_response(
    W=99.6,
    L=0.15,
    Rs=50.5,
    Cs=3.3e-12,
    Rd=100,
    Ibias=1.25e-3
    ):

    circuit = Circuit("CTLE")

    circuit.raw_spice += f'.lib "{_PDK_LIB}" tt'

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
        1.8 @ u_V
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
Vvin1 vinp 0 DC 1.2 AC 1m 0
Vvin2 vinn 0 DC 1.2 AC 1m 180
"""

    simulator = circuit.simulator(
        temperature=27,
        nominal_temperature=27
    )

    analysis = simulator.ac(
        start_frequency=10 @ u_MHz,
        stop_frequency=10 @ u_GHz,
        number_of_points=1000,
        variation='dec'
    )

    vout_diff = np.array(analysis.voutp) - np.array(analysis.voutn)
    vin_diff  = np.array(analysis.vinp) - np.array(analysis.vinn)

    gain = vout_diff / vin_diff

    gain_db = 20 * np.log10(np.abs(gain))

    freq = np.array(analysis.frequency)

    f_target = 2.5e9  # 2.5 GHz

    gain_at_target = np.interp(
        np.log10(f_target),
        np.log10(freq),
        gain_db
    )

    print(f"Gain at 2.5 GHz = {gain_at_target:.3f} dB")

    plt.figure(figsize=(8, 5))
    plt.semilogx(freq, gain_db, label="CTLE")

    plt.scatter(
        f_target,
        gain_at_target,
        s=60,
        zorder=5,
        label=f"2.5 GHz: {gain_at_target:.2f} dB"
    )

    plt.axvline(
        f_target,
        linestyle="--",
        linewidth=1
    )

    plt.annotate(
        f"2.5 GHz\n{gain_at_target:.2f} dB",
        xy=(f_target, gain_at_target),
        xytext=(15, 25),
        textcoords="offset points",
        arrowprops=dict(arrowstyle="->")
    )

    plt.xlabel("Frequency (Hz)")
    plt.ylabel("Gain (dB)")
    plt.title("CTLE Frequency Response")
    plt.grid(True, which="both")
    plt.legend()

    plt.show()