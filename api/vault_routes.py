from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from core.dependencies import get_db
from core.models import MasterContent, PlatformVariant, MarketingCampaign
from core.schemas import VaultContentSchema, VaultVariantSchema

vault_router = APIRouter(prefix="/api/vault", tags=["Vault"])

@vault_router.get("/contents", response_model=List[VaultContentSchema])
async def get_vault_contents(db: Session = Depends(get_db)):
    """
    Retrieve all approved master contents and their platform variants.
    """
    try:
        approved_contents = db.query(MasterContent).filter(
            MasterContent.approval_status == 'approved'
        ).order_by(MasterContent.created_at.desc()).all()
    
        data = []
        for mc in approved_contents:
            camp = db.query(MarketingCampaign).filter_by(id=mc.campaign_id).first()
            pvs = db.query(PlatformVariant).filter_by(master_content_id=mc.id).all()
        
            variants_list = []
            for pv in pvs:
                variants_list.append(VaultVariantSchema(
                    platform=pv.platform,
                    adapted_copy=pv.adapted_copy,
                    publish_status=pv.publish_status,
                    created_at=pv.created_at.strftime('%Y-%m-%d %H:%M:%S') if pv.created_at else None
                ))
        
            data.append(VaultContentSchema(
                id=str(mc.id),
                campaign_name=camp.name if camp else "",
                core_message=mc.core_message,
                created_at=mc.created_at.strftime('%d/%m/%Y %H:%M') if mc.created_at else None,
                variants=variants_list
            ))
        return data
    except Exception as e:
        import logging
        logger = logging.getLogger("vault_routes")
        logger.error(f"Error fetching vault contents: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
