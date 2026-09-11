import core
globals().update(vars(core))

from circuits.ctle import ctle

def frequency_response(
    W=99.6,
    L=0.15,
    Rs=50.5,
    Cs=3.3e-12,
    Rd=100,
    Ibias=1.25e-3,
    save_path=None,
    Vdd = 1.8,
    temperature = 27,
    corner = 'tt'
    ):

    circuit = Circuit("CTLE")

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
Vvin1 vinp 0 DC 1.2 AC 1m 0
Vvin2 vinn 0 DC 1.2 AC 1m 180
"""

    simulator = circuit.simulator(
        temperature=temperature,
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

    f_nyquist = 2.5e9  # 2.5 GHz
    f_dc_ref  = 10e6   # lowest simulated freq used as proxy for DC

    gain_at_nyquist = np.interp(
        np.log10(f_nyquist),
        np.log10(freq),
        gain_db
    )

    gain_at_dc = gain_db[0]

    boost_db = gain_at_nyquist - gain_at_dc

    # Find peak frequency
    peak_idx   = np.argmax(gain_db)
    peak_freq  = freq[peak_idx]
    peak_gain  = gain_db[peak_idx]

    print(f"DC gain          = {gain_at_dc:.3f} dB")
    print(f"Gain at 2.5 GHz  = {gain_at_nyquist:.3f} dB")
    print(f"Boost            = {boost_db:.3f} dB")
    print(f"Peak gain        = {peak_gain:.3f} dB  @ {peak_freq/1e9:.3f} GHz")

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.semilogx(freq, gain_db, label="CTLE", linewidth=2)

    ax.scatter(
        f_nyquist,
        gain_at_nyquist,
        s=60,
        zorder=5,
        label=f"2.5 GHz: {gain_at_nyquist:.2f} dB"
    )

    ax.axvline(f_nyquist, linestyle="--", linewidth=1, color="gray")

    ax.annotate(
        f"2.5 GHz\n{gain_at_nyquist:.2f} dB",
        xy=(f_nyquist, gain_at_nyquist),
        xytext=(15, 25),
        textcoords="offset points",
        arrowprops=dict(arrowstyle="->")
    )

    ax.set_xlabel("Frequency (Hz)")
    ax.set_ylabel("Gain (dB)")
    ax.set_title("CTLE Frequency Response")
    ax.grid(True, which="both")
    ax.legend()

    if save_path is not None:
        fig.savefig(save_path, dpi=120, bbox_inches="tight")
        print(f"[frequency_response] plot saved → {save_path}")
    else:
        plt.show()

    plt.close(fig)

    return {
        "freq":            freq,
        "gain_db":         gain_db,
        "gain_at_nyquist": gain_at_nyquist,
        "boost_db":        boost_db,
        "peak_freq":       peak_freq,
        "peak_gain":       peak_gain,
        "dc_gain":         gain_at_dc,
    }