from app.services.chunking import token_counter
from app.services.chunking.token_counter import TokenCounter, warmup_tokenizer


class FakeEncoding:
    def __init__(self):
        self.disallowed_special_values = []

    def encode(self, text, *, disallowed_special):
        self.disallowed_special_values.append(disallowed_special)
        return list(text)

    @staticmethod
    def decode(tokens):
        return "".join(tokens)


def test_tokenizer_is_cached_and_treats_special_token_text_as_literal(
    monkeypatch,
):
    fake_encoding = FakeEncoding()
    calls = []
    monkeypatch.setattr(
        token_counter.tiktoken,
        "get_encoding",
        lambda name: calls.append(name) or fake_encoding,
    )
    token_counter._get_encoding.cache_clear()

    warmup_tokenizer()
    counter = TokenCounter()
    text = 'value = "<|endoftext|>"'

    assert counter.encode(text) == list(text)
    assert counter.count(text) == len(text)
    assert fake_encoding.disallowed_special_values == [(), ()]
    assert calls == ["cl100k_base"]

    token_counter._get_encoding.cache_clear()
