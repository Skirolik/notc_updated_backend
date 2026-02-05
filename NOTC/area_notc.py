import math
import numpy as np
import pandas as pd
from numba import njit

@njit(cache=True)
def _cross_z(a0, a1, b0, b1):
    return a0 * b1 - a1 * b0

@njit(cache=True)
def _normalize2(v0, v1):
    n = math.sqrt(v0*v0 + v1*v1)
    if n == 0.0:
        return 0.0, 0.0
    return v0 / n, v1 / n

@njit(cache=True)
def _ray_intersects_segment(px, pz, rx, rz, ax, az, bx, bz):
    sx = bx - ax
    sz = bz - az
    rxs = _cross_z(rx, rz, sx, sz)
    if abs(rxs) < 1e-12:
        return False
    qpx = ax - px
    qpz = az - pz
    t = _cross_z(qpx, qpz, sx, sz) / rxs
    u = _cross_z(qpx, qpz, rx, rz) / rxs
    return (t >= 1e-9) and (0.0 <= u <= 1.0)

RAW_CELLS = np.array([
    [113.91, 0.00, 1.31, 0.00, 112.6],
    [0.00, 114.23, 0.00, 1.63, 112.6],
    [97.91, 102.41, 55.46, 87.63, 43.2],
    [100.55, 48.51, 55.10, 33.73, 47.8],
    [104.80, 70.44, 69.59, 81.84, 37.0],
    [104.07, 16.45, 68.87, 27.84, 37.0],
    [59.95, 60.05, 32.82, 77.77, 32.4],
    [46.73, 108.48, 19.49, 90.94, 32.4],
])

CELL_NAMES = [
    "C8", "C1", "C4", "C6",
    "C5", "C7",
    "C3", "C2"
]

KEEP_ALBEDO = [True, True, False, False, False, False, False, False]

def make_area_matrix_fast(zen_deg, azi_deg, tilt_deg, module_azimuth_deg, samples=120):
    zen = math.radians(zen_deg)
    azi = math.radians(azi_deg)

    sx = math.sin(zen) * math.sin(azi)
    sy = math.sin(zen) * math.cos(azi)
    sz = math.cos(zen)

    am = math.radians(module_azimuth_deg)
    sun_h = sx * math.sin(am) + sy * math.cos(am)

    rx, rz = _normalize2(-sun_h, -sz)
    lx, lz = -rx, -rz

    th = math.radians(tilt_deg)
    Yt, Xt, Yb, Xb, W = RAW_CELLS.T

    c, s = math.cos(th), math.sin(th)
    Xtr, Ytr = c*Xt - s*Yt, s*Xt + c*Yt
    Xbr, Ybr = c*Xb - s*Yb, s*Xb + c*Yb

    dx, dz = Xbr - Xtr, Ybr - Ytr
    L = np.sqrt(dx*dx + dz*dz) + 1e-12
    nx, nz = -(dz/L), (dx/L)

    cos_i = np.clip(np.abs(nx*lx + nz*lz), 0, 1)

    shade0 = np.zeros(8)
    Ax, Az, Bx, Bz = Xtr, Ytr, Xbr, Ybr

    for i in range(8):
        ts = (np.arange(samples)+0.5)/samples
        px = Ax[i] + (Bx[i]-Ax[i])*ts
        pz = Az[i] + (Bz[i]-Az[i])*ts
        visible = 0
        for k in range(samples):
            blocked = False
            for j in range(8):
                if j == i: continue
                if _ray_intersects_segment(px[k], pz[k], -rx, -rz,
                                           Ax[j], Az[j], Bx[j], Bz[j]):
                    blocked = True
                    break
            if not blocked:
                visible += 1
        shade0[i] = visible / samples

    A = W * 182.0

    return pd.DataFrame({
        "Cell": CELL_NAMES,
        "Cosine": cos_i,
        "Direct_Area_mm2": shade0 * A,
        "Shaded_Area_mm2": (1 - shade0) * A,
        "Rear_Area_mm2": np.where(KEEP_ALBEDO, A, 0),
        "Rear_Area_2": np.where(~np.array(KEEP_ALBEDO), A, 0),
    })