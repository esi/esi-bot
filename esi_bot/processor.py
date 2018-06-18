"""Message processing for ESI-bot."""


import os
import re
import random
from datetime import datetime

from esi_bot import LOG
from esi_bot import REPLY
from esi_bot import SNIPPET
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

    def _send_msg(self, msg, attachments=None, channel=None):
        """Sends a message to the channel, or the primary channel."""

        self._slack.api_call(
            "chat.postMessage",
            channel=channel or self._channels.primary,
            text=msg,
            attachments=attachments,
            username="ESI (bot)",
            icon_emoji=":techco:",
        )

    def _send_snippet(self, reply, channel=None):
        """Sends a snippet to the channel, or the primary channel."""

        # There is a 1 megabyte file size limit for files uploaded as snippets.
        megb = 1024 ** 2
        if len(reply.content) > megb:
            snip = "<snipped>"
            content = "{}{}".format(reply.content[:megb - len(snip)], snip)
        else:
            content = reply.content

        self._slack.api_call(
            "files.upload",
            content=content,
            filename=reply.filename,
            filetype=reply.filetype,
            initial_comment=reply.comment,
            title=reply.title,
            editable=False,  # doesn't actually work
            username="ESI (bot)",  # same, but maybe someday
            channels=channel or self._channels.primary,
        )

    def _process_snippet_reply(self, reply, event):
        """Process code snippet replies."""

        if len(reply.content) > 2900:
            self._send_snippet(reply, channel=event["channel"])
        else:
            self._send_msg(
                "{}\n{}\n```{}```".format(
                    reply.title,
                    reply.comment,
                    reply.content,
                ),
                channel=event["channel"],
            )

    def _process_message_reply(self, reply, event):
        """Process text message replies."""

        self._send_msg(
            reply.content,
            attachments=reply.attachments,
            channel=event["channel"],
        )

    def _process_str_reply(self, reply, event):
        """Process replies returning strings."""

        self._send_msg(reply, channel=event["channel"])

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

            # PEOPLE SHOULD BE FREE TO TYPE IN ALL CAPS
            event["text"] = event["text"].lower()

            try:
                prefix, command, *args = event["text"].split(" ")
            except ValueError:
                # one word message. if it's our prefix, show help
                prefix, command, *args = event["text"], "help"

            if prefix == self._prefix:
                reply = _process_msg(MESSAGE(event["user"], command, args))

                if reply:
                    if isinstance(reply, SNIPPET):
                        self._process_snippet_reply(reply, event)
                    elif isinstance(reply, REPLY):
                        self._process_message_reply(reply, event)
                    else:
                        self._process_str_reply(reply, event)
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
