"""Commands for checking the status of ESI."""

import time

from esi_bot import ESI
from esi_bot import ESI_CHINA
from esi_bot import REPLY
from esi_bot import command
from esi_bot import do_request
from esi_bot.utils import esi_base_url

STATUS = {
    ESI: {"timestamp": 0, "status": []},
    ESI_CHINA: {"timestamp": 0, "status": []},
}


def _status_str(statuses):
    """Generate a string to describe the route statuses."""

    if statuses:
        statuses.sort(key=lambda x: (x["route"], x["method"]))
        method_pad = max([len(route["method"]) for route in statuses])
        lines = ["{} {}".format(
            route["method"].upper().ljust(method_pad),
            route["route"],
        ) for route in statuses]
        if len(statuses) > 99:
            lines = lines[0:80]
            lines.append("And {} more...".format(len(statuses) - 80))
        return "```{}```".format("\n".join(lines))
    return ""


@command
def status(msg):
    """Return the current ESI health/status."""

    base_url = esi_base_url(msg)

    now = time.time()
    if now - STATUS[base_url]["timestamp"] > 60:
        code, esi_status = do_request("{}/status.json".format(base_url))
        if code == 200:
            STATUS[base_url]["status"] = esi_status
        else:
            return ":fire: (failed to fetch status.json)"

    attachments = []
    categories = [
        ("red", ":fire:", "danger"),
        ("yellow", ":fire_engine:", "warning"),
    ]
    status_json = STATUS[base_url]["status"]

    for status_color, emoji, color_value in categories:
        routes = [route for route in status_json if
                  route["status"] == status_color]
        if routes:
            attachments.append({
                "color": color_value,
                "fallback": "{}: {} out of {}, {:.2%}".format(
                    status_color.capitalize(),
                    len(routes),
                    len(status_json),
                    len(routes) / len(status_json),
                ),
                "text": "{emoji} {count} {emoji} {details}".format(
                    emoji=emoji * max(min(
                        int(round(len(routes) / len(status_json) * 10)),
                        5), 1),
                    count="{} {} (out of {}, {:.2%})".format(
                        len(routes),
                        status_color,
                        len(status_json),
                        len(routes) / len(status_json),
                    ),
                    details=_status_str(routes),
                )
            })

    if not attachments:
        attachments.append({
            "color": "good",
            "text": ":ok_hand:",
        })

    return REPLY(content=None, attachments=attachments)
