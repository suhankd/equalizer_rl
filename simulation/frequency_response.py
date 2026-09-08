import core
globals().update(vars(core))

def ac_analysis(circuit):

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