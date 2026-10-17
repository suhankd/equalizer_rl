def generate_cml_latch_netlist(
    subckt_name="cml_latch",
    w_input=5,
    nf_input=5,
    w_latch=4,
    nf_latch=4,
    w_clk=5,
    nf_clk=5,
    res_w="1.41u",
    res_l="4.4u",
    i_tail="300u",
):
    
    fet_model = "sky130_fd_pr__nfet_01v8"
    fet_params = (
        "L=0.15 ad='int((nf+1)/2) * W/nf * 0.29' as='int((nf+2)/2) * W/nf * 0.29' "
        "pd='2*int((nf+1)/2) * (W/nf + 0.29)' ps='2*int((nf+2)/2) * (W/nf + 0.29)' "
        "nrd='0.29 / W' nrs='0.29 / W' sa=0 sb=0 sd=0 mult=1 m=1"
    )

    return f"""* SkyWater 130nm CML Latch Subcircuit
.subckt {subckt_name} inp inn outp outn ck ckb vdd

* Tracking Stage (Input Pair)
XM1 outp inp net1 GND {fet_model} W={w_input} nf={nf_input} {fet_params}
XM7 outn inn net1 GND {fet_model} W={w_input} nf={nf_input} {fet_params}
XM3 net1 ck net1b GND {fet_model} W={w_clk} nf={nf_clk} {fet_params}

* Latching Stage (Cross-Coupled Pair)
XM4 outp outn net7 GND {fet_model} W={w_latch} nf={nf_latch} {fet_params}
XM5 outn outp net7 GND {fet_model} W={w_latch} nf={nf_latch} {fet_params}
XM6 net7 ckb net7b GND {fet_model} W={w_clk} nf={nf_clk} {fet_params}

* Poly Load Resistors
XR1 outn vdd GND sky130_fd_pr__res_high_po W={res_w} L={res_l} mult=1 m=1
XR2 outp vdd GND sky130_fd_pr__res_high_po W={res_w} L={res_l} mult=1 m=1

* Tail Current Sources
Itail1 net1b GND {i_tail}
Itail2 net7b GND {i_tail}

.ends {subckt_name}
"""
