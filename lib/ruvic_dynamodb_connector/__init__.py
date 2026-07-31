"""Conector Ruvic de operaciones directas sobre tablas AWS DynamoDB."""

from .client import DynamodbClient
from .config import ENV_PREFIX, DynamodbConfig
from .exceptions import (
    DynamodbAuthError,
    DynamodbConnectorError,
    DynamodbDataError,
    DynamodbNetworkError,
)
from .logging_utils import setup_logging

__all__ = [
    "ENV_PREFIX",
    "DynamodbAuthError",
    "DynamodbClient",
    "DynamodbConfig",
    "DynamodbConnectorError",
    "DynamodbDataError",
    "DynamodbNetworkError",
    "setup_logging",
]

__version__ = "1.0.0"
