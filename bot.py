# -*- coding: utf-8 -*-
"""Slack IRC/incoming-webhooks bot for tweetfleet."""


import os
import re
import json
import time
import logging

import irc3
import requests
from requests.adapters import HTTPAdapter


LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)

WELCOMED_IN = os.environ.get("IRC_CHANNELS", "#esi").split(" ")
ESI_SPECS = {
    x: {"timestamp": 0, "spec": {}} for x in ("latest", "legacy", "dev")
}
ESI = "https://esi.tech.ccp.is"
WEBHOOK = os.environ.get("SLACK_WEBHOOK")
STATUS = {"timestamp": 0, "status": []}


if not WEBHOOK:
    raise SystemExit("I need a webhook url to post multiline responses")


def _build_session():
    """Builds a requests session with a pool and retries."""

    ses = requests.Session()
    ses.headers["User-Agent"] = "esi-bot/0.0.1 -- this is the slack ESI bot"
    adapt = HTTPAdapter(max_retries=3, pool_connections=10, pool_maxsize=100)
    ses.mount("http://", adapt)
    ses.mount("https://", adapt)
    return ses


SESSION = _build_session()


def _channel_request(send, speaker, command, *args):
    """Invite request for new channels (TODO)."""

    send((
        "I can't do that right now {} . "
        "ask @ccp_snowedin to add me in another channel"
    ).format(speaker))


def _hello_response(send, speaker, command, *args):
    """Someone has said hello to us."""

    if "whatup" in args:
        send("not much. whatup {}".format(speaker))
    elif command in ("o7", "o/"):
        send("o7 {}".format(speaker))
    else:
        send("hey {} howsit goin?".format(speaker))


def _issue_details(match, send, speaker, command, *args):
    """Look up esi-issue details on github."""

    status, details = _do_request(
        "https://api.github.com/repos/ccpgames/esi-issues/issues/{}".format(
            match.groupdict()["gh_issue"]
        )
    )

    if status >= 400:
        send("failed to lookup details for issue {}".format(command))
    else:
        send("{} ({})".format(details["html_url"], details["state"]))


def _esi_request(match, send, speaker, command, *args):
    """Make an ESI GET request, if the path is known."""

    version, *req_sections = match.groupdict()["esi_path"].split("/")
    if re.match(r"^v[0-9]+$", version):
        send("sorry, but I only support latest, legacy or dev versions")
        return
    elif version not in ("latest", "legacy", "dev"):
        req_sections.insert(0, version)
        version = "latest"

    params = ""
    if "?" in req_sections[-1]:
        if req_sections[-1].startswith("?"):
            params = req_sections.pop()
            params = params[1:]
        else:
            # qsparams passed w/out trailing slash
            final_path, params = req_sections.pop().split("?")
            req_sections.append(final_path)

    path = "/{}/".format("/".join(x for x in req_sections if x))
    if _valid_path(path, version):
        url = "{}/{}{}{}{}".format(
            ESI,
            version,
            path,
            "?" * int(params != ""),
            params,
        )
        status, res = _do_request(url)
        if not _send_multiline("{}\n{}\n```{}```".format(
                url,
                status,
                json.dumps(res, sort_keys=True, indent=4)
            )):
            # fallback in case webhook fails
            send("{} ({}): `{}`".format(url, status, res))
    else:
        send("failed to find GET {} in the {} ESI spec".format(path, version))


def _clean_multiline_text(text):
    """Cleans multiline text, if it's longer than slack's limit."""

    content = text[:2900]
    if content != text:
        content = "{}\n<content snipped>".format(content)

    if content.count("```") % 2 != 0:
        content = "{}\n```".format(content)

    return content


def _send_multiline(text):
    """Send a multiline message via slack's incoming webhooks."""

    try:
        res = SESSION.post(WEBHOOK, json={
            "text": _clean_multiline_text(text),
            "username": "ESI (bot)",
            "icon_emoji": ":techco:",
        })
        res.raise_for_status()
        return True
    except Exception as error:
        LOG.warning("Failed to send to slack: %r", error)
        return False


def _valid_path(path, version):
    """Check if the path is known."""

    spec = ESI_SPECS[version]["spec"]
    for spec_path, operations in spec["paths"].items():
        # we could pre-validate arguments.... *effort* though
        if re.match(re.sub(r"{.*}", "[^/]+", spec_path), path):
            # we only make get requests
            return "get" in operations
    return False


def _help(send, speaker, command, *args):
    """Return basic help on available commands."""

    commands = []  # list of command help strings
    for targets in COMMANDS:
        if isinstance(targets, (list, tuple)):
            commands.append(", ".join(targets))
        elif isinstance(targets, re._pattern_type):
            commands.append(targets.pattern)
        else:
            commands.append(targets)
    send("The following commands are enabled: {}".format(
        " ".join("`{}`".format(x) for x in commands)
    ))


def _refresh_spec(send, speaker, command, *args):
    """Refresh internal specs."""

    refreshed = _do_refresh()
    if refreshed:
        send("I refreshed my internal copy of the {}{}{} spec{}".format(
            ", ".join(refreshed[:-1]),
            " and " * int(len(refreshed) > 1),
            refreshed[-1],
            "s" * int(len(refreshed) != 1),
        ))
    else:
        send("my internal specs are up to date (try again later)")


def _status(send, speaker, command, *args):
    """Generic ESI status."""

    now = time.time()
    if now - STATUS["timestamp"] > 60:
        code, esi_status = _do_request("{}/status.json".format(ESI))
        if code == 200:
            STATUS["status"] = esi_status
        else:
            send(":fire: (failed to fetch status.json)")
            return

    red = yellow = 0
    for status in STATUS["status"]:
        red += status["status"] == "red"
        yellow += status["status"] == "yellow"

    if red:
        send(":fire: {} red {} yellow :fire:".format(red, yellow))
    elif yellow:
        send(":fire_engine: {} yellow :fire_engine:".format(yellow))
    else:
        send(":ok_hand:")


