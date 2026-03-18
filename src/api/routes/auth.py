from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from db.database import get_db

from db.models import UserRecord
from utils.jwt import create_access_token
from utils.hash import hash_password, verify_password

from api.models import LoginRequest, SignupRequest, TokenResponse, UserResponse
from sqlalchemy.orm import Session
router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(UserRecord).filter(UserRecord.email == body.email).first()

    if not user or not user.password_hash or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    return TokenResponse(
        access_token=create_access_token(data={"sub": str(user.id), "email": user.email}),
        user=UserResponse.model_validate(user),
    )


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def signup(body: SignupRequest, db: Session = Depends(get_db)):

    user = UserRecord(
        email=body.email,
        name=body.name,
        password_hash=hash_password(body.password),
    )

    try:
        db.add(user)
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )


    return TokenResponse(
        access_token=create_access_token(data={"sub": str(user.id), "email": user.email}),
        user=UserResponse.model_validate(user),
    )