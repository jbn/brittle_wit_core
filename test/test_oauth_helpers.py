"""
Test the OAuth functions against the test data and expectations provided
by Twitter's API documentation.

See: https://dev.twitter.com/oauth/overview
"""
import json
import os
from brittle_wit_core.common import TwitterRequest, POST
from brittle_wit_core.oauth import (_generate_nonce,
                                    _generate_timestamp,
                                    _generate_header_string,
                                    _generate_param_string,
                                    _generate_sig_base_string,
                                    _generate_signing_key,
                                    _generate_signature,
                                    _quote,
                                    generate_req_headers,
                                    ClientCredentials,
                                    AppCredentials)


def test_quote_type_conversion():
    assert _quote(1) == "1"
    assert _quote(1.0) == "1.0"
    assert _quote(True) == "true"
    assert _quote(False) == "false"


def test_quote_url_escaping():
    assert _quote("hello/world") == "hello%2Fworld"


def test_nonce_variable_length():
    assert len(_generate_nonce(100)) == 100


def test_nonce_randomness():
    assert _generate_nonce() != _generate_nonce()


def test_generate_timestamp_is_an_int_not_float():
    assert type(_generate_timestamp()) == int


def test_generate_header_string():
    params = load_fixture_json("oauth_params.json")
    expected = load_fixture_txt("header_string.txt")
    assert _generate_header_string(params) == expected


def test_generate_param_string():
    params = load_fixture_json("request_params.json")
    expected = load_fixture_txt("param_string.txt")
    assert _generate_param_string(params) == expected


def test_generate_sig_base_string():
    method = "POST"
    url = "https://api.twitter.com/1/statuses/update.json"
    param_string = load_fixture_txt("param_string.txt")
    assert _generate_sig_base_string(method, url, param_string) == \
        load_fixture_txt("sig_base_string.txt")


def test_generate_signing_key_basic():
    consumer_secret = "kAcSOqF21Fu85e7zjz7ZN2U4ZRhfV3WpwPAoE3Z7kBw"
    token_secret = "LswwdoUaIvS8ltyTt5jkRh4J50vUPVVHtR2YPi5kE"
    k = _generate_signing_key(consumer_secret, token_secret)
    expected = load_fixture_txt("signing_key.txt")
    assert k == expected


def test_generate_signing_key_no_token():
    consumer_secret = "kAcSOqF21Fu85e7zjz7ZN2U4ZRhfV3WpwPAoE3Z7kBw"
    k = _generate_signing_key(consumer_secret)
    expected = load_fixture_txt("signing_key_no_oauth.txt")
    assert k == expected


def test_generate_signature():
    signing_key = load_fixture_txt("signing_key.txt")
    sig_base_string = load_fixture_txt("sig_base_string.txt")
    expected = "tnnArxj06cWHq44gCs1OSKk/jLY="

    assert _generate_signature(sig_base_string, signing_key) == expected


def test_generate_req_headers():
    oauth_params = load_fixture_json("oauth_params.json")

    app = AppCredentials(oauth_params['oauth_consumer_key'],
                         "kAcSOqF21Fu85e7zjz7ZN2U4ZRhfV3WpwPAoE3Z7kBw")
    client = ClientCredentials(1,
                               oauth_params['oauth_token'],
                               "LswwdoUaIvS8ltyTt5jkRh4J50vUPVVHtR2YPi5kE")

    status = "Hello Ladies + Gentlemen, a signed OAuth request!"
    req = TwitterRequest(POST,
                         "https://api.twitter.com/1/statuses/update.json",
                         'statuses',
                         'statuses/update',
                         dict(include_entities='true', status=status))
    expected = load_fixture_txt("header_string.txt")

    overrides = {k: oauth_params[k]
                 for k in ['oauth_nonce', 'oauth_timestamp']}

    auth = generate_req_headers(req, app, client, **overrides)
    assert 'Authorization' in auth
    assert auth['Authorization'] == expected


SELF_DIR = os.path.dirname(os.path.realpath(__file__))
FIXTURES_DIR = os.path.join(SELF_DIR, "fixtures")


def load_fixture_txt(file_name):
    with open(os.path.join(FIXTURES_DIR, file_name)) as fp:
        return fp.read()


def load_fixture_json(file_name):
    with open(os.path.join(FIXTURES_DIR, file_name)) as fp:
        return json.load(fp)
