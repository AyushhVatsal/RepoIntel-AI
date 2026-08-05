"""
Module docstring.
"""

import os
import json as js

from pathlib import Path
from pydantic import BaseModel
from typing import Any


API_VERSION = "1.0"


class User(BaseModel):
    """
    User model.
    """

    @staticmethod
    def login(
        self,
        username: str,
        password: str,
    ) -> bool:
        return True


async def fetch_users():
    pass