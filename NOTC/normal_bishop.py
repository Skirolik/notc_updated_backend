import numpy as np
from scipy.optimize import fsolve
from typing import Dict
import pandas as pd




def bishop_module1_performance(avg_wm2: float, temp_c: float,dni, n_cells: int = 5):
    """Module 1 performance with number of series cells for monthly energy calculation."""

    T_cell = temp_c + (43 - 20) * (dni / 800)

    q = 1.602e-19
    k = 1.381e-23
    T = float(T_cell) + 273.15
    Vt = k * T / q
    n = 1.2
    ref_cm2 = (182 * 182) / 100.0
    Jph1000 = 13.857 / ref_cm2

    cells = {"Base": (182 * 182) / 100.0}
    G_full = max(float(avg_wm2), 1.0)

    Iph_segments, Rs_segments, Rsh_segments, I0_segments = [], [], [], []
    for cell, area_cm2 in cells.items():
        G = G_full
        Iph = Jph1000 * (G / 1000.0) * area_cm2
        print('2D IPH',Iph)
        Rs = 0.0062
        Rsh = 2082
        I0 = 1e-12 * area_cm2
        Iph_segments.append(Iph)
        Rs_segments.append(Rs)
        Rsh_segments.append(Rsh)
        I0_segments.append(I0)

    V = np.linspace(0, 0.763, 500)
    I_total = []

    def diode_eq(I, V, Iph, I0, Rs, Rsh, n, Vt):
        return I - (Iph - I0 * (np.exp((V + I * Rs) / (n * Vt)) - 1.0) - (V + I * Rs) / Rsh)

    for v in V:
        I_cells = []
        for Iph, I0, Rs, Rsh in zip(Iph_segments, I0_segments, Rs_segments, Rsh_segments):
            guess = Iph
            I_sol = fsolve(diode_eq, guess, args=(v, Iph, I0, Rs, Rsh, n, Vt))[0]
            I_cells.append(max(float(I_sol), 0.0))
        I_total.append(sum(I_cells))

    I_total = np.array(I_total)
    P = V * I_total
    Pmax = float(np.max(P))
    idx = int(np.argmax(P))
    Vmp, Imp = float(V[idx]), float(I_total[idx])
    Isc = float(I_total[0])
    Voc = 0.763
    FF = (Vmp * Imp) / (Voc * Isc) if (Voc * Isc) > 0 else 0.0

    ## series values:
    Imp_series = Imp
    Isc_seris = Isc
    Voc_series = Voc * n_cells
    Vmp_series = Vmp * n_cells
    Pmax_series = (Vmp_series * Imp_series)
    FF_series = (Pmax_series) / (Isc_seris * Voc_series)

    return {"Isc": round(Isc, 2),"Imp": round(Imp, 2),
             "Pmax": round(Pmax, 4), "FF": round(FF, 4),
            "Pmax_series": round(Pmax_series, 4),
            "Vmp_series": round(Vmp_series, 4), "Voc_series": round(Voc_series, 4), "FF_series": round(FF_series, 2)}