"""
Generate simulated datasets per ZeTheta spec Section B4.

Dataset 1: notification_events.csv     (minimum 100,000 rows)
Dataset 2: user_profiles.csv           (minimum 10,000 rows)
Dataset 3: delivery_failures.csv       (minimum 5,000 rows)
Dataset 4: user_complaints.csv         (minimum 2,000 rows)

Run: python scripts/datasets/generate_datasets.py
"""
import csv
import json
import random
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ── Configuration ─────────────────────────────────────────────────────────────
OUTPUT_DIR = Path("data/datasets")
SEED = 42
random.seed(SEED)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Event taxonomy per spec A2 ─────────────────────────────────────────────────
EVENT_TYPES = [
    # 40% transaction events
    ("TXNX-001", 2, "sms,push,email", "transactional"),
    ("TXNX-002", 2, "sms,push,email", "transactional"),
    ("TXNX-003", 2, "push,sms", "transactional"),
    ("TXNX-004", 3, "email,push", "transactional"),
    ("TXNX-005", 2, "sms,push", "transactional"),
    # 20% risk events
    ("RISK-001", 1, "sms,push,call", "transactional"),
    ("RISK-002", 1, "sms,push,email,call", "transactional"),
    ("RISK-003", 1, "sms,push,email", "transactional"),
    ("RISK-004", 2, "push,email", "transactional"),
    ("RISK-005", 3, "email,in_app", "transactional"),
    # 15% SIP events
    ("SIPX-001", 3, "push,whatsapp", "transactional"),
    ("SIPX-002", 2, "sms,email", "transactional"),
    ("SIPX-003", 2, "sms,push,email", "transactional"),
    ("SIPX-004", 5, "email,in_app", "promotional"),
    ("SIPX-005", 5, "push,in_app", "promotional"),
    # 15% market events
    ("MKTX-001", 2, "push,sms", "transactional"),
    ("MKTX-002", 1, "push,sms", "transactional"),
    ("MKTX-003", 5, "push", "promotional"),
    ("MKTX-004", 3, "push,email", "transactional"),
    ("MKTX-005", 3, "email,in_app", "promotional"),
    # 10% regulatory events
    ("REGX-001", 2, "sms,email,push", "transactional"),
    ("REGX-002", 3, "email,push", "transactional"),
    ("REGX-003", 2, "email", "transactional"),
    ("REGX-004", 3, "email,in_app", "transactional"),
    ("REGX-005", 5, "email", "informational"),
]

# Weights per spec B4.1
EVENT_WEIGHTS = (
    [8] * 5    # 40% TXNX
    + [4] * 5  # 20% RISK
    + [3] * 5  # 15% SIPX
    + [3] * 5  # 15% MKTX
    + [2] * 5  # 10% REGX
)

CHANNELS = ["sms", "email", "push", "whatsapp", "in_app"]
LANGUAGES = ["en"] * 20 + ["hi"] * 42 + ["mr"] * 18 + ["ta"] * 12 + ["te"] * 8
TIMEZONES = ["Asia/Kolkata"] * 90 + ["Asia/Mumbai"] * 10
STATUSES = ["delivered"] * 75 + ["failed"] * 8 + ["skipped"] * 10 + ["retrying"] * 4 + ["dead"] * 3
FAILURE_REASONS = [
    ("invalid_recipient", 35),
    ("provider_timeout", 20),
    ("rate_limited", 15),
    ("network_error", 10),
    ("invalid_template", 8),
    ("dnd_blocked", 7),
    ("expired_token", 5),
]
COMPLAINT_TYPES = [
    ("too_many_notifications", 35),
    ("wrong_time", 25),
    ("irrelevant_content", 20),
    ("wrong_channel", 12),
    ("missing_critical_notification", 8),
]
ACCOUNT_TYPES = ["basic"] * 50 + ["premium"] * 35 + ["HNI"] * 15
RISK_PROFILES = ["conservative"] * 40 + ["moderate"] * 40 + ["aggressive"] * 20
PROVIDERS = ["twilio", "msg91", "sendgrid", "fcm", "internal"]


def _random_phone() -> str:
    return f"+91{random.randint(7000000000, 9999999999)}"


def _random_email(name: str) -> str:
    domains = ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com"]
    return f"{name.lower().replace(' ', '.')}{random.randint(1, 999)}@{random.choice(domains)}"


def _market_hour_timestamp(base_date: datetime) -> datetime:
    """80% during market hours 09:15-15:30 IST, 10% pre, 10% post."""
    r = random.random()
    if r < 0.80:
        hour = random.randint(9, 15)
        minute = random.randint(15 if hour == 9 else 0, 30 if hour == 15 else 59)
    elif r < 0.90:
        hour = random.randint(7, 9)
        minute = random.randint(0, 14)
    else:
        hour = random.randint(15, 20)
        minute = random.randint(31, 59)
    return base_date.replace(hour=hour, minute=minute, second=random.randint(0, 59))


