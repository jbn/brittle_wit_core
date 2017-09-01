"""
This module contains a bare-bones OAuth implementation. It is
minimally-compliant so as to conform to Twitter's requirements.

See: https://dev.twitter.com/oauth/overview
"""
import binascii
import hashlib
import hmac
import os
import random
import time

from functools import total_ordering
from six.moves.urllib.parse import quote as urllib_quote
from six.moves.urllib.parse import parse_qs

from brittle_wit_core import __version__
from brittle_wit_core.common import TwitterRequest


ANY_CREDENTIALS = None

ALPHANUMERIC = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"

USER_AGENT = 'BrittleWit/' + __version__

REQUEST_TOKEN_URI = "https://api.twitter.com/oauth/request_token"

REDIRECT_URI = "https://api.twitter.com/oauth/authenticate?oauth_token={}"

ACCESS_TOKEN_URI = "https://api.twitter.com/oauth/access_token"


class AppCredentials:
    """
    An Immutable set of application credentials.

    Two different AppCredentials objects have hash equivalence if their key
    and secret are the same. This allows use in sets and dict keys.
    """

    __slots__ = '_key', '_secret'

    @staticmethod
    def load_from_env():
        """
        Create an AppCredentials object from environmental variables.

        ENV:
        - TWITTER_APP_KEY
        - TWITTER_APP_SECRET
        """
        return AppCredentials(os.environ['TWITTER_APP_KEY'],
                              os.environ['TWITTER_APP_SECRET'])

    def __init__(self, key, secret):
        self._key, self._secret = key, secret

    @property
    def key(self):
        return self._key

    @property
    def secret(self):
        return self._secret

    def __str__(self):
        s = "AppCredentials({}, {})"
        return s.format(self._key, "*" * len(self._secret))

    def __repr__(self):
        return self.__str__()

    def __hash__(self):
        return hash((self._key, self._secret))

    def __eq__(self, other):
        return self.key == self.key and self.secret == other.secret

    def __ne__(self, other):
        return not self == other


@total_ordering
class ClientCredentials:
    """
    An Immutable set of client credentials.

    Note: Equality testing and hashing is a function of the user_id alone!
    """

    __slots__ = '_user_id', '_token', '_secret'

    @staticmethod
    def load_from_env():
        return ClientCredentials(os.environ['TWITTER_USER_ID'],
                                 os.environ['TWITTER_USER_TOKEN'],
                                 os.environ['TWITTER_USER_SECRET'])

    def __init__(self, user_id, token, secret):
        self._user_id, self._token, self._secret = user_id, token, secret

    @property
    def token(self):
        return self._token

    @property
    def secret(self):
        return self._secret

    @property
    def user_id(self):
        return self._user_id

    @property
    def as_dict(self):
        return {'user_id': self._user_id,
                'token': self._token,
                'secret': self._secret}

    @staticmethod
    def from_dict(d):
        return ClientCredentials(d['user_id'], d['token'], d['secret'])

    def __str__(self):
        s = "ClientCredentials({}, {}, {})"
        return s.format(self.user_id, self._token, "*" * len(self._secret))

    def __repr__(self):
        return self.__str__()

    def __hash__(self):
        return hash(self._user_id)

    def __eq__(self, other):
        return self.user_id == other.user_id

    def __ne__(self, other):
        return not self == other

    def __lt__(self, other):
        return self.user_id < other.user_id


def _quote(s):
    """
    :return: stringifed inputs, escaped for urls
    """
    if type(s) is int or type(s) is float:
        s = str(s)
    elif s is True:
        s = 'true'
    elif s is False:
        s = 'false'

    return urllib_quote(s, safe='')


def _generate_nonce(length=42):
    """
    Generate an alpha numeric string that is unique for each request.

    Twitter used a 42 character alpha-numeric (case-sensitive) string in the
    API documentation. However, they note "any approach which produces a
    relatively random alphanumeric string should be OK here." I opted not to
    use a cryptographically secure source of entropy. `SystemRandom` is
    convenient, but it uses file IO to connect to `/dev/urandom`. Adding
    `async` machinery here seems like expensive complexity.
    """
    return "".join(random.choice(ALPHANUMERIC) for _ in range(length))


def _generate_timestamp():
    """
    :return: the integer timestamp to send as part of OAuth params.
    """
    # XXX: Does this block? It is a system-call, isn't it?
    return int(time.time())


def _generate_header_string(params):
    """
    Generate the string for use in the http "Authorization" header field.

    :param params: a dictionary with the oauth_* key-values.
    """
    return "OAuth " + ", ".join('{}="{}"'.format(k, _quote(params[k]))
                                for k in sorted(params))


def _generate_param_string(params):
    """
    Generate the parameter string for signing.

    :param params: A dictionary with both the request and oauth_* parameters,
        less the `oauth_signature`.
    """
    d = {_quote(k): _quote(v) for k, v in params.items()}
    return "&".join(["{}={}".format(k, d[k]) for k in sorted(d)])


