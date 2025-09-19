from fastapi import Depends, FastAPI, Query, HTTPException, Body
from fastapi.security import OAuth2PasswordRequestForm
import requests

from database import SessionLocal, engine
import models
from auth import hash_password, verify_password, create_access_token, get_current_user
from schemas import UserResponse, UserCreate, TokenResponse, AddressCreate, AddressUpdate, AddressResponse, AddressesResponse

# Make sure tables exist (safety net in case create_tables.py wasn't run)
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Weather API with DB")

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# ----------------------------
# Public Weather Endpoints
# ----------------------------
@app.get("/weather")
def get_weather(
    latitude: float = 51.5074, 
    longitude: float = -0.1278,
    current_user: models.User = Depends(get_current_user)
    ):
    """
    Fetch weather from Open-Meteo, save request into DB,
    and return a clean JSON response.
    """
    params = {"latitude": latitude, "longitude": longitude, "current_weather": True}
    response = requests.get(OPEN_METEO_URL, params=params, timeout=10)
    data = response.json()

    if "current_weather" not in data:
        raise HTTPException(status_code=400, detail="Weather not available")

    current = data["current_weather"]

    # Save to database
    db = SessionLocal()
    weather_entry = models.WeatherRequest(
        city=f"Lat:{latitude}, Lon:{longitude}",   # placeholder city
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
        "time": current["time"]
    }


@app.get("/history")
def get_history():
    """
    Retrieve all past weather requests from DB.
    """
    db = SessionLocal()
    history = db.query(models.WeatherRequest).order_by(models.WeatherRequest.timestamp.desc()).all()
    return history

# ----------------------------
# Auth Endpoints
# ----------------------------
@app.post("/signup", response_model=UserResponse)
def signup(user: UserCreate = Body(...)):
    db = SessionLocal()
    existing = db.query(models.User).filter(models.User.username == user.username).first()
    if existing:
        raise HTTPException(status_code=409, detail="Username already exists")
    
    new_user = models.User(
        username=user.username,
        hashed_password=hash_password(user.password)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user

@app.post("/login", response_model=TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    db = SessionLocal()
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    token = create_access_token(data={"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}


@app.get("/me", response_model=UserResponse)
def read_users_me(current_user: models.User = Depends(get_current_user)):
    """
    Return the currently authenticated user's information.
    Requires Authorization: Bearer <token>.
    """
    return current_user

@app.post("/home-address", response_model=AddressResponse)
def add_or_update_home_address(
    address: AddressCreate,
    current_user: models.User = Depends(get_current_user),
):
    """
    Add or update the user's home address.
    """
    db = SessionLocal()

    if current_user.home_address:
        # Update existing
        current_user.home_address.street = address.street
        current_user.home_address.city = address.city
        current_user.home_address.pincode = address.pincode
        db.commit()
        db.refresh(current_user.home_address)
        return current_user.home_address
    else:
        # Create new
        new_home = models.HomeAddress(
            user_id=current_user.id,
            street=address.street,
            city=address.city,
            pincode=address.pincode,
        )
        db.add(new_home)
        db.commit()
        db.refresh(new_home)
        return new_home


@app.delete("/home-address")
def delete_home_address(current_user: models.User = Depends(get_current_user)):
    """
    Delete the user's home address.
    """
    db = SessionLocal()
    if not current_user.home_address:
        raise HTTPException(status_code=404, detail="No home address found")

    db.delete(current_user.home_address)
    db.commit()
    return {"message": "Home address deleted"}


# ----------------- Work Address -----------------
@app.post("/work-address", response_model=AddressResponse)
def add_or_update_work_address(
    address: AddressCreate,
    current_user: models.User = Depends(get_current_user),
):
    """
    Add or update the user's work address.
    """
    db = SessionLocal()

    if current_user.work_address:
        current_user.work_address.street = address.street
        current_user.work_address.city = address.city
        current_user.work_address.pincode = address.pincode
        db.commit()
        db.refresh(current_user.work_address)
        return current_user.work_address
    else:
        new_work = models.WorkAddress(
            user_id=current_user.id,
            street=address.street,
            city=address.city,
            pincode=address.pincode,
        )
        db.add(new_work)
        db.commit()
        db.refresh(new_work)
        return new_work


@app.delete("/work-address")
def delete_work_address(current_user: models.User = Depends(get_current_user)):
    """
    Delete the user's work address.
    """
    db = SessionLocal()
    if not current_user.work_address:
        raise HTTPException(status_code=404, detail="No work address found")

    db.delete(current_user.work_address)
    db.commit()
    return {"message": "Work address deleted"}

@app.get("/addresses", response_model= AddressesResponse)
def get_user_addresses(current_user: models.User = Depends(get_current_user)):
    """
    Fetch the logged-in user's home and work addresses.
    Returns None if they don't exist.
    """
    return {
        "home_address": current_user.home_address,
        "work_address": current_user.work_address,
    }

@app.put("/home-address", response_model=AddressResponse)
def update_home_address(
    address: AddressCreate,
    current_user: models.User = Depends(get_current_user),
):
    """
    Replace (full update) the user's home address.
    """
    db = SessionLocal()
    if not current_user.home_address:
        raise HTTPException(status_code=404, detail="No home address found")

    current_user.home_address.street = address.street
    current_user.home_address.city = address.city
    current_user.home_address.pincode = address.pincode
    db.commit()
    db.refresh(current_user.home_address)
    return current_user.home_address


@app.patch("/home-address", response_model=AddressResponse)
def patch_home_address(
    address: AddressUpdate,
    current_user: models.User = Depends(get_current_user),
):
    """
    Partially update the user's home address.
    """
    db = SessionLocal()
    if not current_user.home_address:
        raise HTTPException(status_code=404, detail="No home address found")

    if address.street:
        current_user.home_address.street = address.street
    if address.city:
        current_user.home_address.city = address.city
    if address.pincode:
        current_user.home_address.pincode = address.pincode

    db.commit()
    db.refresh(current_user.home_address)
    return current_user.home_address
