"""Helper utilities for sending Slack notifications."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import requests
from decouple import config

logger = logging.getLogger(__name__)

SLACK_BOT_TOKEN = config('SLACK_BOT_TOKEN', default='')
SLACK_FALLBACK_CHANNEL = config('SLACK_FALLBACK_CHANNEL', default='')
SLACK_TIMEOUT = float(config('SLACK_TIMEOUT', default='6'))

_API_BASE = 'https://slack.com/api/'


def _slack_api_post(method: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Internal helper that POSTs to the Slack Web API and returns the parsed JSON."""
    if not SLACK_BOT_TOKEN:
        logger.debug("Slack notification skipped: SLACK_BOT_TOKEN not configured")
        return {"ok": False, "error": "missing_slack_token"}

    url = f"{_API_BASE}{method}"
    headers = {
        'Authorization': f'Bearer {SLACK_BOT_TOKEN}',
        'Content-Type': 'application/json; charset=utf-8',
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=SLACK_TIMEOUT)
    except Exception as exc:  # pragma: no cover - network failure is nondeterministic
        logger.warning("Slack API request to %s failed: %s", method, exc)
        return {"ok": False, "error": str(exc)}

    try:
        data = response.json()
    except ValueError:
        logger.warning("Slack API %s returned non-JSON response: %s", method, response.text[:200])
        return {"ok": False, "error": "invalid_json"}

    if not data.get('ok'):
        logger.warning("Slack API %s responded with error: %s", method, data.get('error', 'unknown'))
    return data


def send_dm_to_user(user, text: str, blocks: Optional[list] = None) -> bool:
    """Send a direct Slack message to the given user model.

    The user must have ``slack_user_id`` populated with their Slack member ID (e.g. ``U123ABC``).
    """
    if not text:
        return False
    if not user or not getattr(user, 'slack_user_id', None):
        if SLACK_FALLBACK_CHANNEL and text:
            logger.debug("Slack DM fallback: user missing slack_user_id, posting to fallback channel")
            fallback_payload: Dict[str, Any] = {'channel': SLACK_FALLBACK_CHANNEL, 'text': text}
            post_result = _slack_api_post('chat.postMessage', fallback_payload)
            return bool(post_result.get('ok'))
        logger.debug("Slack DM skipped: user missing slack_user_id and no fallback channel")
        return False

    # Open / reuse a DM channel
    open_payload = {'users': user.slack_user_id}
    open_result = _slack_api_post('conversations.open', open_payload)
    channel_id = (open_result.get('channel') or {}).get('id')

    if not channel_id and SLACK_FALLBACK_CHANNEL:
        channel_id = SLACK_FALLBACK_CHANNEL
        logger.debug("Using fallback Slack channel %s for notification", SLACK_FALLBACK_CHANNEL)

    if not channel_id:
        return False

    message_payload: Dict[str, Any] = {
        'channel': channel_id,
        'text': text,
    }
    if blocks:
        message_payload['blocks'] = blocks

    post_result = _slack_api_post('chat.postMessage', message_payload)
    return bool(post_result.get('ok'))


def send_channel_message(channel, text: str, blocks: Optional[list] = None) -> bool:
    """Send a Slack message to a channel (or user ID acting as a channel)."""
    if not text or not channel:
        return False
    message_payload: Dict[str, Any] = {
        'channel': channel,
        'text': text,
    }
    if blocks:
        message_payload['blocks'] = blocks
    post_result = _slack_api_post('chat.postMessage', message_payload)
    return bool(post_result.get('ok'))


class SlackDisabled(Exception):
    """Raised when Slack is disabled (missing token)."""
    pass


def build_reminder_message(reminder):
    """Return a concise Slack message for a reminder instance."""
    try:
        status = 'COMPLETED' if getattr(reminder, 'completed', False) else 'PENDING'
        due_dt = getattr(reminder, 'reminder_start_date', None)
        if due_dt is not None:
            try:
                from django.utils import timezone
                local_due = timezone.localtime(due_dt)
                due_str = local_due.strftime('%Y-%m-%d %H:%M')
            except Exception:
                due_str = str(due_dt)
        else:
            due_str = 'n/a'
        desc = (getattr(reminder, 'description', '') or '').strip()
        if len(desc) > 300:
            desc = desc[:297] + '...'
        return f"Reminder {getattr(reminder,'unique_id','')} | {getattr(reminder,'title','(no title)')}\nDue: {due_str}\nStatus: {status}\n{desc}".strip()
    except Exception as exc:  # pragma: no cover
        logger.warning("Failed to build reminder message: %s", exc)
        return "Reminder update"


# Backward-compatible wrapper expected by tasks.py
def send_dm(user, text: str):
    """Wrapper for legacy import path; returns bool. Raises SlackDisabled if disabled."""
    if not SLACK_BOT_TOKEN:
        raise SlackDisabled("Slack token not configured")
    return send_dm_to_user(user, text)


# Add logging for lookup attempts (used externally)
def log_slack_lookup(email: str, success: bool, error: Optional[str] = None):
    if success:
        logger.info(f"Slack lookup success for {email}")
    else:
        logger.debug(f"Slack lookup failed for {email}: {error}")
