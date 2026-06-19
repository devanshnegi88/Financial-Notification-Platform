from typing import Any, Dict, Optional

from jinja2 import Environment, StrictUndefined, TemplateNotFound, select_autoescape
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import FinancialEventType, NotificationChannel
from app.core.logging import get_logger
from app.repositories.template_repository import TemplateRepository

logger = get_logger(__name__)

_jinja_env = Environment(
    autoescape=select_autoescape(["html", "xml"]),
    undefined=StrictUndefined,
    trim_blocks=True,
    lstrip_blocks=True,
)


class TemplateService:
    def __init__(self, session: AsyncSession):
        self.repo = TemplateRepository(session)

    async def render(
        self,
        event_type: FinancialEventType,
        channel: NotificationChannel,
        locale: str,
        context: Dict[str, Any],
        user=None,
    ) -> Optional[Dict[str, Any]]:
        template = await self.repo.get_by_event_channel_locale(event_type, channel, locale)
        if not template:
            return None

        render_context = {**context}
        if user:
            render_context["user_name"] = user.full_name
            render_context["user_email"] = user.email

        try:
            body_tmpl = _jinja_env.from_string(template.body)
            rendered_body = body_tmpl.render(**render_context)

            rendered_subject = None
            if template.subject:
                subject_tmpl = _jinja_env.from_string(template.subject)
                rendered_subject = subject_tmpl.render(**render_context)

            rendered_html = None
            if template.html_body:
                html_tmpl = _jinja_env.from_string(template.html_body)
                rendered_html = html_tmpl.render(**render_context)

            return {
                "subject": rendered_subject,
                "body": rendered_body,
                "html_body": rendered_html,
                "template_id": str(template.id),
            }
        except Exception as e:
            logger.error(
                "template_render_failed",
                template_id=str(template.id),
                error=str(e),
            )
            return None

    async def render_by_id(self, template_id: str, variables: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        from uuid import UUID
        from app.repositories.base import BaseRepository
        from app.models.template import NotificationTemplate

        repo = TemplateRepository(self.repo.session)
        template = await repo.get(UUID(template_id))
        if not template:
            return None

        try:
            body_tmpl = _jinja_env.from_string(template.body)
            rendered_body = body_tmpl.render(**variables)

            rendered_subject = None
            if template.subject:
                subject_tmpl = _jinja_env.from_string(template.subject)
                rendered_subject = subject_tmpl.render(**variables)

            return {
                "subject": rendered_subject,
                "body": rendered_body,
                "template_id": template_id,
            }
        except Exception as e:
            logger.error("template_render_by_id_failed", template_id=template_id, error=str(e))
            return None
