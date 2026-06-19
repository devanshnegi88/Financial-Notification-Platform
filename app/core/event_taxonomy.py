"""
Financial Event Taxonomy per ZeTheta spec Section A2.
Uses coded event types (TXNX-001, RISK-001, etc.) with integer priorities (1=CRITICAL, 5=LOW).
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class EventPriority(int, Enum):
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 5


class NotificationChannel(str, Enum):
    SMS = "sms"
    EMAIL = "email"
    PUSH = "push"
    WHATSAPP = "whatsapp"
    IN_APP = "in_app"
    CALL = "call"


class RegulatoryClass(str, Enum):
    SEBI_MANDATORY = "sebi_mandatory"
    AMFI_REQUIRED = "amfi_required"
    BANKING_REG = "banking_reg"
    IT_ACT_REQUIRED = "it_act_required"
    EXCHANGE_MANDATE = "exchange_mandate"
    BEST_PRACTICE = "best_practice"
    ADVISORY = "advisory"
    INFORMATIONAL = "informational"
    ENGAGEMENT = "engagement"


class MessageClassification(str, Enum):
    TRANSACTIONAL = "transactional"   # DND exempt
    PROMOTIONAL = "promotional"        # NOT DND exempt


@dataclass
class EventDefinition:
    code: str
    name: str
    priority: EventPriority
    regulatory: RegulatoryClass
    channels: List[NotificationChannel]
    max_latency_seconds: Optional[int]
    classification: MessageClassification
    personalisation_fields: List[str]
    bypass_quiet_hours: bool = False
    bypass_dnd: bool = False
    bypass_frequency_cap: bool = False


# ── Category 1: Transaction Events (TXNX-*) ──────────────────────────────────
TRANSACTION_EVENTS: List[EventDefinition] = [
    EventDefinition(
        code="TXNX-001",
        name="Buy Order Executed",
        priority=EventPriority.HIGH,
        regulatory=RegulatoryClass.SEBI_MANDATORY,
        channels=[NotificationChannel.SMS, NotificationChannel.PUSH, NotificationChannel.EMAIL],
        max_latency_seconds=30,
        classification=MessageClassification.TRANSACTIONAL,
        personalisation_fields=["stock_name", "qty", "price", "total", "portfolio_value", "order_id"],
    ),
    EventDefinition(
        code="TXNX-002",
        name="Sell Order Executed",
        priority=EventPriority.HIGH,
        regulatory=RegulatoryClass.SEBI_MANDATORY,
        channels=[NotificationChannel.SMS, NotificationChannel.PUSH, NotificationChannel.EMAIL],
        max_latency_seconds=30,
        classification=MessageClassification.TRANSACTIONAL,
        personalisation_fields=["stock_name", "qty", "price", "pnl", "tax_implication", "order_id"],
    ),
    EventDefinition(
        code="TXNX-003",
        name="Order Rejected",
        priority=EventPriority.HIGH,
        regulatory=RegulatoryClass.ADVISORY,
        channels=[NotificationChannel.PUSH, NotificationChannel.SMS],
        max_latency_seconds=15,
        classification=MessageClassification.TRANSACTIONAL,
        personalisation_fields=["reason_code", "alternative_action", "support_link", "order_id"],
    ),
    EventDefinition(
        code="TXNX-004",
        name="Dividend Credited",
        priority=EventPriority.MEDIUM,
        regulatory=RegulatoryClass.INFORMATIONAL,
        channels=[NotificationChannel.EMAIL, NotificationChannel.PUSH],
        max_latency_seconds=3600,
        classification=MessageClassification.TRANSACTIONAL,
        personalisation_fields=["company", "amount", "record_date", "bank_account"],
    ),
    EventDefinition(
        code="TXNX-005",
        name="Funds Deposited",
        priority=EventPriority.HIGH,
        regulatory=RegulatoryClass.BANKING_REG,
        channels=[NotificationChannel.SMS, NotificationChannel.PUSH],
        max_latency_seconds=60,
        classification=MessageClassification.TRANSACTIONAL,
        personalisation_fields=["amount", "source", "available_balance"],
    ),
]

# ── Category 2: Risk & Margin Events (RISK-*) ────────────────────────────────
RISK_EVENTS: List[EventDefinition] = [
    EventDefinition(
        code="RISK-001",
        name="Margin Call Warning",
        priority=EventPriority.CRITICAL,
        regulatory=RegulatoryClass.SEBI_MANDATORY,
        channels=[NotificationChannel.SMS, NotificationChannel.PUSH, NotificationChannel.CALL],
        max_latency_seconds=10,
        classification=MessageClassification.TRANSACTIONAL,
        personalisation_fields=["shortfall_amount", "deadline", "liquidation_risk", "affected_positions"],
        bypass_quiet_hours=True,
        bypass_dnd=True,
        bypass_frequency_cap=True,
    ),
    EventDefinition(
        code="RISK-002",
        name="Margin Shortfall",
        priority=EventPriority.CRITICAL,
        regulatory=RegulatoryClass.SEBI_MANDATORY,
        channels=[
            NotificationChannel.SMS, NotificationChannel.PUSH,
            NotificationChannel.EMAIL, NotificationChannel.CALL,
        ],
        max_latency_seconds=5,
        classification=MessageClassification.TRANSACTIONAL,
        personalisation_fields=["shortfall_amount", "action_required", "auto_square_off_time"],
        bypass_quiet_hours=True,
        bypass_dnd=True,
        bypass_frequency_cap=True,
    ),
    EventDefinition(
        code="RISK-003",
        name="Position Squared Off",
        priority=EventPriority.CRITICAL,
        regulatory=RegulatoryClass.SEBI_MANDATORY,
        channels=[NotificationChannel.SMS, NotificationChannel.PUSH, NotificationChannel.EMAIL],
        max_latency_seconds=15,
        classification=MessageClassification.TRANSACTIONAL,
        personalisation_fields=["positions_closed", "pnl_impact", "remaining_positions"],
        bypass_quiet_hours=True,
        bypass_dnd=True,
        bypass_frequency_cap=True,
    ),
    EventDefinition(
        code="RISK-004",
        name="Portfolio Risk Alert",
        priority=EventPriority.HIGH,
        regulatory=RegulatoryClass.ADVISORY,
        channels=[NotificationChannel.PUSH, NotificationChannel.EMAIL],
        max_latency_seconds=300,
        classification=MessageClassification.TRANSACTIONAL,
        personalisation_fields=["risk_metric", "affected_holdings", "suggestion"],
    ),
    EventDefinition(
        code="RISK-005",
        name="Concentration Alert",
        priority=EventPriority.MEDIUM,
        regulatory=RegulatoryClass.ADVISORY,
        channels=[NotificationChannel.EMAIL, NotificationChannel.IN_APP],
        max_latency_seconds=3600,
        classification=MessageClassification.TRANSACTIONAL,
        personalisation_fields=["sector_stock", "allocation_percent"],
    ),
]

# ── Category 3: SIP & Investment Events (SIPX-*) ─────────────────────────────
SIP_EVENTS: List[EventDefinition] = [
    EventDefinition(
        code="SIPX-001",
        name="SIP Due Reminder",
        priority=EventPriority.MEDIUM,
        regulatory=RegulatoryClass.BEST_PRACTICE,
        channels=[NotificationChannel.PUSH, NotificationChannel.WHATSAPP],
        max_latency_seconds=None,  # T-3 days
        classification=MessageClassification.TRANSACTIONAL,
        personalisation_fields=["fund_name", "amount", "due_date", "bank_balance_check"],
    ),
    EventDefinition(
        code="SIPX-002",
        name="SIP Executed",
        priority=EventPriority.HIGH,
        regulatory=RegulatoryClass.AMFI_REQUIRED,
        channels=[NotificationChannel.SMS, NotificationChannel.EMAIL],
        max_latency_seconds=7200,
        classification=MessageClassification.TRANSACTIONAL,
        personalisation_fields=["fund_name", "units_allotted", "nav", "total_investment"],
    ),
    EventDefinition(
        code="SIPX-003",
        name="SIP Failed",
        priority=EventPriority.HIGH,
        regulatory=RegulatoryClass.ADVISORY,
        channels=[NotificationChannel.SMS, NotificationChannel.PUSH, NotificationChannel.EMAIL],
        max_latency_seconds=1800,
        classification=MessageClassification.TRANSACTIONAL,
        personalisation_fields=["reason", "retry_date", "action_required"],
    ),
    EventDefinition(
        code="SIPX-004",
        name="SIP Step-Up Reminder",
        priority=EventPriority.LOW,
        regulatory=RegulatoryClass.ADVISORY,
        channels=[NotificationChannel.EMAIL, NotificationChannel.IN_APP],
        max_latency_seconds=None,  # Annual
        classification=MessageClassification.PROMOTIONAL,
        personalisation_fields=["current_amount", "suggested_increase", "goal_impact"],
    ),
    EventDefinition(
        code="SIPX-005",
        name="Goal Milestone Reached",
        priority=EventPriority.LOW,
        regulatory=RegulatoryClass.ENGAGEMENT,
        channels=[NotificationChannel.PUSH, NotificationChannel.IN_APP],
        max_latency_seconds=14400,
        classification=MessageClassification.PROMOTIONAL,
        personalisation_fields=["goal_name", "percent_complete", "projected_completion"],
    ),
]

# ── Category 4: Market & Price Events (MKTX-*) ───────────────────────────────
MARKET_EVENTS: List[EventDefinition] = [
    EventDefinition(
        code="MKTX-001",
        name="Price Alert Triggered",
        priority=EventPriority.HIGH,
        regulatory=RegulatoryClass.ADVISORY,
        channels=[NotificationChannel.PUSH, NotificationChannel.SMS],
        max_latency_seconds=15,
        classification=MessageClassification.TRANSACTIONAL,
        personalisation_fields=["stock", "target_price", "current_price", "direction"],
    ),
    EventDefinition(
        code="MKTX-002",
        name="Circuit Breaker Hit",
        priority=EventPriority.CRITICAL,
        regulatory=RegulatoryClass.EXCHANGE_MANDATE,
        channels=[NotificationChannel.PUSH, NotificationChannel.SMS],
        max_latency_seconds=10,
        classification=MessageClassification.TRANSACTIONAL,
        personalisation_fields=["stock", "circuit_level", "trading_halt_duration"],
        bypass_quiet_hours=True,
        bypass_dnd=True,
        bypass_frequency_cap=True,
    ),
    EventDefinition(
        code="MKTX-003",
        name="Market Open/Close",
        priority=EventPriority.LOW,
        regulatory=RegulatoryClass.ENGAGEMENT,
        channels=[NotificationChannel.PUSH],
        max_latency_seconds=None,  # At event time
        classification=MessageClassification.PROMOTIONAL,
        personalisation_fields=["index_levels", "portfolio_overnight_change"],
    ),
    EventDefinition(
        code="MKTX-004",
        name="52-Week High/Low",
        priority=EventPriority.MEDIUM,
        regulatory=RegulatoryClass.ADVISORY,
        channels=[NotificationChannel.PUSH, NotificationChannel.EMAIL],
        max_latency_seconds=1800,
        classification=MessageClassification.TRANSACTIONAL,
        personalisation_fields=["stock", "new_milestone", "holding_status"],
    ),
    EventDefinition(
        code="MKTX-005",
        name="Earnings Announcement",
        priority=EventPriority.MEDIUM,
        regulatory=RegulatoryClass.ADVISORY,
        channels=[NotificationChannel.EMAIL, NotificationChannel.IN_APP],
        max_latency_seconds=None,  # T-1 day
        classification=MessageClassification.PROMOTIONAL,
        personalisation_fields=["company", "date", "expected_eps", "historical_eps"],
    ),
]

# ── Category 5: Regulatory & Compliance Events (REGX-*) ──────────────────────
REGULATORY_EVENTS: List[EventDefinition] = [
    EventDefinition(
        code="REGX-001",
        name="KYC Expiry Warning",
        priority=EventPriority.HIGH,
        regulatory=RegulatoryClass.SEBI_MANDATORY,
        channels=[NotificationChannel.SMS, NotificationChannel.EMAIL, NotificationChannel.PUSH],
        max_latency_seconds=None,  # T-30, T-15, T-7 days
        classification=MessageClassification.TRANSACTIONAL,
        personalisation_fields=["expiry_date", "documents_needed", "submission_link"],
        bypass_dnd=True,
    ),
    EventDefinition(
        code="REGX-002",
        name="Nominee Update Reminder",
        priority=EventPriority.MEDIUM,
        regulatory=RegulatoryClass.ADVISORY,
        channels=[NotificationChannel.EMAIL, NotificationChannel.PUSH],
        max_latency_seconds=None,  # Quarterly
        classification=MessageClassification.TRANSACTIONAL,
        personalisation_fields=["current_nominee_status", "deadline", "update_link"],
    ),
    EventDefinition(
        code="REGX-003",
        name="Contract Note Generated",
        priority=EventPriority.HIGH,
        regulatory=RegulatoryClass.SEBI_MANDATORY,
        channels=[NotificationChannel.EMAIL],
        max_latency_seconds=None,  # T+1 EOD
        classification=MessageClassification.TRANSACTIONAL,
        personalisation_fields=["trade_date", "pdf_attachment", "summary"],
    ),
    EventDefinition(
        code="REGX-004",
        name="Tax Statement Available",
        priority=EventPriority.MEDIUM,
        regulatory=RegulatoryClass.IT_ACT_REQUIRED,
        channels=[NotificationChannel.EMAIL, NotificationChannel.IN_APP],
        max_latency_seconds=None,  # Quarterly
        classification=MessageClassification.TRANSACTIONAL,
        personalisation_fields=["period", "download_link", "key_figures"],
    ),
    EventDefinition(
        code="REGX-005",
        name="Regulatory Policy Change",
        priority=EventPriority.LOW,
        regulatory=RegulatoryClass.INFORMATIONAL,
        channels=[NotificationChannel.EMAIL],
        max_latency_seconds=86400,
        classification=MessageClassification.INFORMATIONAL,
        personalisation_fields=["change_summary", "impact_on_user", "effective_date"],
    ),
]

# ── Master registry ───────────────────────────────────────────────────────────
ALL_EVENTS: List[EventDefinition] = (
    TRANSACTION_EVENTS + RISK_EVENTS + SIP_EVENTS + MARKET_EVENTS + REGULATORY_EVENTS
)

EVENT_REGISTRY: dict[str, EventDefinition] = {e.code: e for e in ALL_EVENTS}


def get_event(code: str) -> Optional[EventDefinition]:
    return EVENT_REGISTRY.get(code)


def get_priority_for_event(code: str) -> EventPriority:
    event = EVENT_REGISTRY.get(code)
    return event.priority if event else EventPriority.MEDIUM


def is_dnd_exempt(code: str) -> bool:
    event = EVENT_REGISTRY.get(code)
    if not event:
        return False
    return event.bypass_dnd or event.classification == MessageClassification.TRANSACTIONAL


def is_quiet_hours_exempt(code: str) -> bool:
    event = EVENT_REGISTRY.get(code)
    return bool(event and event.bypass_quiet_hours)


def is_frequency_cap_exempt(code: str) -> bool:
    event = EVENT_REGISTRY.get(code)
    return bool(event and event.bypass_frequency_cap)


def get_mandatory_channels(code: str) -> List[NotificationChannel]:
    """Returns channels mandated by regulation that cannot be disabled by user."""
    event = EVENT_REGISTRY.get(code)
    if not event:
        return []
    if event.regulatory in (
        RegulatoryClass.SEBI_MANDATORY,
        RegulatoryClass.AMFI_REQUIRED,
        RegulatoryClass.BANKING_REG,
        RegulatoryClass.EXCHANGE_MANDATE,
    ):
        return event.channels
    return []


def is_promotional(code: str) -> bool:
    event = EVENT_REGISTRY.get(code)
    return bool(event and event.classification == MessageClassification.PROMOTIONAL)
