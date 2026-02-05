from app import db
import uuid
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import Column, String, Text, TIMESTAMP, ForeignKey, Float


class Notc_calculations(db.Model):
    __tablename__ = "notc_calculations"
    __table_args__ = {"schema": "pixi"}

    calc_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("pixi.users.user_id"), nullable=False)

    latitude = Column(Float, nullable=False)  # maps to double precision
    longitude = Column(Float, nullable=False)  # maps to double precision

    result = Column(JSONB, nullable=False)  # JSONB column
    created_at = Column(TIMESTAMP, default=datetime.utcnow)