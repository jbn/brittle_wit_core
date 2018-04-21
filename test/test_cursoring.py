import pytest
from brittle_wit_core.common import (Cursor,
                                     GET,
                                     TwitterRequest,
                                     TwitterResponse)


@pytest.fixture
def req():
    return TwitterRequest(GET, "http://twitter.com/f/s", "f", "f/s")


def test_cursor_on_end_of_pages(req):
    cursor = iter(Cursor(req))
    assert req is next(cursor)

    cursor.update(TwitterResponse(None, None, {'next_cursor': 0}))
    with pytest.raises(StopIteration):
        next(cursor)


def test_next_cursored_page(req):
    cursor = iter(Cursor(req))
    cursor.update(TwitterResponse(None, None, {'next_cursor': 100}))
    req = next(cursor)
    assert req.params['cursor'] == 100


def test_must_call_update(req):
    cursor = iter(Cursor(req))
    assert req is next(cursor)
    with pytest.raises(RuntimeError):
        next(cursor)
