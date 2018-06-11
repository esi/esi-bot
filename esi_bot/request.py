"""Make GET requests to ESI."""


import re
import json
import time
import html

from esi_bot import ESI
from esi_bot import command
from esi_bot import do_request


ESI_SPECS = {
    x: {"timestamp": 0, "spec": {}} for x in ("latest", "legacy", "dev")
}


@command(trigger=re.compile(
    r"^<?(https://esi\.(evetech\.net|tech\.ccp\.is))?/(?P<esi_path>.+?)>?$"
))
def request(match, *_):
    """Make an ESI GET request, if the path is known."""

    version, *req_sections = match.groupdict()["esi_path"].split("/")
    if version not in ESI_SPECS:
        req_sections.insert(0, version)
        version = "latest"

    params = ""
    if "?" in req_sections[-1]:
        if req_sections[-1].startswith("?"):
            params = req_sections.pop()
            params = params[1:]
        else:
            # qsparams passed w/out trailing slash
            final_path, params = req_sections.pop().split("?")
            req_sections.append(final_path)

    params = html.unescape(params)
    path = "/{}/".format("/".join(x for x in req_sections if x))
    if _valid_path(path, version):
        url = "{}/{}{}{}{}".format(
            ESI,
            version,
            path,
            "?" * int(params != ""),
            params,
        )
        status, res = do_request(url)
        return "{}\n{}\n```{}```".format(
            url,
            status,
            json.dumps(res, sort_keys=True, indent=4)
        )
    return "failed to find GET {} in the {} ESI spec".format(path, version)


@command(trigger="refresh")
def refresh(*_):
    """Refresh internal specs."""

    refreshed = do_refresh()
    if refreshed:
        return "I refreshed my internal copy of the {}{}{} spec{}".format(
            ", ".join(refreshed[:-1]),
            " and " * int(len(refreshed) > 1),
            refreshed[-1],
            "s" * int(len(refreshed) != 1),
        )
    return "my internal specs are up to date (try again later)"


def do_refresh():
    """DRY helper to refresh all stale ESI specs.

    Returns:
        list of updated ESI spec versions
    """

    status, versions = do_request("{}/versions/".format(ESI))
    if status == 200:
        for version in versions:
            if version not in ESI_SPECS:
                ESI_SPECS[version] = {"timestamp": 0, "spec": {}}

    updates = {}
    for version, details in ESI_SPECS.items():
        if not details["spec"] or details["timestamp"] < time.time() + 300:
            status, spec = do_request("{}/{}/swagger.json".format(
                ESI,
                version,
            ))
            if status == 200:
                updates[version] = {"timestamp": time.time(), "spec": spec}

    ESI_SPECS.update(updates)
    return list(updates)


def _valid_path(path, version):
    """Check if the path is known."""

    spec = ESI_SPECS[version]["spec"]
    for spec_path, operations in spec["paths"].items():
        # we could pre-validate arguments.... *effort* though
        if re.match(re.sub(r"{.*}", "[^/]+", spec_path), path):
            # we only make get requests
            return "get" in operations
    return False
