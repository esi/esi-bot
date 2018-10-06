"""Commands for displaying instructions on opening new issues."""

from esi_bot import ESI_DOCS
from esi_bot import ESI_ISSUES
from esi_bot import REPLY
from esi_bot import command


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
