import json
import pytest
import sys
from brittle_wit_core.oauth import ClientCredentials


def test_accessors():
    client_1 = ClientCredentials(1, "token_1", "secret")
    assert client_1.user_id == 1
    assert client_1.token == 'token_1'
    assert client_1.secret == 'secret'


def test_representation():
    client_cred = ClientCredentials(42, "a_token", "a_secret")
    assert str(client_cred) == "ClientCredentials(42, 'a_token', '********')"
    assert repr(client_cred) == str(client_cred)


class TestCollectionSemantics:

    def test_set_semantics(self):
        assert len({ClientCredentials(1, "tok", "secret"),
                    ClientCredentials(1, "tok", "secret_2"),
                    ClientCredentials(1, "tok_2", "secret"),
                    ClientCredentials(2, "tok", "secret")}) == 2

    def test_equals(self):
        assert ClientCredentials(1, "tok", "secret") == \
            ClientCredentials(1, 'tok', 'secret')

        assert ClientCredentials(1, "tok_1", "secret") == \
            ClientCredentials(1, 'tok', 'secret'), "ID based comparisons"

        assert ClientCredentials(1, "tok", "secret") == \
            ClientCredentials(1, 'tok', 'secret_2'), "ID based comparisons"

    def test_total_ordering(self):
        assert ClientCredentials(2, "tok", "secret") > \
            ClientCredentials(1, 'tok', 'secret')


def test_dict_serialization():
    client_1 = ClientCredentials(1, "token_1", "secret")
    client_2 = ClientCredentials.from_dict(client_1.as_dict)

    assert client_1.user_id == client_2.user_id
    assert client_1.secret == client_2.secret
    assert client_1.token == client_2.token


def test_load_many_from_json(tmpdir):
    expected = [ClientCredentials(1, "tok_{}".format(i), "sec_{}".format(i))
                for i in range(5)]
    cred_file = tmpdir.join('client_cred.json')
    cred_file.write(json.dumps([cred.as_dict for cred in expected]))

    creds = ClientCredentials.load_many_from_json(str(cred_file))
    assert creds == expected


def test_env_loading(monkeypatch):
    monkeypatch.setenv('TWITTER_USER_ID', "the user id")
    monkeypatch.setenv('TWITTER_USER_TOKEN', "the token")
    monkeypatch.setenv('TWITTER_USER_SECRET', "the secret")

    client_cred = ClientCredentials.load_from_env()

    assert client_cred.user_id == 'the user id'
    assert client_cred.token == 'the token'
    assert client_cred.secret == 'the secret'


@pytest.mark.skipif(sys.version_info < (3, 0),
                    reason='Python 2.X properties are assignable.')
def test_client_credential_immutability():
    client_1 = ClientCredentials(1, "token_1", "secret")

    with pytest.raises(AttributeError):
        client_1.token = 10  # Immutable(ish)
