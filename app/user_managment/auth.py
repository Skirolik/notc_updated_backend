from flask_jwt_extended import create_access_token
from datetime import timedelta

def generate_access_token(user):
    return create_access_token(
        identity=str(user.user_id),
        expires_delta=timedelta(days=1)
    )