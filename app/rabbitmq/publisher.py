import json
import time
from typing import Any, Dict, Optional
from uuid import UUID

import aio_pika
from aio_pika import Message

from app.core.logging import get_logger
from app.rabbitmq.client import (
    EXCHANGE_NOTIFICATIONS,
    PRIORITY_QUEUE_MAP,
    QUEUE_MEDIUM,
    get_rabbitmq_channel,
)

logger = get_logger(__name__)

# Map spec integer priorities to routing keys
PRIORITY_ROUTING_MAP = {
    1: "critical",
    2: "high",
    3: "medium",
    5: "low",
}


class NotificationPublisher:
    """
    Publishes notification delivery tasks to RabbitMQ priority queues.

    Kafka handles event ingestion and fan-out (high throughput streaming).
    RabbitMQ handles delivery routing with priority queues (per spec Section A3.3).
    """

    async def publish(
        self,
        notification_id: str,
        channel: str,
        priority: int = 3,
        event_data: Optional[Dict[str, Any]] = None,
        retry_count: int = 0,
    ) -> None:
        routing_key = PRIORITY_ROUTING_MAP.get(priority, "medium")

        payload = {
            "notification_id": notification_id,
            "channel": channel,
            "priority": priority,
            "retry_count": retry_count,
            "event_data": event_data or {},
            "published_at": time.time(),
        }

        try:
            amqp_channel = await get_rabbitmq_channel()
            exchange = await amqp_channel.get_exchange(EXCHANGE_NOTIFICATIONS)

            message = Message(
                body=json.dumps(payload).encode("utf-8"),
                content_type="application/json",
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                priority=_amqp_priority(priority),
                headers={
                    "notification_id": notification_id,
                    "channel": channel,
                    "retry_count": str(retry_count),
                },
            )

            await exchange.publish(message, routing_key=routing_key)

            logger.info(
                "rabbitmq_notification_published",
                notification_id=notification_id,
                channel=channel,
                routing_key=routing_key,
                priority=priority,
            )
        except Exception as e:
            logger.error(
                "rabbitmq_publish_failed",
                notification_id=notification_id,
                error=str(e),
            )
            raise

    async def publish_batch(
        self,
        notifications: list[Dict[str, Any]],
    ) -> None:
        """Publish multiple notifications efficiently."""
        amqp_channel = await get_rabbitmq_channel()
        exchange = await amqp_channel.get_exchange(EXCHANGE_NOTIFICATIONS)

        for notif in notifications:
            priority = notif.get("priority", 3)
            routing_key = PRIORITY_ROUTING_MAP.get(priority, "medium")
            payload = json.dumps(notif).encode("utf-8")

            message = Message(
                body=payload,
                content_type="application/json",
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                priority=_amqp_priority(priority),
            )
            await exchange.publish(message, routing_key=routing_key)

        logger.info("rabbitmq_batch_published", count=len(notifications))


def _amqp_priority(spec_priority: int) -> int:
    """
    Convert spec priority (1=critical, 5=low) to AMQP priority (0-9).
    Higher AMQP value = processed first.
    """
    mapping = {
        1: 9,   # CRITICAL → highest AMQP priority
        2: 7,   # HIGH
        3: 5,   # MEDIUM
        5: 2,   # LOW
    }
    return mapping.get(spec_priority, 5)
