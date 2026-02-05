from Backend_functions.area_matrix_calcualtion import make_area_matrix
from Backend_functions.bishops_equation import bishop_from_matrices
from Backend_functions.illumination_matrix import make_illumination_matrix
from Backend_functions.irradance_cal import LightField

from NOTC.tilt_analysis import run_sim_analytic_best_tilt, run_sim_analytic_fixed_tilt
import traceback
from flask import jsonify


def notc_best_angle(data):
    try:
        lat=float(data.get("lat"))
        lon=float(data.get("lon"))
        df=run_sim_analytic_best_tilt(lat=lat,lon=lon,alpha_rear=0.3657,samples=80)
        print('df',df)
        return df
    except Exception as e:
        print('error',e)
        return jsonify({
            "status": "error",
            "message": str(e),
            "trace": traceback.format_exc()
        })

def stc_calc_update(data):
    try:
        irradiance=data.get("irradiance")
        tilt = [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 100]
        albedo=data.get("albedo")
        n=0.1125
        result=[]
        for angle in tilt:
            area_df=make_area_matrix(base_tilt_deg=angle,samples_per_cell=200,verbose=False)
            lf=LightField(G_dir=irradiance,G_albedo=albedo,n=n).compute()
            illum=make_illumination_matrix(area_df,lf.G_dir,lf.G_diff,lf.G_albedo,verbose=False)

            out=bishop_from_matrices(area_df=area_df,illum_df=illum,temp_c=25.0,n_cells_series=5)

            safe_out={}
            for k,v in out.items():
                if isinstance(v,(int,float)):
                    safe_out[k]=round(v,4)
                else:
                    safe_out[k]=v

            result.append({"Tilt_deg":angle,**safe_out})
        return jsonify({"success":True,"result":result}),200
    except Exception as e:
        return jsonify({"success":False,"message":str(e)}),400

def notc_without_tracker(data):
    try:
        lat=float(data.get("lat"))
        lon=float(data.get("lon"))
        df=run_sim_analytic_fixed_tilt(lat=lat,lon=lon,alpha_rear=0.3657,samples=80,fixed_tilt_3d=31.0)
        print('df',df)
        return df
    except Exception as e:
        print('error',e)
        return jsonify({
            "status": "error",
            "message": str(e),
            "trace": traceback.format_exc()
        })
