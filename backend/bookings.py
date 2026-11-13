
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Booking, Trip, Seat, User, Payment
from backend.schemas import BookingCreate, BookingResponse
from backend.auth import get_current_user, get_current_staff


router = APIRouter(
    prefix="/bookings",
    tags=["Booking Management"]
)


# EXPIRE PENDING BOOKINGS AFTER 10 MINUTES
def expire_pending_bookings(db: Session):
    cutoff_time = datetime.now(timezone.utc).replace(
        tzinfo=None
    ) - timedelta(minutes=60)

    pending_bookings = db.query(Booking).filter(
        Booking.booking_status == "pending",
        Booking.booking_date <= cutoff_time
    ).all()

    for booking in pending_bookings:
        seat = db.query(Seat).filter(
            Seat.id == booking.seat_id
        ).first()

        if seat and seat.status == "pending":
            seat.status = "available"

        booking.booking_status = "cancelled"

    if pending_bookings:
        db.commit()


# PASSENGER BOOKS A SEAT
@router.post("/", response_model=BookingResponse)
def create_booking(
    booking_data: BookingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    expire_pending_bookings(db)

    if current_user.role != "passenger":
        raise HTTPException(
            status_code=403,
            detail="Only passengers can book seats"
        )

    trip = db.query(Trip).filter(
        Trip.id == booking_data.trip_id
    ).first()

    if not trip:
        raise HTTPException(
            status_code=404,
            detail="Trip not found"
        )

    seat = db.query(Seat).filter(
        Seat.id == booking_data.seat_id,
        Seat.trip_id == booking_data.trip_id
    ).with_for_update().first()

    if not seat:
        raise HTTPException(
            status_code=404,
            detail="Seat not found"
        )

    if seat.status != "available":
        raise HTTPException(
            status_code=400,
            detail="Seat is not available"
        )

    new_booking = Booking(
        user_id=current_user.id,
        trip_id=booking_data.trip_id,
        seat_id=booking_data.seat_id,
        booking_status="pending",
        total_amount=trip.fare,
        booking_date=datetime.now(timezone.utc)
    )

    seat.status = "pending"
    db.add(new_booking)

    try:
        db.commit()
        db.refresh(new_booking)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Booking could not be completed"
        )

    return new_booking


# VIEW BOOKED SEAT PASSENGER DETAILS
@router.get("/trip/{trip_id}/seat/{seat_id}/details")
def get_booked_seat_details(
    trip_id: int,
    seat_id: int,
    db: Session = Depends(get_db),
    current_staff: User = Depends(get_current_staff)
):
    seat = db.query(Seat).filter(
        Seat.id == seat_id,
        Seat.trip_id == trip_id
    ).first()

    if not seat:
        raise HTTPException(
            status_code=404,
            detail="Seat not found"
        )

    if seat.status != "booked":
        raise HTTPException(
            status_code=400,
            detail="Passenger details are available only for booked seats"
        )

    booking = db.query(Booking).filter(
        Booking.seat_id == seat_id,
        Booking.trip_id == trip_id,
        Booking.booking_status == "confirmed"
    ).order_by(Booking.id.desc()).first()

    if not booking:
        raise HTTPException(
            status_code=404,
            detail="Confirmed booking not found"
        )

    passenger = db.query(User).filter(
        User.id == booking.user_id
    ).first()

    payment = db.query(Payment).filter(
        Payment.booking_id == booking.id
    ).first()

    return {
        "booking_id": booking.id,
        "passenger_name": passenger.name,
        "passenger_phone": passenger.phone,
        "seat_number": seat.seat_number,
        "trip_id": trip_id,
        "booking_status": booking.booking_status,
        "payment_status": payment.payment_status if payment else "not_recorded"
    }
