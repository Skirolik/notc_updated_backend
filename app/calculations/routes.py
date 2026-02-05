from flask import Blueprint,request
from app.calculations.controller import notc_best_angle, notc_without_tracker, stc_calc_update

cal_bp=Blueprint('call',__name__,url_prefix='/api')

@cal_bp.route("/calculate_py",methods=['POST'])
def calculate_py():
    data=request.get_json()
    print('data received',data)
    return notc_best_angle(data)

@cal_bp.route("/notc_custom",methods=['POST'])
def cal_notc_cust():
    data=request.get_json()
    print('data received',data)
    return notc_without_tracker(data)

@cal_bp.route("/stc",methods=['POST'])
def cal_stc():
    data=request.get_json()
    print('data received',data)
    return stc_calc_update(data)