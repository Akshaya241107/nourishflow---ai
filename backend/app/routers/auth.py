from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..security import create_token, get_current_user, hash_password, verify_password
from ..serializers import user_out

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=schemas.TokenOut)
def register(data: schemas.RegisterIn, db: Session = Depends(get_db)):
    email = data.email.lower()
    if db.query(models.User).filter(models.User.email == email).first():
        raise HTTPException(409, "An account with this email already exists")
    user = models.User(
        name=data.name, email=email, hashed_password=hash_password(data.password),
        role=data.role, organization=data.organization,
        latitude=data.latitude, longitude=data.longitude,
        capacity_kg=data.capacity_kg, accepted_categories=",".join(data.accepted_categories),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"access_token": create_token(user.id), "user": user_out(user)}


@router.post("/login", response_model=schemas.TokenOut)
def login(data: schemas.LoginIn, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == data.email.lower()).first()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(401, "Wrong email or password")
    return {"access_token": create_token(user.id), "user": user_out(user)}


@router.get("/me", response_model=schemas.UserOut)
def me(user: models.User = Depends(get_current_user)):
    return user_out(user)