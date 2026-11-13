
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.database import Base, engine
from backend import models
from backend.auth import router as auth_router
from backend.buses import router as buses_router
from backend.trips import router as trips_router
from backend.bookings import router as bookings_router
from backend.payment import router as payment_router

# Create Database Tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="My Bus Booking System",
    description="Online Passenger Bus Ticket Booking",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(buses_router)
app.include_router(trips_router)
app.include_router(bookings_router)
app.include_router(payment_router)

@app.get("/")
def home():
    return {
        "message": "Welcome to My Bus Booking System!",
        "status": "Backend Running Successfully"
    }

@app.get("/health")
def health():
    return {"status": "OK"}

@app.get("/database-status")
def database_status():
    return {
        "message": "Database Connected Successfully",
        "tables": [
            "users",
            "buses",
            "trips",
            "seats",
            "bookings",
            "payments"
        ]
    }
