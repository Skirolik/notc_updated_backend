import pandas as pd


def make_illumination_matrix(area_df:pd.DataFrame,G_dir:float,G_diff:float,G_albedo:float,use_cos_for_direct:bool=True,verbose:bool=True)->pd.DataFrame:
    """
    Illumination Assumptions
    Direct_area:G_dir*cos(theta)+G_diff
    Shaded area: G_diff
    Rear area: G_albedo
    Rear area 2 : G_diff
    """
    rows=[]
    for _,r in area_df.iterrows():
        cosc=float(r["Cosine"])

        direct_Wm2=(G_dir*cosc if use_cos_for_direct else G_dir) + G_diff
        shaded_Wm2=G_diff
        rear_Wm2=G_albedo
        rear2_Wm2=G_diff

        rows.append({
            "Cell":r["Cell"],
            "Direct_Wm2":round(direct_Wm2,2),
            "Shaded_Wm2":round(shaded_Wm2,2),
            "Rear_Wm2":round(rear_Wm2,2),
            "Rear2_Wm2":round(rear2_Wm2,2),
        })
    out=pd.DataFrame(rows)

    if verbose:
        print(out.to_string(index=False))
    return out