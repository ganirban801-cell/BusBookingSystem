
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from jose import jwt, JWTError
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User
from backend.schemas import UserRegister, UserResponse, UserLogin
from backend.security import hash_password, verify_password


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


# JWT SETTINGS
SECRET_KEY = "change-this-to-a-long-random-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60


# CREATE ACCESS TOKEN
def create_access_token(data: dict):
    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    to_encode.update({"exp": expire})

    return jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM
    )


# TOKEN VERIFICATION
oauth2_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"}
    )

    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        user_id = payload.get("sub")

        if user_id is None:
            raise credentials_exception

        user_id = int(user_id)

    except (JWTError, ValueError, TypeError):
        raise credentials_exception

    user = db.query(User).filter(
        User.id == user_id
    ).first()

    if user is None or not user.is_active:
        raise credentials_exception

    return user


# PASSENGER REGISTRATION
@router.post("/register", response_model=UserResponse)
def register_passenger(
    user_data: UserRegister,
    db: Session = Depends(get_db)
):
    existing_user = db.query(User).filter(
        User.phone == user_data.phone
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Phone number already registered"
        )

    new_user = User(
        name=user_data.name,
        phone=user_data.phone,
        password=hash_password(user_data.password),
        role="passenger"
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


# PASSENGER LOGIN
@router.post("/login")
def login_passenger(
    user_data: UserLogin,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(
        User.phone == user_data.phone
    ).first()

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid phone number or password"
        )

    if not verify_password(
        user_data.password,
        user.password
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid phone number or password"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="Account is inactive"
        )

    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "role": user.role
        }
    )

    return {
        "message": "Login Successful",
        "access_token": access_token,
        "token_type": "bearer"
    }


# GET LOGGED-IN USER PROFILE
@router.get("/me", response_model=UserResponse)
def get_my_profile(
    current_user: User = Depends(get_current_user)
):
    return current_user
# ADMIN ONLY ACCESS
def get_current_admin(
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )

    return current_user
# CREATE ADMIN ACCOUNT
@router.post("/create-admin", response_model=UserResponse)
def create_admin(
    user_data: UserRegister,
    db: Session = Depends(get_db)
):
    existing_user = db.query(User).filter(
        User.phone == user_data.phone
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Phone number already registered"
        )

    new_admin = User(
        name=user_data.name,
        phone=user_data.phone,
        password=hash_password(user_data.password),
        role="admin"
    )

    db.add(new_admin)
    db.commit()
    db.refresh(new_admin)

    return new_admin

# ADMIN AND CONDUCTOR ACCESS

def get_current_staff(
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in ["admin", "conductor"]:
        raise HTTPException(
            status_code=403,
            detail="Staff access required"
        )

    return current_user

# CREATE CONDUCTOR ACCOUNT (ADMIN ONLY)

@router.post("/create-conductor", response_model=UserResponse)
def create_conductor(
    user_data: UserRegister,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    existing_user = db.query(User).filter(
        User.phone == user_data.phone
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Phone number already registered"
        )

    new_conductor = User(
        name=user_data.name,
        phone=user_data.phone,
        password=hash_password(user_data.password),
        role="conductor"
    )

    db.add(new_conductor)
    db.commit()
    db.refresh(new_conductor)

    return new_conductor
