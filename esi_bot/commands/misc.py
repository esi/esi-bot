"""Miscellaneous commands."""

from esi_bot import command
from esi_bot import __version__


@command(trigger=("hey", "hi", "hello", "o7", "7o", "o/", r"\o"))
def hello(msg):
    """TIL you need help to say hello."""

    if "whatup" in msg.args:
        return "not much. whatup <@{}>".format(msg.speaker)
    if msg.command in ("o7", "o/"):
        return "o7 <@{}>".format(msg.speaker)
    if msg.command in ("7o", r"\o"):
        return "7o <@{}>".format(msg.speaker)
    return "hey <@{}> howsit goin?".format(msg.speaker)


@command
def version(*_):
    """Display ESI-bot's running version."""

    return "ESI-bot version {}".format(__version__)
