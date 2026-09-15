import core
globals().update(vars(core))

from dataclasses import dataclass

@dataclass
class CTLEParams_initial:

    W: float = 99.6
    L: float = 0.15

    Rs: float = 50.5
    Cs: float = 3.3e-12

    Rd: float = 80.0
    Ibias: float = 1.25e-3

    dfe_coefficient: float = 1/30.9