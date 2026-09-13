"""
llm_optimizer.py  –  5-iteration Claude feedback loop for CTLE sizing.

Each iteration:
  1. Run frequency_response() → save PNG + collect metrics
  2. Run hd3_analysis()       → get HD3 scalar (dB)
  3. Send plot image + metrics + current params to Claude (vision API)
  4. Parse the returned params.py code block and overwrite params.py
  5. Reload params for the next iteration
"""

import os
import re
import base64
import importlib
from pathlib import Path

from anthropic import Anthropic

import core                                         # noqa: F401  (patches ngspice)
globals().update(vars(core))

from simulation.frequency_response import frequency_response
from simulation.hd3_analysis import hd3_analysis

PARAMS_FILE  = Path("evaluation/params.py")
SPECS_FILE   = Path("evaluation/specs.py")
PLOTS_DIR    = Path("optimizer_plots")
N_ITERATIONS = 5


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


def ask_claude(
    iteration: int,
    current_params_text: str,
    freq_metrics: dict,
    hd3_db: float,
    plot_path: Path,
) -> str:

    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    specs  = read_file(SPECS_FILE)

    system = (
        "You are an expert analog IC designer specialising in CMOS equaliser circuits "
        "for high-speed serial links. Your job is to iteratively improve the design "
        "parameters of a CTLE implemented in the SKY130A process, based on simulation results."
    )

    ibias_match = re.search(r'Ibias.*?=\s*([\d.e+-]+)', current_params_text)
    power_mw = 2 * float(ibias_match.group(1)) * 1.8 * 1000 if ibias_match else 0.0

    metrics_summary = (
        f"### Simulation results (iteration {iteration})\n\n"
        f"| Metric            | Value                        | Target                        |\n"
        f"|-------------------|------------------------------|-------------------------------|\n"
        f"| DC gain           | {freq_metrics['dc_gain']:.2f} dB         | Prefer close to 0 dB; avoid excessive negative gain.                             |\n"
        f"| Max Gain Frequency| {freq_metrics['peak_freq']/1e9:.2f} GHz         | Maximum gain frequency must be <= 2.5 GHz and >= 1.25GHz. Take care not to cross over.                             |\n"
        f"| Gain @ 2.5 GHz    | {freq_metrics['gain_at_nyquist']:.2f} dB | —                             |\n"
        f"| Boost (2.5G–DC)   | {freq_metrics['boost_db']:.2f} dB        | 3.0 – 12.0 dB                 |\n"
        f"| Peak gain         | {freq_metrics['peak_gain']:.2f} dB @ {freq_metrics['peak_freq']/1e9:.2f} GHz | peak in 1.25–2.5 GHz |\n"
        f"| HD3 @ 100 MHz     | {hd3_db:.2f} dB              | < -30 dB                      |\n"
        f"| Power (est.)      | {power_mw:.1f} mW            | < 15 mW                       |\n"
    )

    user_text = f"""
## Iteration {iteration} / {N_ITERATIONS}

{metrics_summary}

The frequency-response plot for this iteration is attached as an image. Study the shape carefully:
- Is the boost in the right frequency range (1.25–2.5 GHz)?
- Is the boost magnitude within spec (3–12 dB)?
- Is there excessive peaking or roll-off before Nyquist?

## Design specs (from `specs.py`)
```python
{specs}
```

## Current `params.py`
```python
{current_params_text}
```

## Parameter constraints (SKY130A)
| Parameter | Constraint |
|-----------|-----------|
| W  | 0.36 … 99.6 µm, multiple of 0.36 µm, **never exceed 99.6 µm** |
| L  | 0.15 … 2.0 µm |
| Rs | > 0 Ω |
| Cs | 0.1 pF … 10 pF |
| Rd | > 0 Ω |
| Ibias | 0.1 mA … 5 mA |

## Design intuition
1. **Zero frequency**: `f_z = 1 / (2π·Rs·Cs)` — target ≈ 1–2 GHz for peak at Nyquist.
2. **Boost magnitude**: ≈ `20·log10(1 + gm·Rs)`. Increase Rs to raise boost; decrease Rs to lower it.
3. **DC gain**: `|Av| ≈ gm·Rd`. Adjust Rd to shift overall level without changing boost shape.
4. **HD3**: larger W/L and moderate overdrive improves linearity. Increasing Ibias also helps.
5. **Power**: `P ≈ 2·Ibias·1.8`. Must stay under 15 mW.

## Instructions

You are optimizing the CTLE over only 5 iterations.

For this iteration:
1. Analyze the frequency-response plot and simulation metrics.
2. Identify the most important problems.
3. Choose concrete parameter changes that improve the design.
4. Prefer small, targeted changes rather than changing every parameter.
5. The SPICE simulation results are authoritative; the equations above are
   only approximate design intuition.
6. Respect ALL parameter constraints.

Output the complete updated `params.py` in exactly ONE ```python``` block.

Keep the exact same file structure, imports, dataclass, and field names.
Only change the numeric default values.
Do not add comments inside the dataclass.
"""

    image_b64 = encode_image(plot_path)

    print(f"[llm_optimizer] Iteration {iteration}: sending plot + metrics to Claude…")

    response = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=2048,
        system=system,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": image_b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": user_text,
                    },
                ],
            }
        ],
    )

    reply = response.content[0].text

    print(f"\n── Claude (iteration {iteration}) ──────────────────────────────────────────")
    print(reply)
    print("───────────────────────────────────────────────────────────────────────────\n")

    return reply


def run():
    PLOTS_DIR.mkdir(exist_ok=True)

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
        plot_path = PLOTS_DIR / f"iter_{iteration:02d}_freq_response.png"

        print("[llm_optimizer] Running frequency_response()…")
        freq_metrics = frequency_response(**kwargs, save_path=plot_path)

        print("[llm_optimizer] Running hd3_analysis()…")
        hd3_db = hd3_analysis(**kwargs)
        print(f"HD3 @ 100 MHz = {hd3_db:.2f} dB  (target < −30 dB)\n")
        
        # ── ask Claude ───────────────────────────────────────────────
        current_params_text = read_file(PARAMS_FILE)
        reply = ask_claude(
            iteration=iteration,
            current_params_text=current_params_text,
            freq_metrics=freq_metrics,
            hd3_db=hd3_db,
            plot_path=plot_path,
        )

        # ── update params.py ─────────────────────────────────────────
        new_params = extract_code_block(reply)
        if new_params is None:
            print(f"[llm_optimizer] WARNING: no ```python block found in iteration {iteration}. "
                  "params.py unchanged, continuing with current values.\n")
            continue

        write_params(new_params)

    print("\n[llm_optimizer] All iterations complete.")
    print(f"Plots saved in: {PLOTS_DIR.resolve()}")
    print(f"Final params:   {PARAMS_FILE.resolve()}")


run()