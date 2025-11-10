"""Application enumerations."""

from enum import StrEnum


class Environment(StrEnum):
    """Application environment."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    SANDBOX = "sandbox"
    STAGING = "staging"
    PRODUCTION = "production"

