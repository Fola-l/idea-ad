from supabase import create_client, Client
from typing import Optional, Dict, Any, List
import json
from datetime import datetime

from app.config import get_settings


class SupabaseClient:
    _instance: Optional[Client] = None

    @classmethod
    def get_client(cls) -> Client:
        if cls._instance is None:
            settings = get_settings()
            cls._instance = create_client(
                settings.supabase_url,
                settings.supabase_anon_key
            )
        return cls._instance


def get_db() -> Client:
    """Get Supabase client instance."""
    return SupabaseClient.get_client()


# Ad Runs Operations
async def create_ad_run(
    job_id: str,
    prompt: str,
    status: str = "pending",
    sandbox_mode: bool = True
) -> Dict[str, Any]:
    """Create a new ad run record."""
    db = get_db()
    data = {
        "job_id": job_id,
        "prompt": prompt,
        "status": status,
        "sandbox_mode": sandbox_mode
    }
    result = db.table("ad_runs").insert(data).execute()
    return result.data[0] if result.data else {}


async def get_ad_run(job_id: str) -> Optional[Dict[str, Any]]:
    """Get an ad run by job_id."""
    db = get_db()
    result = db.table("ad_runs").select("*").eq("job_id", job_id).execute()
    return result.data[0] if result.data else None


async def update_ad_run(job_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """Update an ad run record."""
    db = get_db()
    updates["updated_at"] = datetime.utcnow().isoformat()
    result = db.table("ad_runs").update(updates).eq("job_id", job_id).execute()
    return result.data[0] if result.data else {}


async def list_ad_runs(limit: int = 50) -> List[Dict[str, Any]]:
    """List recent ad runs."""
    db = get_db()
    result = db.table("ad_runs").select("*").order(
        "created_at", desc=True
    ).limit(limit).execute()
    return result.data


# Interest Cache Operations
async def get_cached_interest(interest_name: str) -> Optional[Dict[str, Any]]:
    """Get a cached interest ID by name."""
    db = get_db()
    result = db.table("interest_cache").select("*").eq(
        "interest_name", interest_name.lower()
    ).execute()
    return result.data[0] if result.data else None


async def cache_interest(
    interest_name: str,
    interest_id: str,
    audience_size: Optional[int] = None
) -> Dict[str, Any]:
    """Cache an interest ID."""
    db = get_db()
    data = {
        "interest_name": interest_name.lower(),
        "interest_id": interest_id,
        "audience_size": audience_size
    }
    # Upsert - update if exists, insert if not
    result = db.table("interest_cache").upsert(
        data, on_conflict="interest_name"
    ).execute()
    return result.data[0] if result.data else {}


# Storage Operations
async def upload_file(
    bucket: str,
    path: str,
    file_data: bytes,
    content_type: str = "application/octet-stream"
) -> str:
    """Upload a file to Supabase storage and return public URL."""
    db = get_db()
    try:
        # Try to upload (will fail if exists)
        db.storage.from_(bucket).upload(
            path,
            file_data,
            file_options={"content-type": content_type}
        )
    except Exception as e:
        # If file exists, update it instead
        if "Duplicate" in str(e) or "already exists" in str(e):
            db.storage.from_(bucket).update(
                path,
                file_data,
                file_options={"content-type": content_type}
            )
        else:
            raise e
    # Get public URL
    public_url = db.storage.from_(bucket).get_public_url(path)
    return public_url


async def get_file_url(bucket: str, path: str) -> str:
    """Get public URL for a file."""
    db = get_db()
    return db.storage.from_(bucket).get_public_url(path)
