import math
import pandas as pd
import pvlib

from NOTC.area_notc import make_area_matrix_fast
from NOTC.illuminiation_notc import apply_notc_irradiacne
from NOTC.normal_bishop import bishop_module1_performance
from NOTC.pixi_bishop import bishop2

print("IMPORTING tilt_analysis")
# ------------------------------------------------------------------
# TIMEZONE
# ------------------------------------------------------------------
def infer_timezone(lat, lon, fallback="UTC"):
    try:
        from timezonefinder import TimezoneFinder
        tf = TimezoneFinder()
        return tf.timezone_at(lat=float(lat), lng=float(lon)) or fallback
    except Exception:
        return fallback


# ------------------------------------------------------------------
# SOLAR DATA
# ------------------------------------------------------------------
def site_sun_and_clearsky_batch(lat, lon, time_utc, tz_str):
    solpos = pvlib.solarposition.get_solarposition(time_utc, lat, lon)
    zen = solpos["apparent_zenith"].to_numpy(float)
    azi = solpos["azimuth"].to_numpy(float)

    loc = pvlib.location.Location(lat, lon, tz_str)
    cs = loc.get_clearsky(time_utc)

    return (
        zen,
        azi,
        cs["dni"].to_numpy(float),
        cs["dhi"].to_numpy(float),
        cs["ghi"].to_numpy(float),
    )


# ------------------------------------------------------------------
# ANALYTIC BEST TILT (2D)
# ------------------------------------------------------------------
def analytic_best_tilt_deg(solar_zen_deg, solar_azi_deg, module_azimuth_deg):
    if solar_zen_deg >= 90:
        return 0.0
    zen = math.radians(solar_zen_deg)
    delta = math.radians(solar_azi_deg - module_azimuth_deg)
    return abs(math.degrees(math.atan(math.tan(zen) * math.cos(delta))))


# ------------------------------------------------------------------
# 2D IRRADIANCE (UNCHANGED PHYSICS)
# ------------------------------------------------------------------
def compute_2d_irradiance(
    dni, dhi,ghi,
    zen, tilt, sun_azi, mod_az,
    alpha_ground,
    beta=0.7
):
    zen_r = math.radians(zen)
    tilt_r = math.radians(tilt)
    sun_azi_r = math.radians(sun_azi)
    mod_az_r = math.radians(mod_az)

    cos_theta = (
        math.cos(zen_r) * math.cos(tilt_r)
        + math.sin(zen_r) * math.sin(tilt_r)
        * math.cos(sun_azi_r - mod_az_r)
    )
    cos_theta = max(cos_theta, 0.0)

    # Front-side
    G_direct = dni * cos_theta
    G_diffuse = dhi

    # ✅ Albedo from diffuse ONLY
    G_albedo = beta * alpha_ground * ghi * (1 - math.cos(tilt_r)) / 2

    return G_direct + G_diffuse + G_albedo


