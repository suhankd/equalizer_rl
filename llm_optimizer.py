"""
llm_optimizer.py  –  5-iteration DeepSeek feedback loop for CTLE sizing.

Each iteration:
  1. Run frequency_response() → save PNG + collect metrics
  2. Run hd3_analysis()       → get HD3 scalar (dB)
  3. Run eye_opening()        → save eye PNG + collect eye width/height metrics
  4. Send freq plot + eye plot + metrics + current params to Claude (vision API)
  5. Parse the returned params.py code block and overwrite params.py
  6. Reload params for the next iteration
"""

import os
import re
import base64
import importlib
from pathlib import Path

import time

from openai import OpenAI

import core                                         # noqa: F401  (patches ngspice)
globals().update(vars(core))

from simulation.frequency_response import frequency_response
from simulation.hd3_analysis import hd3_analysis
from simulation.eye_analysis import eye_opening

PARAMS_FILE  = Path("evaluation/params.py")
SPECS_FILE   = Path("evaluation/specs.py")
PLOTS_DIR    = Path("optimizer_plots")
EYE_PLOTS_DIR = Path("eye_plots")
N_ITERATIONS = 10


def read_file(path: Path) -> str:
    return path.read_text()


def write_params(new_content: str):
    PARAMS_FILE.write_text(new_content)
    print("[llm_optimizer] params.py updated.\n")


def extract_code_block(text: str) -> str | None:
    match = re.search(r"```python\s*(.*?)```", text, re.DOTALL)
    return match.group(1).strip() if match else None


def load_params():
    import sys

    if "evaluation.params" in sys.modules:
        del sys.modules["evaluation.params"]

    from evaluation.params import CTLEParams
    return CTLEParams()

def encode_image(path: Path) -> str:
    return base64.standard_b64encode(path.read_bytes()).decode("utf-8")


def compute_composite_reward(freq_metrics: dict, eye_metrics: dict) -> float:
    """
    Computes the RL composite reward function R in [0, 1]:
      R = 1/5 * [ min(H / 0.1, 1) + min(W / 0.4, 1) + S_B + S_F + exp(-|G_DC|) ]
    where:
      H    : Eye height in Volts
      W    : Eye width in UI
      S_B  : Peaking boost score based on boost_db
      S_F  : Peak frequency score based on peak_freq in GHz
      G_DC : DC gain in dB
    """
    import math

    H = eye_metrics.get("eye_height", 0.0)
    W = eye_metrics.get("eye_width", 0.0)
    G_DC = freq_metrics.get("dc_gain", 0.0)
    B = freq_metrics.get("boost_db", 0.0)
    f_p = freq_metrics.get("peak_freq", 0.0) / 1e9  # Convert Hz to GHz

    term_H = min(H / 0.1, 1.0)
    term_W = min(W / 0.4, 1.0)

    # Peaking Boost Score (S_B)
    if B < 3.0:
        S_B = B / 3.0
    elif B <= 12.0:
        S_B = 1.0
    else:
        S_B = 12.0 / B

    # Peak Frequency Score (S_F)
    if f_p < 1.25:
        S_F = f_p / 1.25
    elif f_p <= 2.5:
        S_F = 1.0
    else:
        S_F = 2.5 / f_p

    # DC Gain Penalty term
    term_dc = math.exp(-abs(G_DC))

    R = (1.0 / 5.0) * (term_H + term_W + S_B + S_F + term_dc)
    return float(R)


