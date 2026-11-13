
from sqlalchemy import (
    Column, Integer, String, Boolean,
    DateTime, Date, ForeignKey,
    Float, UniqueConstraint
)
from backend.database import Base


# 1. User Table
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(15), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    role = Column(String(20), default="passenger")
    is_active = Column(Boolean, default=True)


# 2. Bus Table
class Bus(Base):
    __tablename__ = "buses"

    id = Column(Integer, primary_key=True, index=True)
    bus_number = Column(String(30), unique=True)
    bus_name = Column(String(100))
    bus_type = Column(String(30))
    total_seats = Column(Integer, nullable=False)


# 3. Journey Table
class Trip(Base):
    __tablename__ = "trips"

    id = Column(Integer, primary_key=True, index=True)
    bus_id = Column(Integer, ForeignKey("buses.id"))
    source = Column(String(100))
    destination = Column(String(100))
    journey_date = Column(Date)
    departure_time = Column(String(20))
    fare = Column(Float)


# 4. Seat Table
class Seat(Base):
    __tablename__ = "seats"

    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(Integer, ForeignKey("trips.id"))
    seat_number = Column(String(10))
    status = Column(String(20), default="available")

    __table_args__ = (
        UniqueConstraint(
            "trip_id", "seat_number",
            name="unique_trip_seat"
        ),
    )


# 5. Booking Table
class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    trip_id = Column(Integer, ForeignKey("trips.id"))
    seat_id = Column(Integer, ForeignKey("seats.id"))
    booking_status = Column(String(20), default="pending")
    total_amount = Column(Float)
    booking_date = Column(DateTime)


# 6. Payment Table
class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"))
    amount = Column(Float)
    payment_status = Column(String(20), default="pending")
    payment_method = Column(String(30))
    transaction_id = Column(String(100))
