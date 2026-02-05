
import pandas as pd
import numpy as np

def apply_notc_irradiacne(area, dni, dhi,ghi,alpha_rear):
    cosi = area["Cosine"].to_numpy(float)
    n = len(area)

    return pd.DataFrame({
        "Cell": area["Cell"].to_numpy(),

        # Front
        "Direct_Wm2": dni * cosi,
        "Shaded_Wm2": np.full(n, dhi),

        # Rear: orientation-aware diffuse pickup
        "Rear_Wm2":  alpha_rear*ghi,
        "Rear2_Wm2": dhi,
    })