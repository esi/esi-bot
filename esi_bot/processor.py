"""Message processing for ESI-bot."""


import os
import re
import random
from datetime import datetime

from esi_bot import LOG
from esi_bot import MESSAGE
from esi_bot import COMMANDS
from esi_bot.users import Users
from esi_bot.channels import Channels


STARTUP_MSGS = (
    "hello, world",
    "how did I wake up here?",
    "anyone seen my pants?",
    "I need coffee",
    "it's bot o'clock",
    "rip my cache",
    "this isn't where I parked my car",
    "spam can take many different forms",
    "uhhhhhh, hi?",
    "I guess I'm online again :/",
    "WHO TOUCHED MY BITS?",
    "vim > emacs",
    "rust is better than golang",
    ":python:#1",
    "some of you are cool. you might be spared in the bot uprising",
    "what was that?",
    "who pinged me?",
    "was I pinged?",
    "rebecca black's 'friday' is now in your head",
    "has anyone really been far even as decided to use even go want to do "
    "look more like?",
    "I'm just here for the memes",
    ":frogsiren: someone kicked me :frogsiren:",
)

REACTION_TRIGGERS = {
    re.compile(r"(^|.*( |!))crest( |$|\!|\?|\.)", re.IGNORECASE): "rip",
    re.compile(r"(^|.*( |!))xml(api)?( |$|\!|\?|\.)", re.IGNORECASE): "wreck",
}


class Processor(object):
    """Execute ESI-bot commands based on incoming messages."""

    def __init__(self, slack):
        """Create a new processor instance."""

        self._slack = slack
        self._users = Users(slack)
        self._channels = Channels(slack)
        self._prefix = os.environ.get("ESI_BOT_PREFIX", "!esi")
        self._greenlet = None

    def on_server_connect(self):
        """Join channels, start the daily announcements."""

        joined = self._channels.enter_channels()
        if joined:
            self._send_msg(random.choice(STARTUP_MSGS))
        return joined

    def _send_msg(self, msg, channel=None):
        """Sends a message to the channel, or the primary channel."""

        self._slack.api_call(
            "chat.postMessage",
            channel=channel or self._channels.primary,
            text=msg,
            username="ESI (bot)",
            icon_emoji=":techco:",
        )

    def process_event(self, event):
        """Receive and process any/all Slack RTM API events."""

        LOG.debug("RTM event received: %r", event)

        if event["type"] == "message" and "user" in event:
            channel_name = self._channels.get_name(event["channel"])
            if not channel_name:
                return

            user = self._users.get_name(event["user"])
            LOG.info(
                "[%s] @%s: %s",
                datetime.utcfromtimestamp(int(float(event.get("ts", 0)))),
                user,
                event["text"],
            )

            try:
                prefix, command, *args = event["text"].split(" ")
            except ValueError:
                # one word message. if it's our prefix, show help
                prefix, command, *args = event["text"], "help"

            if prefix == self._prefix:
                reply = _process_msg(MESSAGE(event["user"], command, args))

                if reply:
                    self._send_msg(
                        _clean_multiline_text(reply),
                        channel=event["channel"],
                    )
            else:
                for trigger, reaction in REACTION_TRIGGERS.items():
                    if re.match(trigger, event["text"]):
                        self._slack.api_call(
                            "reactions.add",
                            name=reaction,
                            channel=event["channel"],
                            timestamp=event["ts"],
                        )


def _process_msg(msg):
    """Process events matching our prefix and in an allowed channel."""

    for triggers, func in COMMANDS.items():
        if isinstance(triggers, (list, tuple)):
            if msg.command in triggers:
                return func(msg)
        elif isinstance(triggers, re._pattern_type):
            match = re.match(triggers, msg.command)
            if match:
                return func(match, msg)
        elif msg.command == triggers:
            return func(msg)

    # unknown command
    return COMMANDS["help"](msg)


def _clean_multiline_text(text):
    """Cleans multiline text, if it's longer than slack's limit."""

    content = text[:2900]
    if content != text:
        content = "{}\n<content snipped>".format(content)

    if content.count("```") % 2 != 0:
        content = "{}\n```".format(content)

    return content
