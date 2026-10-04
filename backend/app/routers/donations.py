from datetime import timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..ml.expiry import safe_hours
from ..ml.matcher import score_match
from ..models import utcnow
from ..security import get_current_user, require_role
from ..serializers import donation_out

router = APIRouter(prefix="/donations", tags=["donations"])


def ngo_load(db: Session, ngo_id: int) -> float:
    total = db.query(func.coalesce(func.sum(models.Donation.quantity_kg), 0)).filter(
        models.Donation.claimed_by_id == ngo_id,
        models.Donation.status.in_(["claimed", "picked_up"]),
    ).scalar()
    return float(total)


def get_or_404(db: Session, donation_id: int) -> models.Donation:
    d = db.get(models.Donation, donation_id)
    if not d:
        raise HTTPException(404, "Donation not found")
    return d


def to_naive_utc(dt):
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


# ---- static routes first (before /{donation_id}/...) ----

@router.get("/safe-window/{category}")
def safe_window(category: str):
    return {"category": category, "safe_hours": safe_hours(category)}


@router.post("", response_model=schemas.DonationOut)
def create_donation(
    data: schemas.DonationCreate,
    user: models.User = Depends(require_role("donor")),
    db: Session = Depends(get_db),
):
    now = utcnow()
    expiry = to_naive_utc(data.expiry_time) if data.expiry_time else now + timedelta(hours=safe_hours(data.category))
    if expiry <= now:
        raise HTTPException(400, "Expiry time must be in the future")
    d = models.Donation(
        donor_id=user.id, food_name=data.food_name, category=data.category,
        quantity_kg=data.quantity_kg, description=data.description, expiry_time=expiry,
        latitude=data.latitude if data.latitude is not None else user.latitude,
        longitude=data.longitude if data.longitude is not None else user.longitude,
        created_at=now,
    )
    db.add(d)
    db.commit()
    db.refresh(d)
    return donation_out(d, now)


@router.get("", response_model=list[schemas.DonationOut])
def list_donations(
    status: str | None = None,
    category: str | None = None,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    now = utcnow()
    q = db.query(models.Donation)
    if status:
        q = q.filter(models.Donation.status == status)
    if status == "posted":
        q = q.filter(models.Donation.expiry_time > now)
    if category:
        q = q.filter(models.Donation.category == category)
    return [donation_out(d, now) for d in q.order_by(models.Donation.created_at.desc()).all()]


@router.get("/mine", response_model=list[schemas.DonationOut])
def my_donations(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    now = utcnow()
    col = models.Donation.donor_id if user.role == "donor" else models.Donation.claimed_by_id
    rows = db.query(models.Donation).filter(col == user.id).order_by(models.Donation.created_at.desc()).all()
    return [donation_out(d, now) for d in rows]


@router.get("/feed", response_model=list[schemas.DonationOut])
def ngo_feed(user: models.User = Depends(require_role("ngo")), db: Session = Depends(get_db)):
    """Open donations ranked by how well they fit this NGO."""
    now = utcnow()
    load = ngo_load(db, user.id)
    rows = db.query(models.Donation).filter(
        models.Donation.status == "posted", models.Donation.expiry_time > now
    ).all()
    out = [donation_out(d, now, score_match(d, user, load, now)) for d in rows]
    out.sort(key=lambda x: x["match"]["score"], reverse=True)
    return out


# ---- per-donation routes ----

@router.get("/{donation_id}/matches", response_model=list[schemas.NgoMatch])
def best_matches(
    donation_id: int,
    user: models.User = Depends(require_role("donor")),
    db: Session = Depends(get_db),
):
    d = get_or_404(db, donation_id)
    if d.donor_id != user.id:
        raise HTTPException(403, "This is not your donation")
    now = utcnow()
    out = []
    for ngo in db.query(models.User).filter(models.User.role == "ngo").all():
        m = score_match(d, ngo, ngo_load(db, ngo.id), now)
        out.append({**m, "ngo_id": ngo.id, "ngo_name": ngo.name, "organization": ngo.organization or ngo.name})
    out.sort(key=lambda x: x["score"], reverse=True)
    return out


@router.post("/{donation_id}/claim", response_model=schemas.DonationOut)
def claim(
    donation_id: int,
    user: models.User = Depends(require_role("ngo")),
    db: Session = Depends(get_db),
):
    d = get_or_404(db, donation_id)
    now = utcnow()
    if d.status != "posted" or d.expiry_time <= now:
        raise HTTPException(409, "This donation is no longer available")
    m = score_match(d, user, ngo_load(db, user.id), now)
    if not m["fits_capacity"]:
        raise HTTPException(400, "You don't have enough free capacity for this donation")
    if not m["reachable"]:
        raise HTTPException(400, "You can't reach the pickup before this food expires")
    d.claimed_by_id = user.id
    d.status = "claimed"
    d.claimed_at = now
    db.commit()
    db.refresh(d)
    return donation_out(d, now)


ALLOWED_FROM = {"picked_up": ("claimed",), "delivered": ("picked_up",), "cancelled": ("posted", "claimed")}


@router.patch("/{donation_id}/status", response_model=schemas.DonationOut)
def update_status(
    donation_id: int,
    data: schemas.StatusIn,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    d = get_or_404(db, donation_id)
    if user.id not in (d.donor_id, d.claimed_by_id):
        raise HTTPException(403, "Only the donor or the NGO that claimed it can update this")
    if d.status not in ALLOWED_FROM[data.status]:
        raise HTTPException(400, f"Can't mark a {d.status.replace('_', ' ')} donation as {data.status.replace('_', ' ')}")
    now = utcnow()
    d.status = data.status
    if data.status == "delivered":
        d.delivered_at = now
    db.commit()
    db.refresh(d)
    return donation_out(d, now)