
import os
from pathlib import Path

import razorpay
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Booking, Seat, Payment, User
from backend.auth import get_current_user
from backend.bookings import expire_pending_bookings
from pydantic import BaseModel

load_dotenv(Path(__file__).resolve().parent / ".env")

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

router = APIRouter(
    prefix="/payments",
    tags=["Payment Management"]
)
class PaymentVerifyRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str

@router.post("/create-order/{booking_id}")
def create_payment_order(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    expire_pending_bookings(db)

    if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
        raise HTTPException(
            status_code=500,
            detail="Razorpay API keys are not configured"
        )

    booking = db.query(Booking).filter(
        Booking.id == booking_id
    ).first()

    if not booking:
        raise HTTPException(
            status_code=404,
            detail="Booking not found"
        )

    if booking.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You cannot pay for this booking"
        )

    if booking.booking_status != "pending":
        raise HTTPException(
            status_code=400,
            detail="Booking is not pending"
        )

    seat = db.query(Seat).filter(
        Seat.id == booking.seat_id
    ).first()

    if not seat or seat.status != "pending":
        raise HTTPException(
            status_code=400,
            detail="Seat is not pending"
        )

    amount_paise = int(round(booking.total_amount * 100))

    if amount_paise <= 0:
        raise HTTPException(
            status_code=400,
            detail="Invalid payment amount"
        )

    try:
        client = razorpay.Client(
            auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET)
        )

        order = client.order.create({
            "amount": amount_paise,
            "currency": "INR",
            "receipt": f"booking_{booking.id}"
        })

        payment = Payment(
            booking_id=booking.id,
            amount=booking.total_amount,
            payment_status="pending",
            payment_method="razorpay",
            transaction_id=order["id"]
        )

        db.add(payment)
        db.commit()

        return {
            "message": "Payment order created successfully",
            "booking_id": booking.id,
            "order_id": order["id"],
            "amount": amount_paise,
            "currency": "INR",
            "key_id": RAZORPAY_KEY_ID
        }

    except HTTPException:
        raise

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=502,
            detail="Could not create Razorpay payment order"
        )

@router.post("/verify")
def verify_payment(
    payment_data: PaymentVerifyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
        raise HTTPException(
            status_code=500,
            detail="Razorpay API keys are not configured"
        )

    payment = db.query(Payment).filter(
        Payment.transaction_id == payment_data.razorpay_order_id
    ).first()

    if not payment:
        raise HTTPException(
            status_code=404,
            detail="Payment order not found"
        )

    booking = db.query(Booking).filter(
        Booking.id == payment.booking_id
    ).first()

    if not booking:
        raise HTTPException(
            status_code=404,
            detail="Booking not found"
        )

    if booking.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You cannot verify this payment"
        )

    if booking.booking_status != "pending" or payment.payment_status != "pending":
        raise HTTPException(
            status_code=400,
            detail="Booking or payment is not pending"
        )

    seat = db.query(Seat).filter(
        Seat.id == booking.seat_id
    ).first()

    if not seat or seat.status != "pending":
        raise HTTPException(
            status_code=400,
            detail="Seat is not pending"
        )

    try:
        client = razorpay.Client(
            auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET)
        )

        client.utility.verify_payment_signature({
            "razorpay_order_id": payment_data.razorpay_order_id,
            "razorpay_payment_id": payment_data.razorpay_payment_id,
            "razorpay_signature": payment_data.razorpay_signature
        })

        razorpay_payment = client.payment.fetch(
            payment_data.razorpay_payment_id
        )

        if razorpay_payment.get("status") != "captured":
            raise HTTPException(
                status_code=400,
                detail="Payment is not captured"
            )

        if razorpay_payment.get("order_id") != payment_data.razorpay_order_id:
            raise HTTPException(
                status_code=400,
                detail="Payment order mismatch"
            )

        if int(razorpay_payment.get("amount", 0)) != int(round(booking.total_amount * 100)):
            raise HTTPException(
                status_code=400,
                detail="Payment amount mismatch"
            )

        if razorpay_payment.get("currency") != "INR":
            raise HTTPException(
                status_code=400,
                detail="Payment currency mismatch"
            )

        payment.payment_status = "success"
        payment.transaction_id = payment_data.razorpay_payment_id

        booking.booking_status = "confirmed"
        seat.status = "booked"

        db.commit()

        return {
            "message": "Payment verified successfully",
            "booking_id": booking.id,
            "booking_status": booking.booking_status,
            "seat_status": seat.status,
            "payment_status": payment.payment_status
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Payment verification failed"
        )