def ask_claude(
    iteration: int,
    current_params_text: str,
    freq_metrics: dict,
    hd3_db: float,
    freq_plot_path: Path,
    eye_metrics: dict,
    eye_plot_path: Path,
) -> str:

    client = OpenAI(
        api_key=os.environ["DEEPSEEK_API_KEY"],
        base_url="https://api.deepseek.com",
    )

    specs  = read_file(SPECS_FILE)

    system = (
        "You are an expert analog IC designer specialising in CMOS equaliser circuits "
        "for high-speed serial links. Your job is to iteratively improve the design "
        "parameters of a CTLE implemented in the SKY130A process, based on simulation results. "
        "Be concise in your analysis — identify the key issues quickly and output the updated params.py directly."
    )

    ibias_match = re.search(r'Ibias.*?=\s*([\d.e+-]+)', current_params_text)
    power_mw = 2 * float(ibias_match.group(1)) * 1.8 * 1000 if ibias_match else 0.0

    eye_height_mv = eye_metrics["eye_height"] * 1e3
    composite_reward = compute_composite_reward(freq_metrics, eye_metrics)

    metrics_summary = (
        f"### Simulation results (iteration {iteration})\n\n"
        f"| Metric            | Value                        | Target                        |\n"
        f"|-------------------|------------------------------|-------------------------------|\n"
        f"| DC gain           | {freq_metrics['dc_gain']:.2f} dB | Target ≈ 0 dB; minimize unnecessary DC gain/attenuation. |\n"
        f"| Max Gain Frequency| {freq_metrics['peak_freq']/1e9:.2f} GHz         | Maximum gain frequency must be <= 2.5 GHz and >= 1.25GHz. Take care not to cross over. |\n"
        f"| Gain @ 2.5 GHz    | {freq_metrics['gain_at_nyquist']:.2f} dB | —                             |\n"
        f"| Boost (2.5G–DC)   | {freq_metrics['boost_db']:.2f} dB        | 3.0 – 12.0 dB                 |\n"
        f"| Peak gain         | {freq_metrics['peak_gain']:.2f} dB @ {freq_metrics['peak_freq']/1e9:.2f} GHz | peak in 1.25–2.5 GHz |\n"
        f"| HD3 @ 100 MHz     | {hd3_db:.2f} dB              | < -30 dB                      |\n"
        f"| Power (est.)      | {power_mw:.1f} mW            | < 15 mW                       |\n"
        f"| Eye Height        | {eye_height_mv:.1f} mV       | >= 100 mV {'✓ PASS' if eye_metrics['eye_height_pass'] else '✗ FAIL'}  |\n"
        f"| Eye Width         | {eye_metrics['eye_width']:.3f} UI      | >= 0.4 UI {'✓ PASS' if eye_metrics['eye_width_pass'] else '✗ FAIL'}  |\n"
        f"| Eye Overall       | {'PASS' if eye_metrics['passed'] else 'FAIL'}                    | Both EH and EW pass           |\n"
        f"| Composite Reward R| {composite_reward:.4f}                   | Maximize R -> 1.0 (RL score)  |\n"
    )

    user_text = f"""
## Iteration {iteration} / {N_ITERATIONS}

{metrics_summary}

Two plots are attached as images:
1. **Frequency-response plot** — Study the boost shape carefully:
   - Is the boost in the right frequency range (1.25–2.5 GHz)?
   - Is the boost magnitude within spec (3–12 dB)?
   - Is there excessive peaking or roll-off before Nyquist?
2. **Eye diagram** — Study the eye opening carefully:
   - Is the eye height >= 100 mV?
   - Is the eye width >= 0.4 UI?
   - Is the DFE coefficient cancelling ISI effectively, or is it over/under-correcting?

## Design specs (from `specs.py`)
```python
{specs}
```

## Current `params.py`
```python
{current_params_text}
```

## Parameter constraints (SKY130A)
| Parameter       | Constraint |
|-----------------|------------|
| W               | 0.36 … 99.6 µm, multiple of 0.36 µm, **never exceed 99.6 µm** |
| L               | 0.15 … 2.0 µm |
| Rs              | > 0 Ω |
| Cs              | 0.1 pF … 10 pF |
| Rd              | > 0 Ω |
| Ibias           | 0.1 mA … 5 mA |
| dfe_coefficient | 0.001 … 0.2 (dimensionless) |

## Design intuition
1. **Zero frequency**: `f_z = 1 / (2π·Rs·Cs)` — target ≈ 1–2 GHz for peak at Nyquist.
2. **Boost magnitude**: ≈ `20·log10(1 + gm·Rs)`. Increase Rs to raise boost; decrease Rs to lower it.
3. **DC gain**: `|Av| ≈ gm·Rd`. Adjust Rd to shift overall level without changing boost shape.
4. **HD3**: larger W/L and moderate overdrive improves linearity. Increasing Ibias also helps.
5. **Power**: `P ≈ 2·Ibias·1.8`. Must stay under 15 mW.
6. **DFE coefficient**: cancels post-cursor ISI. The ideal value equals the ratio of the
   first post-cursor tap to the main cursor of the channel impulse response.
   If the eye is open but narrow, try increasing `dfe_coefficient` slightly.
   If the eye collapses (over-correction), decrease it.
   Start from the current value and make small, targeted adjustments.

## Instructions

You are optimizing the CTLE over only 5 iterations.

For this iteration:
1. Analyze both the frequency-response plot and the eye diagram.
2. Identify the most important problems (boost shape, eye height, eye width, HD3).
3. Choose concrete parameter changes that improve the design.
4. Prefer small, targeted changes rather than changing every parameter.
5. The SPICE simulation results are authoritative; the equations above are
   only approximate design intuition.
6. Respect ALL parameter constraints.
7. You MUST also tune `dfe_coefficient` if the eye metrics are not passing.
8. Aim to maximize the composite reward score R (target 1.0).

Output the complete updated `params.py` in exactly ONE ```python``` block.

Keep the exact same file structure, imports, dataclass, and field names.
Only change the numeric default values.
Do not add comments inside the dataclass.
"""

    freq_image_b64 = encode_image(freq_plot_path)
    eye_image_b64  = encode_image(eye_plot_path)

    print(f"[llm_optimizer] Iteration {iteration}: sending freq plot + eye plot + metrics to DeepSeek…")

    response = client.chat.completions.create(
        model="deepseek-flash",
        max_tokens=65536,
        messages=[
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": user_text,
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{freq_image_b64}",
                        },
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{eye_image_b64}",
                        },
                    },
                ],
            },
        ],
    )

    choice = response.choices[0]
    finish_reason = choice.finish_reason
    reply = choice.message.content or ""
    reasoning = getattr(choice.message, "reasoning_content", None) or ""

    print(f"\n── DeepSeek (iteration {iteration}) [finish_reason={finish_reason}, reasoning_tokens~={len(reasoning.split())}] ─")
    if not reply:
        print(f"[llm_optimizer] WARNING: empty reply from DeepSeek! full choice: {choice}")
    else:
        print(reply)
    print("───────────────────────────────────────────────────────────────────────────\n")

    return reply


