import json
from typing import Any, Dict, Optional
from uuid import UUID

from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaError

from app.core.config import settings
from app.core.exceptions import KafkaPublishError
from app.core.logging import get_logger

logger = get_logger(__name__)

_producer: Optional[AIOKafkaProducer] = None


async def get_producer() -> AIOKafkaProducer:
    global _producer
    if _producer is None:
        _producer = AIOKafkaProducer(
            bootstrap_servers=settings.kafka_bootstrap_servers_list,
            value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
            key_serializer=lambda k: k.encode("utf-8") if k else None,
            acks="all",
            enable_idempotence=True,
            max_in_flight_requests_per_connection=5,
            retries=5,
            compression_type="gzip",
        )
        await _producer.start()
        logger.info("Kafka producer started")
    return _producer


async def stop_producer() -> None:
    global _producer
    if _producer:
        await _producer.stop()
        _producer = None
        logger.info("Kafka producer stopped")


class NotificationEventProducer:
    def __init__(self, producer: AIOKafkaProducer):
        self.producer = producer

    async def publish_notification_event(
        self,
        payload: Dict[str, Any],
        partition_key: Optional[str] = None,
    ) -> None:
        try:
            await self.producer.send_and_wait(
                topic=settings.KAFKA_TOPIC_NOTIFICATION_EVENTS,
                value=payload,
                key=partition_key,
            )
            logger.info(
                "notification_event_published",
                topic=settings.KAFKA_TOPIC_NOTIFICATION_EVENTS,
                event_type=payload.get("event_type"),
                user_id=payload.get("user_id"),
            )
        except KafkaError as e:
            logger.error("kafka_publish_failed", error=str(e), topic=settings.KAFKA_TOPIC_NOTIFICATION_EVENTS)
            raise KafkaPublishError(f"Failed to publish notification event: {e}") from e

    async def publish_status_update(
        self,
        notification_id: str,
        status: str,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        payload = {
            "notification_id": notification_id,
            "status": status,
            **(extra or {}),
        }
        try:
            await self.producer.send_and_wait(
                topic=settings.KAFKA_TOPIC_NOTIFICATION_STATUS,
                value=payload,
                key=notification_id,
            )
        except KafkaError as e:
            logger.error("kafka_status_publish_failed", error=str(e))
            raise KafkaPublishError(f"Failed to publish status update: {e}") from e

    async def publish_to_dlq(self, original_payload: Dict[str, Any], error: str) -> None:
        payload = {
            "original": original_payload,
            "error": error,
        }
        try:
            await self.producer.send_and_wait(
                topic=settings.KAFKA_TOPIC_DLQ,
                value=payload,
            )
            logger.warning("message_sent_to_dlq", error=error)
        except KafkaError as e:
            logger.error("dlq_publish_failed", error=str(e))

    async def publish_analytics_event(self, payload: Dict[str, Any]) -> None:
        try:
            await self.producer.send_and_wait(
                topic=settings.KAFKA_TOPIC_ANALYTICS,
                value=payload,
            )
        except KafkaError as e:
            logger.error("analytics_publish_failed", error=str(e))

    async def publish_retry(self, payload: Dict[str, Any], delay_seconds: int) -> None:
        payload["retry_after"] = delay_seconds
        try:
            await self.producer.send_and_wait(
                topic=settings.KAFKA_TOPIC_RETRY,
                value=payload,
            )
        except KafkaError as e:
            logger.error("retry_publish_failed", error=str(e))
            raise KafkaPublishError(f"Failed to publish retry: {e}") from e
