"""Rate-limited WhatsApp distribution via Twilio."""

from __future__ import annotations

import os
import time
from datetime import datetime

import structlog
from sqlalchemy.orm import Session
from twilio.rest import Client as TwilioClient

from .config import WhatsAppConfig
from .db import ArtifactVersion, WhatsAppDelivery, WhatsAppSubscriber

logger = structlog.get_logger()


class WhatsAppSender:
    def __init__(self, config: WhatsAppConfig, session: Session):
        self.config = config
        self.db = session
        account_sid = os.environ.get("TWILIO_ACCOUNT_SID", "")
        auth_token = os.environ.get("TWILIO_AUTH_TOKEN", "")
        self.twilio = TwilioClient(account_sid, auth_token) if account_sid else None
        self.from_number = os.environ.get("WHATSAPP_PHONE_ID", "")

    def send_to_subscribers(
        self,
        version: ArtifactVersion,
        subscribers: list[WhatsAppSubscriber] | None = None,
    ) -> list[WhatsAppDelivery]:
        """Send an approved artifact to all active subscribers, rate-limited."""
        if not self.twilio:
            logger.warning("whatsapp.no_client", reason="Missing Twilio credentials")
            return []

        if subscribers is None:
            subscribers = (
                self.db.query(WhatsAppSubscriber)
                .filter_by(status="active")
                .all()
            )

        deliveries = []
        interval = 1.0 / self.config.rate_limit_per_second

        for subscriber in subscribers:
            # Skip if already delivered
            existing = (
                self.db.query(WhatsAppDelivery)
                .filter_by(artifact_version_id=version.id, subscriber_id=subscriber.id)
                .filter(WhatsAppDelivery.delivery_status.in_(["sent", "delivered", "read"]))
                .first()
            )
            if existing:
                continue

            delivery = self._send_single(version, subscriber)
            deliveries.append(delivery)
            time.sleep(interval)

        self.db.flush()
        logger.info(
            "whatsapp.batch_sent",
            version_id=version.id,
            sent=len([d for d in deliveries if d.delivery_status == "sent"]),
            failed=len([d for d in deliveries if d.delivery_status == "failed"]),
        )
        return deliveries

    def _send_single(
        self,
        version: ArtifactVersion,
        subscriber: WhatsAppSubscriber,
    ) -> WhatsAppDelivery:
        """Send to a single subscriber with retry."""
        delivery = WhatsAppDelivery(
            artifact_version_id=version.id,
            subscriber_id=subscriber.id,
            delivery_status="queued",
        )
        self.db.add(delivery)

        for attempt in range(self.config.max_retries + 1):
            try:
                message = self.twilio.messages.create(
                    from_=f"whatsapp:{self.from_number}",
                    to=f"whatsapp:{subscriber.phone_number}",
                    media_url=[version.url] if version.url else None,
                    body=f"Daily Rambam content",
                )
                delivery.whatsapp_message_id = message.sid
                delivery.sent_at = datetime.utcnow()
                delivery.delivery_status = "sent"
                delivery.retry_count = attempt

                logger.info(
                    "whatsapp.sent",
                    subscriber_id=subscriber.id,
                    message_sid=message.sid,
                )
                return delivery

            except Exception as e:
                delivery.retry_count = attempt + 1
                delivery.error_message = str(e)
                if attempt < self.config.max_retries:
                    backoff = 2 ** attempt
                    time.sleep(backoff)
                    logger.warning(
                        "whatsapp.retry",
                        subscriber_id=subscriber.id,
                        attempt=attempt + 1,
                        error=str(e),
                    )

        delivery.delivery_status = "failed"
        logger.error(
            "whatsapp.failed",
            subscriber_id=subscriber.id,
            error=delivery.error_message,
        )
        return delivery
