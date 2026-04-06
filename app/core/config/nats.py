"""NATS settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class NATSSettings(BaseSettings):
    """Settings for NATS connection."""

    model_config = SettingsConfigDict(env_prefix="NATS_", case_sensitive=False)

    hosts: str = "nats://localhost:4222"
    subject: str = "template.>"
    consumer_durable: str = "template-service-consumer"
    consumer_ack_wait: int = 7200  # 2 hours
    consumer_max_deliver: int = 3
    fetch_batch_size: int = 10  # Number of messages to fetch at once

    # JetStream stream settings
    stream_name: str = "template"
    stream_max_age: int = 86400  # 24 hours
    stream_max_bytes: int = 1073741824  # 1GB
    stream_max_messages: int = -1  # unlimited
    stream_storage_type: str = "file"  # file or memory
