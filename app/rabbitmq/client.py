import asyncio
import json
from typing import Any, Callable, Dict, Optional

import aio_pika
from aio_pika import ExchangeType, Message, connect_robust
from aio_pika.abc import AbstractChannel, AbstractConnection, AbstractExchange, AbstractQueue

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# ── Exchange and Queue Names ──────────────────────────────────────────────────
EXCHANGE_NOTIFICATIONS = "notifications"
EXCHANGE_DLQ = "notifications.dlq"

QUEUE_CRITICAL = "notifications.critical"
QUEUE_HIGH = "notifications.high"
QUEUE_MEDIUM = "notifications.medium"
QUEUE_LOW = "notifications.low"
QUEUE_DLQ = "notifications.dead"

# RabbitMQ priority levels (1=highest, 5=lowest as per spec)
PRIORITY_QUEUE_MAP = {
    1: QUEUE_CRITICAL,   # CRITICAL
    2: QUEUE_HIGH,       # HIGH
    3: QUEUE_MEDIUM,     # MEDIUM
    5: QUEUE_LOW,        # LOW
}

_connection: Optional[AbstractConnection] = None
_channel: Optional[AbstractChannel] = None


async def get_rabbitmq_connection() -> AbstractConnection:
    global _connection
    if _connection is None or _connection.is_closed:
        _connection = await connect_robust(
            settings.RABBITMQ_URL,
            client_properties={"connection_name": "fnp-notification-service"},
        )
        logger.info("rabbitmq_connected", url=settings.RABBITMQ_HOST)
    return _connection


async def get_rabbitmq_channel() -> AbstractChannel:
    global _channel
    connection = await get_rabbitmq_connection()
    if _channel is None or _channel.is_closed:
        _channel = await connection.channel()
        await _channel.set_qos(prefetch_count=10)
        logger.info("rabbitmq_channel_opened")
    return _channel


async def close_rabbitmq() -> None:
    global _connection, _channel
    if _channel and not _channel.is_closed:
        await _channel.close()
        _channel = None
    if _connection and not _connection.is_closed:
        await _connection.close()
        _connection = None
    logger.info("rabbitmq_connection_closed")


async def setup_topology() -> None:
    """
    Declare all exchanges, queues, and bindings.
    Must be called once at application startup.
    """
    channel = await get_rabbitmq_channel()

    # ── Main notifications exchange (direct) ──────────────────────────────────
    exchange = await channel.declare_exchange(
        EXCHANGE_NOTIFICATIONS,
        ExchangeType.DIRECT,
        durable=True,
    )

    # ── Dead letter exchange ──────────────────────────────────────────────────
    dlq_exchange = await channel.declare_exchange(
        EXCHANGE_DLQ,
        ExchangeType.FANOUT,
        durable=True,
    )

    # ── Priority queues with DLQ routing ─────────────────────────────────────
    queue_configs = [
        (QUEUE_CRITICAL, "critical", 10),   # max 10 retries for CRITICAL
        (QUEUE_HIGH,     "high",     5),
        (QUEUE_MEDIUM,   "medium",   3),
        (QUEUE_LOW,      "low",      2),
    ]

    for queue_name, routing_key, _ in queue_configs:
        queue = await channel.declare_queue(
            queue_name,
            durable=True,
            arguments={
                "x-dead-letter-exchange": EXCHANGE_DLQ,
                "x-message-ttl": 86400000,   # 24h TTL before DLQ
                "x-max-priority": 10,         # Enable per-message priority
            },
        )
        await queue.bind(exchange, routing_key=routing_key)

    # ── Dead letter queue ─────────────────────────────────────────────────────
    dlq = await channel.declare_queue(QUEUE_DLQ, durable=True)
    await dlq.bind(dlq_exchange, routing_key="")

    logger.info(
        "rabbitmq_topology_configured",
        exchange=EXCHANGE_NOTIFICATIONS,
        queues=[QUEUE_CRITICAL, QUEUE_HIGH, QUEUE_MEDIUM, QUEUE_LOW, QUEUE_DLQ],
    )
