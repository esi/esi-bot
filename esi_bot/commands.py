"""ESI-bot commands."""


import re
import time
import json
from collections import Counter

from esi_bot import ESI
from esi_bot import command
from esi_bot import COMMANDS
from esi_bot import do_request
from esi_bot import EXTENDED_HELP
from esi_bot import __version__


STATUS = {"timestamp": 0, "status": []}
ESI_ISSUES = "https://github.com/esi/esi-issues/"
ESI_DOCS = "https://docs.esi.evetech.net/"


def _fmt_speaker(msg):
    """With the RTM API, you have to use user ids and this wonky format."""

    return " <@{}>".format(msg.speaker)


@command(trigger="help")
def get_help(msg):
    """Return help on an available command, or list all commands."""

    if msg.args and msg.args[0] in EXTENDED_HELP:
        return "ESI-bot help for {}:\n```{}```".format(
            msg.args[0],
            EXTENDED_HELP[msg.args[0]],
        )

    commands = []  # list of command help strings
    for targets in COMMANDS:
        if isinstance(targets, (list, tuple)):
            commands.append(", ".join(targets))
        elif isinstance(targets, re._pattern_type):
            commands.append("{}: {}".format(
                COMMANDS[targets].__name__,
                targets.pattern
            ))
        else:
            commands.append(targets)

    return "{}The following commands are enabled: {}".format(
        # don't echo unknown commands and start a bot fight
        "I'm sorry{}, that's an unknown command. ".format(_fmt_speaker(msg))
        * int(msg.command != "help"),
        " ".join("`{}`".format(x) for x in commands),
    )


@command(trigger=("hey", "hi", "hello", "o7", "7o", "o/"))
def hello(msg):
    """TIL you need help to say hello."""

    if "whatup" in msg.args:
        return "not much. whatup{}".format(_fmt_speaker(msg))
    elif msg.command in ("o7", "o/"):
        return "o7{}".format(_fmt_speaker(msg))
    elif msg.command == "7o":
        return "7o{}".format(_fmt_speaker(msg))
    return "hey{} howsit goin?".format(_fmt_speaker(msg))


@command(trigger=re.compile(r"^#?(?P<gh_issue>[0-9]+)$"))
def issue(match, msg):
    """Look up ESI-issue details on GitHub."""

    code, details = do_request(
        "https://api.github.com/repos/esi/esi-issues/issues/{}".format(
            match.groupdict()["gh_issue"]
        )
    )

    if code >= 400:
        return "failed to lookup details for issue {}".format(msg.command)
    return "{} ({})".format(details["html_url"], details["state"])


def _status_str(statuses):
    """Generate a string to describe the route statuses."""

    if statuses:
        if len(statuses) < 9:
            lines = ["{} {}".format(
                route["method"].upper(),
                route["route"]
            ) for route in statuses]
        else:
            # Assuming that all ESI routes only have a single tag.
            counter = Counter([route["tags"][0] for route in statuses])
            lines = ["{} in {}".format(
                count,
                tag
            ) for tag, count in counter.items()]
        return "```{}```".format("\n".join(lines))
    else:
        return ""


@command
def status(*_):
    """Generic ESI status."""

    now = time.time()
    if now - STATUS["timestamp"] > 60:
        code, esi_status = do_request("{}/status.json".format(ESI))
        if code == 200:
            STATUS["status"] = esi_status
        else:
            return ":fire: (failed to fetch status.json)"

    red_routes = [route for route in STATUS["status"] if
                  route["status"] == "red"]
    yellow_routes = [route for route in STATUS["status"] if
                     route["status"] == "yellow"]

    slow_route_count = len(red_routes) + len(yellow_routes)
    slow_route_ratio = slow_route_count / len(STATUS["status"])
    if slow_route_ratio > 0.3:
        return ":fire:" * round(slow_route_ratio * 10)

    status_messages = []
    if red_routes:
        status_messages.append(
            ":fire: {} red :fire: {}".format(
                len(red_routes),
                _status_str(red_routes),
            )
        )
    if yellow_routes:
        status_messages.append(
            ":fire_engine: {} yellow :fire_engine: {}".format(
                len(yellow_routes),
                _status_str(yellow_routes),
            )
        )

    return "\n".join(status_messages) if status_messages else ":ok_hand:"


@command(trigger=("id", "ids", "ranges"))
def ids(*_):
    """Return a link to the ID ranges gist."""

    return (
        "https://gist.github.com/a-tal/5ff5199fdbeb745b77cb633b7f4400bb\n"
        "assets: "
        "https://forums.eveonline.com/t/asset-location-id-quick-reference/"
    )


@command
def waffle(*_):
    """Return a link to the ESI issues waffle board."""

    return "https://waffle.io/esi/esi-issues"


@command
def faq(*_):
    """Return a link to the ESI issues FAQ."""

    return "{}docs/FAQ".format(ESI_DOCS)


@command(trigger=("new", "bug", "br"))
def new(msg):
    """Return a link to open a new ESI bug."""

    return (
        "You can open a new bug with this link{}: "
        "{}issues/new?template=bug.md"
    ).format(_fmt_speaker(msg), ESI_ISSUES)


@command(trigger=("feature", "fr", "enhancement"))
def feature(msg):
    """Return a link to create a new feature request."""

    return (
        "You can make a new feature request with this link{}: "
        "{}issues/new?template=feature_request.md"
    ).format(_fmt_speaker(msg), ESI_ISSUES)


@command
def inconsistency(msg):
    """Return a link to report an inconsistency."""

    return (
        "You can report an inconsistency with this link{}: "
        "{}issues/new?template=inconsistency.md"
    ).format(_fmt_speaker(msg), ESI_ISSUES)


@command
def issues(*_):
    """Return a link to ESI issues."""

    return ESI_ISSUES


@command
def sso(*_):
    """Return a link to SSO issues."""

    return "https://github.com/ccpgames/sso-issues/issues/"


@command(trigger=("ui", "webui"))
def webui(*_):
    """Return a link to the ui (v3)."""

    return "{}/ui/".format(ESI)


@command(trigger=("legacy", "v2ui"))
def legacy(*_):
    """Return links to the old v2 ui."""

    return (
        "Legacy (v2) UIs are still available at {esi}/latest/ "
        "{esi}/dev/ and {esi}/legacy/"
    ).format(esi=ESI)


@command(trigger=("diff", "diffs"))
def diff(*_):
    """Return a link to the ESI spec diffs page."""

    return "{}/diff/latest/dev/".format(ESI)


@command(trigger=("source", "repo"))
def source(msg):
    """Return a link to the repo for this bot."""

    return (
        "I'm an open source bot{}. If you want to contribute or are curious "
        "how I work, my source is available for you to browse here: "
        "https://github.com/esi/esi-bot/"
    ).format(_fmt_speaker(msg))


@command
def version(*_):
    """Display ESI-bot's running version."""

    return "ESI-bot version {}".format(__version__)


@command(trigger=("tq", "tranquility"))
def tq(*_):  # pylint: disable=invalid-name
    """Display current status of Tranquility, the main game server."""

    tq_ = do_request("{}/dev/status/".format(ESI))[1]
    return "Tranquility status: ```{}```".format(
        json.dumps(tq_, sort_keys=True, indent=4)
    )


@command(trigger=("sisi", "singularity"))
def sisi(*_):
    """Display current status of Singularity, the main test server."""

    sisi_ = do_request("{}/dev/status/?datasource=singularity".format(ESI))[1]
    return "Singularity status: ```{}```".format(
        json.dumps(sisi_, sort_keys=True, indent=4)
    )
