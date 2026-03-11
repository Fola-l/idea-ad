import uuid
from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import get_settings
from app.models import (
    GenerateRequest, GenerateResponse, CreativeRequest, CreativeResponse,
    PreviewResponse, DeployRequest, DeployResponse, StatusResponse,
    ActivateResponse, JobStatus, AdCopy, Audience, CampaignSettings, CreativeUrls
)
from app.services.claude_orchestrator import ClaudeOrchestrator, fetch_image_as_base64
from app.services.creative_pipeline import CreativePipeline
from app.services.meta_client import MetaClient, MetaAPIError
from app.db.supabase_client import (
    create_ad_run, get_ad_run, update_ad_run, list_ad_runs, upload_file
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    print("Starting idea-Ad API...")
    yield
    # Shutdown
    print("Shutting down idea-Ad API...")


app = FastAPI(
    title="idea-Ad API",
    description="AI-powered Facebook ad generation and deployment",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
orchestrator = ClaudeOrchestrator()
creative_pipeline = CreativePipeline()
meta_client = MetaClient()


@app.get("/health")
async def health_check():
    """Health check endpoint for uptime monitoring."""
    return {"status": "ok", "service": "idea-ad"}


@app.post("/api/upload")
async def upload_asset(
    file: UploadFile = File(...),
    type: str = Form(...)
):
    """
    Upload brand asset (logo, image, or video) to Supabase Storage.

    Args:
        file: The file to upload
        type: Asset type - 'logo', 'image', or 'video'

    Returns:
        JSON with the public URL of the uploaded file
    """
    # Validate file type
    allowed_types = {
        'logo': ['image/png', 'image/jpeg', 'image/jpg', 'image/webp'],
        'image': ['image/png', 'image/jpeg', 'image/jpg', 'image/webp'],
        'video': ['video/mp4', 'video/quicktime', 'video/x-msvideo', 'video/webm']
    }

    if type not in allowed_types:
        raise HTTPException(status_code=400, detail=f"Invalid type. Must be one of: logo, image, video")

    if file.content_type not in allowed_types[type]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type for {type}. Allowed: {', '.join(allowed_types[type])}"
        )

    # Validate file size (5MB for logos, 10MB for images, 50MB for videos)
    max_sizes = {'logo': 5 * 1024 * 1024, 'image': 10 * 1024 * 1024, 'video': 50 * 1024 * 1024}
    file_data = await file.read()
    if len(file_data) > max_sizes[type]:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Max size for {type}: {max_sizes[type] / (1024*1024):.0f}MB"
        )

    try:
        # Generate unique filename
        file_extension = file.filename.split('.')[-1] if '.' in file.filename else ''
        unique_filename = f"{uuid.uuid4()}.{file_extension}" if file_extension else str(uuid.uuid4())

        # Upload to appropriate bucket
        bucket_name = f"brand-assets-{type}s"  # logos, images, videos
        file_path = unique_filename

        # Upload to Supabase Storage
        public_url = await upload_file(
            bucket=bucket_name,
            path=file_path,
            file_data=file_data,
            content_type=file.content_type
        )

        return {"url": public_url, "type": type, "filename": file.filename}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@app.post("/api/generate", response_model=GenerateResponse)
