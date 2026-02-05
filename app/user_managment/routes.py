from flask import Blueprint,request

from app.user_managment.controller import check_login, add_user

user_management_bp=Blueprint('user_management_bp',__name__,url_prefix='/api')

@user_management_bp.route('/login',methods=['POST'])
def login():
    data=request.json
    print('Recived login data',data)
    return check_login(data)

@user_management_bp.route('/create_login',methods=['POST'])
def create_login():
    data=request.json
    print('data in create login',data)
    return  add_user(data)