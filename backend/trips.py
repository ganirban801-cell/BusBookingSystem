
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Trip, Bus, User, Seat
from backend.schemas import TripCreate, TripResponse
from backend.auth import get_current_admin, get_current_staff
from backend.bookings import expire_pending_bookings

router = APIRouter(
    prefix="/trips",
    tags=["Trip Management"]
)


# CREATE NEW TRIP AND AUTOMATICALLY CREATE SEATS
@router.post("/", response_model=TripResponse)
def create_trip(
    trip_data: TripCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    bus = db.query(Bus).filter(
        Bus.id == trip_data.bus_id
    ).first()

    if not bus:
        raise HTTPException(
            status_code=404,
            detail="Bus not found"
        )

    new_trip = Trip(
        bus_id=trip_data.bus_id,
        source=trip_data.source,
        destination=trip_data.destination,
        journey_date=trip_data.journey_date,
        departure_time=trip_data.departure_time,
        fare=trip_data.fare
    )

    db.add(new_trip)
    db.flush()

    # AUTOMATICALLY CREATE ALL SEATS
    for number in range(1, bus.total_seats + 1):
        new_seat = Seat(
            trip_id=new_trip.id,
            seat_number=str(number),
            status="available"
        )
        db.add(new_seat)

    db.commit()
    db.refresh(new_trip)

    return new_trip

# GET ALL SEATS OF A TRIP

@router.get("/{trip_id}/seats")
def get_trip_seats(
    trip_id: int,
    db: Session = Depends(get_db)
):
    expire_pending_bookings(db)
    trip = db.query(Trip).filter(
        Trip.id == trip_id
    ).first()

    if not trip:
        raise HTTPException(
            status_code=404,
            detail="Trip not found"
        )

    seats = db.query(Seat).filter(
        Seat.trip_id == trip_id
    ).order_by(Seat.id).all()

    return seats

# GET ALL TRIPS

@router.get("/", response_model=list[TripResponse])
def get_all_trips(
    db: Session = Depends(get_db)
):
    trips = db.query(Trip).all()
    return trips

# BLOCK A SEAT (ADMIN OR CONDUCTOR)

@router.patch("/{trip_id}/seats/{seat_id}/block")
def block_seat(
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

    if seat.status != "available":
        raise HTTPException(
            status_code=400,
            detail="Only available seats can be blocked"
        )

    seat.status = "blocked"
    db.commit()
    db.refresh(seat)

    return {
        "message": "Seat blocked successfully",
        "seat_number": seat.seat_number,
        "status": seat.status
    }


# UNBLOCK A SEAT (ADMIN OR CONDUCTOR)

@router.patch("/{trip_id}/seats/{seat_id}/unblock")
def unblock_seat(
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

    if seat.status != "blocked":
        raise HTTPException(
            status_code=400,
            detail="Only blocked seats can be unblocked"
        )

    seat.status = "available"
    db.commit()
    db.refresh(seat)

    return {
        "message": "Seat unblocked successfully",
        "seat_number": seat.seat_number,
        "status": seat.status
    }
