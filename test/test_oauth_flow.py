import pytest
from brittle_wit_core.oauth import (extract_access_token,
                                    extract_request_token,
                                    obtain_access_token,
                                    obtain_request_token,
                                    redirect_url,
                                    AppCredentials)


def test_extract_request_token_bad_status():
    assert extract_request_token(999, "") == (None, None)


def test_extract_request_token_good_status_bad_resp():
    assert extract_request_token(200, "") == (None, None)


def test_extract_request_token_good_status_good_resp():
    params = "oauth_token=a,oauth_token_secret=b,oauth_callback_confirmed=true"
    resp_body = "&".join(params.split(","))
    assert extract_request_token(200, resp_body) == ('a', 'b')


def test_redirect_url():
    base_uri = "https://api.twitter.com/oauth/authenticate"
    expected = base_uri + "?oauth_token=hello%2Fworld"
    assert redirect_url("hello/world") == expected


def test_extract_access_token_bad_status():
    assert extract_access_token(999, "") is None


def test_extract_access_token_bad_resp():
    assert extract_access_token(200, "") is None


def test_extract_access_token_good_status_good_resp():
    d = {'oauth_token': 'token',
         'oauth_token_secret': 'secret',
         'screen_name': 'techcrunch',
         'user_id': 42,
         'x_auth_expires': '0'}
    resp_body = "&".join(["{}={}".format(k, v) for k, v in d.items()])

    assert extract_access_token(200, resp_body) == d


@pytest.fixture
def app_cred():
    # See: https://dev.twitter.com/web/sign-in/implementing
    return AppCredentials("cChZNFj6T5R0TigYB9yd1w",
                          "L8qq9PZyRg6ieKGEKhZolGC0vJWLw8iEJ88DRdyOg")


def test_obtain_request_token(app_cred):
    callback_url = "http://localhost/sign-in-with-twitter/"

    overrides = {'oauth_timestamp': "1318467427",
                 'oauth_callback': callback_url,
                 'oauth_nonce': "ea9ec8429b68d6b77cd5600adbbb0456"}

    _, headers = obtain_request_token(app_cred, callback_url, **overrides)

    expected_substr = 'oauth_signature="F1Li3tvehgcraF8DMJ7OyxO4w9Y%3D"'

    assert expected_substr in headers['Authorization']


def test_obtain_access_token(app_cred):
    assert app_cred.key == "cChZNFj6T5R0TigYB9yd1w"

    tok = "NPcudxy0yU5T3tBzho7iCotZ3cnetKwcTIRlX0iwRl0"

    verifier = "uw7NjWHT6OJ1MpJOXsHfNxoAhPKpgI8BlYDhxEjIBY"

    overrides = {'oauth_timestamp': "1318467427",
                 'oauth_nonce': "a9900fe68e2573b27a37f10fbad6a755"}

    _, headers = obtain_access_token(app_cred, tok, verifier, **overrides)

    expected_substr = 'oauth_signature="eLn5QjdCqHdlBEvOogMeGuRxW4k%3D"'

    assert expected_substr in headers['Authorization']
