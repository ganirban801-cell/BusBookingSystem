
import os
import uuid
from pathlib import Path

import httpx
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Booking, Seat, Payment, User
from backend.auth import get_current_user
from backend.bookings import expire_pending_bookings

load_dotenv(Path(__file__).resolve().parent / ".env")

CASHFREE_CLIENT_ID = os.getenv("CASHFREE_CLIENT_ID")
CASHFREE_CLIENT_SECRET = os.getenv("CASHFREE_CLIENT_SECRET")

CASHFREE_BASE_URL = "https://sandbox.cashfree.com/pg"
CASHFREE_API_VERSION = "2025-01-01"

router = APIRouter(
    prefix="/payments",
    tags=["Payment Management"]
)


class PaymentVerifyRequest(BaseModel):
    order_id: str


def cashfree_headers():
    return {
        "x-client-id": CASHFREE_CLIENT_ID,
        "x-client-secret": CASHFREE_CLIENT_SECRET,
        "x-api-version": CASHFREE_API_VERSION,
        "Content-Type": "application/json"
    }


@router.post("/create-order/{booking_id}")
def create_payment_order(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    expire_pending_bookings(db)

    if not CASHFREE_CLIENT_ID or not CASHFREE_CLIENT_SECRET:
        raise HTTPException(
            status_code=500,
            detail="Cashfree API keys are not configured"
        )

    booking = db.query(Booking).filter(
        Booking.id == booking_id
    ).first()

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

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

    amount = float(booking.total_amount)

    if amount <= 0:
        raise HTTPException(
            status_code=400,
            detail="Invalid payment amount"
        )

    order_id = f"bus_{booking.id}_{uuid.uuid4().hex[:12]}"

    payload = {
        "order_id": order_id,
        "order_amount": amount,
        "order_currency": "INR",
        "customer_details": {
            "customer_id": str(current_user.id),
            "customer_name": current_user.name,
            "customer_phone": current_user.phone
        }
    }

    try:
        response = httpx.post(
            f"{CASHFREE_BASE_URL}/orders",
            json=payload,
            headers=cashfree_headers(),
            timeout=20
        )

        if response.status_code not in (200, 201):
            raise HTTPException(
                status_code=502,
                detail="Cashfree could not create payment order"
            )

        order = response.json()

        payment = Payment(
            booking_id=booking.id,
            amount=booking.total_amount,
            payment_status="pending",
            payment_method="cashfree",
            transaction_id=order_id
        )

        db.add(payment)
        db.commit()

        return {
            "message": "Cashfree payment order created successfully",
            "booking_id": booking.id,
            "order_id": order_id,
            "payment_session_id": order["payment_session_id"],
            "amount": amount,
            "currency": "INR"
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=502,
            detail="Could not create Cashfree payment order"
        )


@router.post("/verify")
def verify_payment(
    payment_data: PaymentVerifyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not CASHFREE_CLIENT_ID or not CASHFREE_CLIENT_SECRET:
        raise HTTPException(
            status_code=500,
            detail="Cashfree API keys are not configured"
        )

    payment = db.query(Payment).filter(
        Payment.transaction_id == payment_data.order_id,
        Payment.payment_method == "cashfree"
    ).first()

    if not payment:
        raise HTTPException(
            status_code=404,
            detail="Cashfree payment order not found"
        )

    booking = db.query(Booking).filter(
        Booking.id == payment.booking_id
    ).first()

    if not booking or booking.user_id != current_user.id:
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
        response = httpx.get(
            f"{CASHFREE_BASE_URL}/orders/{payment_data.order_id}",
            headers=cashfree_headers(),
            timeout=20
        )

        if response.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail="Could not verify Cashfree order"
            )

        order = response.json()

        if order.get("order_status") != "PAID":
            raise HTTPException(
                status_code=400,
                detail="Cashfree payment is not successful"
            )

        if order.get("order_id") != payment_data.order_id:
            raise HTTPException(
                status_code=400,
                detail="Payment order mismatch"
            )

        if float(order.get("order_amount", 0)) != float(booking.total_amount):
            raise HTTPException(
                status_code=400,
                detail="Payment amount mismatch"
            )

        if order.get("order_currency") != "INR":
            raise HTTPException(
                status_code=400,
                detail="Payment currency mismatch"
            )

        payment.payment_status = "success"
        booking.booking_status = "confirmed"
        seat.status = "booked"

        db.commit()

        return {
            "message": "Cashfree payment verified successfully",
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
            detail="Cashfree payment verification failed"
        )
