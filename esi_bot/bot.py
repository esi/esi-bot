"""ESI slack bot for tweetfleet."""

import os
import time

from slackclient import SlackClient

from esi_bot import ESI
from esi_bot import ESI_CHINA
from esi_bot import LOG
from esi_bot import request
from esi_bot.processor import Processor
from esi_bot.commands import (  # noqa: F401;  # pylint: disable=unused-import
    get_help, issue_details, issue_new, status_esi, status_server, type_info)


def main():
    """Connect to the slack RTM API and pull messages forever."""

    LOG.info("ESI bot launched")
    request.do_refresh(ESI)
    request.do_refresh(ESI_CHINA)
    LOG.info("Loaded ESI specs")
    slack = SlackClient(os.environ["SLACK_TOKEN"])
    processor = Processor(slack)
    while True:
        if slack.rtm_connect(auto_reconnect=True):
            if not processor.on_server_connect():
                raise SystemExit("Could not join channels")

            LOG.info("Connected to Slack")
            cycle = 0
            while slack.server.connected is True:
                cycle += 1

                for msg in slack.rtm_read():
                    processor.process_event(msg)

                if cycle > 10:
                    processor.garbage_collect()
                    cycle = 0

                time.sleep(1)  # rtm_read should block, but it doesn't :/

        else:
            raise SystemExit("Connection to slack failed :(")


if __name__ == '__main__':
    main()
