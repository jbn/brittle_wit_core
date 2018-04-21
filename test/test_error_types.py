import pytest
from brittle_wit_core.common import (TwitterError, WrappedException, POST,
                                     BrittleWitError,
                                     TwitterRequest)
from brittle_wit_core.oauth import ClientCredentials


def test_errors_not_retryable_by_default():
    assert not BrittleWitError().is_retryable


@pytest.fixture
def client_cred():
    return ClientCredentials(1, "token", "secret")


@pytest.fixture
def twitter_req():
    return TwitterRequest(POST, "REQ-URL", "FAM", "SVC")


@pytest.fixture
def resp(mocker):
    resp = mocker.MagicMock()
    resp.status = 429
    return resp


class TestTwitterError:

    def test_accessors(self, client_cred, twitter_req, resp):
        err = TwitterError(client_cred, twitter_req, resp, "m")
        assert err.credentials is client_cred
        assert err.twitter_req is twitter_req
        assert err.status_code == resp.status
        assert not err.is_retryable
        assert err.message == "m"

    def test_human_readable(self, client_cred, twitter_req, resp):
        err = TwitterError(client_cred, twitter_req, resp, "m")
        assert str(err) == "TwitterError(code=429, msg=m)"
        assert str(err) == repr(err)

    def test_on_retryable_code(self, client_cred, twitter_req, resp):
        resp.status = 500
        err = TwitterError(client_cred, twitter_req, resp, "m")
        assert err.is_retryable


class TestWrappedExceptions:

    def test_human_readable(self):
        err = WrappedException(KeyboardInterrupt())
        assert str(err) == "WrappedException(KeyboardInterrupt())"
        assert repr(err) == str(err)

    def test_keyboard_interrupt_not_retryable(self):
        underlying = KeyboardInterrupt()
        err = WrappedException(underlying)
        assert underlying is err.underlying_exception
        assert not err.is_retryable

    def test_on_retryable(self, monkeypatch):
        monkeypatch.setattr(WrappedException,
                            'RETRYABLE_EXCEPTIONS',
                            {KeyboardInterrupt})
        err = WrappedException(KeyboardInterrupt())
        assert err.is_retryable

    def test_wrap_if_nessessary_when_unnessessary(self):
        e = BrittleWitError()
        assert e is WrappedException.wrap_if_nessessary(e)

    def test_wrap_if_nessessary_when_nessessary(self):
        e = Exception()
        assert e is not WrappedException.wrap_if_nessessary(e)
