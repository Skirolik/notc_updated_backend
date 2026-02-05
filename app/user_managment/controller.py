from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash
import uuid
from datetime import datetime
from .auth import generate_access_token
from werkzeug.security import check_password_hash
from flask import jsonify
from .models import User
from app import db


def check_login(data):
    user=User.query.filter_by(email=data['email']).first()

    if not user:
        return jsonify({"msg":"Invalid credentials"}),401
    if not check_password_hash(user.password_hash,data['password']):
        return jsonify({"msg":"Invalid Credentials"}),403

    token=generate_access_token(user)
    user_data={
        "id":str(user.user_id),
        "name":user.username,
        "email":user.email,
        "company_name":user.company_name,
    }

    return jsonify({
        "access_token":token,
        "user_data":user_data,
    })

def add_user(data):
    try:
        user_id=uuid.uuid4()

        while db.session.query(User).filter_by(user_id=user_id).first():
            user_id=uuid.uuid4()

        #have to check email id as well
        while db.session.query(User).filter_by(email=data['email_id']).first():
            return jsonify({"msg": "Email id already exsists"}), 401

        hashed_password=generate_password_hash(data["password_hash"])

        new_user=User(
            user_id=user_id,
            username=data['name'],
            email=data['email_id'],
            password_hash=hashed_password,
            company_name=data['company_name'],
            created_at=datetime.utcnow(),
        )
        db.session.add(new_user)
        db.session.commit()

        return {"user_id":str(user_id)}
    except IntegrityError as e:
        db.session.rollback()
        raise Exception ("User creation failed") from e