# ------------------------------------------------------------------
# MAIN DRIVER — BEST 2D vs BEST 3D
# ------------------------------------------------------------------
def run_sim_analytic_best_tilt(
    lat,
    lon,
    alpha_rear,
    year=2024,
    months=range(1, 13),
    hours=range(9, 17),
    samples=120,
):
    from collections import defaultdict

    tz = infer_timezone(lat, lon)
    mod_az = 180.0 if lat >= 0 else 0.0

    # timestamps
    t_local = pd.DatetimeIndex(
        [pd.Timestamp(f"{year}-{m:02d}-21 {h:02d}:00", tz=tz)
         for m in months for h in hours]
    )
    t_utc = t_local.tz_convert("UTC")

    # ---------------- TEMPERATURE (EXACT OLD LOGIC) ----------------
    try:
        tmy, _ = pvlib.iotools.get_pvgis_tmy(lat, lon)
        tmy_year = tmy.index[0].year
        tmy.index = tmy.index.tz_convert(tz)

        t_local_tmy = t_local.map(lambda ts: ts.replace(year=tmy_year))
        temp_air = pd.Series(
            tmy["temp_air"].reindex(t_local_tmy, method="nearest").values,
            index=t_local
        )
    except Exception:
        temp_air = pd.Series(45.0, index=t_local)

    zen, azi, dni, dhi, ghi = site_sun_and_clearsky_batch(lat, lon, t_utc, tz)

    records = []
    monthly_sums = defaultdict(lambda: defaultdict(float))
    monthly_counts = defaultdict(int)

    total_pmax_2d = 0.0
    total_pmax_3d = 0.0

    # ------------------------------------------------------------------
    # MAIN LOOP
    # ------------------------------------------------------------------
    for i in range(len(t_utc)):
        if zen[i] >= 90:
            continue

        T_amb = float(temp_air.iloc[i])
        month = t_local[i].strftime("%b")

        # =========================
        # 2D — BEST TILT (ANALYTIC)
        # =========================
        best_tilt_2d = analytic_best_tilt_deg(zen[i], azi[i], mod_az)

        G2D = compute_2d_irradiance(
            dni[i], dhi[i], ghi[i],
            zen[i], best_tilt_2d, azi[i], mod_az,
            alpha_rear
        )
        out_2d = bishop_module1_performance(G2D, T_amb, dni[i], n_cells=5)

        # =========================
        # 3D — BEST TILT (SWEEP)
        # =========================
        best_pmax_3d = -1.0
        best_tilt_3d = 0.0
        best_out_3d = None

        for tilt in range(0, 61, 5):
            area = make_area_matrix_fast(zen[i], azi[i], tilt, mod_az, samples)
            illum = apply_notc_irradiacne(area, dni[i], dhi[i],alpha_rear,ghi[i])
            out = bishop2(area, illum, T_amb, dni[i])

            if out["Pmax"] > best_pmax_3d:
                best_pmax_3d = out["Pmax"]
                best_tilt_3d = tilt
                best_out_3d = out

        out_3d = best_out_3d

        pmax_2d = out_2d["Pmax_series"]
        pmax_3d = out_3d["Pmax"]

        total_pmax_2d += pmax_2d
        total_pmax_3d += pmax_3d

        rec = {
            "timestamp_local": str(t_local[i]),
            "timestamp_utc": str(t_utc[i]),
            "month": month,
            "zen": float(zen[i]),
            "azi": float(azi[i]),
            "dni": float(dni[i]),
            "dhi": float(dhi[i]),
            "ghi": float(ghi[i]),
            "T_ambient": T_amb,

            # 2D
            "tilt_analytic_2D": best_tilt_2d,
            "Isc_2D": out_2d["Isc"],
            "Voc_2D": out_2d["Voc_series"],
            "Imp_2D": out_2d["Imp"],
            "Vmp_2D": out_2d["Vmp_series"],
            "Pmax_2D": pmax_2d,
            "FF_2D": out_2d["FF"],

            # 3D
            "tilt_optimal_3D": best_tilt_3d,
            "Isc_3D": out_3d["Isc"],
            "Imp_3D": out_3d["Imp"],
            "Vmp_3D": out_3d["Vmp"],
            "Voc_3D": out_3d["Voc"],
            "Pmax_3D": pmax_3d,
            "FF_3D": out_3d["FF"],
        }

        records.append(rec)

        for k, v in rec.items():
            if isinstance(v, (int, float)):
                monthly_sums[month][k] += v
        monthly_counts[month] += 1

    # ---------------- MONTHLY AVERAGES ----------------
    # ---------------- MONTHLY OUTPUT (MATCH OLD CONTRACT) ----------------
    monthly_out = {}

    for m, sums in monthly_sums.items():
        cnt = max(monthly_counts[m], 1)

        monthly_out[m] = {
            # totals
            "Pmax_2D_monthly_total": float(sums["Pmax_2D"]),
            "Pmax_3D_monthly_total": float(sums["Pmax_3D"]),

            # averages
            "Isc_2D_monthly_avg": float(sums["Isc_2D"] / cnt),
            "Isc_3D_monthly_avg": float(sums["Isc_3D"] / cnt),
            "Imp_2D_monthly_avg": float(sums["Imp_2D"] / cnt),
            "Imp_3D_monthly_avg": float(sums["Imp_3D"] / cnt),
            "Vmp_2D_monthly_avg": float(sums["Vmp_2D"] / cnt),
            "Vmp_3D_monthly_avg": float(sums["Vmp_3D"] / cnt),
            "tilt_analytic_2D_monthly_avg": float(sums["tilt_analytic_2D"] / cnt),
            "tilt_optimal_3D_monthly_avg": float(sums["tilt_optimal_3D"] / cnt),
            "FF_2D_monthly_avg": float(sums["FF_2D"] / cnt),
            "FF_3D_monthly_avg": float(sums["FF_3D"] / cnt),

            "count": int(cnt),
        }

    # ---------------- FINAL RETURN (EXACT OLD SHAPE) ----------------
    return {
        "status": "ok",
        "rows": len(records),
        "data": records,  # per-timestamp (unchanged)
        "monthly": monthly_out,  # OLD monthly schema
        "yearly_totals": {
            "Pmax_2D_total": float(total_pmax_2d),
            "Pmax_3D_total": float(total_pmax_3d),
        },
    }


