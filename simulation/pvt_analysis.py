import core
globals().update(vars(core))

from circuits.ctle import ctle
from simulation.frequency_response import *
from simulation.hd3_analysis import *
from simulation.noise_analysis import *

import numpy as np
import matplotlib.pyplot as plt

PROCESS_CORNERS = ["tt", "ss", "ff", "sf", "fs"]
VDD_VALUES = [1.71, 1.80, 1.89]
TEMPERATURES = list(range(0, 126, 25))


def pvt_analysis(W, L, Rs, Cs, Rd, Ibias, save_path="pvt_heatmap.png"):

    results = []

    # rows = corner × VDD, columns = temperature
    heatmap = np.zeros((len(PROCESS_CORNERS) * len(VDD_VALUES),
                        len(TEMPERATURES)))

    row_labels = []

    row = 0

    for corner in PROCESS_CORNERS:
        for vdd in VDD_VALUES:

            row_labels.append(f"{corner.upper()}  {vdd:.2f}V")

            for col, temperature in enumerate(TEMPERATURES):

                freq = frequency_response(
                    W=W, L=L, Rs=Rs, Cs=Cs, Rd=Rd, Ibias=Ibias,
                    corner=corner, Vdd=vdd, temperature=temperature
                )

                hd3 = hd3_analysis(
                    W=W, L=L, Rs=Rs, Cs=Cs, Rd=Rd, Ibias=Ibias,
                    corner=corner, Vdd=vdd, temperature=temperature
                )

                noise = input_referred_noise(
                    W=W, L=L, Rs=Rs, Cs=Cs, Rd=Rd, Ibias=Ibias,
                    corner=corner, Vdd=vdd, temperature=temperature
                )

                # ----- normalized specification score -----

                boost_score = min(
                    max((freq["boost_db"] - 3) / 9, 0),
                    1
                )

                freq_score = min(
                    max((freq["peak_freq"] - 1.25e9) / 1.25e9, 0),
                    1
                )

                hd3_score = min(
                    max((-hd3 - 30) / 40, 0),
                    1
                )

                noise_score = min(
                    max((1.5e-3 - noise) / 1.5e-3, 0),
                    1
                )

                score = (
                    boost_score +
                    freq_score +
                    hd3_score +
                    noise_score
                ) / 4

                heatmap[row, col] = score

                results.append({
                    "corner": corner,
                    "vdd": vdd,
                    "temperature": temperature,
                    "boost_db": freq["boost_db"],
                    "peak_freq": freq["peak_freq"],
                    "hd3_db": hd3,
                    "noise_rms": noise,
                    "score": score,
                    "pass": score >= 0.99
                })

            row += 1

    # ---------- Heatmap ----------
    fig, ax = plt.subplots(figsize=(10, 8))

    im = ax.imshow(
        heatmap,
        cmap="RdYlGn",
        vmin=0,
        vmax=1,
        aspect="auto"
    )

    ax.set_xticks(range(len(TEMPERATURES)))
    ax.set_xticklabels(TEMPERATURES)
    ax.set_xlabel("Temperature (°C)")

    ax.set_yticks(range(len(row_labels)))
    ax.set_yticklabels(row_labels)
    ax.set_ylabel("Process Corner / VDD")

    ax.set_title("PVT Verification Heatmap")

    cbar = plt.colorbar(im)
    cbar.set_label("Specification Score")

    # annotate pass/fail
    for i in range(heatmap.shape[0]):
        for j in range(heatmap.shape[1]):
            txt = "✓" if heatmap[i, j] > 0.99 else ""
            ax.text(j, i, txt,
                    ha="center", va="center",
                    fontsize=8, color="black")

    plt.tight_layout()
    plt.savefig(save_path, dpi=300)
    plt.close()

    return results, heatmap