"""ESI-bot commands."""


import re
import json
import time
from datetime import datetime

from esi_bot import ESI
from esi_bot import REPLY
from esi_bot import SNIPPET
from esi_bot import EPHEMERAL
from esi_bot import command
from esi_bot import COMMANDS
from esi_bot import do_request
from esi_bot import multi_request
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

    cmd_list = "The following commands are enabled: {}".format(
        " ".join("`{}`".format(x) for x in commands)
    )

    if msg.command == "help":
        return cmd_list
    return EPHEMERAL(
        content="{} {}".format(
            "I'm sorry, that's an unknown command.",
            cmd_list,
        ),
        attachments=None,
    )


@command(trigger=("hey", "hi", "hello", "o7", "7o", "o/"))
def hello(msg):
    """TIL you need help to say hello."""

    if "whatup" in msg.args:
        return "not much. whatup{}".format(_fmt_speaker(msg))
    if msg.command in ("o7", "o/"):
        return "o7{}".format(_fmt_speaker(msg))
    if msg.command == "7o":
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
        if len(statuses) > 99:
            lines = lines[0:80]
            lines.append("And {} more...".format(len(statuses) - 80))
        return "```{}```".format("\n".join(lines))
    return ""


@command
def status(*_):
    """Return the current ESI health/status."""

    now = time.time()
    if now - STATUS["timestamp"] > 60:
        code, esi_status = do_request("{}/status.json".format(ESI))
        if code == 200:
            STATUS["status"] = esi_status
        else:
            return ":fire: (failed to fetch status.json)"

    attachments = []
    categories = [
        ("red", ":fire:", "danger"),
        ("yellow", ":fire_engine:", "warning"),
    ]

    for status_color, emoji, color_value in categories:
        routes = [route for route in STATUS["status"] if
                  route["status"] == status_color]
        if routes:
            attachments.append({
                "color": color_value,
                "fallback": "{}: {} out of {}, {:.2%}".format(
                    status_color.capitalize(),
                    len(routes),
                    len(STATUS["status"]),
                    len(routes) / len(STATUS["status"]),
                ),
                "text": "{emoji} {count} {emoji} {details}".format(
                    emoji=emoji * max(min(
                        int(round(len(routes) / len(STATUS["status"]) * 10)),
                        5), 1),
                    count="{} {} (out of {}, {:.2%})".format(
                        len(routes),
                        status_color,
                        len(STATUS["status"]),
                        len(routes) / len(STATUS["status"]),
                    ),
                    details=_status_str(routes),
                )
            })

    if not attachments:
        attachments.append({
            "color": "good",
            "text": ":ok_hand:",
        })

    return REPLY(content=None, attachments=attachments)


@command(trigger=("id", "ids", "ranges"))
def ids(*_):
    """Return a link to the ID ranges gist and asset location IDs doc."""

    return (
        "ID ranges reference:"
        "https://gist.github.com/a-tal/5ff5199fdbeb745b77cb633b7f4400bb\n"
        "Asset `location_id` reference: "
        "{}docs/asset_location_id"
    ).format(ESI_DOCS)


@command
def waffle(*_):
    """Return a link to the ESI issues waffle board."""

    return "https://waffle.io/esi/esi-issues"


@command
def faq(*_):
    """Return a link to the ESI issues FAQ."""

    return "{}docs/FAQ".format(ESI_DOCS)


ISSUE_NEW = {
    "title": "Opening a new issue",
    "title_link": "{}#opening-a-new-issue".format(ESI_DOCS),
    "text": ("Before opening a new issue, please use the "
             "<{}issues|search function> to see if a similar issue "
             "exists, or has already been closed.").format(ESI_ISSUES),
}
ISSUE_BUG = {
    "title": "Report a new bug",
    "text": ("• unexpected 500 responses\n"
             "• incorrect information in the swagger spec\n"
             "• otherwise invalid or unexpected responses"),
    "color": "danger",
    "actions": [
        {
            "type": "button",
            "text": "Report a bug",
            "url": "{}issues/new?template=bug.md".format(ESI_ISSUES),
            "style": "danger",
        },
    ],
}
ISSUE_FEATURE = {
    "title": "Request a new feature",
    "text": ("• adding an attribute to an existing route\n"
             "• exposing other readily available client data\n"
             "• meta requests, adding some global parameter to the specs"),
    "color": "good",
    "actions": [
        {
            "type": "button",
            "text": "Request a feature",
            "url": "{}issues/new?template=feature_request.md".format(
                ESI_ISSUES
            ),
            "style": "primary",
        },
    ],
}
ISSUE_INCONSISTENCY = {
    "title": "Report an inconsistency",
    "text": ("• two endpoints returning slightly "
             "different names for the same attribute\n"
             "• attribute values are returned with "
             "different formats for different routes"),
    "color": "warning",
    "actions": [
        {
            "type": "button",
            "text": "Report an inconsistency",
            "url": "{}issues/new?template=inconsistency.md".format(
                ESI_ISSUES
            ),
        },
    ],
}