def _generate_sig_base_string(method, base_url, param_string):
    """
    :param method: either `GET` or `POST`
    :param base_url: the API base URL (i.e. without parameters)
    :param param_string: string generated by generate_param_string
    """
    return "&".join([method, _quote(base_url), _quote(param_string)])


def _generate_signing_key(consumer_secret, oauth_token_secret=None):
    """
    :param consumer_secret: Your application's secret for signing
    :param oauth_token_secret: Your client's secret for signing. If not
        specified, assume this is part of an authenication flow to get
        the client's secret
    """
    return _quote(consumer_secret) + "&" + _quote(oauth_token_secret or "")


def _generate_signature(sig_base_string, signing_key):
    """
    :param sig_base_string: result of _generate_sig_base_string
    :param signing_key: result of _generate_signing_key
    """
    digest = hmac.new(signing_key.encode('ascii'),
                      sig_base_string.encode('ascii'),
                      hashlib.sha1).digest()

    return binascii.b2a_base64(digest)[:-1].decode('utf8')  # Strip newline


def generate_req_headers(twitter_req, app_cred, client_cred=None, **overrides):
    """
    Generate the 'Authorization' and 'User-Agent' headers.

    :param twitter_req: A TwitterRequest object
    :param app_cred: an AppCredentials object
    :param client_cred: a ClientCredentials object. If none, assume the call
        is working on an authentication flow
    :param overrides: key-value pairs which override (or, adds a new value
        to) the oauth_* dictionary used for signature generation.
    """
    oauth_d = {'oauth_consumer_key': app_cred.key,
               'oauth_nonce': _generate_nonce(),
               'oauth_signature_method': "HMAC-SHA1",
               'oauth_timestamp': str(_generate_timestamp()),
               'oauth_version': "1.0"}

    if client_cred:
        oauth_d['oauth_token'] = client_cred.token
        client_secret = client_cred.secret
    else:
        client_secret = None

    if overrides:
        oauth_d.update(overrides)

    params = oauth_d.copy()
    params.update(twitter_req.params)
    param_string = _generate_param_string(params)
    sig_base_string = _generate_sig_base_string(twitter_req.method,
                                                twitter_req.url,
                                                param_string)
    signing_key = _generate_signing_key(app_cred.secret, client_secret)
    oauth_d['oauth_signature'] = _generate_signature(sig_base_string,
                                                     signing_key)

    return {'Authorization': _generate_header_string(oauth_d),
            'User-Agent': USER_AGENT}


def obtain_request_token(app_cred, callback_uri="oob", **overrides):
    """
    Create a TwitterRequest for getting an authentication token.

    :param app_cred: an AppCredential instance
    :param callback_uri: if oob uses pin-based authentication; otherwise, this
        is the uri for redirect following authorization.
    """
    overrides['oauth_callback'] = callback_uri
    twitter_req = TwitterRequest('POST', REQUEST_TOKEN_URI, '_', '_')
    headers = generate_req_headers(twitter_req, app_cred, **overrides)

    return twitter_req, headers


def extract_request_token(status_code, resp_body):
    """
    :param status_code: the HTTP status code
    :param resp_body: the unicode str of the response body
    :return: a tuple of (oauth_token, oauth_token secret), both of which
        are None on error
    """
    if int(status_code) != 200:
        return None, None

    params = parse_qs(resp_body)

    if ('oauth_token' not in params or
            'oauth_token_secret' not in params or
            params['oauth_callback_confirmed'] != ['true']):
        return None, None

    return params['oauth_token'][0], params['oauth_token_secret'][0]


def redirect_url(oauth_token):
    """
    :param oauth_token: the oauth token returned by Twitter.
    :return: the redirect URL
    """
    return REDIRECT_URI.format(_quote(oauth_token))


def obtain_access_token(app_cred, oauth_token, oauth_verifier, **overrides):
    """
    :param app_cred: an AppCredential instance
    :param oauth_token: the oauth token returned from ``obtain_access_token``
    :param oauth_verifier: the verification returned after redirect
    """
    params = {'oauth_verifier': oauth_verifier}
    overrides['oauth_token'] = oauth_token
    twitter_req = TwitterRequest('POST', ACCESS_TOKEN_URI, '_', '_',
                                 params=params)
    headers = generate_req_headers(twitter_req, app_cred, **overrides)

    return twitter_req, headers


def extract_access_token(status_code, resp_body):
    """
    :param status_code: the HTTP status code
    :param resp_body: the unicode str of the response body
    :return: a dictionary of the credentials including oauth_token and
        oauth_token_secret
    """
    if int(status_code) != 200:
        return None

    d = {k: v[0] for k, v in parse_qs(resp_body).items()}

    if 'oauth_token' not in d or 'oauth_token_secret' not in d:
        return None

    if 'user_id' in d:
        d['user_id'] = int(d['user_id'])

    return d
