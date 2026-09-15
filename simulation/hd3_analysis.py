import core
globals().update(vars(core))

from circuits.ctle import ctle

def hd3_analysis(
    W=99.6,
    L=0.15,
    Rs=50.5,
    Cs=3.3e-12,
    Rd=80,
    Ibias=1.25e-3,
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
    Vvin1 vinp 0 DC 1.2 SIN(0 10m 100Meg)
    Vvin2 vinn 0 DC 1.2 SIN(0 -10m 100Meg)
    """

    import subprocess

    netlist = str(circuit)

    netlist += f"""
    .control
    .temp {temperature}
    set filetype=ascii
    tran 10p 1u
    set wr_singlescale
    set wr_vecnames
    wrdata hd3_data.txt v(voutp) v(voutn)
    .endc
    """

    with open("ctle.sp", "w") as f:
        f.write(netlist)

    result = subprocess.run(
        ["ngspice", "-b", "ctle.sp"],
        capture_output=True,
        text=True
    )

    data = np.loadtxt("hd3_data.txt", skiprows=1)

    time = data[:, 0]
    voutp = data[:, 1]
    voutn = data[:, 2]

    vout = voutp - voutn

    start = 500e-9
    end = 1e-6

    mask = (time >= start) & (time <= end)

    time = time[mask]
    vout = vout[mask]

    dt = 10e-12

    uniform_time = np.arange(
        start,
        end,
        dt
    )

    vout_uniform = np.interp(
        uniform_time,
        time,
        vout
    )

    vout_uniform -= np.mean(vout_uniform)

    N = len(vout_uniform)

    spectrum = np.fft.rfft(vout_uniform)

    frequency = np.fft.rfftfreq(
        N,
        d=dt
    )

    magnitude = 2 * np.abs(spectrum) / N

    f1 = 100e6
    f3 = 300e6

    i1 = np.argmin(np.abs(frequency - f1))
    i3 = np.argmin(np.abs(frequency - f3))

    V1 = magnitude[i1]
    V3 = magnitude[i3]

    HD3 = 20 * np.log10(V3 / V1)


    print("N =", N)
    print("Frequency resolution =", frequency[1] - frequency[0])

    print()
    print("Fundamental frequency:", frequency[i1])
    print("Fundamental amplitude:", V1, "V")

    print()
    print("Third harmonic frequency:", frequency[i3])
    print("Third harmonic amplitude:", V3, "V")

    print()
    print("HD3:", HD3, "dB")

    os.remove("hd3_data.txt")
    os.remove("ctle.sp")

    return HD3

