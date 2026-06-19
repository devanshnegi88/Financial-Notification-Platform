"""
Compliance audit endpoints required for TRAI/SEBI regulatory reporting.
Provides complete audit trails, DND check logs, and delivery proofs.
Per spec Section B2.3 (Compliance Audit Challenge).
"""
from datetime import date, datetime, timedelta
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.middleware.auth_middleware import require_admin, require_analyst
from app.models.notification import Notification
from app.models.notification_state_log import NotificationStateLog
from app.schemas.common import MessageResponse

router = APIRouter(prefix="/compliance", tags=["Compliance Audit"])


@router.get("/notification/{notification_id}/audit-trail", response_model=list)
async def get_notification_audit_trail(
    notification_id: UUID,
    _=Depends(require_analyst),
    db: AsyncSession = Depends(get_db),
):
    """
    Complete state history for a single notification.
    Required for TRAI compliance audit: proves DND check was performed before SMS dispatch.
    """
    result = await db.execute(
        select(NotificationStateLog)
        .where(NotificationStateLog.notification_id == notification_id)
        .order_by(NotificationStateLog.created_at)
    )
    logs = result.scalars().all()

    return [
        {
            "status": log.to_status,
            "from_status": log.from_status,
            "timestamp": log.created_at.isoformat(),
            "actor": log.actor,
            "metadata": log.metadata_,
        }
        for log in logs
    ]


@router.get("/dnd-check-report", response_model=list)
async def get_dnd_check_report(
    from_date: date = Query(default_factory=lambda: date.today() - timedelta(days=90)),
    to_date: date = Query(default_factory=date.today),
    channel: str = Query(default="sms"),
    _=Depends(require_analyst),
    db: AsyncSession = Depends(get_db),
):
    """
    Report showing every SMS sent with DND check timestamp and result.
    Required for TRAI audit: 12,847 DND violations context from spec.
    """
    from_dt = datetime.combine(from_date, datetime.min.time())
    to_dt = datetime.combine(to_date, datetime.max.time())

    # Get all state log entries where DND was checked (actor = dnd_service)
    result = await db.execute(
        select(NotificationStateLog)
        .where(
            and_(
                NotificationStateLog.actor == "dnd_service",
                NotificationStateLog.created_at >= from_dt,
                NotificationStateLog.created_at <= to_dt,
            )
        )
        .order_by(NotificationStateLog.created_at.desc())
        .limit(10000)
    )
    dnd_logs = result.scalars().all()

    return [
        {
            "notification_id": str(log.notification_id),
            "dnd_check_timestamp": log.created_at.isoformat(),
            "dnd_result": log.metadata_.get("dnd_check_result", "NOT_REGISTERED") if log.metadata_ else "NOT_REGISTERED",
            "classification": log.metadata_.get("classification", "TRANSACTIONAL") if log.metadata_ else "TRANSACTIONAL",
            "action_taken": log.to_status,
        }
        for log in dnd_logs
    ]


@router.get("/margin-call-delivery-proof", response_model=list)
async def get_margin_call_delivery_proof(
    from_date: date = Query(default_factory=lambda: date.today() - timedelta(days=30)),
    to_date: date = Query(default_factory=date.today),
    _=Depends(require_analyst),
    db: AsyncSession = Depends(get_db),
):
    """
    Delivery receipts proving margin calls were sent within SEBI timelines.
    RISK-001/RISK-002 must be delivered within 10 seconds of event.
    """
    from_dt = datetime.combine(from_date, datetime.min.time())
    to_dt = datetime.combine(to_date, datetime.max.time())

    result = await db.execute(
        select(Notification)
        .where(
            and_(
                Notification.event_type.in_(["RISK-001", "RISK-002", "RISK-003"]),
                Notification.created_at >= from_dt,
                Notification.created_at <= to_dt,
            )
        )
        .order_by(Notification.created_at.desc())
        .limit(5000)
    )
    notifications = result.scalars().all()

    records = []
    for n in notifications:
        latency_ms = None
        if n.delivered_at and n.created_at:
            latency_ms = int((n.delivered_at - n.created_at).total_seconds() * 1000)

        within_sebi_timeline = latency_ms is not None and latency_ms <= 10000  # 10 seconds

        records.append({
            "notification_id": str(n.id),
            "event_type": n.event_type,
            "channel": n.channel,
            "status": n.status,
            "created_at": n.created_at.isoformat(),
            "sent_at": n.sent_at.isoformat() if n.sent_at else None,
            "delivered_at": n.delivered_at.isoformat() if n.delivered_at else None,
            "latency_ms": latency_ms,
            "within_sebi_timeline_10s": within_sebi_timeline,
            "provider_message_id": n.provider_message_id,
        })

    return records


