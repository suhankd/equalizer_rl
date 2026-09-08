from dataclasses import dataclass

@dataclass

class ctle_specs:

    data_rate = 5e9
    nyquist = 2.5e9
    bit_period = 1 / data_rate

    boost_min_db = 3.0
    boost_max_db = 12.0

    peak_freq_min = 1.25e9
    peak_freq_max = 2.5e9

    noise_max = 1.5e-3
    noise_fmin = 10e6
    noise_fmax = 5e9

    hd3_max_db = -30.0
    hd3_frequency = 100e6

    power_max = 15e-3

    area_max = 0.05 # mm^2

    eye_width_min = 0.4
    eye_height_min = 100e-3

    temp_min = 0
    temp_max = 125

    vdd_nominal = 1.8
    vdd_tolerance = 0.05