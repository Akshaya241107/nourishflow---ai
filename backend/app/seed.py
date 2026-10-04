"""Fills the database with demo accounts and donations.  Run:  python -m app.seed"""
from datetime import timedelta

from . import models
from .database import SessionLocal, engine
from .models import utcnow
from .security import hash_password

models.Base.metadata.create_all(bind=engine)
db = SessionLocal()

if db.query(models.User).count():
    print("Database already has users, skipping seed.")
    raise SystemExit

pw = hash_password("demo1234")
donor = models.User(name="Ravi Kumar", email="donor@demo.com", hashed_password=pw, role="donor",
                    organization="Hotel Saravana", latitude=13.4125, longitude=80.1146)
ngos = [
    models.User(name="Meena", email="ngo1@demo.com", hashed_password=pw, role="ngo", organization="Annam Foundation",
                latitude=13.4000, longitude=80.1200, capacity_kg=80),
    models.User(name="Joseph", email="ngo2@demo.com", hashed_password=pw, role="ngo", organization="Hope Shelter, Ponneri",
                latitude=13.3394, longitude=80.1946, capacity_kg=40, accepted_categories="cooked,bakery"),
    models.User(name="Latha", email="ngo3@demo.com", hashed_password=pw, role="ngo", organization="Sevai Trust",
                latitude=13.1067, longitude=80.2206, capacity_kg=120, accepted_categories="produce,packaged,bakery"),
]
db.add_all([donor, *ngos])
db.commit()

now = utcnow()


def add(food, cat, kg, hours_to_expiry, status="posted", age_h=0.5, claimer=None):
    created = now - timedelta(hours=age_h)
    d = models.Donation(donor_id=donor.id, food_name=food, category=cat, quantity_kg=kg,
                        expiry_time=now + timedelta(hours=hours_to_expiry), created_at=created,
                        latitude=donor.latitude, longitude=donor.longitude, status=status,
                        claimed_by_id=claimer.id if claimer else None)
    if status == "delivered":
        d.delivered_at = now - timedelta(hours=2)
    db.add(d)


add("Veg biryani", "cooked", 15, 3)
add("Bread and buns", "bakery", 8, 20)
add("Mixed vegetables", "produce", 25, 40)
add("Sambar rice", "cooked", 12, -6, "delivered", age_h=10, claimer=ngos[0])
add("Idli and chutney", "cooked", 30, -20, "delivered", age_h=24, claimer=ngos[1])
db.commit()
print("Seeded. Log in with donor@demo.com or ngo1@demo.com (password: demo1234)")