# ── Dataset 1: notification_events.csv ────────────────────────────────────────
def generate_notification_events(num_rows: int = 100_000) -> list[str]:
    print(f"Generating notification_events.csv ({num_rows:,} rows)...")
    filepath = OUTPUT_DIR / "notification_events.csv"
    user_ids = [str(uuid.uuid4()) for _ in range(10_000)]
    base_date = datetime.now(timezone.utc) - timedelta(days=30)

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "event_id", "event_type", "user_id", "timestamp", "priority",
            "source_system", "payload", "channel_preference", "status",
        ])

        for _ in range(num_rows):
            event_def = random.choices(EVENT_TYPES, weights=EVENT_WEIGHTS, k=1)[0]
            event_code, priority, channels_str, classification = event_def
            day_offset = random.randint(0, 29)
            ts = _market_hour_timestamp(base_date + timedelta(days=day_offset))

            # Build realistic payload per event type
            payload = _build_payload(event_code)
            status = random.choice(STATUSES)

            writer.writerow([
                f"EVT-{uuid.uuid4().hex[:16].upper()}",
                event_code,
                random.choice(user_ids),
                ts.isoformat(),
                priority,
                _source_system(event_code),
                json.dumps(payload),
                channels_str.split(",")[0],
                status,
            ])

    print(f"  → {filepath}")
    return [str(filepath)]


def _source_system(event_code: str) -> str:
    prefix = event_code.split("-")[0]
    return {
        "TXNX": "trading_engine",
        "RISK": "margin_engine",
        "SIPX": "investment_platform",
        "MKTX": "market_data_feed",
        "REGX": "compliance_system",
    }.get(prefix, "core_system")


def _build_payload(event_code: str) -> dict:
    amount = round(random.uniform(500, 500000), 2)
    if event_code.startswith("RISK"):
        return {
            "shortfall_amount": amount,
            "current_margin": round(amount * 0.75, 2),
            "required_margin": amount,
            "deadline": (datetime.utcnow() + timedelta(hours=1)).isoformat() + "Z",
            "auto_square_off_time": (datetime.utcnow() + timedelta(hours=2)).isoformat() + "Z",
        }
    if event_code.startswith("TXNX"):
        stocks = ["RELIANCE", "TCS", "INFY", "HDFC", "ICICIBANK", "SBIN", "BAJFINANCE"]
        return {
            "stock_name": random.choice(stocks),
            "qty": random.randint(1, 500),
            "price": round(random.uniform(100, 5000), 2),
            "total": round(amount, 2),
            "order_id": f"ORD-{uuid.uuid4().hex[:8].upper()}",
        }
    if event_code.startswith("SIPX"):
        funds = ["Mirae Asset Large Cap", "Axis Bluechip", "SBI Small Cap", "Parag Parikh Flexi"]
        return {
            "fund_name": random.choice(funds),
            "amount": round(random.uniform(1000, 50000), 2),
            "units_allotted": round(random.uniform(10, 1000), 4),
            "nav": round(random.uniform(10, 200), 4),
        }
    if event_code.startswith("MKTX"):
        stocks = ["NIFTY50", "SENSEX", "RELIANCE", "TCS", "INFY"]
        return {
            "stock": random.choice(stocks),
            "current_price": round(random.uniform(100, 5000), 2),
            "target_price": round(random.uniform(100, 5000), 2),
            "direction": random.choice(["up", "down"]),
        }
    return {"event_code": event_code, "amount": amount}


# ── Dataset 2: user_profiles.csv ──────────────────────────────────────────────
def generate_user_profiles(num_rows: int = 10_000) -> None:
    print(f"Generating user_profiles.csv ({num_rows:,} rows)...")
    filepath = OUTPUT_DIR / "user_profiles.csv"
    first_names = ["Rahul", "Priya", "Amit", "Sneha", "Raj", "Pooja", "Vikram", "Anita",
                   "Suresh", "Kavya", "Arjun", "Deepa", "Nikhil", "Shreya", "Rohit"]
    last_names = ["Sharma", "Patel", "Singh", "Kumar", "Gupta", "Joshi", "Mehta",
                  "Nair", "Reddy", "Verma", "Iyer", "Shah", "Rao", "Bose", "Das"]

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "user_id", "name", "phone", "email", "language", "timezone",
            "dnd_status", "dnd_categories", "account_type", "risk_profile",
            "notification_preferences", "quiet_hours_start", "quiet_hours_end",
            "created_at",
        ])

        for i in range(num_rows):
            name = f"{random.choice(first_names)} {random.choice(last_names)}"
            lang = random.choice(LANGUAGES)
            dnd_registered = random.random() < 0.30  # 30% DND per spec
            dnd_cats = "1" if dnd_registered and random.random() < 0.5 else ""

            prefs = {
                "sms": not dnd_registered or random.random() > 0.3,
                "email": True,
                "push": True,
                "whatsapp": random.random() > 0.6,
                "in_app": True,
            }

            created = datetime.now(timezone.utc) - timedelta(days=random.randint(1, 730))
            writer.writerow([
                str(uuid.uuid4()),
                name,
                _random_phone(),
                _random_email(name),
                lang,
                random.choice(TIMEZONES),
                "registered" if dnd_registered else "not_registered",
                dnd_cats,
                random.choice(ACCOUNT_TYPES),
                random.choice(RISK_PROFILES),
                json.dumps(prefs),
                random.choice([21, 22, 23]),
                random.choice([6, 7, 8]),
                created.isoformat(),
            ])

    print(f"  → {filepath}")


