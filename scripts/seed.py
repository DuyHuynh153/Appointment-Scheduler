#!/usr/bin/env python
"""Seed script — inserts reference data if the database is empty.

Idempotent: checks for the seed dealer by its fixed ID before inserting.
Run from the project root (or inside the api container):

    python scripts/seed.py

All IDs below are fixed so that example curl commands in README.md
remain stable across re-seeds.
"""
from __future__ import annotations

import sys
import uuid

# Ensure project root is on the path when run from any working directory.
sys.path.insert(0, ".")

from app.db.session import SessionLocal  # noqa: E402
from app.models.dealer import Dealer  # noqa: E402
from app.models.service_bay import ServiceBay  # noqa: E402
from app.models.service_type import ServiceType  # noqa: E402
from app.models.technician import Technician  # noqa: E402
from app.models.vehicle import Vehicle  # noqa: E402

# ---------------------------------------------------------------------------
# Fixed seed IDs — keep in sync with README.md example curl commands
# ---------------------------------------------------------------------------

DEALER_ID = uuid.UUID("10000000-0000-0000-0000-000000000001")

TECH_A_ID = uuid.UUID("20000000-0000-0000-0000-000000000001")
TECH_B_ID = uuid.UUID("20000000-0000-0000-0000-000000000002")

BAY_A_ID = uuid.UUID("30000000-0000-0000-0000-000000000001")
BAY_B_ID = uuid.UUID("30000000-0000-0000-0000-000000000002")

VEHICLE_A_ID = uuid.UUID("40000000-0000-0000-0000-000000000001")
VEHICLE_B_ID = uuid.UUID("40000000-0000-0000-0000-000000000002")

OIL_CHANGE_ID = uuid.UUID("50000000-0000-0000-0000-000000000001")
TIRE_ROTATION_ID = uuid.UUID("50000000-0000-0000-0000-000000000002")
BRAKE_INSPECTION_ID = uuid.UUID("50000000-0000-0000-0000-000000000003")


def seed() -> None:
    db = SessionLocal()
    try:
        if db.get(Dealer, DEALER_ID) is not None:
            print("Database already seeded — skipping.")
            _print_ids()
            return

        dealer = Dealer(id=DEALER_ID, name="Sunrise Auto", timezone="UTC")
        db.add(dealer)

        db.add(Technician(id=TECH_A_ID, dealer_id=DEALER_ID, name="Alice Smith"))
        db.add(Technician(id=TECH_B_ID, dealer_id=DEALER_ID, name="Bob Jones"))

        db.add(ServiceBay(id=BAY_A_ID, dealer_id=DEALER_ID, name="Bay A"))
        db.add(ServiceBay(id=BAY_B_ID, dealer_id=DEALER_ID, name="Bay B"))

        db.add(Vehicle(id=VEHICLE_A_ID, dealer_id=DEALER_ID, vin="1HGCM82633A000001", owner_name="Jane Doe"))
        db.add(Vehicle(id=VEHICLE_B_ID, dealer_id=DEALER_ID, vin="1HGCM82633A000002", owner_name="John Smith"))

        db.add(ServiceType(id=OIL_CHANGE_ID, name="Oil Change", duration_minutes=30))
        db.add(ServiceType(id=TIRE_ROTATION_ID, name="Tire Rotation", duration_minutes=45))
        db.add(ServiceType(id=BRAKE_INSPECTION_ID, name="Brake Inspection", duration_minutes=60))

        db.commit()
        print("Seeded successfully.")
        _print_ids()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _print_ids() -> None:
    print("""
┌─────────────────────────────────────────────────────────────────────┐
│  Seed data reference                                                │
├──────────────────────┬──────────────────────────────────────────────┤
│  dealer_id           │  10000000-0000-0000-0000-000000000001        │
│  vehicle_id (Jane)   │  40000000-0000-0000-0000-000000000001        │
│  vehicle_id (John)   │  40000000-0000-0000-0000-000000000002        │
│  service_type: 30min │  50000000-0000-0000-0000-000000000001        │
│  service_type: 45min │  50000000-0000-0000-0000-000000000002        │
│  service_type: 60min │  50000000-0000-0000-0000-000000000003        │
└──────────────────────┴──────────────────────────────────────────────┘
""")


if __name__ == "__main__":
    seed()
