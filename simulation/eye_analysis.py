import core
globals().update(vars(core))

from circuits.ctle import ctle
from circuits.channel import channel, channel_section

import os
import uuid
import subprocess
import numpy as np
import matplotlib.pyplot as plt


def apply_dfe(v, t, ui, coefficient=1 / 30.9):
    previous = np.interp(
        t - ui,
        t,
        v,
        left=v[0]
    )
    return v - coefficient * previous


def eye_opening(
    W=99.6,
    L=0.15,
    Rs=50.5,
    Cs=3.3e-12,
    Rd=100,
    Ibias=1.25e-3,
    save_path=None,
    Vdd=1.8,
    temperature=27,
    corner='tt',
    coefficient = (1/30.9)
):

    N_BITS = 300
    DATA_RATE = 5e9
    Tb = 1 / DATA_RATE
    VCM = 1.2
    V_SWING = 0.1
    STEP_TIME = 2e-12
    N_SETTLE = 20
    SEED = 42

    EYE_WIDTH_MIN = 0.4
    EYE_HEIGHT_MIN = 0.1

    END_TIME = N_BITS * Tb

    rng = np.random.default_rng(SEED)
    bits = rng.integers(0, 2, size=N_BITS)

    def _build_pwl(bits, polarity):
        points = []

        for i, b in enumerate(bits):
            level = VCM + polarity * V_SWING * (2 * b - 1)
            t_start = i * Tb
            points.append(
                f"{t_start:.15e} {level:.6f}"
            )

        return "PWL(\n+ " + "\n+ ".join(points) + ")"

    pwl_vinp = _build_pwl(bits, +1)
    pwl_vinn = _build_pwl(bits, -1)

    # =========================================================
    # Channel + CTLE
    # =========================================================

    circuit = Circuit("Channel + CTLE Eye")

    circuit.raw_spice += (
        f'.lib "{_PDK_LIB}" {corner}'
    )

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

    circuit.V(
        'dd',
        'vdd',
        circuit.gnd,
        Vdd @ u_V
    )

    # Channel input resistance

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

    # Channel output termination

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

    # Input data

    circuit.raw_spice += f"""
Vvin1 SRCP 0 {pwl_vinp}
Vvin2 SRCN 0 {pwl_vinn}
"""

    # Differential channel

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

    # CTLE

    circuit.X(
        'CTLE',
        'ctle',
        'Pchannel_OUTPUT',
        'Nchannel_OUTPUT',
        'voutp',
        'voutn',
        'vdd'
    )

    circuit.R(
        'Rloadp',
        'voutp',
        '0',
        1e3
    )

    circuit.R(
        'Rloadn',
        'voutn',
        '0',
        1e3
    )

    # =========================================================
    # NGSPICE
    # =========================================================

    tag = uuid.uuid4().hex[:8]

    sp_file = f"_eye_{tag}.sp"
    data_file = f"_eye_{tag}.txt"

    netlist = str(circuit)

    netlist += f"""
.control
.temp {temperature}
set filetype=ascii
tran {STEP_TIME:.15e} {END_TIME:.15e}
set wr_singlescale
set wr_vecnames
wrdata {data_file} v(voutp) v(voutn)
.endc
"""

    with open(sp_file, "w") as f:
        f.write(netlist)

    result = subprocess.run(
        ["ngspice", "-b", sp_file],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        for fn in (sp_file, data_file):
            if os.path.exists(fn):
                os.remove(fn)

        raise RuntimeError(
            f"ngspice failed (rc={result.returncode}):\n"
            f"{result.stderr}"
        )

    data = np.loadtxt(
        data_file,
        skiprows=1
    )

    time = data[:, 0]
    voutp = data[:, 1]
    voutn = data[:, 2]

    # =========================================================
    # Ideal 1-tap DFE
    # =========================================================

    vout_diff = apply_dfe(
        voutp - voutn,
        time,
        Tb,
        coefficient
    )

    if os.path.exists(sp_file):
        os.remove(sp_file)

    if os.path.exists(data_file):
        os.remove(data_file)

    # =========================================================
    # Remove settling
    # =========================================================

    mask = time >= N_SETTLE * Tb

    time = time[mask]
    vout_diff = vout_diff[mask]

    # =========================================================
    # Phase alignment
    # =========================================================

    phase_raw = np.mod(time, Tb)
    phase_edges = np.linspace(0, Tb, 51)
    variances = []

    for i in range(50):

        in_bin = (
            (phase_raw >= phase_edges[i]) &
            (phase_raw < phase_edges[i + 1])
        )

        if np.sum(in_bin) > 5:
            variances.append(
                np.var(vout_diff[in_bin])
            )
        else:
            variances.append(0)

    idx_crossing = np.argmin(variances)

    t_crossing_phase = (
        phase_edges[idx_crossing] +
        phase_edges[idx_crossing + 1]
    ) / 2.0

    t_aligned = time - t_crossing_phase

    # =========================================================
    # Fold eye
    # =========================================================

    two_ui = 2.0 * Tb

    t_folded = np.mod(
        t_aligned,
        two_ui
    )

    t_ui = t_folded / Tb

    t_ui_single = (
        np.mod(t_aligned, Tb) / Tb
    )

    # =========================================================
    # Eye height
    # =========================================================

    center_mask = (
        (t_ui_single >= 0.45) &
        (t_ui_single <= 0.55)
    )

    v_center = vout_diff[center_mask]

    logic_1_samples = v_center[
        v_center > 0
    ]

    logic_0_samples = v_center[
        v_center <= 0
    ]

    if (
        len(logic_1_samples) > 0 and
        len(logic_0_samples) > 0
    ):

        v_high = np.percentile(
            logic_1_samples,
            1
        )

        v_low = np.percentile(
            logic_0_samples,
            99
        )

        eye_height = max(
            0.0,
            float(v_high - v_low)
        )

    else:
        eye_height = 0.0

    # =========================================================
    # Eye width
    # =========================================================

    phase = np.mod(
        t_aligned,
        Tb
    ) / Tb

    crossings = []

    for i in range(len(vout_diff) - 1):

        v1 = vout_diff[i]
        v2 = vout_diff[i + 1]

        if v1 * v2 < 0:

            frac = -v1 / (v2 - v1)

            t_cross = (
                phase[i] +
                frac *
                (phase[i + 1] - phase[i])
            )

            if abs(
                phase[i + 1] - phase[i]
            ) < 0.1:

                crossings.append(
                    t_cross
                )

    crossings = np.asarray(
        crossings
    )

    left = crossings[
        crossings < 0.5
    ]

    right = crossings[
        crossings > 0.5
    ]

    if (
        len(left) > 0 and
        len(right) > 0
    ):

        left_edge = np.percentile(
            left,
            95
        )

        right_edge = np.percentile(
            right,
            5
        )

        eye_width = (
            right_edge -
            left_edge
        )

    else:
        eye_width = 0.0

    eye_width = float(
        np.clip(
            eye_width,
            0.0,
            1.0
        )
    )

    # =========================================================
    # Pass / fail
    # =========================================================

    eye_width_pass = (
        eye_width >= EYE_WIDTH_MIN
    )

    eye_height_pass = (
        eye_height >= EYE_HEIGHT_MIN
    )

    passed = (
        eye_width_pass and
        eye_height_pass
    )

    print(
        f"Eye height       = "
        f"{eye_height * 1e3:.1f} mV"
    )

    print(
        f"Eye width        = "
        f"{eye_width:.3f} UI"
    )

    print(
        f"Eye height spec  : "
        f"{'PASS' if eye_height_pass else 'FAIL'}"
    )

    print(
        f"Eye width spec   : "
        f"{'PASS' if eye_width_pass else 'FAIL'}"
    )

    print(
        f"Overall eye spec : "
        f"{'PASS' if passed else 'FAIL'}"
    )

    # =========================================================
    # Plot
    # =========================================================

    fig, ax = plt.subplots(
        figsize=(9, 5),
        facecolor="black"
    )

    ax.set_facecolor("black")

    pts_per_segment = int(
        round(two_ui / STEP_TIME)
    )

    n_segments = (
        len(vout_diff) //
        pts_per_segment
    )

    for s in range(n_segments):

        idx0 = s * pts_per_segment
        idx1 = idx0 + pts_per_segment

        shade = 0.35 + 0.55 * (
            s / max(1, n_segments - 1)
        )

        ax.plot(
            t_ui[idx0:idx1],
            vout_diff[idx0:idx1],
            color=plt.cm.Reds(shade),
            alpha=0.18,
            linewidth=0.8
        )

    ax.set_xlabel(
        "Time (UI)",
        fontsize=11,
        fontweight="bold",
        color="white"
    )

    ax.set_ylabel(
        "Differential Output Voltage (V)",
        fontsize=11,
        fontweight="bold",
        color="white"
    )

    ax.set_title(
        f"Channel + CTLE + Ideal 1-Tap DFE\n"
        f"EH = {eye_height * 1e3:.1f} mV, "
        f"EW = {eye_width:.2f} UI "
        f"[{'PASS' if passed else 'FAIL'}]",
        fontsize=12,
        fontweight="bold",
        color="white"
    )

    ax.set_xlim(0, 2)

    ax.grid(
        True,
        linestyle="--",
        alpha=0.25,
        color="white"
    )

    ax.tick_params(
        colors="white"
    )

    for spine in ax.spines.values():
        spine.set_color("white")

    if save_path is not None:

        fig.savefig(
            save_path,
            dpi=150,
            bbox_inches="tight",
            facecolor="black"
        )

        print(
            f"[eye_opening] plot saved → "
            f"{save_path}"
        )
    else:
        plt.show()

    plt.close(fig)

    return {
        "figure": fig,
        "eye_width": eye_width,
        "eye_height": eye_height,
        "eye_width_pass": eye_width_pass,
        "eye_height_pass": eye_height_pass,
        "passed": passed,
    }