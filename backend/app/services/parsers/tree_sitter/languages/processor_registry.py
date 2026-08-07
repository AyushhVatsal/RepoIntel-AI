from .javascript import JavaScriptProcessor
from .python import PythonProcessor
from .java import JavaProcessor
from .typescript import TypeScriptProcessor


class ProcessorRegistry:

    _registry = {
        "python": PythonProcessor,
        "java": JavaProcessor,
        "javascript": JavaScriptProcessor,
        "typescript": TypeScriptProcessor,
    }

    @classmethod
    def get(
        cls,
        language: str,
    ):
        return cls._registry[language.lower()]