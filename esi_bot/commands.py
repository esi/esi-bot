"""ESI-bot commands."""


import re
import time

from esi_bot import ESI
from esi_bot import REPLY
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
        return "ESI-bot help for {}:\n>>>{}".format(
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
                targets.pattern,
            ))
        else:
            commands.append(targets)

    return "{}The following commands are enabled: {}".format(
        # don't echo unknown commands and start a bot fight
        "I'm sorry{}, that's an unknown command. ".format(
            _fmt_speaker(msg)
        ) * int(msg.command != "help"),
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
        statuses.sort(key=lambda x: (x["route"], x["method"]))
        method_pad = max([len(route["method"]) for route in statuses])
        lines = ["{} {}".format(
            route["method"].upper().ljust(method_pad),
            route["route"],
        ) for route in statuses]
        return "```{}```".format("\n".join(lines))
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

    attachments = []
    if red_routes:
        attachments.append({
            "color": "danger",
            "fallback": "{} red".format(len(red_routes)),
            "text": "{emoji} {count} red {emoji} {details}".format(
                emoji=":fire:" * int(max(
                    round(len(red_routes) / len(STATUS["status"]) * 10),
                    1,
                )),
                count=len(red_routes),
                details=_status_str(red_routes),
            )
        })
    if yellow_routes:
        attachments.append({
            "color": "warning",
            "fallback": "{} yellow".format(len(yellow_routes)),
            "text": "{emoji} {count} yellow {emoji} {details}".format(
                emoji=":fire_engine:" * int(max(
                    round(len(yellow_routes) / len(STATUS["status"]) * 10),
                    1,
                )),
                count=len(yellow_routes),
                details=_status_str(yellow_routes),
            )
        })
    if not red_routes and not yellow_routes:
        attachments.append({
            "color": "good",
            "text": ":ok_hand:",
        })

    return REPLY(content=None, attachments=attachments)


@command(trigger=("id", "ids", "ranges"))
def ids(*_):
    """Return a link to the ID ranges gist and asset location IDs doc."""

    return (
        "https://gist.github.com/a-tal/5ff5199fdbeb745b77cb633b7f4400bb\n"
        "assets: "
        "https://docs.esi.evetech.net/docs/asset_location_id"
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


def server_status(datasource):
    """Generate """

    if datasource not in ("tranquility", "singularity"):
        return "Cannot request server status for `{}`".format(datasource)

    status_code, response = do_request("{}/v1/status/?datasource={}".format(
        ESI,
        datasource,
    ))
    server_name = datasource.capitalize()

    if status_code == 200:
        vip = response.get("vip")
        attachment = {
            "color": "warning" if vip else "good",
            "title": "{} status".format(server_name),
            "fields": [
                {
                    "title": "Players online",
                    "value": "{:,}".format(response["players"]),
                    "short": True,
                },
                {
                    "title": "Server started",
                    "value": response["start_time"],
                    "short": True,
                },
            ],
            "fallback": "{} status: {:,} online, started at {}{}".format(
                server_name,
                response["players"],
                response["start_time"],
                ", in VIP" * int(vip is True),
            ),
        }
        if vip:
            attachment["fields"].append({"title": "In VIP mode"})

    elif status == 503:
        attachment = {
            "color": "danger",
            "title": "{} status".format(server_name),
            "text": "Offline",
            "fallback": "{} status: Offline".format(server_name),
        }
    else:
        indeterminate = (
            "Cannot determine server status. "
            "It might be offline, or experiencing connectivity issues."
        )
        attachment = {
            "color": "danger",
            "title": "{} status".format(server_name),
            "text": indeterminate,
            "fallback": "{} status: {}".format(server_name, indeterminate),
        }

    return REPLY(content=None, attachments=[attachment])


@command(trigger=("tq", "tranquility"))
def tq(*_):  # pylint: disable=invalid-name
    """Display current status of Tranquility, the main game server."""

    return server_status("tranquility")


@command(trigger=("sisi", "singularity"))
def sisi(*_):
    """Display current status of Singularity, the main test server."""

    return server_status("singularity")
