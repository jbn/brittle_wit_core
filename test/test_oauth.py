import os
import sys
import unittest
from test.helpers import load_fixture_txt, load_fixture_json
from brittle_wit_core.common import TwitterRequest
from brittle_wit_core.oauth import (_generate_nonce,
                                    _generate_timestamp,
                                    _generate_header_string,
                                    _generate_param_string,
                                    _generate_sig_base_string,
                                    _generate_signing_key,
                                    _generate_signature,
                                    _quote,
                                    generate_req_headers,
                                    obtain_request_token,
                                    obtain_access_token,
                                    redirect_url,
                                    ClientCredentials,
                                    AppCredentials)


IMMUTABLE_TEST = sys.version_info >= (3, 0)


class TestAppCredentials(unittest.TestCase):

    def test_env_loading(self):
        mock_env = {'TWITTER_APP_KEY': 'the key',
                    'TWITTER_APP_SECRET': 'the secret'}
        os.environ.update(mock_env)
        app_cred = AppCredentials.load_from_env()
        self.assertEqual(app_cred.key, 'the key')
        self.assertEqual(app_cred.secret, 'the secret')

    def test_app_credentials(self):
        app_1 = AppCredentials("app_1", "secret")
        self.assertEqual(app_1, AppCredentials("app_1", "secret"))

        app_2 = AppCredentials("app_2", "password")
        self.assertNotEqual(app_1, app_2)

        self.assertEqual(len({app_1, app_2}), 2)
        self.assertEqual(str(app_1), "AppCredentials(app_1, ******)")
        self.assertEqual(repr(app_1), "AppCredentials(app_1, ******)")

        if IMMUTABLE_TEST:
            with self.assertRaises(AttributeError):
                app_1.key = 10  # Immutable(ish)


class TestClientCredentials(unittest.TestCase):

    def test_env_loading(self):
        mock_env = {'TWITTER_USER_ID': 'the user id',
                    'TWITTER_USER_TOKEN': 'the token',
                    'TWITTER_USER_SECRET': 'the secret'}
        os.environ.update(mock_env)

        client_cred = ClientCredentials.load_from_env()

        self.assertEqual(client_cred.user_id, 'the user id')
        self.assertEqual(client_cred.token, 'the token')
        self.assertEqual(client_cred.secret, 'the secret')

    def test_client_credentials(self):
        client_1 = ClientCredentials(1, "token_1", "secret")
        self.assertEqual(client_1, ClientCredentials(1, "token_1", "secret"))

        client_2 = ClientCredentials(2, "token_2", "secret")
        self.assertNotEqual(client_1, client_2)

        self.assertEqual(len({client_1, client_2}), 2)
        self.assertEqual(str(client_1),
                         "ClientCredentials(1, token_1, ******)")
        self.assertEqual(repr(client_1),
                         "ClientCredentials(1, token_1, ******)")

        if IMMUTABLE_TEST:
            with self.assertRaises(AttributeError):
                client_1.token = 10  # Immutable(ish)

        self.assertTrue(client_2 > client_1)

    def test_dict_serialization(self):
        client_1 = ClientCredentials(1, "token_1", "secret")
        client_2 = ClientCredentials.from_dict(client_1.as_dict)

        self.assertEqual(client_1.user_id, client_2.user_id)
        self.assertEqual(client_1.secret, client_2.secret)
        self.assertEqual(client_1.token, client_2.token)


