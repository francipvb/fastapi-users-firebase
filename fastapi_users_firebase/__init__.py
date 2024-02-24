"""FastAPI Users Firebase Plugin.

This is the entrypoint of a plugin to interact with Firebase Authentication from FastAPI users plugin.
"""

from .schemas import CreateFirebaseUserModel, CreateUpdateFirebaseUserModel, UpdateFirebaseUserModel
from .user import FirebaseUser
from .user_database import FirebaseUserDatabase

__all__ = [
    "FirebaseUser",
    "FirebaseUserDatabase",
    "CreateFirebaseUserModel",
    "CreateUpdateFirebaseUserModel",
    "UpdateFirebaseUserModel",
]
