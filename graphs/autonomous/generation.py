# graphs/autonomous/generation.py
import logging
import uuid
from core.dependencies import get_session
from core.models import (
    BrandIdentity, CustomerPersona, ProductService, SocialAccount, CampaignSocialAccount
)
from core.ollama_client import generate_text
from core.utils import parse_llm_json, load_prompt
from graphs.supervisor.state import AgencyState
from graphs.autonomous.telemetry import instrument_node

logger = logging.getLogger("autonomous_nodes")


def generate_platform_variant(
    workspace_id: str,
    product_name: str,
    product_usp: str,
    persona_pains: str,
    brand_voice: str,
    angle: str,
    platform: str,
    idx: int
) -> dict:
    """
    Helper function to generate a single creative variant for a platform and angle.
    """
    if platform == "tiktok":
        content_type = "video_script"
        format_instructions = load_prompt("creative", "autonomous_format_tiktok.txt")
    else:
        content_type = "text"
        format_instructions = load_prompt("creative", "autonomous_format_facebook.txt")

    generation_template = load_prompt("creative", "autonomous_creative_generation.txt")
    prompt = generation_template.format(
        product_name=product_name,
        product_usp=product_usp,
        persona_pains=persona_pains,
        brand_voice=brand_voice,
        angle=angle,
        platform_upper=platform.upper(),
        format_instructions=format_instructions
    )

    logger.info(f"Generating variant #{idx+1} for angle: {angle} on platform {platform.upper()}...")
    try:
        res_str = generate_text(prompt, system_prompt="Output valid JSON only.", json_format=True, workspace_id=workspace_id)
        data = parse_llm_json(res_str)
        data["platform"] = platform
        data["content_type"] = content_type
        data["variant_id"] = str(uuid.uuid4())
        return data
    except Exception as e:
        logger.error(f"Error generating copy for angle {angle} on {platform}: {e}")
        raise RuntimeError(f"Failed to generate copy for angle {angle} on {platform}: {e}") from e


@instrument_node("creative_generation")
def creative_generation_node(state: AgencyState) -> dict:
    """
    Creative Generation Node (Copywriter Master).
    Queries database directly to inject TOPVNSPORT brand context without hallucinatory data.
    """
    logger.info("Executing Creative Generation Node...")
    workspace_id = state.get("workspace_id")
    product_id = state.get("product_id")
    mix = state.get("selected_actions") or []
    campaign_id = state.get("campaign_id")
    
    # Query database directly for seed context and target platforms
    brand_voice = ""
    persona_pains = ""
    product_usp = ""
    product_name = ""
    target_platforms = []
    
    with get_session() as db:
        brand = db.query(BrandIdentity).filter_by(workspace_id=uuid.UUID(str(workspace_id))).first()
        if brand:
            brand_voice = brand.voice_and_tone or ""
        
        persona = db.query(CustomerPersona).filter_by(workspace_id=uuid.UUID(str(workspace_id))).first()
        if persona:
            pains = persona.psychographics.get("pain_points", []) if persona.psychographics else []
            persona_pains = ", ".join(pains) if isinstance(pains, list) else str(pains)
            
        product = db.query(ProductService).filter_by(id=uuid.UUID(str(product_id))).first()
        if product:
            product_name = product.name
            product_usp = product.usp or ""
            
        # Query platforms from Junction Table
        social_links = []
        if campaign_id:
            social_links = db.query(SocialAccount).join(
                CampaignSocialAccount, 
                SocialAccount.id == CampaignSocialAccount.social_account_id
            ).filter(
                CampaignSocialAccount.campaign_id == uuid.UUID(str(campaign_id))
            ).all()
            
        # Fallback to all connected accounts in the workspace if campaign has no explicit links
        if not social_links:
            logger.info("No explicit campaign-level social links found. Falling back to workspace accounts.")
            social_links = db.query(SocialAccount).filter_by(workspace_id=uuid.UUID(str(workspace_id))).all()
            
        if social_links:
            target_platforms = list(set([acc.platform.lower() for acc in social_links]))
                
    if not target_platforms:
        raise ValueError("No target platforms connected in this workspace. Cannot generate creatives.")
        
    logger.info(f"Loaded Brand Context: Brand={brand.brand_name if brand else 'N/A'}, Target Platforms: {target_platforms}")
    
    generated_variants = []
    
    # Loop and generate copies using Ollama for each angle and platform in the mix
    for idx, action in enumerate(mix):
        angle = action["angle"]
        for platform in target_platforms:
            variant_data = generate_platform_variant(
                workspace_id=workspace_id,
                product_name=product_name,
                product_usp=product_usp,
                persona_pains=persona_pains,
                brand_voice=brand_voice,
                angle=angle,
                platform=platform,
                idx=idx
            )
            generated_variants.append(variant_data)
            
    return {
        "generated_variants": generated_variants,
        "sop_stage": "guardian_sandbox"
    }
