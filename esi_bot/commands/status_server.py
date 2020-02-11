"""Commands for checking the status of various EVE servers."""

from datetime import datetime

from esi_bot import ESI
from esi_bot import ESI_CHINA
from esi_bot import REPLY
from esi_bot import command
from esi_bot import do_request


@command(trigger=("tq", "tranquility"))
def tranquility(*_):
    """Display current status of Tranquility, the main game server."""

    return server_status("tranquility")


@command
def serenity(*_):
    """Display current status of Serenity, the main server in China."""

    return server_status("serenity")


def server_status(datsource):
    """Generate a reply describing the status of an EVE server/datasource."""

    if datsource == "tranquility":
        base_url = ESI
    elif datsource == "serenity":
        base_url = ESI_CHINA
    else:
        return "Cannot request server status for `{}`".format(datsource)

    status_code, response = do_request("{}/v1/status/?datasource={}".format(
        base_url,
        datsource,
    ))
    server_name = datsource.capitalize()

    if status_code == 200:
        start_time = datetime.strptime(
            response["start_time"],
            "%Y-%m-%dT%H:%M:%SZ",
        )
        vip = response.get("vip")  # pylint: disable=no-member
        attachment = {
            "color": "warning" if vip else "good",
            "title": "{} status".format(server_name),
            "fields": [
                {
                    "title": "Players online",
                    "value": "{:,}".format(response["players"]),
                },
                {
                    "title": "Started at",
                    "value": response["start_time"],
                    "short": True,
                },
                {
                    "title": "Running for",
                    "value": _running_for(start_time),
                    "short": True,
                },
            ],
            "fallback": "{} status: {:,} online, started at {}{}".format(
                server_name,
                response["players"],
                response["start_time"],
                ", in VIP" * int(vip is True),
            ),
        }
        if vip:
            attachment["fields"].insert(0, {"title": "In VIP mode"})

    elif status_code == 503:
        attachment = {
            "color": "danger",
            "title": "{} status".format(server_name),
            "text": "Offline",
            "fallback": "{} status: Offline".format(server_name),
        }
    else:
        indeterminate = (
            "Cannot determine server status. "
            "It might be offline, or experiencing connectivity issues."
        )
        attachment = {
            "color": "danger",
            "title": "{} status".format(server_name),
            "text": indeterminate,
            "fallback": "{} status: {}".format(server_name, indeterminate),
        }

    return REPLY(content=None, attachments=[attachment])


def _running_for(start_time):
    running_for = int((datetime.utcnow() - start_time).total_seconds())
    if running_for < 60:
        return "less than a minute"

    running_for_list = []
    units = [
        (running_for // (60 * 60), "hour"),
        ((running_for // 60) % 60, "minute"),
    ]
    for number, unit in units:
        running_for_list.append("{} {}{}".format(
            number,
            unit,
            "s" * (number != 1)
        ))
    return ", ".join(running_for_list)
