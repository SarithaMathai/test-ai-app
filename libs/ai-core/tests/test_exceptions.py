import pytest
from ai_core.exceptions import AIError, ConfigError, ProviderError, RetryExhaustedError


def test_ai_error_stores_message():
    err = AIError("something broke")
    assert str(err) == "something broke"
    assert err.message == "something broke"
    assert err.code is None


def test_ai_error_stores_code():
    err = AIError("bad request", code="BAD_REQUEST")
    assert err.code == "BAD_REQUEST"


def test_config_error_is_ai_error():
    err = ConfigError("missing key")
    assert isinstance(err, AIError)
    assert err.message == "missing key"


def test_provider_error_stores_provider():
    err = ProviderError("timeout", provider="openai")
    assert err.provider == "openai"
    assert isinstance(err, AIError)


def test_retry_exhausted_is_provider_error():
    err = RetryExhaustedError("gave up after 3 attempts", provider="thinktank")
    assert isinstance(err, ProviderError)
    assert isinstance(err, AIError)
    assert err.provider == "thinktank"


def test_exceptions_are_catchable_as_base():
    with pytest.raises(AIError):
        raise RetryExhaustedError("failed", provider="openai")
