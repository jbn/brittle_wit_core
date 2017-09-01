"""
Test the OAuth functions against the test data and expectations provided
by Twitter's API documentation.

See: https://dev.twitter.com/oauth/overview
"""
import sys
import unittest
from test.helpers import load_fixture_txt, load_fixture_json, replace_env
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
                                    obtain_request_token,
                                    extract_request_token,
                                    redirect_url,
                                    obtain_access_token,
                                    extract_access_token,
                                    ClientCredentials,
                                    AppCredentials)


IMMUTABLE_TEST = sys.version_info >= (3, 0)


class TestAppCredentials(unittest.TestCase):

    def test_accessors(self):
        app = AppCredentials("my_app", "secret")
        self.assertEqual(app.key, "my_app")
        self.assertEqual(app.secret, "secret")

    def test_equality(self):
        app_1 = AppCredentials("app_1", "secret")
        app_2 = AppCredentials("app_2", "password")

        self.assertEqual(app_1, AppCredentials("app_1", "secret"))
        self.assertNotEqual(app_1, app_2)

    def test_hashing(self):
        app_1 = AppCredentials("app_1", "secret")
        app_1_clone = AppCredentials("app_1", "secret")
        app_2 = AppCredentials("app_2", "password")
        self.assertEqual(hash(app_1), hash(app_1_clone))
        self.assertNotEqual(hash(app_1), hash(app_2))

    def test_set_semantics(self):
        app_1 = AppCredentials("app_1", "secret")
        app_1_clone = AppCredentials("app_1", "secret")
        app_2 = AppCredentials("app_2", "password")
        self.assertEqual(len({app_1, app_1_clone, app_2}), 2)

    def test_str(self):
        app = AppCredentials("my_app", "secret")
        self.assertEqual(str(app), "AppCredentials(my_app, ******)")

    def test_repr(self):
        app = AppCredentials("my_app", "secret")
        self.assertEqual(repr(app), "AppCredentials(my_app, ******)")

    def test_immutable(self):
        app = AppCredentials("my_app", "secret")

        if IMMUTABLE_TEST:
            with self.assertRaises(AttributeError):
                app.key = 10  # Immutable(ish)

    def test_env_loading(self):
        with replace_env(TWITTER_APP_KEY='a key', TWITTER_APP_SECRET='a secret'):
            app_cred = AppCredentials.load_from_env()
            self.assertEqual(app_cred.key, 'a key')
            self.assertEqual(app_cred.secret, 'a secret')


class TestClientCredentials(unittest.TestCase):

    def test_accessors(self):
        client_1 = ClientCredentials(1, "token_1", "secret")
        self.assertEqual(client_1.user_id, 1)
        self.assertEqual(client_1.token, 'token_1')
        self.assertEqual(client_1.secret, 'secret')

    def test_hashing(self):
        client_1 = ClientCredentials(1, "token_1", "secret")
        client_1_clone = ClientCredentials(1, "token_1", "secret")
        client_2 = ClientCredentials(2, "token_1", "secret")

        self.assertEqual(hash(client_1), hash(client_1_clone))
        self.assertNotEqual(hash(client_2), hash(client_1))

    def test_set_semantics(self):
        client_1 = ClientCredentials(1, "token_1", "secret")
        client_1_clone = ClientCredentials(1, "token_1", "secret")
        client_2 = ClientCredentials(2, "token_1", "secret")

        self.assertEqual(len({client_1, client_1_clone, client_2}), 2)

    def test_str(self):
        client_1 = ClientCredentials(1, "token_1", "secret")
        self.assertEqual(str(client_1),
                         "ClientCredentials(1, token_1, ******)")

    def test_repr(self):
        client_1 = ClientCredentials(1, "token_1", "secret")
        self.assertEqual(repr(client_1),
                         "ClientCredentials(1, token_1, ******)")

    def test_equals(self):
        client_1 = ClientCredentials(1, "token_1", "secret")
        self.assertEqual(client_1, ClientCredentials(1, "token_1", "secret"))

    def test_immutable(self):
        client_1 = ClientCredentials(1, "token_1", "secret")

        if IMMUTABLE_TEST:
            with self.assertRaises(AttributeError):
                client_1.token = 10  # Immutable(ish)

    def test_total_ordering(self):
        client_1 = ClientCredentials(1, "token_1", "secret")
        client_2 = ClientCredentials(2, "token_1", "secret")
        self.assertTrue(client_2 > client_1)

    def test_dict_serialization(self):
        client_1 = ClientCredentials(1, "token_1", "secret")
        client_2 = ClientCredentials.from_dict(client_1.as_dict)

        self.assertEqual(client_1.user_id, client_2.user_id)
        self.assertEqual(client_1.secret, client_2.secret)
        self.assertEqual(client_1.token, client_2.token)

    def test_env_loading(self):
        with replace_env(TWITTER_USER_ID='the user id',
                         TWITTER_USER_TOKEN='the token',
                         TWITTER_USER_SECRET='the secret'):
            client_cred = ClientCredentials.load_from_env()

            self.assertEqual(client_cred.user_id, 'the user id')
            self.assertEqual(client_cred.token, 'the token')
            self.assertEqual(client_cred.secret, 'the secret')


