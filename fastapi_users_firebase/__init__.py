"""FastAPI Users Firebase Plugin.

This is the entrypoint of a plugin to interact with Firebase Authentication from FastAPI users plugin.
"""

from .user_store import FirebaseUser, FirebaseUserDatabase

__all__ = ["FirebaseUser", "FirebaseUserDatabase"]