class TestOAuth(unittest.TestCase):
    """
    Test the OAuth functions against the test data and expectations provided
    by Twitter's API documentation.

    See: https://dev.twitter.com/oauth/overview
    """

    def test_quote(self):
        self.assertEqual(_quote(1), "1")
        self.assertEqual(_quote(1.0), "1.0")
        self.assertEqual(_quote(True), "true")
        self.assertEqual(_quote(False), "false")
        self.assertEqual(_quote("hello/world"), "hello%2Fworld")

    def test_generate_nonce(self):
        self.assertEqual(len(_generate_nonce(100)), 100)
        self.assertNotEqual(_generate_nonce(), _generate_nonce())

    def test_generate_timestamp(self):
        self.assertTrue(type(_generate_timestamp()) == int)

    def test_generate_header_string(self):
        params = load_fixture_json("oauth_params.json")
        expected = load_fixture_expectation("header_string.txt")
        self.assertEqual(_generate_header_string(params), expected)

    def test_generate_param_string(self):
        params = load_fixture_json("request_params.json")
        expected = load_fixture_expectation("param_string.txt")
        self.assertEqual(_generate_param_string(params), expected)

    def test_generate_sig_base_string(self):
        method = "post"  # Keep lowercase as test of uppercase assurance
        url = "https://api.twitter.com/1/statuses/update.json"
        param_string = load_fixture_expectation("param_string.txt")

        result = _generate_sig_base_string(method, url, param_string)
        expected = load_fixture_expectation("sig_base_string.txt")

        self.assertEqual(result, expected)

    def test_generate_signing_key_basic(self):
        consumer_secret = "kAcSOqF21Fu85e7zjz7ZN2U4ZRhfV3WpwPAoE3Z7kBw"
        token_secret = "LswwdoUaIvS8ltyTt5jkRh4J50vUPVVHtR2YPi5kE"
        k = _generate_signing_key(consumer_secret, token_secret)
        expected = load_fixture_expectation("signing_key.txt")
        self.assertEqual(k, expected)

    def test_generate_signing_key_no_token(self):
        consumer_secret = "kAcSOqF21Fu85e7zjz7ZN2U4ZRhfV3WpwPAoE3Z7kBw"
        k = _generate_signing_key(consumer_secret)
        expected = load_fixture_expectation("signing_key_no_oauth.txt")
        self.assertEqual(k, expected)

    def test_generate_signature(self):
        signing_key = load_fixture_expectation("signing_key.txt")
        sig_base_string = load_fixture_expectation("sig_base_string.txt")
        expected = "tnnArxj06cWHq44gCs1OSKk/jLY="

        self.assertEqual(_generate_signature(sig_base_string, signing_key),
                         expected)

    def test_generate_req_headers(self):
        oauth_params = load_fixture_json("oauth_params.json")

        app = AppCredentials(oauth_params['oauth_consumer_key'],
                             "kAcSOqF21Fu85e7zjz7ZN2U4ZRhfV3WpwPAoE3Z7kBw")
        client = ClientCredentials(1,
                                   oauth_params['oauth_token'],
                                   "LswwdoUaIvS8ltyTt5jkRh4J50vUPVVHtR2YPi5kE")

        status = "Hello Ladies + Gentlemen, a signed OAuth request!"
        req = TwitterRequest("POST",
                             "https://api.twitter.com/1/statuses/update.json",
                             'statuses',
                             'statuses/update',
                             dict(include_entities='true', status=status))
        expected = load_fixture_expectation("header_string.txt")

        overrides = {k: oauth_params[k]
                     for k in ['oauth_nonce', 'oauth_timestamp']}

        auth = generate_req_headers(req, app, client, **overrides)
        self.assertIn('Authorization', auth.keys())
        self.assertEqual(auth['Authorization'], expected)


class TestAuthFlow(unittest.TestCase):

    def setUp(self):
        # See: https://dev.twitter.com/web/sign-in/implementing
        app_cred = AppCredentials("cChZNFj6T5R0TigYB9yd1w",
                                  "L8qq9PZyRg6ieKGEKhZolGC0vJWLw8iEJ88DRdyOg")
        self.app_cred = app_cred

    def test_obtain_request_token(self):
        app_cred = self.app_cred

        callback_url = "http://localhost/sign-in-with-twitter/"

        overrides = {'oauth_timestamp': "1318467427",
                     'oauth_callback': callback_url,
                     'oauth_nonce': "ea9ec8429b68d6b77cd5600adbbb0456"}

        _, headers = obtain_request_token(app_cred, callback_url, **overrides)

        expected_substr = 'oauth_signature="F1Li3tvehgcraF8DMJ7OyxO4w9Y%3D"'

        self.assertIn(expected_substr, headers['Authorization'])

    def test_redirect_url(self):
        base_uri = "https://api.twitter.com/oauth/authenticate"

        expected = base_uri + "?oauth_token=hello%2Fworld"

        self.assertEqual(redirect_url("hello/world"), expected)

    def test_obtain_access_token(self):
        app_cred = self.app_cred

        self.assertEqual(app_cred.key, "cChZNFj6T5R0TigYB9yd1w")

        tok = "NPcudxy0yU5T3tBzho7iCotZ3cnetKwcTIRlX0iwRl0"

        verifier = "uw7NjWHT6OJ1MpJOXsHfNxoAhPKpgI8BlYDhxEjIBY"

        overrides = {'oauth_timestamp': "1318467427",
                     'oauth_nonce': "a9900fe68e2573b27a37f10fbad6a755"}

        _, headers = obtain_access_token(app_cred, tok, verifier, **overrides)

        expected_substr = 'oauth_signature="eLn5QjdCqHdlBEvOogMeGuRxW4k%3D"'

        self.assertIn(expected_substr, headers['Authorization'])


def load_fixture_expectation(file_name):
    return load_fixture_txt(file_name)


if __name__ == '__main__':
    unittest.main()
