from collections import namedtuple


GET, POST, PUT, HEAD, DELETE = 'GET', 'POST', 'PUT', 'HEAD', 'DELETE'


class _ELIDE:
    """
    Explicitly mark a parameter in a ``TwitterRequest`` as redundant

    The Twitter API has functions such that either this parameter is required
    or that one is, but not both. It leads to some ambiguity if you want to
    use required argument semantics for functions as required arguments. To
    get around this, you mark the irrelevant parameter with ELIDE.
    """

    def __repr__(self):
        return 'ELIDE'

    def __str__(self):
        return 'ELIDE'


ELIDE = _ELIDE()  # Singleton


class TwitterRequest:
    """
    A (mostly) immutable twitter request

    It's *mostly* immutable for two reasons:

    1. Python 2.7 doesn't throw an attribute error when you try to assign to
       a non-explicit slot.
    2. The ``parse_as`` setter method let's you update ``parse_as`` in-place.
       Using a setter method sends a clear signal though, and it's a form of
       reuse that would fail loudly
    """

    # This is a static mapping from the request url to the Twitter API
    # documentation URL.
    DOC_URLS = {}

    __slots__ = ('_method', '_url', '_family',
                 '_service', '_parse_as', '_params')

    def __init__(self, method, url, family, service,
                 params=None, parse_as='json'):
        """
        Create a TwitterRequest object.

        :param method: the HTTP verb (capitalization expected but not verified)
            e.g. ``GET``
        :param url: the twitter api endpoint url
            e.g. ``https://api.twitter.com/1.1/account/settings.json``
        :param family: the resource family for twitter rate limiting purposes
            e.g. ``rest:account``
        :param service: the specific sub-service identifier
            e.g. ``get-account-settings``
        """
        self._method = method
        self._url = url
        self._family = family
        self._service = service
        self._parse_as = parse_as

        # See: _ELIDE documentation above.
        if params:
            self._params = {k: v for k, v in params.items() if v is not ELIDE}
        else:
            self._params = {}

    @property
    def method(self):
        return self._method

    @property
    def url(self):
        return self._url

    @property
    def family(self):
        return self._family

    @property
    def service(self):
        return self._service

    @property
    def parse_as(self):
        return self._parse_as

    @parse_as.setter
    def parse_as(self, parse_format):
        self._parse_as = parse_format

    @property
    def params(self):
        return self._params

    def __str__(self):
        return "TwitterRequest(url={})".format(self._url)

    def clone_and_merge(self, overrides):
        """
        Create a new ``TwitterRequest`` with updated parameters.

        :param overrides: a dict that overrides existing parameters
        """
        params = self.params.copy()
        params.update(overrides)

        return TwitterRequest(self._method, self._url, self._family,
                              self._service,
                              params=params,
                              parse_as=self._parse_as)


class Cursor:
    """
    A cursor for navigating collections.

    See: https://dev.twitter.com/overview/api/cursoring
    """

    def __init__(self, twitter_req):
        """
        Create a cursor over some endpoint that paginates.

        :param twitter_req: A twitter request that has paged results.
        """
        self._req = twitter_req
        self._cursor = -1
        self._update_called = True

    def update(self, resp):
        """
        Update the cursor given the response from the endpoint.

        :param resp: a TwitterResponse object
        """
        next_cursor = resp.body.get('next_cursor', 0)

        if next_cursor == 0:
            self._req = None
        else:
            self._cursor = next_cursor
            self._req = self._req.clone_and_merge({'cursor': next_cursor})

        self._update_called = True

    def __iter__(self):
        return self

    def next(self):
        return self.__next__()

    def __next__(self):
        # This helps prevent the (easy-to-make) bug where you fail to
        # update the request to get a new cursor, and just burn up your
        # rate limit on the same page.
        if not self._update_called:
            raise RuntimeError("Must call update() between `__next__`s")

        if self._req is None:
            raise StopIteration

        self._update_called = False

        return self._req


TwitterResponse = namedtuple('TwitterResponse', 'req resp body')


class BrittleWitError(Exception):
    """
    Base class for errors that allows for retries.
    """

    @property
    def is_retryable(self):
        """
        :return: True if the error is transient and the request can be retried
        """
        return False


class TwitterError(BrittleWitError):
    """
    Class that captures errors associated with TwitterRequests
    """

    # Developers can update this set if their semantics demand it.
    RETRYABLE_STATUS_CODES = {500,  # INTERNAL SERVER ERROR
                              502,  # BAD GATEWAY
                              503,  # SERVICE UNAVAILABLE
                              504}  # GATEWAY TIMEOUT

    def __init__(self, credentials, twitter_req, http_resp, message):
        """
        :param credentials: ClientCredentials associated with the failed
            request
        :param twitter_req: The request which failed
        :param http_resp: the http_response (transport specific) but must
            have a ``status`` attribute
        :param message: the error message associated with the failure
        """
        self._credentials = credentials
        self._twitter_req = twitter_req
        self._http_resp = http_resp
        self._status_code = http_resp.status
        self._message = message

    @property
    def status_code(self):
        return self._status_code

    @property
    def twitter_req(self):
        return self._twitter_req

    @property
    def is_retryable(self):
        return self._status_code in TwitterError.RETRYABLE_STATUS_CODES

    @property
    def message(self):
        return self._message

    @property
    def credentials(self):
        return self._credentials

    def __str__(self):
        return "TwitterError(code={}, msg={})".format(self._status_code,
                                                      self._message)

    def __repr__(self):
        return self.__str__()


class WrappedException(BrittleWitError):
    """
    Wraps an exception for error handling with retryable semantics.
    """

    # Update this set depending on your http transport library and
    # application semantics.
    RETRYABLE_EXCEPTIONS = set()

    @staticmethod
    def wrap_if_nessessary(underlying_exception):
        """
        Wraps the given exception if it is not a ``BrittleWitError``
        :param underlying_exception: the caught exception
        :return: a WrappedException if nessessary
        """
        if isinstance(underlying_exception, BrittleWitError):
            return underlying_exception
        else:
            return WrappedException(underlying_exception)

    def __init__(self, underlying_exception):
        """
        :param underlying_exception: The caught exception
        """
        self._underlying_exception = underlying_exception

    @property
    def underlying_exception(self):
        return self._underlying_exception

    @property
    def is_retryable(self):
        kind = type(self._underlying_exception)
        return kind in WrappedException.RETRYABLE_EXCEPTIONS

    def __str__(self):
        fmt = "WrappedException({})"
        return fmt.format(repr(self._underlying_exception))

    def __repr__(self):
        return self.__str__()


