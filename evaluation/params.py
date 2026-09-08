# evaluation/params.py

from dataclasses import dataclass


@dataclass
class CTLEParams:

    W: float = 99.6
    L: float = 0.15

    Rs: float = 50.5
    Cs: float = 3.3e-12

    Rd: float = 80
    Ibias: float = 1.25e-3