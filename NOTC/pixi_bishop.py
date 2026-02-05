from scipy.optimize import fsolve
from typing import Dict
import numpy as np
import pandas as pd



def bishop2(area_df, illum,Temp,dni):
    T_cell=(Temp+10) + (43-20)* (dni/800)
    beta=0.7
    q=1.602e-19
    k=1.381e-23
    T=T_cell+273.15

    Vt=k*T/q
    n=1.2
    Voc=0.763
    ref_cm2=(182*182)/100.0
    Jph_1000=13.857/ref_cm2

    mat = pd.merge(area_df, illum, on="Cell", how="inner")

    Iph_map={}
    I0_map={}

    print("\n--- PER-CELL INPUTS (bishop2) ---")
    for _,r in mat.iterrows():
        name=r["Cell"]
        A=lambda k:float(r[k])/100.0

        Ad, As, Ar, Ar2 = (
            A("Direct_Area_mm2"),
            A("Shaded_Area_mm2"),
            A("Rear_Area_mm2"),
            A("Rear_Area_2"),
        )

        Gd, Gs, Gr, Gr2 = (
            r["Direct_Wm2"],
            r["Shaded_Wm2"],
            r["Rear_Wm2"],
            r["Rear2_Wm2"],
        )

        Iph = (
                Jph_1000
                * (
                        Ad * (Gd / 1000)
                        + As * (Gs / 1000)
                        + beta * Ar * (Gr / 1000)
                        + Ar2 * beta * (Gr2 / 1000)
                )
                * 1
        )
        area_cm2_total = Ad + As + Ar + Ar2
        I0 = 1e-12 * max(area_cm2_total, 1e-6)

        Iph_map[name] = Iph
        I0_map[name] = I0

    V = np.linspace(0, Voc, 400)

    # Continue solver (unchanged)
    V=np.linspace(0,Voc,500)
    def diode_eq(I, V, Iph, I0, Rs, Rsh):
        return I - (Iph - I0*(np.exp((V + I*Rs)/(n*Vt)) - 1) - (V + I*Rs)/Rsh)

    I_total=[]
    for v in V:
        row=[]
        for name in Iph_map:
            try:
                I = fsolve(diode_eq, Iph_map[name],
                           args=(v, Iph_map[name], I0_map[name], 0.015,2282),
                           xtol=1e-8, maxfev=200)[0]
                row.append(max(I,0))
            except:
                row.append(0)
        I_total.append(sum(row))

    I_total=np.array(I_total)
    idx=int(np.argmax(I_total*V))

    # base single-cell outputs
    Isc_single = float(I_total[0])
    Imp_single = float(I_total[idx])
    Vmp_single = float(V[idx])
    Pmax_single = float(I_total[idx] * V[idx])
    FF_single = float((V[idx] * I_total[idx]) / (Voc * I_total[0] if I_total[0] != 0 else 1e-12))

    # scale for series cells: Voc, Vmp and Pmax scaled up to represent cells in series
    Voc_scaled = float(Voc * 5)
    Vmp_scaled = float(Vmp_single * 5)
    Pmax_scaled = float(Pmax_single * 5)

    return {
        "Isc": Isc_single,
        "Imp": Imp_single,
        "Vmp": Vmp_scaled,
        "Pmax": Pmax_scaled,
        "FF": FF_single,
        "Voc": Voc_scaled,
    }
