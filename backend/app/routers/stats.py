from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..models import utcnow

router = APIRouter(tags=["stats"])

KG_PER_MEAL = 0.5       # rough planning figure
CO2E_PER_KG = 2.5       # kg CO2-equivalent avoided per kg of food kept out of landfill (estimate)


@router.get("/stats")
def stats(db: Session = Depends(get_db)):
    D = models.Donation
    now = utcnow()
    kg = float(db.query(func.coalesce(func.sum(D.quantity_kg), 0)).filter(D.status == "delivered").scalar())
    return {
        "donations_posted": db.query(D).count(),
        "donations_delivered": db.query(D).filter(D.status == "delivered").count(),
        "kg_rescued": round(kg, 1),
        "meals_served": int(kg / KG_PER_MEAL),
        "co2_avoided_kg": round(kg * CO2E_PER_KG, 1),
        "open_now": db.query(D).filter(D.status == "posted", D.expiry_time > now).count(),
        "donors": db.query(models.User).filter(models.User.role == "donor").count(),
        "ngos": db.query(models.User).filter(models.User.role == "ngo").count(),
    }