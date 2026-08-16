from typing import Optional
from pydantic import BaseModel, Field, field_validator


class UpdateWorkspaceRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=500)

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if v else v


class WorkspaceStatusResponse(BaseModel):
    workspace_id: int
    request_exists: bool
    approved: bool
    status: Optional[str] = None
    reviewed_at: Optional[str] = None
    rejection_reason: Optional[str] = None
