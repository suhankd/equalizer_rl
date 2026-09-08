import os
import re
from pathlib import Path

from anthropic import Anthropic


PARAMS_FILE = Path("evaluation/params.py")
SPECS_FILE  = Path("evaluation/specs.py")


def read_file(path: Path) -> str:
    return path.read_text()


def write_params(new_content: str):
    PARAMS_FILE.write_text(new_content)
    print("\n[llm_optimizer] params.py updated.")


def extract_code_block(text: str) -> str | None:
    """Pull the first ```python ... ``` block out of the LLM reply."""
    match = re.search(r"```python\s*(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return None


def ask_claude() -> str:
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    current_params = read_file(PARAMS_FILE)
    specs          = read_file(SPECS_FILE)

    system = (
        "You are an expert analog IC designer specialising in CMOS equaliser circuits "
        "for high-speed serial links.  Your job is to propose improved design parameters "
        "for a Continuous-Time Linear Equaliser (CTLE) implemented in the SKY130A process."
    )

    user = f"""
## Task
You are given the current `params.py` for a CTLE that targets a **5 Gb/s NRZ** receiver.

The six tunable parameters are:

| Parameter | Meaning                          | Typical constraints (SKY130A)          |
|-----------|----------------------------------|----------------------------------------|
| W         | NMOS differential pair width (µm)| 0.36 … 200 µm, must be a multiple of 0.36 µm |
| L         | NMOS gate length (µm)            | 0.15 µm (minimum) … 2 µm              |
| Rs        | Source-degeneration resistance (Ω)| > 0                                   |
| Cs        | Source-degeneration capacitor (F) | > 0, typically 0.1 pF … 10 pF         |
| Rd        | Drain load resistance (Ω)        | > 0                                    |
| Ibias     | Tail bias current *per side* (A) | typically 0.1 mA … 5 mA               |

## Design targets (from `specs.py`)

```python
{specs}
```

## Current parameters (from `params.py`)

```python
{current_params}
```

## Design intuition to guide your reasoning

1. **Boost & bandwidth**: The zero frequency of the CTLE is  
   `f_z = 1 / (2π · Rs · Cs)`.  For a boost that peaks around **2–2.5 GHz** (Nyquist),  
   target `f_z ≈ 1 – 2 GHz`.  Increasing Rs or Cs shifts the zero lower.

2. **DC gain**: `|A_v| ≈ gm · Rd` where `gm ≈ √(2 · μn·Cox · (W/L) · Id)`.  
   Larger W or smaller L increases gm.

3. **Power**: `P ≈ 2 · Ibias · Vdd` (two tail sources, Vdd = 1.8 V).  
   Must stay < {15e-3*1000:.0f} mW.

4. **Harmonic distortion (HD3)**: Keep W large relative to overdrive; higher Ibias helps  
   push HD3 below **{-30} dB** at 100 MHz.

5. **Noise**: Larger W lowers thermal noise; lower Rs reduces noise figure.

## Instructions

1. Analyse each current parameter value against the targets above.
2. Reason step-by-step (show your working) about what should change and why.
3. Propose a new set of parameter values that better meet the specs.
4. Output the **complete, updated `params.py`** in a single ```python … ``` code block.
   - Keep exactly the same file structure (imports, dataclass, field names).
   - Only change the default values of the six fields.
   - Do **not** add comments inside the dataclass body.
"""

    print("[llm_optimizer] Sending params.py to Claude for analysis…")

    response = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=2048,
        system=system,
        messages=[{"role": "user", "content": user}],
    )

    reply = response.content[0].text

    print("\n── Claude's analysis ──────────────────────────────────────────────────────")
    print(reply)
    print("───────────────────────────────────────────────────────────────────────────\n")

    return reply


def run():
    reply = ask_claude()

    new_params = extract_code_block(reply)
    if new_params is None:
        print("[llm_optimizer] WARNING: no ```python block found in response. params.py unchanged.")
        return

    write_params(new_params)


if __name__ == "__main__":
    run()