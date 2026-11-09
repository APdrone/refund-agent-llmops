"""
Dynamic Data Provider for Refund Agent
This module bridges SQLite persistence and provides relative, dynamic dates
to ensure the 30-day refund policy tests never become stale.
"""
from datetime import date, timedelta
from typing import Dict, Any
from agent.db import get_user_purchase_dict, seed_db, init_db

# Ensure the database is initialized
init_db()


class DynamicUsersData(dict):
    """
    A dictionary-like view that retrieves user purchase records directly from SQLite.
    If an entry is accessed, it pulls the most up-to-date record from the database.
    """
    def __getitem__(self, user_id: str) -> Dict[str, Any]:
        data = get_user_purchase_dict(user_id)
        if data is None:
            raise KeyError(user_id)
        return data

    def get(self, user_id: str, default=None):
        data = get_user_purchase_dict(user_id)
        return data if data is not None else default

    def __contains__(self, user_id: object) -> bool:
        if not isinstance(user_id, str):
            return False
        return get_user_purchase_dict(user_id) is not None


# Dynamic dictionary proxy so legacy code continues to work without modification
users_data = DynamicUsersData()
