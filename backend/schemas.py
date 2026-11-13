
from pydantic import BaseModel, Field, ConfigDict


# Passenger Registration
class UserRegister(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    phone: str = Field(min_length=10, max_length=15)
    password: str = Field(min_length=8)


# User Login
class UserLogin(BaseModel):
    phone: str
    password: str


# User Information Response
class UserResponse(BaseModel):
    id: int
    name: str
    phone: str
    role: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)
# BUS SCHEMAS

class BusCreate(BaseModel):
    bus_number: str = Field(min_length=3, max_length=30)
    bus_name: str = Field(min_length=2, max_length=100)
    bus_type: str = Field(pattern="^(AC Seater|Non-AC Seater)$")
    total_seats: int = Field(gt=0, le=100)


class BusResponse(BaseModel):
    id: int
    bus_number: str
    bus_name: str
    bus_type: str
    total_seats: int

    model_config = ConfigDict(from_attributes=True)

# TRIP SCHEMAS

from datetime import date

class TripCreate(BaseModel):
    bus_id: int = Field(gt=0)
    source: str = Field(min_length=2, max_length=100)
    destination: str = Field(min_length=2, max_length=100)
    journey_date: date
    departure_time: str
    fare: float = Field(gt=0)


class TripResponse(BaseModel):
    id: int
    bus_id: int
    source: str
    destination: str
    journey_date: date
    departure_time: str
    fare: float

    model_config = ConfigDict(from_attributes=True)

# BOOKING SCHEMAS

class BookingCreate(BaseModel):
    trip_id: int = Field(gt=0)
    seat_id: int = Field(gt=0)


class BookingResponse(BaseModel):
    id: int
    user_id: int
    trip_id: int
    seat_id: int
    booking_status: str
    total_amount: float

    model_config = ConfigDict(from_attributes=True)
