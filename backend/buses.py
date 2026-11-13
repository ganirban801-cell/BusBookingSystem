
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Bus, User
from backend.schemas import BusCreate, BusResponse
from backend.auth import get_current_admin


router = APIRouter(
    prefix="/buses",
    tags=["Bus Management"]
)


# ADD NEW BUS (ADMIN ONLY)
@router.post("/", response_model=BusResponse)
def create_bus(
    bus_data: BusCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    existing_bus = db.query(Bus).filter(
        Bus.bus_number == bus_data.bus_number
    ).first()

    if existing_bus:
        raise HTTPException(
            status_code=400,
            detail="Bus number already exists"
        )

    new_bus = Bus(
        bus_number=bus_data.bus_number,
        bus_name=bus_data.bus_name,
        bus_type=bus_data.bus_type,
        total_seats=bus_data.total_seats
    )

    db.add(new_bus)
    db.commit()
    db.refresh(new_bus)

    return new_bus

# GET ALL BUSES
@router.get("/", response_model=list[BusResponse])
def get_all_buses(
    db: Session = Depends(get_db)
):
    buses = db.query(Bus).all()
    return buses
