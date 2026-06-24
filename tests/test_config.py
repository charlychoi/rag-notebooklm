import pytest
from src.config import redact_secret, require_env
import os


def test_redact_short():
    assert redact_secret("abc") == "****"


def test_redact_normal():
    result = redact_secret("ak_jp91IBp9PFA7Y2X9nan8")
    assert result.startswith("ak_j")
    assert result.endswith("an8")
    assert "****" in result


def test_require_env_raises():
    key = "__TEST_MISSING_ENV__"
    os.environ.pop(key, None)
    with pytest.raises(EnvironmentError, match=key):
        require_env(key)


def test_require_env_ok():
    os.environ["__TEST_PRESENT__"] = "hello"
    assert require_env("__TEST_PRESENT__") == "hello"
