# models.py
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, func
from database import Base
from sqlalchemy.orm import relationship

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    weather_requests = relationship("WeatherRequest", back_populates="user")
    home_address = relationship("HomeAddress", back_populates="user", uselist=False)
    work_address = relationship("WorkAddress", back_populates="user", uselist=False)

class WeatherRequest(Base):
    __tablename__ = "weather_requests"

    id = Column(Integer, primary_key=True, index=True)
    city = Column(String, index=True)
    latitude = Column(Float)
    longitude = Column(Float)
    temperature = Column(Float)
    description = Column(String)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    user_id = Column(Integer, ForeignKey("users.id"))

    user = relationship("User", back_populates="weather_requests")

class HomeAddress(Base):
    __tablename__ = "home_addresses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    street = Column(String, nullable=False)
    city = Column(String, nullable=False)
    pincode = Column(String, nullable=False)

    user = relationship("User", back_populates="home_address")


class WorkAddress(Base):
    __tablename__ = "work_addresses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    street = Column(String, nullable=False)
    city = Column(String, nullable=False)
    pincode = Column(String, nullable=False)

    user = relationship("User", back_populates="work_address")

