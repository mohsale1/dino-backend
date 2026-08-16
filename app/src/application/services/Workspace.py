from src.core.Exceptions import WorkspaceMismatchError
from typing import Any, Dict, Optional

def assert_own_workspace(workspace_id: int, current_user: Dict[str, Any]) -> None:
    if workspace_id != current_user.get("workspace_id"):
        raise WorkspaceMismatchError()