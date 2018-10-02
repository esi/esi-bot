"""User ID -> name tracking."""


import time

from esi_bot.utils import paginated_id_to_names


class Users:
    """Keep a cache of user IDs to names, perform refreshes."""

    def __init__(self, slack):
        """Create a new Users object and sync names."""

        self._names = {}  # {id: name}
        self._last_sync = 0
        self._slack = slack
        self.update_names()

    def update_names(self):
        """Update our names cache once per minute at max."""

        if time.time() - self._last_sync < 60:
            return

        self._last_sync = time.time()
        names = paginated_id_to_names(self._slack, "users.list", "members")
        if names:
            self._names = names

    def get_name(self, user_id):
        """Return the name for the user ID.

        NB: this can return None if we fail to sync user id/names
        """

        name = self._names.get(user_id)
        if name is None:
            self.update_names()
            name = self._names.get(user_id)
        return name
