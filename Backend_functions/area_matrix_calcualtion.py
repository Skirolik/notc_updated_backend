import math
import numpy as np
import pandas as pd
from typing import Tuple

def _cross_z(a:Tuple[float,float],b:Tuple[float,float])->float:
    return a[0]*b[1]-a[1]*b[0]

def _normalize(v):
    a=np.array(v,float)
    n=np.linalg.norm(a)
    return (0.0,0.0) if n==0 else (a[0]/n,a[1]/n)

def _ray_intersects_segment(ray_p, ray_dir, seg_a, seg_b):
    p = np.array(ray_p, float)
    r = np.array(ray_dir, float)
    q = np.array(seg_a, float)
    s = np.array(seg_b, float) - q

    rxs = _cross_z((r[0], r[1]), (s[0], s[1]))
    if abs(rxs) < 1e-12:
        return (False, np.inf)

    q_p = q - p
    t = _cross_z((q_p[0], q_p[1]), (s[0], s[1])) / rxs
    u = _cross_z((q_p[0], q_p[1]), (r[0], r[1])) / rxs

    if t >= 1e-9 and (u >= -1e-9 and u <= 1 + 1e-9):
        return (True, float(t))
    return (False, np.inf)

def make_area_matrix(base_tilt_deg:float=0.0,samples_per_cell:int=500,verbose:bool=True)->pd.DataFrame:
    keep_albedo_cells={"C8","C1"}

    raw = [
        ("C8", 112.6, 113.91, 0.00, 1.31, 0.00, 90.0),
        ("C1", 112.6, 0.00, 114.23, 0.00, 1.63, 0.0),
        ("C4", 43.2, 97.91, 102.41, 55.46, 87.63, 72.0),
        ("C6", 47.8, 100.55, 48.51, 55.10, 33.73, 72.0),
        ("C5", 37.0, 104.80, 70.44, 69.59, 81.84, 108.0),
        ("C7", 37.0, 104.07, 16.45, 68.87, 27.84, 108.0),
        ("C3", 32.4, 59.95, 60.05, 32.82, 77.77, 123.0),
        ("C2", 32.4, 46.73, 108.48, 19.49, 90.94, 57.0),
    ]
    df = pd.DataFrame(raw, columns=[
        "Cell", "Width_mm", "Y_top", "X_top", "Y_bottom", "X_bottom", "Angle_deg"
    ])

    th = math.radians(base_tilt_deg)
    R = np.array([[math.cos(th), -math.sin(th)],
                  [math.sin(th), math.cos(th)]])

    def rot(x,y):
        v = R @np.array([x,y],float)
        return float(v[0]),float(v[1])

    df["X_top_r"], df["Y_top_r"] = zip(*[rot(x, y) for x, y in zip(df["X_top"], df["Y_top"])])
    df["X_bot_r"], df["Y_bot_r"] = zip(*[rot(x, y) for x, y in zip(df["X_bottom"], df["Y_bottom"])])

    # STC sun: global downward; rays toward sun go upward
    light_dir = _normalize((0.0, -1.0))
    ray_to_sun = _normalize((-light_dir[0], -light_dir[1]))

    segments = [((r.X_top_r, r.Y_top_r), (r.X_bot_r, r.Y_bot_r)) for _, r in df.iterrows()]

    rows = []

    for i, r in df.iterrows():
        a = (r.X_top_r, r.Y_top_r)
        b = (r.X_bot_r, r.Y_bot_r)

        seg_vec = (b[0] - a[0], b[1] - a[1])
        seg_len = math.hypot(seg_vec[0], seg_vec[1])
        tan_u = (0.0, 0.0) if seg_len == 0 else (seg_vec[0] / seg_len, seg_vec[1] / seg_len)

        normal = (-tan_u[1], tan_u[0])
        dot_n = normal[0] * light_dir[0] + normal[1] * light_dir[1]
        cos_i = max(0.0, min(1.0, abs(dot_n)))

        beam_visible_count = 0

        for s in range(samples_per_cell):
            t = (s + 0.5) / samples_per_cell
            pt = (
                a[0] + (b[0] - a[0]) * t,
                a[1] + (b[1] - a[1]) * t
            )
            blocked = False
            for j, seg in enumerate(segments):
                if j == i:
                    continue
                hit, _ = _ray_intersects_segment(pt, ray_to_sun, seg[0], seg[1])
                if hit:
                    blocked = True
                    break
            if not blocked:
                beam_visible_count += 1
        f_direct = beam_visible_count / samples_per_cell
        print('f_direct:', f_direct)
        f_shaded = 1.0 - f_direct

        A_front = r.Width_mm * 182.0
        A_back = A_front

        if r.Cell in keep_albedo_cells:
            rear_area = A_back
            rear_area_2 = 0.0
        else:
            rear_area_2 = A_back
            rear_area = 0.0

        rows.append({
            "Cell": r.Cell,
            "Direct_Area_mm2": round(f_direct * A_front, 3),
            "Shaded_Area_mm2": round(f_shaded * A_front, 3),
            "Rear_Area_mm2": round(rear_area, 3),
            "Rear_Area_2": round(rear_area_2, 3),
            "TwoSided_Total_Area_mm2": round(A_front + A_back, 3),
            "Cosine": round(cos_i, 4),
        })
    out = pd.DataFrame(rows)

    if verbose:
        print("\n--Area Matrix (binary beam shading)---")
        print(out.to_string(index=False))
    return out
