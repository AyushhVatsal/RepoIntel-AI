import re


_CAMEL_CASE_RE = re.compile(
    r"""
    (?<=[a-z0-9])
    (?=[A-Z])
    """,
    re.VERBOSE,
)

NON_ALPHANUMERIC_RE = re.compile(r"[^A-Za-z0-9_]+")


def tokenize_code(text: str) -> list[str]:
    """
    Tokenize source code for lexical retrieval.

    Keeps complete identifiers while also exposing useful
    sub-tokens for compound identifiers.
    """

    if not text:
        return []

    raw_tokens = NON_ALPHANUMERIC_RE.split(text)

    tokens: list[str] = []

    for token in raw_tokens:
        if not token:
            continue

        normalized = token.lower()

        # Preserve the complete identifier.
        tokens.append(normalized)

        # Expose snake_case components.
        if "_" in normalized:
            tokens.extend(
                part
                for part in normalized.split("_")
                if part
            )

        # Expose CamelCase components.
        camel_parts = _CAMEL_CASE_RE.split(token)

        if len(camel_parts) > 1:
            tokens.extend(
                part.lower()
                for part in camel_parts
                if part
            )

    return tokens