def run():
    PLOTS_DIR.mkdir(exist_ok=True)
    EYE_PLOTS_DIR.mkdir(exist_ok=True)

    for iteration in range(1, N_ITERATIONS + 1):
        print(f"\n{'='*60}")
        print(f"  ITERATION {iteration} / {N_ITERATIONS}")
        print(f"{'='*60}\n")

        # ── load current params ──────────────────────────────────────
        params = load_params()
        kwargs = dict(
            W=params.W,
            L=params.L,
            Rs=params.Rs,
            Cs=params.Cs,
            Rd=params.Rd,
            Ibias=params.Ibias,
        )

        # ── run simulations ──────────────────────────────────────────
        freq_plot_path = PLOTS_DIR / f"iter_{iteration:02d}_freq_response.png"
        eye_plot_path  = EYE_PLOTS_DIR / f"iter_{iteration:02d}_eye.png"

        print("[llm_optimizer] Running frequency_response()…")
        freq_metrics = frequency_response(**kwargs, save_path=freq_plot_path)

        print("[llm_optimizer] Running hd3_analysis()…")
        hd3_db = hd3_analysis(**kwargs)
        print(f"HD3 @ 100 MHz = {hd3_db:.2f} dB  (target < −30 dB)\n")

        print("[llm_optimizer] Running eye_opening()…")
        eye_metrics = eye_opening(
            **kwargs,
            coefficient=params.dfe_coefficient,
            save_path=eye_plot_path,
        )
        reward = compute_composite_reward(freq_metrics, eye_metrics)
        print(
            f"Eye height = {eye_metrics['eye_height']*1e3:.1f} mV  "
            f"({'PASS' if eye_metrics['eye_height_pass'] else 'FAIL'}), "
            f"Eye width = {eye_metrics['eye_width']:.3f} UI  "
            f"({'PASS' if eye_metrics['eye_width_pass'] else 'FAIL'}), "
            f"Composite Reward R = {reward:.4f}\n"
        )

        # ── ask Claude ───────────────────────────────────────────────
        current_params_text = read_file(PARAMS_FILE)
        reply = ask_claude(
            iteration=iteration,
            current_params_text=current_params_text,
            freq_metrics=freq_metrics,
            hd3_db=hd3_db,
            freq_plot_path=freq_plot_path,
            eye_metrics=eye_metrics,
            eye_plot_path=eye_plot_path,
        )

        # ── update params.py ─────────────────────────────────────────
        new_params = extract_code_block(reply)
        if new_params is None:
            print(f"[llm_optimizer] WARNING: no ```python block found in iteration {iteration}. "
                  "params.py unchanged, continuing with current values.\n")
            continue

        write_params(new_params)

    print("\n[llm_optimizer] All iterations complete.")
    print(f"Freq plots saved in : {PLOTS_DIR.resolve()}")
    print(f"Eye plots saved in  : {EYE_PLOTS_DIR.resolve()}")
    print(f"Final params        : {PARAMS_FILE.resolve()}")


start_time = time.perf_counter()
run()
total_time = time.perf_counter() - start_time

print(f"\nTotal runtime: {total_time:.2f} s")
print(f"Average time per iteration: {total_time / N_ITERATIONS:.2f} s")