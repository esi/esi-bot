"""Make GET requests to ESI."""


import re
import json
import time
import html
import http

from esi_bot import ESI
from esi_bot import ESI_CHINA
from esi_bot import SNIPPET
from esi_bot import command
from esi_bot import do_request
from esi_bot import multi_request
from esi_bot.utils import esi_base_url


def _initial_specs():
    """Return an initial empty specs dictionary."""

    return {
        x: {"timestamp": 0, "spec": {}} for x in ("latest", "legacy", "dev")
    }


ESI_SPECS = {
    ESI: _initial_specs(),
    ESI_CHINA: _initial_specs(),
}


@command(trigger=re.compile(
    r"^<?(?P<esi>https://esi\.(evetech\.net|evepc\.163\.com))?"
    r"/(?P<esi_path>.+?)>?$"
))
def request(match, msg):
    """Make an ESI GET request, if the path is known.

    Options:
        --headers    nest the response and add the headers
    """

    match_group = match.groupdict()

    if "evepc.163.com" in (match_group["esi"] or ""):
        base_url = ESI_CHINA
    else:
        base_url = esi_base_url(msg)

    version, *req_sections = match_group["esi_path"].split("/")
    if version not in ESI_SPECS[base_url]:
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
    if _valid_path(base_url, path, version):
        url = "{}/{}{}{}{}".format(
            base_url,
            version,
            path,
            "?" * int(params != ""),
            params,
        )
        start = time.time()
        res = do_request(url, return_response=True)

        try:
            content = res.json()
        except ValueError:
            content = res.text

        try:
            status = http.HTTPStatus(res.status_code)  # pylint: disable=E1120
        except ValueError:
            status = str(res.status_code)
        else:
            status = "{} {}".format(status.value, status.name)  # pylint: disable=E1101

        if "--headers" in msg.args:
            res = {"response": content, "headers": dict(res.headers)}
        else:
            res = content

        return SNIPPET(
            content=json.dumps(res, sort_keys=True, indent=4),
            filename="response.json",
            filetype="json",
            comment="{} ({:,.0f}ms)".format(
                status,
                (time.time() - start) * 1000,
            ),
            title=url,
        )

    return "failed to find GET {} in the {} ESI{} spec".format(
        path,
        version,
        " China" * int(base_url == ESI_CHINA),
    )


@command(trigger="refresh")
def refresh(msg):
    """Refresh internal specs."""

    base_url = esi_base_url(msg)
    refreshed = do_refresh(base_url)
    if refreshed:
        return "I refreshed my internal copy of the {}{}{} spec{}{}".format(
            ", ".join(refreshed[:-1]),
            " and " * int(len(refreshed) > 1),
            refreshed[-1],
            "s" * int(len(refreshed) != 1),
            " for ESI China" * int(base_url == ESI_CHINA),
        )
    return "my internal specs are up to date (try again later)"


def do_refresh(base_url):
    """DRY helper to refresh all stale ESI specs.

    Returns:
        list of updated ESI spec versions
    """

    status, versions = do_request("{}/versions/".format(base_url))
    if status == 200:
        for version in versions:
            if version not in ESI_SPECS[base_url]:
                ESI_SPECS[base_url][version] = {"timestamp": 0, "spec": {}}

    spec_urls = {}  # url: version
    for version, details in ESI_SPECS[base_url].items():
        if not details["spec"] or details["timestamp"] < time.time() + 300:
            url = "{}/{}/swagger.json".format(base_url, version)
            spec_urls[url] = version

    updates = {}
    for url, result in multi_request(spec_urls.keys()).items():
        status, spec = result
        if status == 200:
            updates[spec_urls[url]] = {"timestamp": time.time(), "spec": spec}

    ESI_SPECS[base_url].update(updates)
    return list(updates)


def _valid_path(base_url, path, version):
    """Check if the path is known."""

    try:
        spec = ESI_SPECS[base_url][version]["spec"]
    except KeyError:
        return False

    for spec_path, operations in spec["paths"].items():
        # we could pre-validate arguments.... *effort* though
        if re.match(re.sub(r"{.*}", "[^/]+", spec_path), path):
            # we only make get requests
            return "get" in operations

    return False
