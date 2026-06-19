import asyncio
import json
import signal
from typing import Any, Dict

from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaError

from app.core.config import settings
from app.core.logging import get_logger, setup_logging
from app.db.base import AsyncSessionLocal
from app.kafka.handlers import NotificationEventHandler, RetryEventHandler

logger = get_logger(__name__)

_running = True


def _handle_shutdown(signum, frame):
    global _running
    _running = False
    logger.info("shutdown_signal_received", signal=signum)


async def consume_notification_events() -> None:
    consumer = AIOKafkaConsumer(
        settings.KAFKA_TOPIC_NOTIFICATION_EVENTS,
        settings.KAFKA_TOPIC_RETRY,
        bootstrap_servers=settings.kafka_bootstrap_servers_list,
        group_id=settings.KAFKA_CONSUMER_GROUP_ID,
        auto_offset_reset=settings.KAFKA_AUTO_OFFSET_RESET,
        enable_auto_commit=False,
        session_timeout_ms=settings.KAFKA_SESSION_TIMEOUT_MS,
        heartbeat_interval_ms=settings.KAFKA_HEARTBEAT_INTERVAL_MS,
        max_poll_records=settings.KAFKA_MAX_POLL_RECORDS,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
    )

    await consumer.start()
    logger.info("kafka_consumer_started", topics=[settings.KAFKA_TOPIC_NOTIFICATION_EVENTS, settings.KAFKA_TOPIC_RETRY])

    try:
        async for msg in consumer:
            if not _running:
                break

            try:
                payload: Dict[str, Any] = msg.value
                topic = msg.topic

                logger.info(
                    "message_received",
                    topic=topic,
                    partition=msg.partition,
                    offset=msg.offset,
                    key=msg.key,
                )

                async with AsyncSessionLocal() as session:
                    if topic == settings.KAFKA_TOPIC_NOTIFICATION_EVENTS:
                        handler = NotificationEventHandler(session)
                        await handler.handle(payload)
                    elif topic == settings.KAFKA_TOPIC_RETRY:
                        handler = RetryEventHandler(session)
                        await handler.handle(payload)

                await consumer.commit()

            except Exception as e:
                logger.error(
                    "consumer_message_processing_failed",
                    error=str(e),
                    topic=msg.topic,
                    offset=msg.offset,
                )
                # Commit anyway to avoid infinite loop; DLQ handled inside handler
                try:
                    await consumer.commit()
                except Exception:
                    pass

    finally:
        await consumer.stop()
        logger.info("kafka_consumer_stopped")


async def main() -> None:
    setup_logging()
    signal.signal(signal.SIGINT, _handle_shutdown)
    signal.signal(signal.SIGTERM, _handle_shutdown)

    logger.info("starting_kafka_consumer")
    await consume_notification_events()


if __name__ == "__main__":
    asyncio.run(main())
