"""Message board provider for Larry's messages."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..core.logging import get_logger
from .base import BaseProvider, ProviderData
from .registry import ProviderRegistry

logger = get_logger("providers.message_board")

# Shared message file location
MESSAGE_FILE = Path("larry_messages.json")


def get_messages() -> List[Dict[str, Any]]:
    """Read all messages from the message file."""
    if not MESSAGE_FILE.exists():
        return []
    try:
        data = json.loads(MESSAGE_FILE.read_text())
        return data.get("messages", [])
    except Exception as e:
        logger.error(f"Failed to read messages: {e}")
        return []


def add_message(
    text: str,
    category: str = "general",
    priority: str = "normal",
    expires_at: Optional[str] = None,
) -> Dict[str, Any]:
    """Add a new message to the board."""
    messages = get_messages()
    
    message = {
        "id": len(messages) + 1,
        "text": text,
        "category": category,
        "priority": priority,  # low, normal, high
        "created_at": dt.datetime.now().isoformat(),
        "expires_at": expires_at,
        "read": False,
    }
    
    messages.append(message)
    
    # Keep only last 50 messages
    if len(messages) > 50:
        messages = messages[-50:]
    
    MESSAGE_FILE.write_text(json.dumps({"messages": messages}, indent=2))
    logger.info(f"Message added: {text[:50]}...")
    
    return message


def get_latest_message(category: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Get the most recent non-expired message."""
    messages = get_messages()
    now = dt.datetime.now()
    
    for msg in reversed(messages):
        # Check expiry
        if msg.get("expires_at"):
            expires = dt.datetime.fromisoformat(msg["expires_at"])
            if now > expires:
                continue
        
        # Filter by category if specified
        if category and msg.get("category") != category:
            continue
        
        return msg
    
    return None


def clear_messages() -> int:
    """Clear all messages. Returns count of cleared messages."""
    messages = get_messages()
    count = len(messages)
    MESSAGE_FILE.write_text(json.dumps({"messages": []}, indent=2))
    return count


@ProviderRegistry.register("message_board")
class MessageBoardProvider(BaseProvider):
    """
    Message board provider for Larry's messages.
    
    Reads messages from a local JSON file that Larry can write to.
    Messages can have categories (general, workout, reminder, news)
    and priorities (low, normal, high).
    """

    name = "message_board"

    def _validate_config(self) -> None:
        """No required config for message board."""
        pass

    async def fetch(self) -> ProviderData:
        """Fetch latest messages."""
        try:
            messages = get_messages()
            latest = get_latest_message()
            
            # Filter active (non-expired) messages
            now = dt.datetime.now()
            active_messages = []
            for msg in messages:
                if msg.get("expires_at"):
                    expires = dt.datetime.fromisoformat(msg["expires_at"])
                    if now > expires:
                        continue
                active_messages.append(msg)
            
            return ProviderData(
                provider_name=self.name,
                fetched_at=dt.datetime.now(),
                data={
                    "available": True,
                    "latest": latest,
                    "messages": active_messages[-10:],  # Last 10 active
                    "total_count": len(messages),
                    "active_count": len(active_messages),
                },
                ttl_seconds=60,
            )

        except Exception as e:
            logger.error(f"Failed to fetch messages: {e}")
            return ProviderData(
                provider_name=self.name,
                fetched_at=dt.datetime.now(),
                data={
                    "available": False,
                    "error": str(e),
                },
                ttl_seconds=60,
            )
