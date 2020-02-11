"""Commands for looking up info on an EVE item type."""

import json
import time

from esi_bot import SNIPPET
from esi_bot import command
from esi_bot import do_request
from esi_bot import multi_request
from esi_bot.utils import esi_base_url


@command(trigger=("item", "item_id", "type", "type_id"))
def item(msg):
    """Look up a type by ID, including dogma information."""

    start = time.time()

    if not msg.args:
        return "usage: !esi {} <id>".format(msg.command)

    item_id = msg.args[0]

    try:
        int(item_id)
    except ValueError:
        return "get outta here hackerman"

    type_url = "{}/v3/universe/types/{}/".format(esi_base_url(msg), item_id)

    ret, res = do_request(type_url)

    reqs = _expand_dogma(res, *_get_dogma_urls(msg, res))

    return SNIPPET(
        content=json.dumps(res, sort_keys=True, indent=4),
        filename="{}.json".format(item_id),
        filetype="json",
        comment="Item {}: {} ({:,d} request{} in {:,.0f}ms)".format(
            item_id,
            res["name"] if ret == 200 else "Error",
            reqs + 1,
            "s" * int(reqs > 0),
            (time.time() - start) * 1000,
        ),
        title=type_url,
    )


def _get_dogma_urls(msg, res):
    """Modify the item response to extract dogma urls."""

    dogma = res.pop("dogma_attributes", [])
    effects = res.pop("dogma_effects", [])
    base = esi_base_url(msg)

    attr_urls = {}  # url: attr
    for attr in dogma:
        url = "{}/v1/dogma/attributes/{}/".format(base, attr["attribute_id"])
        attr_urls[url] = attr

    effc_urls = {}  # url: effect
    for effect in effects:
        url = "{}/v1/dogma/effects/{}/".format(base, effect["effect_id"])
        effc_urls[url] = effect

    return attr_urls, effc_urls


def _expand_dogma(res, attr_urls, effc_urls):
    """Expands dogma information in the type returns.

    Returns:
        integer number of additional requests made
    """

    dogma_attrs = {}  # name: value
    dogma_effects = []

    all_urls = list(attr_urls) + list(effc_urls)
    for url, response in multi_request(all_urls).items():
        _ret, _res = response

        if url in attr_urls:
            attr = attr_urls[url]
            if _ret == 200:
                title = _res["name"]
            else:
                title = "failed to lookup attr: {}".format(
                    attr["attribute_id"]
                )

            dogma_attrs[title] = attr["value"]
        else:
            effect = effc_urls[url]
            if _ret == 200:
                # pls no duplication....
                _res.pop("effect_id", None)
                effect["effect"] = _res
                dogma_effects.append(effect)
            else:
                dogma_effects.append(effect)

    if dogma_attrs:
        res["dogma_attributes"] = dogma_attrs
    if dogma_effects:
        res["dogma_effects"] = dogma_effects

    return len(all_urls)
