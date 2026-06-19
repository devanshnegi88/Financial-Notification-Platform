import asyncio
import json
import signal
from typing import Any, Dict

import aio_pika
from aio_pika.abc import AbstractIncomingMessage

from app.core.logging import get_logger, setup_logging
from app.rabbitmq.client import (
    QUEUE_CRITICAL,
    QUEUE_HIGH,
    QUEUE_LOW,
    QUEUE_MEDIUM,
    get_rabbitmq_channel,
    setup_topology,
)

logger = get_logger(__name__)
_running = True


def _handle_shutdown(signum, frame):
    global _running
    _running = False
    logger.info("rabbitmq_consumer_shutdown_signal", signal=signum)


async def process_delivery_message(message: AbstractIncomingMessage) -> None:
    async with message.process(requeue=False):
        try:
            payload: Dict[str, Any] = json.loads(message.body.decode("utf-8"))
            notification_id = payload.get("notification_id")
            channel = payload.get("channel")
            retry_count = payload.get("retry_count", 0)

            logger.info(
                "rabbitmq_delivery_message_received",
                notification_id=notification_id,
                channel=channel,
                retry_count=retry_count,
            )

            from app.celery.tasks import send_notification_task
            send_notification_task.apply_async(
                args=[notification_id],
                queue="notifications",
            )

        except Exception as e:
            logger.error(
                "rabbitmq_delivery_processing_failed",
                error=str(e),
                body=message.body.decode("utf-8", errors="replace"),
            )
            # Message will go to DLQ via x-dead-letter-exchange
            raise


async def consume_all_queues() -> None:
    channel = await get_rabbitmq_channel()
    await setup_topology()

    # Consume from all priority queues — critical gets highest prefetch priority
    queue_configs = [
        (QUEUE_CRITICAL, 2),   # lower prefetch = faster processing per message
        (QUEUE_HIGH,     5),
        (QUEUE_MEDIUM,   10),
        (QUEUE_LOW,      20),
    ]

    consumers = []
    for queue_name, prefetch in queue_configs:
        dedicated_channel = await (await channel.connection.channel())
        await dedicated_channel.set_qos(prefetch_count=prefetch)
        queue = await dedicated_channel.declare_queue(queue_name, durable=True, passive=True)
        consumer_tag = await queue.consume(process_delivery_message)
        consumers.append((queue_name, consumer_tag))
        logger.info("rabbitmq_consumer_started", queue=queue_name, prefetch=prefetch)

    logger.info("rabbitmq_all_consumers_active", count=len(consumers))

    # Keep running until shutdown signal
    while _running:
        await asyncio.sleep(1)

    logger.info("rabbitmq_consumers_stopping")


async def main() -> None:
    setup_logging()
    signal.signal(signal.SIGINT, _handle_shutdown)
    signal.signal(signal.SIGTERM, _handle_shutdown)
    logger.info("starting_rabbitmq_consumer")
    await consume_all_queues()


if __name__ == "__main__":
    asyncio.run(main())