@command(trigger="new")
def new_issue(*_):
    """Return instructions for opening a new ESI issue."""

    return REPLY(content=None, attachments=[
        ISSUE_NEW,
        ISSUE_BUG,
        ISSUE_FEATURE,
        ISSUE_INCONSISTENCY,
    ])


@command(trigger=("bug", "br"))
def bug(*_):
    """Return instructions for reporting an ESI bug."""

    return REPLY(content=None, attachments=[
        ISSUE_NEW,
        ISSUE_BUG,
    ])


@command(trigger=("feature", "fr", "enhancement"))
def feature(*_):
    """Return instructions for creating a new feature request."""

    return REPLY(content=None, attachments=[
        ISSUE_NEW,
        ISSUE_FEATURE,
    ])


@command
def inconsistency(*_):
    """Return instructions for reporting an inconsistency."""

    return REPLY(content=None, attachments=[
        ISSUE_NEW,
        ISSUE_INCONSISTENCY,
    ])


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


def _running_for(start_time):
    started = datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%SZ")
    running_for = int((datetime.utcnow() - started).total_seconds())
    if running_for < 60:
        return "less than a minute"

    running_for_list = []
    units = [
        (running_for // (60 * 60), "hour"),
        ((running_for // 60) % 60, "minute"),
    ]
    for number, unit in units:
        running_for_list.append("{} {}{}".format(
            number,
            unit,
            "s" * (number != 1)
        ))
    return ", ".join(running_for_list)


def server_status(datasource):
    """Generate a reply describing the status of an EVE server/datasource."""

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
                },
                {
                    "title": "Started at",
                    "value": response["start_time"],
                    "short": True,
                },
                {
                    "title": "Running for",
                    "value": _running_for(response["start_time"]),
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
            attachment["fields"].insert(0, {"title": "In VIP mode"})

    elif status_code == 503:
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


@command(trigger=("item", "item_id"))
def item(msg):
    """Lookup an item by ID, including dogma information."""

    start = time.time()

    if len(msg.args) != 1:
        return "usage: !esi {} <id>".format(msg.command)

    item_id = msg.args[0]

    try:
        int(item_id)
    except Exception:
        return "get outta here hackerman"

    type_url = "{}/v3/universe/types/{}/".format(ESI, item_id)

    ret, res = do_request(type_url)

    dogma = res.pop("dogma_attributes", [])

    attr_urls = {}  # url: attr
    for attr in dogma:
        url = "{}/v1/dogma/attributes/{}/".format(ESI, attr["attribute_id"])
        attr_urls[url] = attr

    dogma_attrs = {}  # name: value
    for url, response in multi_request(attr_urls.keys()).items():
        _ret, _res = response
        attr = attr_urls[url]

        if _ret == 200:
            title = _res["name"]
        else:
            title = "failed to lookup attr: {}".format(attr["attribute_id"])

        dogma_attrs[title] = attr["value"]

    if dogma_attrs:
        res["dogma_attributes"] = dogma_attrs

    return SNIPPET(
        content=json.dumps(res, sort_keys=True, indent=4),
        filename="{}.json".format(item_id),
        filetype="json",
        comment="Item {}: {} ({:,d} requests in {:,.0f}ms)".format(
            item_id,
            res["name"] if ret == 200 else "Error",
            len(attr_urls) + 1,
            (time.time() - start) * 1000,
        ),
        title=type_url,
    )
