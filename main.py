from fastapi import Depends, FastAPI, HTTPException, Body
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import requests

from database import SessionLocal, engine
import models
from auth import hash_password, verify_password, create_access_token, get_current_user
from schemas import (
    UserResponse, UserCreate, TokenResponse,
    AddressCreate, AddressUpdate, AddressResponse, AddressesResponse
)

# Create tables if not already created
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Weather API with DB")
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


# ----------------------------
# Dependency: DB Session
# ----------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ----------------------------
# Weather Endpoints
# ----------------------------
@app.get("/weather")
def get_weather(
    latitude: float = 51.5074,
    longitude: float = -0.1278,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Fetch weather from Open-Meteo, save request into DB, and return JSON."""
    params = {"latitude": latitude, "longitude": longitude, "current_weather": True}
    response = requests.get(OPEN_METEO_URL, params=params, timeout=10)
    data = response.json()

    if "current_weather" not in data:
        raise HTTPException(status_code=400, detail="Weather not available")

    current = data["current_weather"]

    weather_entry = models.WeatherRequest(
        city=f"Lat:{latitude}, Lon:{longitude}",
        latitude=latitude,
        longitude=longitude,
        temperature=current["temperature"],
        description=f"Windspeed {current['windspeed']} km/h"
    )
    db.add(weather_entry)
    db.commit()
    db.refresh(weather_entry)

    return {
        "user": current_user.username,
        "city": weather_entry.city,
        "temperature": weather_entry.temperature,
        "description": weather_entry.description,
        "time": current["time"],
    }


@app.get("/history")
def get_history(db: Session = Depends(get_db)):
    """Retrieve all past weather requests."""
    return db.query(models.WeatherRequest).order_by(models.WeatherRequest.timestamp.desc()).all()


# ----------------------------
# Auth Endpoints
# ----------------------------
@app.post("/signup", response_model=UserResponse)
def signup(user: UserCreate = Body(...), db: Session = Depends(get_db)):
    if db.query(models.User).filter(models.User.username == user.username).first():
        raise HTTPException(status_code=409, detail="Username already exists")

    new_user = models.User(username=user.username, hashed_password=hash_password(user.password))
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@app.post("/login", response_model=TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_access_token(data={"sub": user.username})

    response = JSONResponse(content={"access_token": token, "token_type": "bearer"})
    response.set_cookie(key="access_token", value=token, httponly=True)
    return response


@app.get("/me", response_model=UserResponse)
def read_users_me(current_user: models.User = Depends(get_current_user)):
    return current_user


# ----------------------------
# Address Endpoints
# ----------------------------
@app.post("/home-address", response_model=AddressResponse)
def add_or_update_home_address(
    address: AddressCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    home = db.query(models.HomeAddress).filter_by(user_id=current_user.id).first()
    if home:
        home.street, home.city, home.pincode = address.street, address.city, address.pincode
        db.commit()
        db.refresh(home)
        return home

    new_home = models.HomeAddress(user_id=current_user.id, **address.dict())
    db.add(new_home)
    db.commit()
    db.refresh(new_home)
    return new_home


@app.put("/home-address", response_model=AddressResponse)
@app.patch("/home-address", response_model=AddressResponse)
def update_home_address(
    address: AddressUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    home = db.query(models.HomeAddress).filter_by(user_id=current_user.id).first()
    if not home:
        raise HTTPException(status_code=404, detail="No home address found")

    if address.street: home.street = address.street
    if address.city: home.city = address.city
    if address.pincode: home.pincode = address.pincode

    db.commit()
    db.refresh(home)
    return home


@app.delete("/home-address")
def delete_home_address(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    home = db.query(models.HomeAddress).filter_by(user_id=current_user.id).first()
    if not home:
        raise HTTPException(status_code=404, detail="No home address found")
    db.delete(home)
    db.commit()
    return {"message": "Home address deleted"}


@app.post("/work-address", response_model=AddressResponse)
@app.put("/work-address", response_model=AddressResponse)
@app.patch("/work-address", response_model=AddressResponse)
def update_work_address(
    address: AddressUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    work = db.query(models.WorkAddress).filter_by(user_id=current_user.id).first()
    if not work:
        work = models.WorkAddress(user_id=current_user.id, **address.dict(exclude_unset=True))
        db.add(work)
    else:
        if address.street: work.street = address.street
        if address.city: work.city = address.city
        if address.pincode: work.pincode = address.pincode
    db.commit()
    db.refresh(work)
    return work


@app.delete("/work-address")
def delete_work_address(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    work = db.query(models.WorkAddress).filter_by(user_id=current_user.id).first()
    if not work:
        raise HTTPException(status_code=404, detail="No work address found")
    db.delete(work)
    db.commit()
    return {"message": "Work address deleted"}


@app.get("/addresses", response_model=AddressesResponse)
def get_user_addresses(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    home = db.query(models.HomeAddress).filter_by(user_id=current_user.id).first()
    work = db.query(models.WorkAddress).filter_by(user_id=current_user.id).first()
    return {"home_address": home, "work_address": work}


# ----------------------------
# Logout
# ----------------------------
@app.post("/logout")
def logout():
    response = JSONResponse(content={"message": "Logged out"})
    response.delete_cookie("access_token")
    return response