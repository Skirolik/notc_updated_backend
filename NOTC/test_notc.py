from NOTC.tilt_analysis import run_sim_analytic_best_tilt,run_sim_analytic_fixed_tilt
import pandas as pd

result = run_sim_analytic_fixed_tilt(
    lat=12.9716,
    lon=77.5945,
    fixed_tilt_3d=31,
    alpha_rear=0.3657
)

df = pd.DataFrame(result["data"])
df.to_csv("notc_2d_vs_3d_results.csv", index=False)

print(df.head())

print("Yearly 2D Energy:", result["yearly_totals"]["Pmax_2D_total"])
print("Yearly 3D Energy:", result["yearly_totals"]["Pmax_3D_total"])