async def generate_ad_strategy(request: GenerateRequest):
    """
    Generate ad strategy from a prompt.

    This endpoint:
    1. Calls Claude to generate ad copy, targeting, and creative brief
    2. Creates a job record in the database
    3. Returns the strategy for preview
    """
    job_id = str(uuid.uuid4())

    try:
        # Fetch image for vision analysis if provided
        demo_image_b64 = None
        if request.demo_image_url:
            demo_image_b64 = await fetch_image_as_base64(request.demo_image_url)

        # Generate ad strategy with Claude
        strategy = await orchestrator.generate_ad_strategy(
            prompt=request.prompt,
            demo_image_base64=demo_image_b64,
            destination_url=request.destination_url
        )

        # Create database record
        await create_ad_run(
            job_id=job_id,
            prompt=request.prompt,
            status="generating"
        )

        # Update with strategy data
        await update_ad_run(job_id, {
            "ad_copy": strategy.ad_copy.model_dump(),
            "audience": strategy.audience.model_dump(),
            "campaign_settings": strategy.campaign.model_dump(),
            "creative_brief": strategy.creative_brief,
            "voiceover_script": strategy.voiceover_script,
            "image_prompt": strategy.image_prompt,
            "format": strategy.format.value,
            "status": "generating"
        })

        return GenerateResponse(
            job_id=job_id,
            ad_copy=strategy.ad_copy,
            audience=strategy.audience,
            campaign_settings=strategy.campaign,
            creative_brief=strategy.creative_brief,
            voiceover_script=strategy.voiceover_script,
            image_prompt=strategy.image_prompt,
            format=strategy.format
        )

    except Exception as e:
        # Update job status to failed
        try:
            await update_ad_run(job_id, {
                "status": "failed",
                "error_message": str(e)
            })
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/creative", response_model=CreativeResponse)
async def generate_creative(request: CreativeRequest):
    """
    Generate creative assets for a job.

    This endpoint:
    1. Retrieves the job data
    2. Generates image/video/voiceover based on format
    3. Uploads assets to storage
    4. Updates job with asset URLs
    """
    # Get job data
    job = await get_ad_run(request.job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    try:
        # Generate creative assets
        creative_urls = await creative_pipeline.generate_creative(
            job_id=request.job_id,
            format=job.get("format", "image"),
            image_prompt=job.get("image_prompt", ""),
            voiceover_script=job.get("voiceover_script"),
            demo_video_url=None,  # Would come from original request
            demo_image_url=None,
            logo_url=None
        )

        # Update job with creative URLs
        await update_ad_run(request.job_id, {
            "creative_urls": creative_urls.model_dump(),
            "status": "preview"
        })

        return CreativeResponse(
            job_id=request.job_id,
            status="preview",
            image_url=creative_urls.image_url,
            video_url=creative_urls.video_url,
            voiceover_url=creative_urls.voiceover_url
        )

    except Exception as e:
        await update_ad_run(request.job_id, {
            "status": "failed",
            "error_message": str(e)
        })
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/preview/{job_id}", response_model=PreviewResponse)
async def get_preview(job_id: str):
    """
    Get full preview data for a job.

    Returns all generated data including ad copy, audience, settings, and creative URLs.
    """
    job = await get_ad_run(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Parse stored JSON data back into models
    ad_copy = AdCopy(**job["ad_copy"]) if job.get("ad_copy") else None
    audience = Audience(**job["audience"]) if job.get("audience") else None
    campaign_settings = CampaignSettings(**job["campaign_settings"]) if job.get("campaign_settings") else None
    creative_urls = CreativeUrls(**job["creative_urls"]) if job.get("creative_urls") else None

    return PreviewResponse(
        job_id=job_id,
        status=JobStatus(job.get("status", "pending")),
        prompt=job["prompt"],
        ad_copy=ad_copy,
        audience=audience,
        campaign_settings=campaign_settings,
        creative_urls=creative_urls,
        creative_brief=job.get("creative_brief"),
        voiceover_script=job.get("voiceover_script"),
        format=job.get("format")
    )


@app.post("/api/deploy", response_model=DeployResponse)
async def deploy_ad(request: DeployRequest):
    """
    Deploy ad to Meta Ads.

    This endpoint:
    1. Creates campaign, adset, creative, and ad in Meta
    2. All objects are created as PAUSED
    3. Returns Meta object IDs
    """
    # Get job data
    job = await get_ad_run(request.job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Update status to deploying
    await update_ad_run(request.job_id, {"status": "deploying"})

    try:
        # Parse approved data
        ad_copy = AdCopy(**request.approved_copy)
        audience = Audience(**request.approved_audience)
        campaign_settings = CampaignSettings(**request.approved_settings)

        # Get creative URLs
        creative_urls = job.get("creative_urls", {})
        image_url = creative_urls.get("image_url")
        video_url = creative_urls.get("video_url")

        # Deploy to Meta
        meta_ids = await meta_client.deploy_ad(
            job_id=request.job_id,
            ad_copy=ad_copy,
            audience=audience,
            campaign_settings=campaign_settings,
            image_url=image_url,
            video_url=video_url
        )

        # Update job with Meta IDs
        await update_ad_run(request.job_id, {
            "meta_ids": meta_ids.model_dump(),
            "status": "live",
            "sandbox_mode": request.sandbox_mode
        })

        return DeployResponse(
            job_id=request.job_id,
            status="live",
            campaign_id=meta_ids.campaign_id,
            adset_id=meta_ids.adset_id,
            creative_id=meta_ids.creative_id,
            ad_id=meta_ids.ad_id
        )

    except MetaAPIError as e:
        await update_ad_run(request.job_id, {
            "status": "failed",
            "error_message": f"Meta API Error: {e.message}"
        })
        raise HTTPException(status_code=400, detail=e.message)

    except Exception as e:
        await update_ad_run(request.job_id, {
            "status": "failed",
            "error_message": str(e)
        })
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/status/{ad_id}", response_model=StatusResponse)
async def get_ad_status(ad_id: str):
    """
    Get the status of a deployed ad from Meta.

    Returns review status and delivery status.

    effective_status values:
    - PENDING_REVIEW: Ad is waiting for Meta review
    - DISAPPROVED: Ad was rejected by Meta
    - PREAPPROVED: Ad is pre-approved
    - ACTIVE: Ad is running
    - PAUSED: Ad is paused by user
    - CAMPAIGN_PAUSED: Parent campaign is paused
    - ADSET_PAUSED: Parent ad set is paused
    """
    try:
        status = await meta_client.get_ad_status(ad_id)

        return StatusResponse(
            ad_id=ad_id,
            effective_status=status.get("effective_status"),
            configured_status=status.get("configured_status"),
            ad_review_feedback=status.get("ad_review_feedback"),
            created_at=status.get("created_time"),
            campaign_id=status.get("campaign_id"),
            adset_id=status.get("adset_id")
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/activate/{ad_id}", response_model=ActivateResponse)
async def activate_ad(ad_id: str):
    """
    Activate a deployed ad.

    This endpoint activates the ad and its parent objects (campaign, adset)
    so the ad starts running and spending budget.

    Prerequisites:
    - Ad must have passed Meta review (not PENDING_REVIEW or DISAPPROVED)
    - Payment method must be configured in Meta Business Manager

    Returns:
    - ActivateResponse with the new status after activation
    """
    try:
        result = await meta_client.activate_ad(ad_id)

        return ActivateResponse(
            ad_id=ad_id,
            success=True,
            effective_status=result.get("effective_status"),
            configured_status=result.get("configured_status"),
            campaign_activated=result.get("campaign_activated", False),
            adset_activated=result.get("adset_activated", False),
            ad_activated=result.get("ad_activated", False)
        )

    except MetaAPIError as e:
        return ActivateResponse(
            ad_id=ad_id,
            success=False,
            error=e.message
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/history")
async def get_history(limit: int = 50):
    """Get list of recent ad runs."""
    runs = await list_ad_runs(limit=limit)
    return {"runs": runs}


@app.post("/api/regenerate-image")
async def regenerate_image(job_id: str):
    """Regenerate the image for a job."""
    job = await get_ad_run(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    image_prompt = job.get("image_prompt")
    if not image_prompt:
        raise HTTPException(status_code=400, detail="No image prompt found")

    try:
        new_image_url = await creative_pipeline.regenerate_image(job_id, image_prompt)

        # Update creative URLs
        creative_urls = job.get("creative_urls", {})
        creative_urls["image_url"] = new_image_url
        await update_ad_run(job_id, {"creative_urls": creative_urls})

        return {"image_url": new_image_url}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/regenerate-voiceover")
async def regenerate_voiceover(job_id: str):
    """Regenerate the voiceover for a job."""
    job = await get_ad_run(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    voiceover_script = job.get("voiceover_script")
    if not voiceover_script:
        raise HTTPException(status_code=400, detail="No voiceover script found")

    try:
        new_voiceover_url = await creative_pipeline.regenerate_voiceover(
            job_id, voiceover_script
        )

        # Update creative URLs
        creative_urls = job.get("creative_urls", {})
        creative_urls["voiceover_url"] = new_voiceover_url
        await update_ad_run(job_id, {"creative_urls": creative_urls})

        return {"voiceover_url": new_voiceover_url}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
