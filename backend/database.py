
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Database file
DATABASE_URL = "sqlite:///./bus_booking.db"

# Create database connection
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

# Database Session
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Database Base
Base = declarative_base()

print("Bus Booking Database Connected!")

# Database Session Dependency

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