def _id_gist(send, *_):
    """Return a link to the ID ranges gist."""

    send("https://gist.github.com/a-tal/5ff5199fdbeb745b77cb633b7f4400bb")


def _waffle(send, *_):
    """Return a link to the ESI issues waffle board."""

    send("https://waffle.io/ccpgames/esi-issues")


def _faq(send, *_):
    """Return a link to the ESI issues FAQ."""

    send("https://github.com/ccpgames/esi-issues#faq")


def _new_issue(send, speaker, *_):

    send((
        "You can make a new issue with this link {}: "
        "https://github.com/ccpgames/esi-issues/issues/new"
    ).format(speaker))


def _issues(send, *_):
    """Return a link to ESI issues."""

    send("https://github.com/ccpgames/esi-issues/issues/")


def _sso_issues(send, *_):
    """Return a link to SSO issues."""

    send("https://github.com/ccpgames/sso-issues/issues/")


def _ui(send, *_):
    """Return a link to the ui (v3)."""

    send("{}/ui/".format(ESI))


def _legacy_ui(send, *_):
    """Return links to the v2 ui."""

    send((
        "Legacy (v2) UIs are still available at {esi}/latest/ "
        "{esi}/dev/ and {esi}/legacy/"
    ).format(esi=ESI))


def _diff(send, *_):
    """Return a link to the ESI spec diffs page."""

    send("{}/diff/latest/dev/".format(ESI))


def _bot_repo(send, speaker, *_):
    """Return a link to the repo for this bot."""

    send((
        "I'm an open source bot {} . If you want to contribute or are curious "
        "how I work, my source is available for you to browse here: "
        "https://github.com/ccpgames/esi-bot/"
    ).format(speaker))


def _do_refresh():
    """DRY helper to refresh all stale ESI specs.

    Returns:
        list of updated ESI spec versions
    """

    updates = {}
    for version, details in ESI_SPECS.items():
        if not details["spec"] or details["timestamp"] < time.time() + 300:
            status, spec = _do_request("{}/{}/swagger.json".format(
                ESI,
                version,
            ))
            if status == 200:
                updates[version] = {"timestamp": time.time(), "spec": spec}

    ESI_SPECS.update(updates)
    return list(updates)


def _do_request(url, *args, **kwargs):
    """Make a GET request, return the status code and json response."""

    try:
        res = SESSION.get(url, *args, **kwargs)
        res.raise_for_status()
    except Exception as error:
        LOG.warning("request to %s failed: %r", url, error)
    else:
        LOG.info("requested: %s", url)
    finally:
        try:
            content = res.json()
        except Exception:
            content = res.text
        return res.status_code, content


# nest commands under a prefix
PREFIX = "!esi"

# first word(s) after !esi: processor function
# can be a list/tuple, a regex pattern, or a single string
COMMANDS = {
    "help": _help,
    re.compile(r"^/(?P<esi_path>.+)$"): _esi_request,
    re.compile(r"^#(?P<gh_issue>[0-9]+)$"): _issue_details,
    ("hey", "hi", "hello", "o7", "o/"): _hello_response,
    ("join", "invite"): _channel_request,
    "refresh": _refresh_spec,
    "status": _status,
    ("id", "ids", "ranges"): _id_gist,
    "waffle": _waffle,
    "faq": _faq,
    ("new", "bug"): _new_issue,
    "issues": _issues,
    "sso": _sso_issues,
    "ui": _ui,
    ("legacy", "v2ui"): _legacy_ui,
    ("diff", "diffs"): _diff,
    ("repo", "source"): _bot_repo,
}


@irc3.plugin
class Plugin(object):
    def __init__(self, bot):
        self.bot = bot

    @irc3.event(irc3.rfc.PRIVMSG)
    def process_message(self, data=None, mask=None, target=None, event=None):
        """Hook private messages to maybe do things."""

        LOG.warning("(%s) @%s: %s", target, mask.nick, data)

        if target in WELCOMED_IN and mask.nick != self.bot.nick:
            try:
                prefix, command, *args = data.split(" ")
            except ValueError:
                return

            if prefix == PREFIX:
                send = lambda x: self.bot.privmsg(target, x)
                speaker = "@{}".format(mask.nick)
                for triggers, func in COMMANDS.items():
                    if isinstance(triggers, (list, tuple)):
                        if command in triggers:
                            func(send, speaker, command, *args)
                            return
                    elif isinstance(triggers, re._pattern_type):
                        match = re.match(triggers, command)
                        if match:
                            func(match, send, speaker, command, *args)
                            return
                    elif command == triggers:
                        func(send, speaker, command, *args)
                        return


def main():
    """Make a config from the environment, be a bot forever."""

    config = {
        "nick": os.environ.get("IRC_NAME", "esibot"),
        "username": os.environ.get("IRC_REALNAME", "esibot"),
        "autojoins": WELCOMED_IN,
        "host": os.environ.get("IRC_NETWORK", "irc.freenode.net"),
        "port": int(os.environ.get("IRC_PORT", "6667")),
        "ssl": bool(os.environ.get("IRC_SSL")),
        "includes": [__name__],
    }

    env_passwd = os.environ.get("IRC_PASSWORD")
    if os.path.isfile(env_passwd):
        with open(env_passwd, "r") as openenvpasswd:
            config["password"] = openenvpasswd.read().strip()
    elif env_passwd:
        config["password"] = env_passwd

    _do_refresh()
    bot = irc3.IrcBot.from_config(config)
    bot.run(forever=True)


if __name__ == '__main__':
    main()
