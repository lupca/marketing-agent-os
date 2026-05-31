# core/schemas.py
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

class PlatformVariantSchema(BaseModel):
    id: UUID
    workspace_id: UUID
    master_content_id: UUID
    platform: str
    adapted_copy: Optional[str] = None
    publish_status: str
    metric_views: int = 0
    metric_likes: int = 0
    metric_shares: int = 0
    metric_comments: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class VaultVariantSchema(BaseModel):
    platform: str
    adapted_copy: Optional[str] = None
    publish_status: str
    created_at: Optional[str] = None

class VaultContentSchema(BaseModel):
    id: str
    campaign_name: str
    core_message: str
    created_at: Optional[str] = None
    variants: List[VaultVariantSchema]

class WorkspaceIntegrationSchema(BaseModel):
    id: str
    platform_name: str
    config_key: str
    config_value: str
    is_active: bool
    created_at: Optional[str] = None

class AIModelSchema(BaseModel):
    id: UUID
    model_id: str
    name: str
    provider: str
    description: Optional[str] = None
    category: str
    tags: List[str]
    series: Optional[str] = None
    context_window: Optional[str] = None
    model_size: Optional[str] = None
    is_custom: bool
    is_new: bool
    special_badge: Optional[str] = None
    api_url: Optional[str] = None
    api_key: Optional[str] = None

    class Config:
        from_attributes = True
