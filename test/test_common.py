import unittest
try:
    from unittest.mock import MagicMock
except ImportError:
    from mock import MagicMock

from brittle_wit_core.common import (TwitterError, WrappedException, GET, POST,
                                     TwitterResponse, Cursor, BrittleWitError,
                                     ELIDE, TwitterRequest)
from brittle_wit_core.oauth import ClientCredentials


class TestElide(unittest.TestCase):

    def test_str(self):
        self.assertEqual(str(ELIDE), 'ELIDE')

    def test_repr(self):
        self.assertEqual(repr(ELIDE), 'ELIDE')

    def test_equal(self):
        self.assertEqual(ELIDE, ELIDE)


class TestTwitterRequest(unittest.TestCase):

    def setUp(self):
        self.req = TwitterRequest(GET, "http://twitter.com/faux/service",
                                  "faux", "faux/service",
                                  {'timeout': 1000, 'name': ELIDE})

    def test_accessors(self):
        self.assertEqual(self.req.method, GET)
        self.assertEqual(self.req.url, "http://twitter.com/faux/service")
        self.assertEqual(self.req.family, "faux")
        self.assertEqual(self.req.service, "faux/service")

        # Enforce this default
        self.assertEqual(self.req.parse_as, "json")

    def test_str(self):
        self.assertEqual(str(self.req),
                         "TwitterRequest(url=http://twitter.com/faux/service)")

    def test_param_eliding(self):
        self.assertIn('timeout', self.req.params)
        self.assertNotIn('name', self.req.params)

    def test_parse_as_updating(self):
        self.req.parse_as = "raw"
        self.assertEqual(self.req.parse_as, "raw")

    def test_clone_and_merge(self):
        dup = self.req.clone_and_merge({'timeout': 0})
        self.assertEqual(dup.params["timeout"], 0)
        self.assertEqual(self.req.params["timeout"], 1000)


class TestCursor(unittest.TestCase):

    def setUp(self):
        self.req = TwitterRequest(GET, "http://twitter.com/f/s", "f", "f/s")

    def test_no_pages(self):
        cursor = iter(Cursor(self.req))
        self.assertIs(self.req, next(cursor))

        cursor.update(TwitterResponse(None, None, {'next_cursor': 0}))
        with self.assertRaises(StopIteration):
            next(cursor)

    def test_pages(self):
        cursor = iter(Cursor(self.req))
        cursor.update(TwitterResponse(None, None, {'next_cursor': 100}))
        self.req = next(cursor)
        self.assertEqual(self.req.params['cursor'], 100)

    def test_must_call_update(self):
        cursor = iter(Cursor(self.req))
        self.assertIs(self.req, next(cursor))
        with self.assertRaises(RuntimeError):
            next(cursor)


class TestBrittleWitError(unittest.TestCase):

    def test_not_retryable_by_default(self):
        self.assertFalse(BrittleWitError().is_retryable)


class TestTwitterError(unittest.TestCase):

    def setUp(self):
        self.client_cred = ClientCredentials(1, "token", "secret")
        self.twitter_req = TwitterRequest(POST, "REQ-URL", "FAM", "SVC")
        resp = MagicMock()
        resp.status = 429
        self.resp = resp

    def test_accessors(self):
        err = TwitterError(self.client_cred, self.twitter_req, self.resp, "m")
        self.assertIs(err.credentials, self.client_cred)
        self.assertIs(err.twitter_req, self.twitter_req)
        self.assertEqual(err.status_code, self.resp.status)
        self.assertFalse(err.is_retryable)
        self.assertEqual(err.message, "m")

    def test_str(self):
        err = TwitterError(self.client_cred, self.twitter_req, self.resp, "m")
        self.assertEqual(str(err), "TwitterError(code=429, msg=m)")

    def test_repr(self):
        err = TwitterError(self.client_cred, self.twitter_req, self.resp, "m")
        self.assertEqual(repr(err), "TwitterError(code=429, msg=m)")

    def test_on_retryable_code(self):
        self.resp.status = 500
        err = TwitterError(self.client_cred, self.twitter_req, self.resp, "m")
        self.assertTrue(err.is_retryable)


class TestWrappedException(unittest.TestCase):

    def test_str(self):
        err = WrappedException(KeyboardInterrupt())
        self.assertEqual(str(err), "WrappedException(KeyboardInterrupt())")

    def test_repr(self):
        err = WrappedException(KeyboardInterrupt())
        self.assertEqual(repr(err), "WrappedException(KeyboardInterrupt())")

    def test_on_not_retryable(self):
        under = KeyboardInterrupt()
        err = WrappedException(under)
        self.assertIs(under, err.underlying_exception)

    def test_on_not_retryable(self):
        err = WrappedException(KeyboardInterrupt())
        self.assertFalse(err.is_retryable)

    def test_on_retryable(self):
        err = WrappedException.RETRYABLE_EXCEPTIONS.add(KeyboardInterrupt)
        err = WrappedException(KeyboardInterrupt())
        self.assertTrue(err.is_retryable)

    def test_wrap_if_nessessary_when_unnessessary(self):
        e = BrittleWitError()
        self.assertTrue(e is WrappedException.wrap_if_nessessary(e))

    def test_wrap_if_nessessary_when_nessessary(self):
        e = Exception()
        self.assertFalse(e is WrappedException.wrap_if_nessessary(e))
