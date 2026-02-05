import numpy as np
import pandas as pd

from Backend_functions.area_matrix_calcualtion import make_area_matrix
from Backend_functions.bishops_equation import bishop_from_matrices
from Backend_functions.illumination_matrix import make_illumination_matrix
from Backend_functions.irradance_cal import LightField

G_dir=1000
G_albedo=135.0
n=0.1125


tilt=[0,5,10,15,20,25,30,35,40,45,50,55,60,65,70,75,80,85,90,95,100]

for angle in tilt:
    print('angle',angle)
    area_df = make_area_matrix(base_tilt_deg=angle, samples_per_cell=500, verbose=False)

    lf = LightField(G_dir, G_albedo, n).compute()

    illum_df = make_illumination_matrix(area_df, lf.G_dir, lf.G_diff, lf.G_albedo, verbose=False)

    bishop_out = bishop_from_matrices(area_df=area_df, illum_df=illum_df, temp_c=25.0, n_cells_series=5)

    print(bishop_out)