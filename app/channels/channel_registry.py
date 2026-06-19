from functools import lru_cache
from typing import Dict

from app.channels.base import BaseChannel
from app.channels.email_channel import EmailChannel
from app.channels.in_app_channel import InAppChannel
from app.channels.push_channel import PushChannel
from app.channels.sms_channel import SMSChannel
from app.channels.whatsapp_channel import WhatsAppChannel
from app.core.constants import NotificationChannel
from app.core.exceptions import ConfigurationError


_channel_instances: Dict[NotificationChannel, BaseChannel] = {}


def get_channel(channel: NotificationChannel) -> BaseChannel:
    if channel not in _channel_instances:
        if channel == NotificationChannel.SMS:
            _channel_instances[channel] = SMSChannel()
        elif channel == NotificationChannel.EMAIL:
            _channel_instances[channel] = EmailChannel()
        elif channel == NotificationChannel.WHATSAPP:
            _channel_instances[channel] = WhatsAppChannel()
        elif channel == NotificationChannel.PUSH:
            _channel_instances[channel] = PushChannel()
        elif channel == NotificationChannel.IN_APP:
            _channel_instances[channel] = InAppChannel()
        else:
            raise ConfigurationError(f"Unknown channel: {channel}")
    return _channel_instances[channel]


async def health_check_all() -> Dict[str, bool]:
    results = {}
    for channel in NotificationChannel:
        try:
            instance = get_channel(channel)
            results[channel.value] = await instance.health_check()
        except Exception:
            results[channel.value] = False
    return results
