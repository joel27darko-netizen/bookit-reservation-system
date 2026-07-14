"""
Seed script: populates the database with demo users, resources, and a
handful of sample bookings so the app is immediately explorable.

Run with:  python seed.py
"""
from datetime import datetime, timedelta

from app.database import Base, engine, SessionLocal
from app.models.user import User, RoleEnum
from app.models.resource import Resource, ResourceTypeEnum
from app.models.booking import Booking, BookingStatusEnum
from app.core.security import hash_password

Base.metadata.create_all(bind=engine)
db = SessionLocal()

def get_or_create_user(full_name, email, password, role):
    user = db.query(User).filter(User.email == email).first()
    if user:
        return user
    user = User(full_name=full_name, email=email, hashed_password=hash_password(password), role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_or_create_resource(**kwargs):
    resource = db.query(Resource).filter(Resource.name == kwargs["name"]).first()
    if resource:
        return resource
    resource = Resource(**kwargs)
    db.add(resource)
    db.commit()
    db.refresh(resource)
    return resource


print("Seeding users...")
admin = get_or_create_user("Ada Admin", "admin@bookit.com", "admin123", RoleEnum.admin)
staff = get_or_create_user("Sam Staff", "staff@bookit.com", "staff123", RoleEnum.staff)
customer = get_or_create_user("Casey Customer", "customer@bookit.com", "customer123", RoleEnum.customer)
customer2 = get_or_create_user("Jordan Client", "jordan@bookit.com", "customer123", RoleEnum.customer)

print("Seeding resources...")
room1 = get_or_create_resource(
    name="Deluxe Suite 101", type=ResourceTypeEnum.room, location="3rd Floor",
    capacity=2, price_per_hour=25.0, open_time="00:00", close_time="23:59",
    description="Hotel deluxe suite with king bed and city view.",
)
room2 = get_or_create_resource(
    name="Standard Room 205", type=ResourceTypeEnum.room, location="2nd Floor",
    capacity=2, price_per_hour=15.0, open_time="00:00", close_time="23:59",
    description="Comfortable standard hotel room.",
)
meeting_room = get_or_create_resource(
    name="Conference Room A", type=ResourceTypeEnum.room, location="Ground Floor",
    capacity=10, price_per_hour=40.0, open_time="08:00", close_time="20:00",
    description="Meeting room with projector and whiteboard.",
)
desk1 = get_or_create_resource(
    name="Hot Desk 12", type=ResourceTypeEnum.table, location="Coworking Zone A",
    capacity=1, price_per_hour=5.0, open_time="07:00", close_time="22:00",
    description="Single hot desk with monitor.",
)
clinic_equipment = get_or_create_resource(
    name="MRI Scanner", type=ResourceTypeEnum.equipment, location="Radiology Wing",
    capacity=1, price_per_hour=120.0, open_time="08:00", close_time="18:00",
    description="MRI scanning equipment, requires technician supervision.",
)
consult_service = get_or_create_resource(
    name="Dr. Lee Consultation", type=ResourceTypeEnum.service, location="Clinic Room 3",
    capacity=1, price_per_hour=60.0, open_time="09:00", close_time="17:00",
    description="General consultation with Dr. Lee.",
)

print("Seeding sample bookings...")
now = datetime.now()

def get_or_create_booking(resource, cust, start, end, status=BookingStatusEnum.confirmed):
    existing = db.query(Booking).filter(
        Booking.resource_id == resource.id, Booking.start_time == start
    ).first()
    if existing:
        return existing
    hours = (end - start).total_seconds() / 3600
    booking = Booking(
        resource_id=resource.id, customer_id=cust.id, start_time=start, end_time=end,
        status=status, party_size=1, total_price=round(hours * resource.price_per_hour, 2),
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking

# A few upcoming and past bookings for dashboard/report demo data.
get_or_create_booking(meeting_room, customer, now + timedelta(hours=3), now + timedelta(hours=4))
get_or_create_booking(desk1, customer2, now + timedelta(days=1, hours=1), now + timedelta(days=1, hours=5))
get_or_create_booking(room1, customer, now - timedelta(days=2), now - timedelta(days=1), status=BookingStatusEnum.completed)
get_or_create_booking(consult_service, customer2, now + timedelta(days=2, hours=2), now + timedelta(days=2, hours=3))

db.close()
print("Done! Seeded demo accounts:")
print("  admin@bookit.com / admin123")
print("  staff@bookit.com / staff123")
print("  customer@bookit.com / customer123")