def run_sim_analytic_fixed_tilt(
    lat,
    lon,
    alpha_rear,
    fixed_tilt_3d,          # ✅ USER-PROVIDED BEST 3D TILT
    year=2024,
    months=range(1, 13),
    hours=range(9, 17),
    samples=120,
):
    from collections import defaultdict

    tz = infer_timezone(lat, lon)
    mod_az = 180.0 if lat >= 0 else 0.0

    # timestamps
    t_local = pd.DatetimeIndex(
        [pd.Timestamp(f"{year}-{m:02d}-21 {h:02d}:00", tz=tz)
         for m in months for h in hours]
    )
    t_utc = t_local.tz_convert("UTC")

    # ---------------- TEMPERATURE (UNCHANGED) ----------------
    try:
        tmy, _ = pvlib.iotools.get_pvgis_tmy(lat, lon)
        tmy_year = tmy.index[0].year
        tmy.index = tmy.index.tz_convert(tz)

        t_local_tmy = t_local.map(lambda ts: ts.replace(year=tmy_year))
        temp_air = pd.Series(
            tmy["temp_air"].reindex(t_local_tmy, method="nearest").values,
            index=t_local
        )
    except Exception:
        temp_air = pd.Series(45.0, index=t_local)

    zen, azi, dni, dhi, ghi = site_sun_and_clearsky_batch(lat, lon, t_utc, tz)

    records = []
    monthly_sums = defaultdict(lambda: defaultdict(float))
    monthly_counts = defaultdict(int)

    total_pmax_2d = 0.0
    total_pmax_3d = 0.0

    # ---------------- MAIN LOOP ----------------
    for i in range(len(t_utc)):
        if zen[i] >= 90:
            continue

        T_amb = float(temp_air.iloc[i])
        month = t_local[i].strftime("%b")

        # =========================
        # 2D — BEST TILT (ANALYTIC)
        # =========================
        best_tilt_2d = analytic_best_tilt_deg(zen[i], azi[i], mod_az)

        G2D = compute_2d_irradiance(
            dni[i], dhi[i], ghi[i],
            zen[i], best_tilt_2d, azi[i], mod_az,
            alpha_rear
        )
        out_2d = bishop_module1_performance(G2D, T_amb, dni[i], n_cells=5)

        # =========================
        # 3D — FIXED USER TILT
        # =========================
        area = make_area_matrix_fast(
            zen[i], azi[i], fixed_tilt_3d, mod_az, samples
        )
        illum = apply_notc_irradiacne(
            area, dni[i], dhi[i], ghi[i], alpha_rear
        )
        out_3d = bishop2(area, illum, T_amb, dni[i])

        pmax_2d = out_2d["Pmax_series"]
        pmax_3d = out_3d["Pmax"]

        total_pmax_2d += pmax_2d
        total_pmax_3d += pmax_3d

        rec = {
            "timestamp_local": str(t_local[i]),
            "timestamp_utc": str(t_utc[i]),
            "month": month,
            "zen": float(zen[i]),
            "azi": float(azi[i]),
            "dni": float(dni[i]),
            "dhi": float(dhi[i]),
            "ghi": float(ghi[i]),
            "T_ambient": T_amb,

            # 2D
            "tilt_analytic_2D": best_tilt_2d,
            "Isc_2D": out_2d["Isc"],
            "Voc_2D": out_2d["Voc_series"],
            "Imp_2D": out_2d["Imp"],
            "Vmp_2D": out_2d["Vmp_series"],
            "Pmax_2D": pmax_2d,
            "FF_2D": out_2d["FF"],

            # 3D
            "tilt_optimal_3D": fixed_tilt_3d,
            "Isc_3D": out_3d["Isc"],
            "Imp_3D": out_3d["Imp"],
            "Vmp_3D": out_3d["Vmp"],
            "Voc_3D": out_3d["Voc"],
            "Pmax_3D": pmax_3d,
            "FF_3D": out_3d["FF"],
        }

        records.append(rec)

        for k, v in rec.items():
            if isinstance(v, (int, float)):
                monthly_sums[month][k] += v
        monthly_counts[month] += 1

    # ---------------- MONTHLY AVERAGES ----------------
    # ---------------- MONTHLY OUTPUT (MATCH OLD CONTRACT) ----------------
    monthly_out = {}

    for m, sums in monthly_sums.items():
        cnt = max(monthly_counts[m], 1)

        monthly_out[m] = {
            # totals
            "Pmax_2D_monthly_total": float(sums["Pmax_2D"]),
            "Pmax_3D_monthly_total": float(sums["Pmax_3D"]),

            # averages
            "Isc_2D_monthly_avg": float(sums["Isc_2D"] / cnt),
            "Isc_3D_monthly_avg": float(sums["Isc_3D"] / cnt),
            "Imp_2D_monthly_avg": float(sums["Imp_2D"] / cnt),
            "Imp_3D_monthly_avg": float(sums["Imp_3D"] / cnt),
            "Vmp_2D_monthly_avg": float(sums["Vmp_2D"] / cnt),
            "Vmp_3D_monthly_avg": float(sums["Vmp_3D"] / cnt),
            "tilt_analytic_2D_monthly_avg": float(sums["tilt_analytic_2D"] / cnt),
            "tilt_optimal_3D_monthly_avg": fixed_tilt_3d,
            "FF_2D_monthly_avg": float(sums["FF_2D"] / cnt),
            "FF_3D_monthly_avg": float(sums["FF_3D"] / cnt),

            "count": int(cnt),
        }

    # ---------------- FINAL RETURN (EXACT OLD SHAPE) ----------------
    return {
        "status": "ok",
        "rows": len(records),
        "data": records,  # per-timestamp (unchanged)
        "monthly": monthly_out,  # OLD monthly schema
        "yearly_totals": {
            "Pmax_2D_total": float(total_pmax_2d),
            "Pmax_3D_total": float(total_pmax_3d),
        },
    }