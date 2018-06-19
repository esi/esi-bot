"""ESI slack bot for tweetfleet."""


import os
import time

from slackclient import SlackClient

from esi_bot import LOG
from esi_bot import request
from esi_bot import commands  # noqa F401  # pylint: disable=unused-import
from esi_bot.processor import Processor


def main():
    """Connect to the slack RTM API and pull messages forever."""

    LOG.info("ESI bot launched")
    request.do_refresh()
    LOG.info("Loaded ESI specs")
    slack = SlackClient(os.environ["SLACK_TOKEN"])
    processor = Processor(slack)
    while True:
        if slack.rtm_connect():
            if not processor.on_server_connect():
                raise SystemExit("Could not join channels")

            LOG.info("Connected to Slack")
            while slack.server.connected is True:
                for msg in slack.rtm_read():
                    processor.process_event(msg)
                time.sleep(1)  # rtm_read should block, but it doesn't :/

        else:
            raise SystemExit("Connection to slack failed :(")


if __name__ == '__main__':
    main()
