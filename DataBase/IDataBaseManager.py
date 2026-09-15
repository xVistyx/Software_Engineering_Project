"""Storage contract used by System. Durations are seconds; owners are server-resolved."""
from abc import ABC, abstractmethod


class IDataBaseManager(ABC):
    @abstractmethod
    def get_users(self):
        """Return provisioned user IDs for startup recovery."""

    @abstractmethod
    def authenticate(self, token):
        """Return the user/role principal, or None for an unknown key."""

    @abstractmethod
    def get_preferences(self, user_id, defaults):
        pass

    @abstractmethod
    def save_preferences(self, user_id, data):
        pass

    @abstractmethod
    def save_session(self, user_id, data):
        """Commit the supplied SessionSummaryForDB dataclass (or its serialized fields).

        Return normally only after commit (including an already saved retry).
        Raise on failure. Do not read or delete the caller's temporary files.
        """

    @abstractmethod
    def get_history(self, user_id):
        """Return saved session records for this owner."""

    @abstractmethod
    def get_session_details(self, user_id, session_id):
        """Return session, summary, optional analysis and storage_status; raise if absent."""

    @abstractmethod
    def get_legacy_sources(self, user_id):
        pass

    @abstractmethod
    def get_ai_session(self, user_id, session_id):
        """Return the existing session_info/website_metadata analysis envelope."""

    @abstractmethod
    def save_session_analysis(self, user_id, session_id, analysis):
        pass
