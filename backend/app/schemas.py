from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field, field_serializer

Category = Literal["cooked", "bakery", "produce", "packaged", "dairy"]
ALL_CATEGORIES = ["cooked", "bakery", "produce", "packaged", "dairy"]


class RegisterIn(BaseModel):
    name: str = Field(min_length=1)
    email: EmailStr
    password: str = Field(min_length=6)
    role: Literal["donor", "ngo"]
    organization: str = ""
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    capacity_kg: float = Field(default=50, gt=0)
    accepted_categories: list[Category] = Field(default_factory=lambda: list(ALL_CATEGORIES))


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    role: str
    organization: str
    latitude: float
    longitude: float
    capacity_kg: float
    accepted_categories: list[str]


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class DonationCreate(BaseModel):
    food_name: str = Field(min_length=1)
    category: Category = "cooked"
    quantity_kg: float = Field(gt=0)
    description: str = ""
    expiry_time: Optional[datetime] = None   # leave empty to use the safe window for the category
    latitude: Optional[float] = None         # defaults to the donor's registered location
    longitude: Optional[float] = None


class StatusIn(BaseModel):
    status: Literal["picked_up", "delivered", "cancelled"]


class MatchInfo(BaseModel):
    score: float
    distance_km: float
    travel_minutes: int
    reachable: bool
    accepts_category: bool
    fits_capacity: bool
    reasons: list[str]


class NgoMatch(MatchInfo):
    ngo_id: int
    ngo_name: str
    organization: str


class DonationOut(BaseModel):
    id: int
    food_name: str
    category: str
    quantity_kg: float
    description: str
    expiry_time: datetime
    created_at: datetime
    latitude: float
    longitude: float
    status: str
    donor_id: int
    donor_name: str
    claimed_by_id: Optional[int] = None
    claimed_by_name: Optional[str] = None
    hours_left: float
    shelf_life_pct: float
    urgency: str
    match: Optional[MatchInfo] = None

    @field_serializer("expiry_time", "created_at")
    def _as_utc(self, v: datetime) -> str:
        return v.isoformat() + "Z"