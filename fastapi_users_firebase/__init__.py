"""FastAPI Users Firebase Plugin.

This is the entrypoint of a plugin to interact with Firebase Authentication from FastAPI users plugin.
"""

from .user_database import FirebaseUserDatabase

__all__ = ["user", "FirebaseUserDatabase"]
