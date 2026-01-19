"""Configuration management for the bot."""

import os
from dataclasses import dataclass


@dataclass
class Config:
    """Bot configuration."""
    
    # Telegram settings
    telegram_bot_token: str
    
    # Website settings
    base_url: str = "https://aitag.win"
    results_per_page: int = 60
    
    # API settings
    api_timeout: int = 30
    
    # Network settings
    proxy_url: str = None
    connection_timeout: int = 30
    read_timeout: int = 30
    
    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not telegram_bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")
        
        return cls(
            telegram_bot_token=telegram_bot_token,
            base_url=os.getenv("BASE_URL", "https://aitag.win"),
            results_per_page=int(os.getenv("RESULTS_PER_PAGE", "5")),
            api_timeout=int(os.getenv("API_TIMEOUT", "30")),
            proxy_url=os.getenv("PROXY_URL"),
            connection_timeout=int(os.getenv("CONNECTION_TIMEOUT", "30")),
            read_timeout=int(os.getenv("READ_TIMEOUT", "30")),
        )
