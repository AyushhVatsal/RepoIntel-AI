from app.services.retrieval.lexical.tokenizer import tokenize_code


def test_tokenize_camel_case_identifier():
    tokens = tokenize_code("RepositoryService")

    assert "repositoryservice" in tokens
    assert "repository" in tokens
    assert "service" in tokens


def test_tokenize_snake_case_identifier():
    tokens = tokenize_code("authenticate_user")

    assert "authenticate_user" in tokens
    assert "authenticate" in tokens
    assert "user" in tokens


def test_tokenize_uppercase_snake_case_identifier():
    tokens = tokenize_code("JWT_SECRET")

    assert "jwt_secret" in tokens
    assert "jwt" in tokens
    assert "secret" in tokens


def test_tokenize_python_code():
    code = """
def authenticate_user(username, password):
    return verify_password(username, password)
"""

    tokens = tokenize_code(code)

    assert "authenticate_user" in tokens
    assert "authenticate" in tokens
    assert "user" in tokens
    assert "verify_password" in tokens
    assert "verify" in tokens
    assert "password" in tokens


def test_empty_input_returns_empty_list():
    assert tokenize_code("") == []


def test_punctuation_is_not_kept_as_tokens():
    tokens = tokenize_code("foo(bar, baz).qux")

    assert "foo" in tokens
    assert "bar" in tokens
    assert "baz" in tokens
    assert "qux" in tokens

    assert "(" not in tokens
    assert ")" not in tokens
    assert "," not in tokens
    assert "." not in tokens


def test_preserves_complete_identifier():
    tokens = tokenize_code("get_user_by_id")

    assert "get_user_by_id" in tokens


def test_repeated_terms_are_preserved():
    tokens = tokenize_code("user user user")

    assert tokens.count("user") == 3