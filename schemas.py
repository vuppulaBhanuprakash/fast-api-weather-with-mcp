# schemas.py
from pydantic import BaseModel
from datetime import datetime


class UserCreate(BaseModel):
    username: str
    password: str
# Response model for User
class UserResponse(BaseModel):
    id: int
    username: str
    created_at: datetime

    class Config:
        from_attributes = True  # Enable ORM mode

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

# Base schema for reuse
class AddressBase(BaseModel):
    street: str
    city: str
    pincode: str


# Create/Update request schema
class AddressCreate(AddressBase):
    pass


class AddressUpdate(BaseModel):
    street: str
    city: str
    pincode: str


# Response schema
class AddressResponse(AddressBase):
    id: int

    class Config:
        from_attributes = True   # allows ORM → schema conversion

class AddressesResponse(BaseModel):
    home_address: AddressResponse | None = None
    work_address: AddressResponse | None = None