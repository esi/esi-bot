"""Help command."""

import typing

from esi_bot import EPHEMERAL
from esi_bot import command
from esi_bot import COMMANDS
from esi_bot import EXTENDED_HELP


@command(trigger="help")
def get_help(msg):
    """Return help on an available command, or list all commands."""

    if msg.args and msg.args[0] in EXTENDED_HELP:
        return "ESI-bot help for {}:\n>>>{}".format(
            msg.args[0],
            EXTENDED_HELP[msg.args[0]],
        )

    commands = []  # list of command help strings
    for targets in COMMANDS:
        if isinstance(targets, (list, tuple)):
            commands.append(", ".join(targets))
        elif isinstance(targets, typing.Pattern):
            commands.append("{}: {}".format(
                COMMANDS[targets].__name__,
                targets.pattern,
            ))
        else:
            commands.append(targets)

    cmd_list = "The following commands are enabled: {}".format(
        " ".join("`{}`".format(x) for x in commands)
    )

    if msg.command == "help":
        return cmd_list
    return EPHEMERAL(
        content="{} {}".format(
            "I'm sorry, that's an unknown command.",
            cmd_list,
        ),
        attachments=None,
    )
