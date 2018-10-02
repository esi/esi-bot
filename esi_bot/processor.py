"""Message processing for ESI-bot."""


import os
import re
import time
import random
from datetime import datetime

from esi_bot import LOG
from esi_bot import REPLY
from esi_bot import EPHEMERAL
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
    re.compile(r"(^|.*( |!))crest( |$|!|\?|\.|,)", re.IGNORECASE): "rip",
    re.compile(r"(^|.*( |!))xml(api)?( |$|!|\?|\.|,)", re.IGNORECASE): "wreck",
}

UNMATCHED = object()


class Processor(object):
    """Execute ESI-bot commands based on incoming messages."""

    def __init__(self, slack):
        """Create a new processor instance."""

        self._slack = slack
        self._users = Users(slack)
        self._channels = Channels(slack)
        self._prefix = os.environ.get("ESI_BOT_PREFIX", "!esi")
        self._greenlet = None
        self._replied_to = {}  # {uuid: timestamp}
        self._edit_window = int(os.environ.get("ESI_BOT_EDIT_WINDOW", 300))

    def garbage_collect(self):
        """Prune the self._replied_to dictionary."""

        prune_time = time.time() - self._edit_window
        prune_keys = []
        for key, timestamp in self._replied_to.items():
            if timestamp < prune_time:
                prune_keys.append(key)

        for key in prune_keys:
            self._replied_to.pop(key)

    def on_server_connect(self):
        """Join channels, start the daily announcements."""

        joined = self._channels.enter_channels()
        if joined:
            self._send_msg(random.choice(STARTUP_MSGS))
        return joined

    def _send_msg(self, msg, attachments=None, unfurling=False, channel=None):
        """Send a message to the channel, or the primary channel."""

        self._slack.api_call(
            "chat.postMessage",
            channel=channel or self._channels.primary,
            text=msg,
            attachments=attachments,
            username="ESI (bot)",
            icon_emoji=":techco:",
            unfurl_links=unfurling,
            unfurl_media=unfurling,
        )

    def _send_ephemeral(self, msg, user, channel, attachments=None):
        """Send an ephemeral message."""

        self._slack.api_call(
            "chat.postEphemeral",
            channel=channel,
            text=msg,
            attachments=attachments,
            user=user,
            as_user=True,
        )

    def _send_snippet(self, reply, channel=None):
        """Send a snippet to the channel, or the primary channel."""

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

    def _process_snippet_reply(self, reply, channel):
        """Process code snippet replies."""

        if len(reply.content) > 2900 or reply.content.count("\n") > 9:
            self._send_snippet(reply, channel=channel)
        else:
            self._send_msg(
                "{}\n{}\n```{}```".format(
                    reply.title,
                    reply.comment,
                    reply.content,
                ),
                channel=channel,
            )

    def _process_message_reply(self, reply, channel):
        """Process text message replies."""

        self._send_msg(
            reply.content,
            attachments=reply.attachments,
            channel=channel,
        )

    def _process_ephemeral_reply(self, reply, user, channel):
        """Process ephemeral replies."""

        self._send_ephemeral(reply.content, user, channel)

    def _process_str_reply(self, reply, channel):
        """Process replies returning strings."""

        self._send_msg(reply, unfurling=True, channel=channel)

    def process_event(self, event):
        """Receive and process any/all Slack RTM API events."""

        LOG.debug("RTM event received: %r", event)

        if event["type"] == "message":
            if "user" in event and "client_msg_id" in event:
                self._process_once(
                    event["client_msg_id"],  # not present in self msgs
                    event["ts"],
                    event["channel"],
                    event["user"],
                    event["text"],
                )
            elif "message" in event and \
                    "edited" in event["message"] and \
                    "client_msg_id" in event["message"] and \
                    event.get("subtype") == "message_changed" and \
                    float(event["message"]["edited"]["ts"]) - \
                    float(event["message"]["ts"]) < self._edit_window:
                self._process_once(
                    event["message"]["client_msg_id"],
                    event["message"]["ts"],
                    event["channel"],
                    event["message"]["edited"]["user"],
                    event["message"]["text"],
                )

    def _process_once(self, msg_id, timestamp, *args):
        """Process an event once.

        Args:
            msg_id: uuid for this event
            *args: arguments for self._process_event
        """

        if msg_id in self._replied_to:
            return

        if self._process_event(timestamp, *args):  # pylint: disable=E1120
            self._replied_to[msg_id] = float(timestamp)

    def _process_event(self, timestamp, channel, user, text):
        """Process valid events, look for our prefix or add a reaction.

        Args:
            timestamp: string, unix timestamp
            channel: slack channel uuid
            user: slack speaker uuid
            text: string, raw event text

        Returns:
            boolean of if this event was replied to (and not the help cmd)
        """

        channel_name = self._channels.get_name(channel)
        if not channel_name:
            return False

        user_name = self._users.get_name(user)
        LOG.info(
            "[%s] @%s: %s",
            datetime.utcfromtimestamp(int(float(timestamp))),
            user_name,
            text,
        )

        # PEOPLE SHOULD BE FREE TO TYPE IN ALL CAPS
        text = text.lower()

        try:
            prefix, command, *args = text.split(" ")
        except ValueError:
            # one word message. if it's our prefix, show help
            prefix, command, *args = text, "help"

        if prefix == self._prefix:
            command, reply = _process_msg(MESSAGE(user, command, args))

            if reply:
                if isinstance(reply, SNIPPET):
                    self._process_snippet_reply(reply, channel)
                elif isinstance(reply, REPLY):
                    self._process_message_reply(reply, channel)
                elif isinstance(reply, EPHEMERAL):
                    self._process_ephemeral_reply(reply, user, channel)
                else:
                    self._process_str_reply(reply, channel)
                # since unknown commands show up as help this lets people
                # edit to a known command and have it processed once still
                return command != UNMATCHED
        else:
            reacted = False
            for trigger, reaction in REACTION_TRIGGERS.items():
                if re.match(trigger, text):
                    reacted = True
                    self._slack.api_call(
                        "reactions.add",
                        name=reaction,
                        channel=channel,
                        timestamp=timestamp,
                    )
            return reacted

        return False


def _process_msg(msg):
    """Process events matching our prefix and in an allowed channel."""

    for triggers, func in COMMANDS.items():
        if isinstance(triggers, (list, tuple)):
            if msg.command in triggers:
                return msg.command, func(msg)
        elif isinstance(triggers, re._pattern_type):
            match = re.match(triggers, msg.command)
            if match:
                return msg.command, func(match, msg)
        elif msg.command == triggers:
            return msg.command, func(msg)

    # unknown command
    return UNMATCHED, COMMANDS["help"](msg)
