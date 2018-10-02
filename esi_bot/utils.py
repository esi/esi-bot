"""Common ESI-bot helper functions."""


from esi_bot import ESI
from esi_bot import ESI_CHINA


def paginated_id_to_names(slack, method, key, **kwargs):
    """Call the paginated method via slack, return a dict of id: name."""

    cursor = True
    mapping = {}
    while cursor:
        if cursor is True:
            api_return = slack.api_call(method, **kwargs)
        else:
            api_return = slack.api_call(method, cursor=cursor, **kwargs)

        if api_return["ok"]:
            mapping.update({x["id"]: x["name"] for x in api_return[key]})
            cursor = api_return.get("response_metadata", {}).get("next_cursor")
        else:
            break

    return mapping


def esi_base_url(message):
    """Return the base URL for ESI given the args in message."""

    for arg in ("china", "cn", "serenity"):
        if arg in message.args or \
                "-{}".format(arg) in message.args or \
                "--{}".format(arg) in message.args:
            return ESI_CHINA
    return ESI
