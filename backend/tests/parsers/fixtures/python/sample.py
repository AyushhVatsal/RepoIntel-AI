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

name: str = "RepoIntel"
count: int = 42


class Animal:
    """Animal docstring."""

    species = "Unknown"

    def speak(self):
        pass


class Pet:
    pass


class Robot:
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

    @staticmethod
    @property
    def version():
        return "1.0"

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


class RoboDog(
    Dog,
    Robot,
):
    """Multiple inheritance."""

    pass


class Outer:
    """Outer class."""

    value = 100

    class Inner:
        """Nested class."""

        def hello(self):
            return "hello"


def helper(
    x: int,
    y: int = 10,
):
    """Helper function."""

    return x + y


def outer():
    """Outer function."""

    def inner():
        return "nested"

    return inner()


async def fetch_data(
    url: str,
):
    return {}


@staticmethod
def top_level_static():
    return True


@classmethod
def top_level_classmethod(cls):
    return cls


@property
def top_level_property():
    return "property"


def route(path: str):
    def decorator(func):
        return func
    return decorator


@route("/users")
def get_users():
    """Decorator with arguments."""

    return []


if __name__ == "__main__":
    helper(1)