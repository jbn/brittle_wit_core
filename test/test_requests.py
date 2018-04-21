import pytest
from brittle_wit_core.common import ELIDE, TwitterRequest, GET


def test_elide():
    assert str(ELIDE) == 'ELIDE'
    assert repr(ELIDE) == 'ELIDE'
    assert ELIDE == ELIDE
    assert ELIDE is ELIDE


@pytest.fixture
def req():
    return TwitterRequest(GET,
                          "http://twitter.com/faux/service",
                          "faux",
                          "faux/service",
                          {'timeout': 1000, 'name': ELIDE})


def test_accessors(req):
    assert req.method == GET
    assert req.url == "http://twitter.com/faux/service"
    assert req.family == "faux"
    assert req.service == "faux/service"

    # Enforce this default
    assert req.parse_as == "json"


def test_human_readable(req):
    assert str(req) == "TwitterRequest(url=http://twitter.com/faux/service)"


def test_param_eliding(req):
    assert 'timeout' in req.params
    assert 'name' not in req.params


def test_clone_and_merge(req):
    dup = req.clone_and_merge({'timeout': 0})
    assert dup.params["timeout"] == 0
    assert req.params["timeout"] == 1000


def test_parse_as_updating(req):
    # This is the default.
    assert req.parse_as == "json"

    req.parse_as = "raw"
    assert req.parse_as == "raw"
