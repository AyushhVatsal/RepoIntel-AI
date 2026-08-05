"""
Module docstring.
"""

import os
import sys as system
import numpy as np

from pathlib import Path
from typing import List, Dict
from collections import defaultdict as dd


PI = 3.14
MAX_SIZE = 100


class Animal:
    """Animal docstring."""

    species = "Unknown"

    def speak(self):
        pass


class Dog(Animal):
    """Dog docstring."""

    breed = "Labrador"

    @staticmethod
    def create(name: str):
        return Dog()

    @classmethod
    def from_age(cls, age: int):
        return cls()

    @property
    def info(self):
        return self.breed

    async def bark(
        self,
        volume: int = 5,
    ) -> str:
        """Async bark."""

        return "Woof"

    def walk(
        self,
        distance: float,
        *args,
        speed: float = 1.0,
        **kwargs,
    ):
        pass


def helper(
    x: int,
    y: int = 10,
):
    """Helper function."""

    return x + y


async def fetch_data(
    url: str,
):
    return {}