class TestOAuthHelpers(unittest.TestCase):

    def test_quote_type_conversion(self):
        self.assertEqual(_quote(1), "1")
        self.assertEqual(_quote(1.0), "1.0")
        self.assertEqual(_quote(True), "true")
        self.assertEqual(_quote(False), "false")

    def test_quote_url_escaping(self):
        self.assertEqual(_quote("hello/world"), "hello%2Fworld")

    def test_nonce_variable_length(self):
        self.assertEqual(len(_generate_nonce(100)), 100)

    def test_nonce_randomness(self):
        self.assertNotEqual(_generate_nonce(), _generate_nonce())

    def test_generate_timestamp_is_an_int_not_float(self):
        self.assertTrue(type(_generate_timestamp()) == int)

    def test_generate_header_string(self):
        params = load_fixture_json("oauth_params.json")
        expected = load_fixture_txt("header_string.txt")
        self.assertEqual(_generate_header_string(params), expected)

    def test_generate_param_string(self):
        params = load_fixture_json("request_params.json")
        expected = load_fixture_txt("param_string.txt")
        self.assertEqual(_generate_param_string(params), expected)

    def test_generate_sig_base_string(self):
        method = "POST"
        url = "https://api.twitter.com/1/statuses/update.json"
        param_string = load_fixture_txt("param_string.txt")
        self.assertEqual(_generate_sig_base_string(method, url, param_string),
                         load_fixture_txt("sig_base_string.txt"))

    def test_generate_signing_key_basic(self):
        consumer_secret = "kAcSOqF21Fu85e7zjz7ZN2U4ZRhfV3WpwPAoE3Z7kBw"
        token_secret = "LswwdoUaIvS8ltyTt5jkRh4J50vUPVVHtR2YPi5kE"
        k = _generate_signing_key(consumer_secret, token_secret)
        expected = load_fixture_txt("signing_key.txt")
        self.assertEqual(k, expected)

    def test_generate_signing_key_no_token(self):
        consumer_secret = "kAcSOqF21Fu85e7zjz7ZN2U4ZRhfV3WpwPAoE3Z7kBw"
        k = _generate_signing_key(consumer_secret)
        expected = load_fixture_txt("signing_key_no_oauth.txt")
        self.assertEqual(k, expected)

    def test_generate_signature(self):
        signing_key = load_fixture_txt("signing_key.txt")
        sig_base_string = load_fixture_txt("sig_base_string.txt")
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
        req = TwitterRequest(POST,
                             "https://api.twitter.com/1/statuses/update.json",
                             'statuses',
                             'statuses/update',
                             dict(include_entities='true', status=status))
        expected = load_fixture_txt("header_string.txt")

        overrides = {k: oauth_params[k]
                     for k in ['oauth_nonce', 'oauth_timestamp']}

        auth = generate_req_headers(req, app, client, **overrides)
        self.assertIn('Authorization', auth)
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

    def test_extract_request_token_bad_status(self):
        self.assertEqual(extract_request_token(999, ""), (None, None))

    def test_extract_request_token_good_status_bad_resp(self):
        self.assertEqual(extract_request_token(200, ""), (None, None))

    def test_extract_request_token_good_status_good_resp(self):
        resp_body = "&".join(["oauth_token=a",
                              "oauth_token_secret=b",
                              "oauth_callback_confirmed=true"])
        self.assertEqual(extract_request_token(200, resp_body),
                         ('a', 'b'))

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

    def test_extract_access_token_bad_status(self):
        self.assertEqual(extract_access_token(999, ""), None)

    def test_extract_access_token_bad_resp(self):
        self.assertEqual(extract_access_token(200, ""), None)

    def test_extract_access_token_good_status_good_resp(self):
        d = {'oauth_token': 'token',
             'oauth_token_secret': 'secret',
             'screen_name': 'techcrunch',
             'user_id': 42,
             'x_auth_expires': '0'}
        resp_body = "&".join(["{}={}".format(k, v) for k, v in d.items()])

        self.assertEqual(extract_access_token(200, resp_body), d)


if __name__ == '__main__':
    unittest.main()
