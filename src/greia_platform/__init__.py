"""Core contracts shared by the Greia OS launcher, activities, and parent service."""

from .activities import ActivityManifest, ActivityRegistry, ActivityValidationError

__all__ = ["ActivityManifest", "ActivityRegistry", "ActivityValidationError"]
