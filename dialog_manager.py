from typing import Dict, List, Any


class DialogManager:
    """
    In‑memory manager for per‑user dialog histories.

    History format per user:
        [
            {"role": "user", "content": "..."},
            {"role": "assistant", "content": "..."},
            ...
        ]
    """

    def __init__(self, max_messages: int = 6) -> None:
        self._dialogs: Dict[int, List[Dict[str, Any]] = {}
        self._max_messages = max_messages

    def get_history(self, user_id: int) -> List[Dict[str, Any]]:
        """Return a copy of user's history (so external code can't mutate it by accident)."""
        return list(self._dialogs.get(user_id, []))

    def _set_history(self, user_id: int, history: List[Dict[str, Any]]) -> None:
        if len(history) > self._max_messages:
            history = history[-self._max_messages :]
        self._dialogs[user_id] = history

    def append_message(self, user_id: int, role: str, content: str) -> List[Dict[str, Any]]:
        """Append a message and automatically trim history; returns updated history."""
        history = self._dialogs.get(user_id, [])
        history.append({"role": role, "content": content})
        self._set_history(user_id, history)
        return self._dialogs[user_id]

    def clear_history(self, user_id: int) -> None:
        """Remove dialog history for a user (if it exists)."""
        self._dialogs.pop(user_id, None)

