from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.core.database import get_db
from app.models import ConfigCloudAccount
from sqlalchemy.future import select
from app.core.security import encrypt_credentials, decrypt_credentials
import boto3

router = APIRouter(prefix="/cloud-config", tags=["Credentials"])

class ConfigCloudAccountCreate(BaseModel):
    provider: str
    account_name: str
    default_region: str = "global"
    credentials: dict

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_config(payload: ConfigCloudAccountCreate, db: AsyncSession = Depends(get_db)):
    encrypted_str = encrypt_credentials(payload.credentials)
    
    db_config = ConfigCloudAccount(
        provider=payload.provider,
        account_name=payload.account_name,
        default_region=payload.default_region,
        encrypted_credentials=encrypted_str,
        verified=False
    )
    db.add(db_config)
    await db.commit()
    await db.refresh(db_config)
    return {"id": db_config.id, "status": "stored", "verified": False}

@router.get("/")
async def list_configs(db: AsyncSession = Depends(get_db)):
    stmt = select(ConfigCloudAccount).order_by(ConfigCloudAccount.id.desc())
    result = await db.execute(stmt)
    configs = result.scalars().all()
    
    return [
        {
            "id": c.id,
            "provider": c.provider,
            "account_name": c.account_name,
            "region": c.default_region,
            "verified": c.verified,
            "auto_sync_enabled": c.auto_sync_enabled,
            "auto_sync_time": c.auto_sync_time,
            "auto_sync_timezone": c.auto_sync_timezone
        }
        for c in configs
    ]

@router.delete("/{config_id}")
async def delete_config(config_id: int, db: AsyncSession = Depends(get_db)):
    db_config = await db.get(ConfigCloudAccount, config_id)
    if not db_config:
        raise HTTPException(status_code=404, detail="Configuration target not found")
        
    await db.delete(db_config)
    await db.commit()
    return {"status": "success", "message": "Deleted config"}

@router.post("/{config_id}/verify")
async def verify_config(config_id: int, db: AsyncSession = Depends(get_db)):
    db_config = await db.get(ConfigCloudAccount, config_id)
    if not db_config:
        raise HTTPException(status_code=404, detail="Configuration target not found")
        
    plain_creds = decrypt_credentials(db_config.encrypted_credentials)
    
    if db_config.provider == "aws":
        try:
            session = boto3.Session(
                aws_access_key_id=plain_creds.get("aws_access_key_id"),
                aws_secret_access_key=plain_creds.get("aws_secret_access_key"),
                region_name=db_config.default_region if db_config.default_region != "global" else "us-east-1"
            )
            sts = session.client('sts')
            sts.get_caller_identity()
            is_valid = True
        except Exception as e:
            is_valid = False
            error_msg = str(e)
    else:
        raise HTTPException(status_code=400, detail="Unsupported cloud provider")
        
    if is_valid:
        db_config.verified = True
        await db.commit()
        return {"status": "success", "message": "Connection verified successfully"}
        
    raise HTTPException(status_code=400, detail=f"Cloud verification check failed: {error_msg}")

class AutoSyncUpdate(BaseModel):
    enabled: bool
    time: str
    timezone: str

@router.patch("/{config_id}/auto-sync")
async def update_auto_sync(config_id: int, payload: AutoSyncUpdate, db: AsyncSession = Depends(get_db)):
    db_config = await db.get(ConfigCloudAccount, config_id)
    if not db_config:
        raise HTTPException(status_code=404, detail="Configuration target not found")
        
    if db_config.auto_sync_time != payload.time:
        db_config.last_sync_date = None
        
    db_config.auto_sync_enabled = payload.enabled
    db_config.auto_sync_time = payload.time
    db_config.auto_sync_timezone = payload.timezone
    await db.commit()
    
    return {"status": "success", "message": "Auto sync settings updated"}
