from scipy.optimize import fsolve
from typing import Dict
import numpy as np
import pandas as pd

def bishop_from_matrices(
    area_df: pd.DataFrame,
    illum_df: pd.DataFrame,
    temp_c: float = 25.0,
    n_cells_series: int = 5,
    Rs_map: Dict[str, float] = None,
    Rsh_map: Dict[str, float] = None,
    label: str = "Pixolar",          # 🔴 LABEL ADDED
) -> Dict:

    mat = pd.merge(area_df, illum_df, on="Cell", how="inner")

    if Rs_map is None:
        Rs_map = {c: 0.0022 for c in mat["Cell"].unique()}
    if Rsh_map is None:
        Rsh_map = {c: 2082.0 for c in mat["Cell"].unique()}

    q = 1.602e-19
    k = 1.381e-23
    T = temp_c + 273.15
    Vt = k * T / q
    n = 1.2
    Voc = 0.729

    ref_cell_area_cm2 = (182 * 182) / 100.0
    Jph_1000 = 13.857 / ref_cell_area_cm2
    beta = 0.7

    Iph_map = {}
    I0_map = {}

    for _, r in mat.iterrows():
        name = r["Cell"]
        A = lambda key: float(r[key]) / 100.0

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

        Iph = Jph_1000 * (
            Ad * (Gd / 1000)
            + As * (Gs / 1000)
            + beta * Ar * (Gr / 1000)
            + Ar2 * beta * (Gr2 / 1000)
        )

        area_cm2_total = Ad + As + Ar + Ar2
        I0 = 1e-12 * max(area_cm2_total, 1e-6)

        Iph_map[name] = Iph
        I0_map[name] = I0

    V = np.linspace(0, Voc, 400)

    def diode_eq(I, V, Iph, I0, Rs, Rsh):
        return I - (
            Iph
            - I0 * (np.exp((V + I * Rs) / (n * Vt)) - 1)
            - (V + I * Rs) / Rsh
        )

    I_tot = []
    for v in V:
        I_cells = []
        for name in Iph_map:
            try:
                Is = fsolve(
                    diode_eq,
                    Iph_map[name],
                    args=(v, Iph_map[name], I0_map[name],
                          Rs_map[name], Rsh_map[name]),
                    xtol=1e-8,
                    maxfev=200,
                )[0]
                I_cells.append(max(Is, 0))
            except:
                I_cells.append(0)
        I_tot.append(sum(I_cells))

    I_tot = np.array(I_tot)
    P = I_tot * V
    idx = int(np.argmax(P))

    Isc = float(I_tot[0])
    Imp = float(I_tot[idx])
    Vmp = float(V[idx])
    FF = (Vmp * Imp) / (Voc * Isc) if Isc > 0 else 0.0

    # 🔥 EXACT OLD RETURN — NOTHING DIFFERENT
    return {
        f"Isc_{label}": Isc,
        f"Voc_{label}": Voc,
        f"Vmp_{label}": Vmp,
        f"Imp_{label}": Imp,
        f"FF_{label}": FF,
        f"Voc_series_{label}": Voc * n_cells_series,
        f"Vmp_series_{label}": Vmp * n_cells_series,
        f"Pmax_series_{label}": Vmp * n_cells_series * Imp,
        f"iv_curve_{label}": {
            "voltage": [round(v, 3) for v in V],
            "current": [round(i, 3) for i in I_tot],
        },
    }