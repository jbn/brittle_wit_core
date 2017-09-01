import json
import os
from collections import namedtuple
from contextlib import contextmanager


SELF_DIR = os.path.dirname(os.path.realpath(__file__))
FIXTURES_DIR = os.path.join(SELF_DIR, "fixtures")


def load_fixture_txt(file_name):
    with open(os.path.join(FIXTURES_DIR, file_name)) as fp:
        return fp.read()


def load_fixture_json(file_name):
    with open(os.path.join(FIXTURES_DIR, file_name)) as fp:
        return json.load(fp)


MockResp = namedtuple("MockResp", "headers")


@contextmanager
def replace_env(**replacements):
    original = os.environ.copy()
    os.environ.update(replacements)
    yield
    os.environ = original
