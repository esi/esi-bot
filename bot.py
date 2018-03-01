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


if not WEBHOOK:
    raise SystemExit("I need a webhook url to post multiline responses")


def _build_session():
    ses = requests.Session()
    ses.headers["User-Agent"] = "esi-bot/0.0.1 -- this is the slack ESI bot"
    adapt = HTTPAdapter(max_retries=3, pool_connections=10, pool_maxsize=100)
    ses.mount("http://", adapt)
    ses.mount("https://", adapt)
    return ses


SESSION = _build_session()


def _channel_request(send, speaker, command, *args):
    send((
        "I can't do that right now {}. "
        "ask @ccp_snowedin to add me in another channel"
    ).format(speaker))


def _hello_response(send, speaker, command, *args):
    if "whatup" in args:
        send("not much. whatup {}".format(speaker))
    elif command in ("o7", "o/"):
        send("o7 {}".format(speaker))
    else:
        send("hey {} howsit goin?".format(speaker))


def _issue_details(match, send, speaker, command, *args):
    url = "https://api.github.com/repos/ccpgames/esi-issues/issues/{}".format(
        match.groupdict()["gh_issue"]
    )
    status, details = _do_request(url)
    if status >= 400:
        send("failed to lookup details for issue {}".format(command))
    else:
        send("{} ({})".format(details["html_url"], details["state"]))


def _esi_request(match, send, speaker, command, *args):
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


def _send_multiline(text):
    """Send a multiline message via slack's incoming webhooks."""

    lines = text.splitlines()
    content = lines[:25]
    if len(lines) > 25:
        content.append("<content snipped>")

    try:
        res = SESSION.post(WEBHOOK, json={
            "text": "\n".join(content),
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
    re.compile(r"^/(?P<esi_path>.*)$"): _esi_request,
    re.compile(r"^#(?P<gh_issue>[0-9]*)$"): _issue_details,
    ("hey", "hi", "hello", "o7", "o/"): _hello_response,
    ("join", "invite"): _channel_request,
    "refresh": _refresh_spec,
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
