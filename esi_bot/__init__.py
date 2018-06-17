"""ESI Slack bot."""


# pylint: disable=unused-argument,wrong-import-position,wrong-import-order
from gevent import monkey
monkey.patch_all()

import re
import os
import logging
import pkg_resources
from functools import wraps
from functools import partial
from collections import namedtuple

import requests
from requests.adapters import HTTPAdapter


LOG = logging.getLogger(__name__)
LOG.setLevel(logging.INFO)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s:%(name)s:%(levelname)s: %(message)s",
)

ESI = "https://esi.evetech.net"
REPLY_SNIPPET = namedtuple("ReplySnippet",
                           ("content", "filename", "filetype", "comment", "title"))
REPLY_MESSAGE = namedtuple("ReplyMessage", ("content", "attachments"))
MESSAGE = namedtuple("Message", ("speaker", "command", "args"))
COMMANDS = {}  # trigger: function
EXTENDED_HELP = {}  # name: docstring
__version__ = pkg_resources.get_distribution("esi-bot").version


def _build_session():
    """Builds a requests session with a pool and retries."""

    ses = requests.Session()
    ses.headers["User-Agent"] = "esi-bot/{}".format(__version__)
    adapt = HTTPAdapter(max_retries=3, pool_connections=10, pool_maxsize=100)
    ses.mount("http://", adapt)
    ses.mount("https://", adapt)
    return ses


SESSION = _build_session()


def command(func=None, **kwargs):
    """Declare a function an ESI-bot command.

    NB: the function name is used as the help name

    KWargs:
        trigger: string, list of strings, or compiled regex pattern.
                 optional, will default to the function name
    """

    if func is None:
        return partial(command, **kwargs)

    COMMANDS[kwargs.get("trigger", func.__name__)] = func
    EXTENDED_HELP[func.__name__] = func.__doc__
    if isinstance(kwargs.get("trigger"), (list, tuple)):
        for trigger in kwargs.get("trigger"):
            EXTENDED_HELP[trigger] = func.__doc__
    return None


def do_request(url, *args, **kwargs):
    """Make a GET request, return the status code and json response."""

    try:
        res = SESSION.get(url, *args, **kwargs)
    except Exception as error:
        LOG.warning("failed to request %s: %r", url, error)
        return 499, "failed to request {}".format(url)

    try:
        res.raise_for_status()
    except Exception as error:
        LOG.warning("request to %s failed: %r", url, error)
    else:
        LOG.info("requested: %s", url)

    try:
        content = res.json()
    except Exception:
        content = res.text

    return res.status_code, content