@router.get("/consent-records/{user_id}", response_model=list)
async def get_user_consent_records(
    user_id: UUID,
    _=Depends(require_analyst),
    db: AsyncSession = Depends(get_db),
):
    """
    All consent opt-in/opt-out records for a user.
    Required for WhatsApp Business Policy and IT Act 2000 compliance.
    """
    from sqlalchemy import text
    result = await db.execute(
        text("""
            SELECT id, user_id, channel, consent_type, classification,
                   ip_address, consent_text, source, created_at
            FROM consent_records
            WHERE user_id = :user_id
            ORDER BY created_at DESC
        """),
        {"user_id": str(user_id)},
    )
    rows = result.mappings().all()
    return [dict(r) for r in rows]


@router.get("/sebi-audit-report", response_model=dict)
async def get_sebi_audit_report(
    from_date: date = Query(default_factory=lambda: date.today() - timedelta(days=30)),
    to_date: date = Query(default_factory=date.today),
    _=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Comprehensive SEBI audit report covering mandatory notification delivery compliance.
    """
    from_dt = datetime.combine(from_date, datetime.min.time())
    to_dt = datetime.combine(to_date, datetime.max.time())
    from sqlalchemy import func

    mandatory_events = ["TXNX-001", "TXNX-002", "RISK-001", "RISK-002", "RISK-003", "REGX-001", "REGX-003"]

    total_mandatory = await db.scalar(
        select(func.count()).select_from(Notification).where(
            and_(
                Notification.event_type.in_(mandatory_events),
                Notification.created_at >= from_dt,
                Notification.created_at <= to_dt,
            )
        )
    )
    delivered_mandatory = await db.scalar(
        select(func.count()).select_from(Notification).where(
            and_(
                Notification.event_type.in_(mandatory_events),
                Notification.created_at >= from_dt,
                Notification.created_at <= to_dt,
                Notification.status == "delivered",
            )
        )
    )
    failed_mandatory = await db.scalar(
        select(func.count()).select_from(Notification).where(
            and_(
                Notification.event_type.in_(mandatory_events),
                Notification.created_at >= from_dt,
                Notification.created_at <= to_dt,
                Notification.status.in_(["failed", "dead"]),
            )
        )
    )
    dnd_violations = await db.scalar(
        select(func.count()).select_from(NotificationStateLog).where(
            and_(
                NotificationStateLog.actor == "dnd_service",
                NotificationStateLog.to_status == "DND_BLOCKED",
                NotificationStateLog.metadata_.op("->>")(
                    "classification"
                ) == "TRANSACTIONAL",
                NotificationStateLog.created_at >= from_dt,
                NotificationStateLog.created_at <= to_dt,
            )
        )
    )

    return {
        "period": {"from": str(from_date), "to": str(to_date)},
        "mandatory_notifications": {
            "total": total_mandatory or 0,
            "delivered": delivered_mandatory or 0,
            "failed": failed_mandatory or 0,
            "delivery_rate": round(
                (delivered_mandatory or 0) / (total_mandatory or 1) * 100, 2
            ),
        },
        "dnd_transactional_violations": dnd_violations or 0,
        "compliance_status": "COMPLIANT" if (dnd_violations or 0) == 0 else "NON_COMPLIANT",
        "generated_at": datetime.utcnow().isoformat(),
    }
