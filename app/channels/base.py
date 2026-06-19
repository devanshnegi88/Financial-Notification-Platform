from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class ChannelResult:
    success: bool
    provider_message_id: Optional[str] = None
    provider_response: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    latency_ms: Optional[int] = None


class BaseChannel(ABC):
    @property
    @abstractmethod
    def channel_name(self) -> str:
        ...

    @abstractmethod
    async def send(
        self,
        recipient: str,
        subject: Optional[str],
        body: str,
        html_body: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> ChannelResult:
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        ...
