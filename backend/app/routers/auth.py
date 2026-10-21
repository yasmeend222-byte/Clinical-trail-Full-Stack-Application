from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import audit, create_token, get_current_researcher, hash_password, verify_password
from ..database import get_db
from ..models import Researcher
from ..schemas import LoginIn, RegisterIn, researcher_out

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    r = db.scalar(select(Researcher).where(Researcher.email == body.email.lower().strip()))
    if not r or not verify_password(body.password, r.password_hash):
        raise HTTPException(401, "Invalid email or password")
    audit(db, r, "login", r.email)
    db.commit()
    return {"token": create_token(r.id), "researcher": researcher_out(r)}


@router.post("/register")
def register(body: RegisterIn, db: Session = Depends(get_db)):
    email = body.email.lower().strip()
    if db.scalar(select(Researcher).where(Researcher.email == email)):
        raise HTTPException(409, "An account with this email already exists")
    r = Researcher(name=body.name, email=email, role=body.role, password_hash=hash_password(body.password))
    db.add(r)
    db.flush()
    audit(db, r, "register", email)
    db.commit()
    return {"token": create_token(r.id), "researcher": researcher_out(r)}


@router.get("/me")
def me(r: Researcher = Depends(get_current_researcher)):
    return researcher_out(r)
