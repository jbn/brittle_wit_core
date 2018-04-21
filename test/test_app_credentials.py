import pytest
import sys
from brittle_wit_core.oauth import AppCredentials


def test_accessors():
    app = AppCredentials("my_app", "secret")
    assert app.key == "my_app"
    assert app.secret == "secret"


def test_representation():
    app_cred = AppCredentials("my_app", "my_secret")
    assert str(app_cred) == "AppCredentials('my_app', '*********')"
    assert repr(app_cred) == str(app_cred)


class TestHashingSemantics():

    def test_equality(self):
        assert AppCredentials("app", "pass") == AppCredentials("app", "pass")
        assert AppCredentials("app", "pass_2") != AppCredentials("app", "pass")
        assert AppCredentials("app_2", "pass") != AppCredentials("app", "pass")

    def test_set_membership(self):
        assert len({AppCredentials("app", "pass"),
                    AppCredentials("app", "pass"),
                    AppCredentials("app_2", "pass_2"),
                    AppCredentials("app_2", "pass")}) == 3


def test_env_loading(monkeypatch):
    monkeypatch.setenv('TWITTER_APP_KEY', 'env_key')
    monkeypatch.setenv('TWITTER_APP_SECRET', 'env_pass')
    app_cred = AppCredentials.load_from_env()
    assert app_cred.key == 'env_key'
    assert app_cred.secret == 'env_pass'


@pytest.mark.skipif(sys.version_info < (3, 0),
                    reason='Python 2.X properties are assignable.')
def test_immutability():
    app = AppCredentials("my_app", "secret")

    with pytest.raises(AttributeError):
        app.key = 10  # Immutable(ish)
