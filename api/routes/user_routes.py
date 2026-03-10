from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db.database import get_db
from db.models import UserRecord
from pydantic import BaseModel

router = APIRouter(prefix="/users", tags=["users"])


class UserCreate(BaseModel):
    email: str
    name: str | None = None
    phone: str | None = None


@router.get("/")
def get_users(db: Session = Depends(get_db)):
    users = db.query(UserRecord).all()
    return users


@router.get("/{user_id}")
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(UserRecord).filter(UserRecord.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/")
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = UserRecord(email=user.email, name=user.name, phone=user.phone)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@router.delete("/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(UserRecord).filter(UserRecord.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    return {"message": "User deleted"}
