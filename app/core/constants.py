from enum import Enum


class FinancialEventType(str, Enum):
    # Transaction Events
    TRANSACTION_SUCCESS = "transaction.success"
    TRANSACTION_FAILURE = "transaction.failure"
    TRANSACTION_PENDING = "transaction.pending"
    TRANSACTION_REVERSED = "transaction.reversed"
    TRANSACTION_DISPUTED = "transaction.disputed"

    # Payment Events
    PAYMENT_DUE = "payment.due"
    PAYMENT_OVERDUE = "payment.overdue"
    PAYMENT_RECEIVED = "payment.received"
    PAYMENT_FAILED = "payment.failed"
    PAYMENT_INITIATED = "payment.initiated"

    # Account Events
    ACCOUNT_CREATED = "account.created"
    ACCOUNT_DEBIT = "account.debit"
    ACCOUNT_CREDIT = "account.credit"
    ACCOUNT_BLOCKED = "account.blocked"
    ACCOUNT_UNBLOCKED = "account.unblocked"
    ACCOUNT_CLOSED = "account.closed"
    ACCOUNT_LOW_BALANCE = "account.low_balance"
    ACCOUNT_STATEMENT_READY = "account.statement_ready"

    # Loan Events
    LOAN_APPROVED = "loan.approved"
    LOAN_REJECTED = "loan.rejected"
    LOAN_DISBURSED = "loan.disbursed"
    LOAN_EMI_DUE = "loan.emi_due"
    LOAN_EMI_PAID = "loan.emi_paid"
    LOAN_EMI_MISSED = "loan.emi_missed"
    LOAN_FORECLOSED = "loan.foreclosed"

    # Investment Events
    INVESTMENT_MATURED = "investment.matured"
    INVESTMENT_DIVIDEND = "investment.dividend"
    INVESTMENT_PURCHASE = "investment.purchase"
    INVESTMENT_REDEMPTION = "investment.redemption"

    # Security Events
    LOGIN_DETECTED = "security.login_detected"
    PASSWORD_CHANGED = "security.password_changed"
    OTP_GENERATED = "security.otp_generated"
    SUSPICIOUS_ACTIVITY = "security.suspicious_activity"

    # KYC Events
    KYC_APPROVED = "kyc.approved"
    KYC_REJECTED = "kyc.rejected"
    KYC_PENDING = "kyc.pending"

    # Offer Events
    OFFER_AVAILABLE = "offer.available"
    OFFER_EXPIRING = "offer.expiring"

    # General
    SYSTEM_MAINTENANCE = "system.maintenance"
    WELCOME = "onboarding.welcome"


class NotificationChannel(str, Enum):
    SMS = "sms"
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    PUSH = "push"
    IN_APP = "in_app"


class NotificationStatus(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"
    DEAD = "dead"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


class NotificationPriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class UserRole(str, Enum):
    SUPERADMIN = "superadmin"
    ADMIN = "admin"
    MANAGER = "manager"
    ANALYST = "analyst"
    USER = "user"


class SkipReason(str, Enum):
    DND_REGISTERED = "dnd_registered"
    QUIET_HOURS = "quiet_hours"
    FREQUENCY_CAPPED = "frequency_capped"
    USER_OPT_OUT = "user_opt_out"
    CHANNEL_DISABLED = "channel_disabled"
    INVALID_CONTACT = "invalid_contact"


class RetryStrategy(str, Enum):
    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    FIXED = "fixed"


class DeliveryStatus(str, Enum):
    UNKNOWN = "unknown"
    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    BOUNCED = "bounced"
    OPENED = "opened"
    CLICKED = "clicked"


class Locale(str, Enum):
    ENGLISH = "en"
    HINDI = "hi"


# Priority-based channel order
CHANNEL_PRIORITY_MAP: dict[str, list[str]] = {
    NotificationPriority.CRITICAL: [
        NotificationChannel.SMS,
        NotificationChannel.PUSH,
        NotificationChannel.EMAIL,
        NotificationChannel.IN_APP,
    ],
    NotificationPriority.HIGH: [
        NotificationChannel.PUSH,
        NotificationChannel.SMS,
        NotificationChannel.EMAIL,
        NotificationChannel.IN_APP,
    ],
    NotificationPriority.MEDIUM: [
        NotificationChannel.EMAIL,
        NotificationChannel.PUSH,
        NotificationChannel.IN_APP,
    ],
    NotificationPriority.LOW: [
        NotificationChannel.EMAIL,
        NotificationChannel.IN_APP,
    ],
}

# Events that bypass quiet hours
CRITICAL_EVENTS = {
    FinancialEventType.SUSPICIOUS_ACTIVITY,
    FinancialEventType.ACCOUNT_BLOCKED,
    FinancialEventType.TRANSACTION_FAILURE,
    FinancialEventType.OTP_GENERATED,
    FinancialEventType.LOAN_EMI_MISSED,
}

# Events that bypass DND
DND_EXEMPT_EVENTS = {
    FinancialEventType.OTP_GENERATED,
    FinancialEventType.SUSPICIOUS_ACTIVITY,
    FinancialEventType.ACCOUNT_BLOCKED,
}

# Default retry counts per channel
CHANNEL_MAX_RETRIES: dict[str, int] = {
    NotificationChannel.SMS: 3,
    NotificationChannel.EMAIL: 5,
    NotificationChannel.WHATSAPP: 3,
    NotificationChannel.PUSH: 3,
    NotificationChannel.IN_APP: 1,
}

# Retry delays in seconds (per attempt)
RETRY_DELAY_SCHEDULE = [60, 300, 900, 3600, 7200]
