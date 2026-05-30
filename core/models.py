# core/models.py
import json
import uuid
from sqlalchemy import Column, String, Text, Numeric, Integer, Boolean, DateTime, Date, ForeignKey, JSON, TypeDecorator
from sqlalchemy.dialects.postgresql import ARRAY, UUID, JSONB
from sqlalchemy.sql import func
from db.connection import Base, IS_MOCK_DATABASE

# Resolve cross-database data types - PostgreSQL Native & pgvector Type Anchor
UUID_TYPE = UUID(as_uuid=True)
ARRAY_TYPE = ARRAY(UUID(as_uuid=True))
JSON_TYPE = JSONB

from pgvector.sqlalchemy import Vector
VECTOR_TYPE = Vector(1024)

# 1. Model: User
class User(Base):
    __tablename__ = "users"
    id = Column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), default="member")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

# 2. Model: Workspace
class Workspace(Base):
    __tablename__ = "workspaces"
    id = Column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    name = Column(String(255), unique=True, nullable=False)
    owner_id = Column(UUID_TYPE, ForeignKey("users.id"))
    members = Column(ARRAY_TYPE, default=list) # Stored as array of UUIDs
    settings = Column(JSON_TYPE, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

# 3. Model: BrandIdentity
class BrandIdentity(Base):
    __tablename__ = "brand_identities"
    id = Column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID_TYPE, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    brand_name = Column(String(255), nullable=False)
    core_messaging = Column(JSON_TYPE, default=dict)
    visual_assets = Column(JSON_TYPE, default=dict)
    voice_and_tone = Column(Text)
    dos_and_donts = Column(JSON_TYPE, default=dict)
    content_pillars = Column(JSON_TYPE, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

# 4. Model: CustomerPersona
class CustomerPersona(Base):
    __tablename__ = "customer_personas"
    id = Column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID_TYPE, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    persona_name = Column(String(255), nullable=False)
    summary = Column(Text)
    demographics = Column(JSON_TYPE, default=dict)
    psychographics = Column(JSON_TYPE, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

# 5. Model: ProductService
class ProductService(Base):
    __tablename__ = "products_services"
    id = Column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID_TYPE, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    brand_id = Column(UUID_TYPE, ForeignKey("brand_identities.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    usp = Column(Text)
    key_features = Column(JSON_TYPE, default=list)
    key_benefits = Column(JSON_TYPE, default=list)
    default_offer = Column(String(1000))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

# 6. Model: MediaAsset
class MediaAsset(Base):
    __tablename__ = "media_assets"
    id = Column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID_TYPE, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    file_key = Column(Text, nullable=False)
    file_url = Column(Text, nullable=False)
    file_type = Column(String(50), nullable=False)
    aspect_ratio = Column(String(50))
    tags = Column(JSON_TYPE, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

# 7. Model: InspirationEvent
class InspirationEvent(Base):
    __tablename__ = "inspiration_events"
    id = Column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID_TYPE, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=True)
    event_name = Column(String(255), nullable=False)
    event_date = Column(Date)
    type = Column(String(100))
    description = Column(Text)
    suggested_angles = Column(JSON_TYPE, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

# 8. Model: SocialAccount
class SocialAccount(Base):
    __tablename__ = "social_accounts"
    id = Column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID_TYPE, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    platform = Column(String(50), nullable=False)
    account_name = Column(String(255), nullable=False)
    account_id = Column(String(255), nullable=False)
    access_token = Column(Text)
    refresh_token = Column(Text)
    expires_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

# 9. Model: PromptTemplate
class PromptTemplate(Base):
    __tablename__ = "prompt_templates"
    id = Column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID_TYPE, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    agent_role = Column(String(255), nullable=False)
    template_text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

# 10. Model: Worksheet
class Worksheet(Base):
    __tablename__ = "worksheets"
    id = Column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID_TYPE, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    event_id = Column(UUID_TYPE, ForeignKey("inspiration_events.id", ondelete="SET NULL"), nullable=True)
    brand_refs = Column(JSON_TYPE, default=list) # List of UUID strings
    customer_refs = Column(JSON_TYPE, default=list) # List of UUID strings
    status = Column(String(50), default="draft")
    agent_context = Column(JSON_TYPE, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

# 11. Model: MarketingCampaign
class MarketingCampaign(Base):
    __tablename__ = "marketing_campaigns"
    id = Column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID_TYPE, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    worksheet_id = Column(UUID_TYPE, ForeignKey("worksheets.id", ondelete="SET NULL"), nullable=True)
    product_id = Column(UUID_TYPE, ForeignKey("products_services.id"), nullable=True)
    name = Column(String(255), nullable=False)
    campaign_type = Column(String(100))
    status = Column(String(50), default="planned")
    budget = Column(Numeric(15, 2), default=0.00)
    kpi_targets = Column(JSON_TYPE, default=dict)
    start_date = Column(Date)
    end_date = Column(Date)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

# 12. Model: ContentBrief
class ContentBrief(Base):
    __tablename__ = "content_briefs"
    id = Column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID_TYPE, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    campaign_id = Column(UUID_TYPE, ForeignKey("marketing_campaigns.id", ondelete="CASCADE"), nullable=False)
    angle_name = Column(String(255), nullable=False)
    funnel_stage = Column(String(100), nullable=False)
    psychological_angle = Column(String(100), nullable=False)
    pain_point_focus = Column(Text)
    key_message_variation = Column(Text)
    call_to_action_direction = Column(Text)
    brief = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

# 13. Model: MasterContent
class MasterContent(Base):
    __tablename__ = "master_contents"
    id = Column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID_TYPE, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    campaign_id = Column(UUID_TYPE, ForeignKey("marketing_campaigns.id", ondelete="CASCADE"), nullable=False)
    content_brief_id = Column(UUID_TYPE, ForeignKey("content_briefs.id", ondelete="SET NULL"), nullable=True)
    core_message = Column(Text)
    primary_media_ids = Column(ARRAY_TYPE, default=list) # List of UUIDs
    approval_status = Column(String(50), default="pending")
    meta_data = Column("metadata", JSON_TYPE, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

# 14. Model: AgentLog
class AgentLog(Base):
    __tablename__ = "agent_logs"
    id = Column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID_TYPE, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    agent_name = Column(String(255), nullable=False)
    action = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False)
    tokens_used = Column(Integer, default=0)
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# 15. Model: PlatformVariant
class PlatformVariant(Base):
    __tablename__ = "platform_variants"
    id = Column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID_TYPE, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    master_content_id = Column(UUID_TYPE, ForeignKey("master_contents.id", ondelete="CASCADE"), nullable=False)
    platform = Column(String(50), nullable=False)
    adapted_copy = Column(Text)
    platform_media_ids = Column(ARRAY_TYPE, default=list) # List of UUIDs
    publish_status = Column(String(50), default="draft")
    content_type = Column(String(50))
    scheduled_at = Column(DateTime(timezone=True))
    published_at = Column(DateTime(timezone=True))
    platform_post_id = Column(String(255))
    meta_data = Column("metadata", JSON_TYPE, default=dict)
    metric_views = Column(Integer, default=0)
    metric_likes = Column(Integer, default=0)
    metric_shares = Column(Integer, default=0)
    metric_comments = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

# 16. Model: TrackingLink
class TrackingLink(Base):
    __tablename__ = "tracking_links"
    id = Column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID_TYPE, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    variant_id = Column(UUID_TYPE, ForeignKey("platform_variants.id", ondelete="CASCADE"), nullable=False)
    original_url = Column(Text, nullable=False)
    short_url = Column(String(255))
    utm_source = Column(String(100))
    utm_campaign = Column(String(100))
    click_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

# 17. Model: SocialInteraction
class SocialInteraction(Base):
    __tablename__ = "social_interactions"
    id = Column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID_TYPE, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    variant_id = Column(UUID_TYPE, ForeignKey("platform_variants.id", ondelete="CASCADE"), nullable=False)
    platform_user_id = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    sentiment = Column(String(50), nullable=False)
    is_handled = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

# 18. Model: Lead
class Lead(Base):
    __tablename__ = "leads"
    id = Column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID_TYPE, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    campaign_id = Column(UUID_TYPE, ForeignKey("marketing_campaigns.id", ondelete="SET NULL"), nullable=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255))
    phone = Column(String(50))
    source = Column(String(50))
    status = Column(String(50), default="new")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

# 19. Model: VideoJob
class VideoJob(Base):
    __tablename__ = "video_jobs"
    id = Column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID_TYPE, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    requested_by = Column(String(255))
    status = Column(String(50), default="queued")
    priority = Column(Numeric, default=0)
    input_json = Column(JSON_TYPE, nullable=False)
    input_images = Column(JSON_TYPE, default=list) # List of image path strings
    input_music = Column(Text)
    input_logo = Column(Text)
    variant_name = Column(String(255))
    output_video = Column(Text)
    thumbnail = Column(Text)
    progress = Column(Integer, default=0)
    progress_stage = Column(String(255))
    attempt_count = Column(Integer, default=0)
    max_attempts = Column(Integer, default=3)
    worker_id = Column(String(255))
    lease_until = Column(DateTime(timezone=True))
    error_message = Column(Text)
    render_duration_ms = Column(Integer, default=0)
    idempotency_key = Column(String(255), unique=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

# 20. Model: RAGAccessTag (Master Tags)
class RAGAccessTag(Base):
    __tablename__ = "rag_access_tags"
    tag_id       = Column("tag_id", UUID_TYPE, primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID_TYPE, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    tag_name     = Column(String(100), nullable=False)
    description  = Column(String(500))
    color        = Column(String(7), nullable=False, default="#6366f1")
    created_at   = Column(DateTime(timezone=True), server_default=func.now())

# 21a. Model: RAGDocument (Parent)
class RAGDocument(Base):
    __tablename__ = "rag_documents"
    document_id     = Column("document_id", UUID_TYPE, primary_key=True, default=uuid.uuid4)
    workspace_id    = Column(UUID_TYPE, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    file_name       = Column(String(255), nullable=False)
    file_key        = Column(Text)                              # MinIO object key
    access_tags     = Column(JSON_TYPE, nullable=False, default=lambda: ["global"])
    upload_status   = Column(String(50), nullable=False, default="processing")
    sync_status     = Column(String(50), nullable=False, default="synced")
    chunk_count     = Column(Integer, nullable=False, default=0)
    file_size_bytes = Column("file_size_bytes", Integer, nullable=False, default=0)
    file_hash       = Column(String(64), nullable=True)
    is_deleted      = Column(Boolean, nullable=False, default=False)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

# 21b. Model: RAGChunk (Child — Vector Store)
class RAGChunk(Base):
    __tablename__ = "rag_chunks"
    chunk_id     = Column("chunk_id", UUID_TYPE, primary_key=True, default=uuid.uuid4)
    document_id  = Column(UUID_TYPE, ForeignKey("rag_documents.document_id", ondelete="CASCADE"), nullable=False)
    workspace_id = Column(UUID_TYPE, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    content      = Column(Text, nullable=False)
    embedding    = Column(VECTOR_TYPE)
    chunk_index  = Column(Integer, nullable=False, default=0)
    # Phi chuẩn hóa từ rag_documents (Zero-JOIN)
    access_tags  = Column(JSON_TYPE, nullable=False, default=lambda: ["global"])
    is_deleted   = Column(Boolean, nullable=False, default=False)

# 21. Model: IntentRoutingKnowledge
class IntentRoutingKnowledge(Base):
    __tablename__ = "intent_routing_knowledge"
    id = Column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID_TYPE, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=True)
    intent_category = Column(String(50), nullable=False)
    utterance = Column(Text, nullable=False)
    embedding = Column(VECTOR_TYPE)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# 22. Model: AgentDecision
class AgentDecision(Base):
    __tablename__ = "agent_decisions"
    id = Column(UUID_TYPE, primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID_TYPE, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    campaign_id = Column(UUID_TYPE, ForeignKey("marketing_campaigns.id", ondelete="SET NULL"), nullable=True)
    agent_name = Column(String(255), nullable=False)
    action = Column(String(255), nullable=False)
    decision_status = Column(String(50), nullable=False)
    reason = Column(Text, nullable=False)
    meta_data = Column("metadata", JSON_TYPE, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())