# ── Dataset 3: delivery_failures.csv ─────────────────────────────────────────
def generate_delivery_failures(num_rows: int = 5_000) -> None:
    print(f"Generating delivery_failures.csv ({num_rows:,} rows)...")
    filepath = OUTPUT_DIR / "delivery_failures.csv"
    failure_pool = []
    for reason, weight in FAILURE_REASONS:
        failure_pool.extend([reason] * weight)

    base_date = datetime.now(timezone.utc) - timedelta(days=90)

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "notification_id", "channel", "provider", "failure_code",
            "failure_reason", "retry_count", "final_status", "timestamp",
        ])

        for _ in range(num_rows):
            channel = random.choice(CHANNELS)
            reason = random.choice(failure_pool)
            retries = random.randint(0, 5)
            final = "dead" if retries >= 3 else "failed"
            ts = base_date + timedelta(days=random.randint(0, 89), seconds=random.randint(0, 86400))

            provider_map = {
                "sms": random.choice(["msg91", "twilio"]),
                "email": "sendgrid",
                "push": "fcm",
                "whatsapp": "twilio",
                "in_app": "internal",
            }

            writer.writerow([
                str(uuid.uuid4()),
                channel,
                provider_map[channel],
                f"ERR_{reason.upper()[:6]}",
                reason,
                retries,
                final,
                ts.isoformat(),
            ])

    print(f"  → {filepath}")


# ── Dataset 4: user_complaints.csv ────────────────────────────────────────────
def generate_user_complaints(num_rows: int = 2_000) -> None:
    print(f"Generating user_complaints.csv ({num_rows:,} rows)...")
    filepath = OUTPUT_DIR / "user_complaints.csv"
    complaint_pool = []
    for ctype, weight in COMPLAINT_TYPES:
        complaint_pool.extend([ctype] * weight)

    descriptions = {
        "too_many_notifications": [
            "Getting too many alerts, very annoying",
            "Spam level notifications every day",
            "Please reduce notification frequency",
        ],
        "wrong_time": [
            "Received notification at 2 AM, woke me up",
            "Getting alerts during my sleep hours",
            "Please respect quiet hours",
        ],
        "irrelevant_content": [
            "Getting stock alerts for stocks I don't hold",
            "Receiving SIP reminders for closed SIPs",
            "Content not relevant to my portfolio",
        ],
        "wrong_channel": [
            "Prefer WhatsApp over SMS",
            "Please send to email not push",
            "Getting SMS when I opted for email only",
        ],
        "missing_critical_notification": [
            "Did not receive margin call alert",
            "Missed order execution confirmation",
            "Critical alert was not delivered",
        ],
    }

    base_date = datetime.now(timezone.utc) - timedelta(days=30)
    event_codes = [e[0] for e in EVENT_TYPES]

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "complaint_id", "user_id", "complaint_type", "channel",
            "event_type", "description", "timestamp", "resolved",
        ])

        for _ in range(num_rows):
            ctype = random.choice(complaint_pool)
            ts = base_date + timedelta(days=random.randint(0, 29), seconds=random.randint(0, 86400))
            writer.writerow([
                str(uuid.uuid4()),
                str(uuid.uuid4()),
                ctype,
                random.choice(CHANNELS),
                random.choice(event_codes),
                random.choice(descriptions[ctype]),
                ts.isoformat(),
                random.choice(["true", "false", "false"]),
            ])

    print(f"  → {filepath}")


if __name__ == "__main__":
    print("=" * 60)
    print("Financial Notification Platform — Dataset Generator")
    print("ZeTheta Spec Section B4")
    print("=" * 60)

    generate_notification_events(100_000)
    generate_user_profiles(10_000)
    generate_delivery_failures(5_000)
    generate_user_complaints(2_000)

    print("\n✓ All datasets generated in:", OUTPUT_DIR.resolve())
    print("\nRow counts:")
    for f in OUTPUT_DIR.glob("*.csv"):
        with open(f) as fh:
            rows = sum(1 for _ in fh) - 1  # subtract header
        print(f"  {f.name}: {rows:,} rows")
