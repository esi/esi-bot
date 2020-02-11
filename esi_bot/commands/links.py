"""Commands which return links to various useful resources."""

from esi_bot import ESI_DOCS
from esi_bot import ESI_ISSUES
from esi_bot import command
from esi_bot.utils import esi_base_url


@command(trigger=("id", "ids", "ranges"))
def ids(*_):
    """Return a link to the ID ranges gist and asset location IDs doc."""

    return (
        "ID ranges reference: "
        "https://gist.github.com/a-tal/5ff5199fdbeb745b77cb633b7f4400bb\n"
        "Asset `location_id` reference: "
        "{}docs/asset_location_id"
    ).format(ESI_DOCS)


@command
def faq(*_):
    """Return a link to the ESI issues FAQ."""

    return "{}docs/FAQ".format(ESI_DOCS)


@command
def issues(*_):
    """Return a link to ESI issues."""

    return ESI_ISSUES


@command
def sso(*_):
    """Return a link to SSO issues."""

    return "https://github.com/ccpgames/sso-issues/issues/"


@command(trigger=("ui", "webui"))
def webui(msg):
    """Return a link to the ui (v3)."""

    return "{}/ui/".format(esi_base_url(msg))


@command(trigger=("diff", "diffs"))
def diff(msg):
    """Return a link to the ESI spec diffs page."""

    return "{}/diff/latest/dev/".format(esi_base_url(msg))


@command(trigger=("source", "repo"))
def source(*_):
    """Return a link to the repo for this bot."""

    return (
        "I'm an open source bot. If you want to contribute or are curious "
        "how I work, my source is available for you to browse here: "
        "https://github.com/esi/esi-bot/"
    )
