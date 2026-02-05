from app import db
import uuid
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Column,String,Text,TIMESTAMP,Integer

class User(db.Model):
    __tablename__='users'
    __table_args__={'schema':'pixi'}

    user_id=Column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4())
    username=Column(String,nullable=False)
    email=Column(String,unique=True,nullable=False)
    password_hash=Column(Text,nullable=False)
    created_at=Column(TIMESTAMP,default=datetime.utcnow())
    company_name=Column(String,nullable=False)
