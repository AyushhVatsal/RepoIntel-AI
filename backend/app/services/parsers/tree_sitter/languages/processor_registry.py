from .javascript import JavaScriptProcessor
from .typescript import TypeScriptProcessor


class ProcessorRegistry:

    _registry = {
        "javascript": JavaScriptProcessor,
        "typescript": TypeScriptProcessor,
    }

    @classmethod
    def get(
        cls,
        language: str,
    ):
        return cls._registry.get(language.lower())