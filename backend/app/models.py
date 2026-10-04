from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base


def utcnow():
    """Naive UTC datetime. All times in the database are UTC."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False)  # donor | ngo
    organization = Column(String, default="")
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    capacity_kg = Column(Float, default=50)  # NGOs: how much food they can hold at once
    accepted_categories = Column(String, default="cooked,bakery,produce,packaged,dairy")
    created_at = Column(DateTime, default=utcnow)


class Donation(Base):
    __tablename__ = "donations"

    id = Column(Integer, primary_key=True, index=True)
    donor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    claimed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    food_name = Column(String, nullable=False)
    category = Column(String, default="cooked")
    quantity_kg = Column(Float, nullable=False)
    description = Column(String, default="")
    expiry_time = Column(DateTime, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    status = Column(String, default="posted")  # posted | claimed | picked_up | delivered | cancelled
    created_at = Column(DateTime, default=utcnow)
    claimed_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)

    donor = relationship("User", foreign_keys=[donor_id])
    claimed_by = relationship("User", foreign_keys=[claimed_by_id])