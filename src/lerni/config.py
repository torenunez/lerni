"""Configuration loading for Lerni."""

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class NotificationConfig:
    """Notification settings."""

    enabled: bool = True
    reminder_time: str = "09:00"


@dataclass
class ReviewConfig:
    """Review behavior settings."""

    lookahead_days: int = 7
    auto_skip_after_days: int = 0


@dataclass
class AIConfig:
    """AI agent settings (Phase 2, but parsed here)."""

    enabled: bool = False
    default_mode: str = "socratic"
    default_rigor: int = 3
    max_turns: int = 5
    save_transcripts: bool = True
    provider: str = "anthropic"
    model: str = "claude-sonnet-4-20250514"
    api_key: Optional[str] = None


@dataclass
class Config:
    """Main configuration container."""

    editor: Optional[str] = None
    notifications: NotificationConfig = field(default_factory=NotificationConfig)
    review: ReviewConfig = field(default_factory=ReviewConfig)
    ai: AIConfig = field(default_factory=AIConfig)


def get_lerni_dir() -> Path:
    """Get Lerni data directory (~/.lerni/), creating if needed."""
    lerni_dir = Path.home() / ".lerni"
    lerni_dir.mkdir(exist_ok=True)
    return lerni_dir


def get_config_path() -> Path:
    """Get path to user config file."""
    return get_lerni_dir() / "config.toml"


def load_config() -> Config:
    """
    Load configuration from ~/.lerni/config.toml.

    Returns defaults if file doesn't exist.

    Returns:
        Config object with all settings.

    Example:
        >>> config = load_config()
        >>> config.notifications.enabled
        True
    """
    config_path = get_config_path()
    if not config_path.exists():
        return Config()

    with open(config_path, "rb") as f:
        data = tomllib.load(f)

    # Parse nested configs
    notifications_data = data.get("notifications", {})
    notifications = NotificationConfig(
        enabled=notifications_data.get("enabled", True),
        reminder_time=notifications_data.get("reminder_time", "09:00"),
    )

    review_data = data.get("review", {})
    review = ReviewConfig(
        lookahead_days=review_data.get("lookahead_days", 7),
        auto_skip_after_days=review_data.get("auto_skip_after_days", 0),
    )

    ai_data = data.get("ai", {})
    ai_api_data = ai_data.get("api", {})
    ai = AIConfig(
        enabled=ai_data.get("enabled", False),
        default_mode=ai_data.get("default_mode", "socratic"),
        default_rigor=ai_data.get("default_rigor", 3),
        max_turns=ai_data.get("max_turns", 5),
        save_transcripts=ai_data.get("save_transcripts", True),
        provider=ai_api_data.get("provider", "anthropic"),
        model=ai_api_data.get("model", "claude-sonnet-4-20250514"),
        api_key=ai_api_data.get("api_key"),
    )

    return Config(
        editor=data.get("general", {}).get("editor"),
        notifications=notifications,
        review=review,
        ai=ai,
    )
