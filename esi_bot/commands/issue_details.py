"""Command for looking up an ESI issue."""

import re

from esi_bot import command
from esi_bot import do_request


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
