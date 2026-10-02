from api_usage import TrackedClient
"""
ArchPanda License Server — Reusable License & AI Backend
FastAPI server for selling and validating licenses across multiple products.
Supports Stripe checkout, license verification, cloud AI proxy, and admin dashboard.
"""

import os
import re
import json
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Header, Depends, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, EmailStr

import database as db

# Load environment variables (.env file if present, with claudeapi.txt fallback)
env_file = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(env_file):
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip("'\""))

if not os.getenv("ANTHROPIC_API_KEY"):
    for cand in [
        "/home/thedemiurge/Documents/claudeapi.txt",
        os.path.expanduser("~/Documents/claudeapi.txt"),
    ]:
        if os.path.exists(cand):
            try:
                with open(cand) as f:
                    keys = re.findall(r"sk-ant-[a-zA-Z0-9_\-]+", f.read())
                    if keys:
                        os.environ["ANTHROPIC_API_KEY"] = keys[0]
                        break
            except Exception:
                pass

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY")
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

# Stripe price IDs
STRIPE_PRICE_PRO = os.getenv("STRIPE_PRICE_PRO")
STRIPE_PRICE_PROPLUS = os.getenv("STRIPE_PRICE_PROPLUS")
STRIPE_PRICE_LIFETIME = os.getenv("STRIPE_PRICE_LIFETIME")

# Initialize optional Stripe
stripe_lib = None
if STRIPE_SECRET_KEY:
    try:
        import stripe
        stripe.api_key = STRIPE_SECRET_KEY
        stripe_lib = stripe
    except ImportError:
        print("Warning: stripe package not installed. Stripe features disabled.")

# Initialize optional Anthropic
anthropic_client = None
if ANTHROPIC_API_KEY:
    try:
        from anthropic import Anthropic
        anthropic_client = TrackedClient(Anthropic(api_key=ANTHROPIC_API_KEY), "devtools")
        print("✓ Anthropic client initialized successfully with Claude AI.")
    except ImportError:
        print("Warning: anthropic package not installed. Cloud AI disabled.")

ANTHROPIC_MODELS_CASCADE = [
    os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001"),
    "claude-haiku-4-5-20251001",
    "claude-sonnet-4-5-20250929",
    "claude-3-5-haiku-20241022",
    "claude-3-haiku-20240307"
]

def create_anthropic_message(**kwargs):
    """Executes message creation with automatic model cascade fallback."""
    if not anthropic_client:
        return None
    kwargs.pop("temperature", None)
    kwargs.pop("top_p", None)
    last_err = None
    requested_model = kwargs.pop("model", ANTHROPIC_MODELS_CASCADE[0])
    models_to_try = [requested_model] + [m for m in ANTHROPIC_MODELS_CASCADE if m != requested_model]
    for m in models_to_try:
        try:
            return anthropic_client.messages.create(model=m, **kwargs)
        except Exception as e:
            last_err = e
            err_str = str(e).lower()
            if "not_found" in err_str or "404" in err_str or "deprecated" in err_str:
                continue
            print(f"Anthropic error on model {m}: {e}")
    if last_err:
        print(f"All Anthropic models failed in cascade: {last_err}")
    return None

security = HTTPBearer(auto_error=False)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: migrate legacy data if present."""
    db.migrate_from_json()
    yield
    # Shutdown cleanup if needed

app = FastAPI(
    title="ArchPanda License Server",
    version="2.0.0",
    description="License validation, Stripe checkout, and Cloud AI proxy",
    lifespan=lifespan
)

# CORS - allow frontend and extension origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://archpanda.xyz", "https://www.archpanda.xyz", FRONTEND_URL, "chrome-extension://*", "http://localhost:*", "https://*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Pydantic Models ─────────────────────────────────────────────────────────

class LicenseVerifyResponse(BaseModel):
    valid: bool
    tier: str = "free"
    credits_remaining: int = 0
    status: str = "active"
    message: Optional[str] = None

class SummarizeRequest(BaseModel):
    abstract: str = Field(..., min_length=20, description="Academic paper abstract")

class SummarizeResponse(BaseModel):
    summary: str
    credits_remaining: int

class SuggestTagsRequest(BaseModel):
    title: str
    abstract: Optional[str] = None

class SuggestTagsResponse(BaseModel):
    tags: List[str]
    credits_remaining: int

class AuraFocusSubTask(BaseModel):
    id: str
    title: str
    duration_minutes: int
    dopamine_score: int

class AuraFocusChunkRequest(BaseModel):
    raw_text: str = Field(..., min_length=3, description="Unstructured brain-dump text")

class AuraFocusChunkResponse(BaseModel):
    dump_id: str
    raw_text: str
    tasks: List[AuraFocusSubTask]
    suggested_soundscape: str
    credits_remaining: int

class LofiTrack(BaseModel):
    id: str
    title: str
    filename: str
    url: str

class LofiTracksResponse(BaseModel):
    tracks: List[LofiTrack]
    total: int

class AuraFocusEmailDraftRequest(BaseModel):
    notes: str = Field(..., min_length=3, description="Blunt, messy bullet points or thoughts to turn into an email")
    tone: str = Field("professional_warm", description="Tone: professional_warm, short_polite, executive_crisp")
    recipient_name: Optional[str] = None


class DevToolsDiagnoseRequest(BaseModel):
    dom_snapshot: str
    error_logs: List[Dict[str, Any]]
    inputs: Optional[List[Dict[str, Any]]] = None
    custom_api_key: Optional[str] = None
    evidence: Optional[Dict[str, Any]] = None

class DevToolsDiagnoseResponse(BaseModel):
    diagnostics: str
    fix_plan: Optional[List[Dict[str, Any]]] = None
    remediation_script: Optional[str] = None
    safe_remediation_script: Optional[str] = None
    git_diff: Optional[str] = None
    credits_remaining: Optional[int] = None
    tier: Optional[str] = None

class AuraFocusEmailDraftResponse(BaseModel):
    subject: str
    body: str
    tone: str
    spoon_saver_tip: Optional[str] = None
    credits_remaining: int
    is_ai: bool = True



class CreateCheckoutRequest(BaseModel):
    tier: str = Field("lifetime", description="Tier to purchase: pro, proplus, lifetime")
    customer_email: Optional[EmailStr] = None
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None

class CheckoutResponse(BaseModel):
    checkout_url: Optional[str] = None
    url: Optional[str] = None
    session_id: Optional[str] = None
    mode: str = "live"
    license_key: Optional[str] = None
    message: Optional[str] = None

class BatchGenerateRequest(BaseModel):
    tier: str = Field(..., description="Tier to generate: pro, proplus, lifetime, team")
    count: int = Field(1, ge=1, le=1000, description="Number of keys to generate")
    customer_email: Optional[EmailStr] = None

class BatchGenerateResponse(BaseModel):
    keys: List[str]
    tier: str
    count: int

class AdminLicenseListResponse(BaseModel):
    licenses: List[Dict[str, Any]]
    total: int
    page: int
    limit: int

class HealthResponse(BaseModel):
    status: str
    version: str
    stripe_enabled: bool
    cloud_ai_enabled: bool
    database: str


# ─── Helpers ─────────────────────────────────────────────────────────────────

def normalize_tier(tier: str) -> str:
    """Normalize tier string to database format."""
    t = tier.lower().strip().replace("+", "_plus").replace("-", "_")
    if t == "proplus":
        t = "pro_plus"
    valid_tiers = ("free", "pro", "pro_plus", "lifetime", "team", "haiku_starter", "haiku_pro", "power_byok")
    if t not in valid_tiers:
        t = "haiku_starter"
    return t

def get_tier_price_id(tier: str) -> Optional[str]:
    """Get Stripe price ID for a tier."""
    mapping = {
        "pro": STRIPE_PRICE_PRO,
        "pro_plus": STRIPE_PRICE_PROPLUS,
        "lifetime": STRIPE_PRICE_LIFETIME
    }
    return mapping.get(tier)

async def verify_admin_auth(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify admin API key."""
    if not ADMIN_API_KEY:
        raise HTTPException(status_code=500, detail="Admin API key not configured")
    if not credentials or credentials.credentials != ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid admin API key")
    return credentials.credentials

async def get_license_user(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    if not authorization:
        return {
            "key": "FREE",
            "tier": "free",
            "credits_remaining": 10
        }

    # Support "Bearer KEY" or just "KEY"

    auth = authorization.strip()
    if auth.lower().startswith("bearer "):
        key = auth[7:].strip()
    else:
        key = auth
    
    key = key.upper()
    
    if not key or key in ("FREE", "DEMO-FREE", "ANONYMOUS"):
        return {
            "key": "FREE",
            "tier": "free",
            "credits_remaining": 10
        }
    
    # Each extension installation has a persistent trial identity. INSERT OR IGNORE
    # ensures opening another panel never replenishes its allowance.
    if re.fullmatch(r"FREE-[0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12}", key):
        with db.get_db() as conn:
            conn.execute("INSERT OR IGNORE INTO licenses (key, tier, credits_remaining, status, source) VALUES (?, 'free', 10, 'active', 'devtools_trial')", (key,))
            conn.commit()

    # Check database
    result = db.verify_license(key)
    if result["valid"]:
        return {
            "key": key,
            "tier": result["tier"],
            "credits_remaining": result.get("credits_remaining", 0)
        }
    
    raise HTTPException(status_code=401, detail="Invalid or unrecognized license key")


# ─── Public Routes ──────────────────────────────────────────────────────────

@app.get("/", response_model=HealthResponse)
async def health_check():
    """Public health check endpoint."""
    return HealthResponse(
        status="online",
        version="2.0.0",
        stripe_enabled=stripe_lib is not None,
        cloud_ai_enabled=anthropic_client is not None,
        database="connected"
    )

@app.get("/api/v1/license/verify", response_model=LicenseVerifyResponse)
async def verify_license_endpoint(authorization: Optional[str] = Header(None)):
    """Verify a license key."""
    if not authorization:
        return LicenseVerifyResponse(valid=False, message="No license key provided")
    
    auth = authorization.strip()
    key = auth[7:].strip().upper() if auth.lower().startswith("bearer ") else auth.upper()
    
    if re.fullmatch(r"FREE-[0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12}", key):
        user = await get_license_user(authorization)
        return LicenseVerifyResponse(valid=True, tier=user['tier'], credits_remaining=user['credits_remaining'])

    # Database lookup
    result = db.verify_license(key)
    if not result["valid"]:
        raise HTTPException(status_code=401, detail=result.get("reason", "Invalid license"))
    
    return LicenseVerifyResponse(
        valid=True,
        tier=result.get("tier", "free"),
        credits_remaining=result.get("credits_remaining", 0),
        status=result.get("status", "unknown"),
        message=None
    )


# ─── Cloud AI Proxy Routes ─────────────────────────────────────────────────

@app.post("/api/v1/summarize", response_model=SummarizeResponse)
async def summarize(
    req: SummarizeRequest,
    user: Dict[str, Any] = Depends(get_license_user)
):
    """Generate AI summary of an academic abstract."""
    if user["tier"] not in ("pro_plus", "lifetime", "free"):
        raise HTTPException(status_code=403, detail="Cloud AI requires Pro+, Lifetime, or Free tier")
    
    if user["credits_remaining"] <= 0:
        raise HTTPException(status_code=402, detail="No Cloud AI credits remaining")
    
    prompt = (
        "You are an expert academic research assistant. Summarize the following academic abstract "
        "in exactly 2 concise, high-impact bullet points focusing on core methodology and key findings:\n\n"
        f"{req.abstract}\n\nSummary:"
    )
    
    summary_text = None
    if anthropic_client:
        try:
            response = create_anthropic_message(
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}]
            )
            if response and response.content:
                summary_text = response.content[0].text.strip()
        except Exception as e:
            print(f"Claude API error: {e}")
    
    if not summary_text:
        # Fallback
        sentences = [s.strip() for s in req.abstract.split('.') if len(s.strip()) > 15]
        first = sentences[0] if sentences else "Proposes novel framework and evaluation."
        last = sentences[-1] if len(sentences) > 1 else "Demonstrates state-of-the-art results."
        summary_text = f"• {first}.\n• {last}."
    
    # Deduct credit
    if user.get("key") == "FREE":
        credits_remaining = max(0, user["credits_remaining"] - 1)
    else:
        result = db.deduct_credit(user["key"], "summarize")
        credits_remaining = result["credits_remaining"] if result["success"] else user["credits_remaining"] - 1
    
    return SummarizeResponse(
        summary=summary_text,
        credits_remaining=credits_remaining
    )

@app.post("/api/v1/suggest-tags", response_model=SuggestTagsResponse)
async def suggest_tags(
    req: SuggestTagsRequest,
    user: Dict[str, Any] = Depends(get_license_user)
):
    """Suggest research tags for a paper."""
    if user["tier"] not in ("pro_plus", "lifetime", "free"):
        raise HTTPException(status_code=403, detail="Cloud AI requires Pro+, Lifetime, or Free tier")
    
    if user["credits_remaining"] <= 0:
        raise HTTPException(status_code=402, detail="No Cloud AI credits remaining")
    
    # Simple heuristic tag extraction
    words = re.findall(r"\b[a-zA-Z]{4,}\b", req.title.lower())
    stop_words = {"this", "that", "with", "from", "using", "approach", "study", "neural", "network", "paper", "based"}
    meaningful = [w for w in words if w not in stop_words][:4]
    tags = [f"research-{w}" for w in meaningful] if meaningful else ["academic-research", "literature-note"]
    
    # Deduct credit
    if user.get("key") == "FREE":
        credits_remaining = max(0, user["credits_remaining"] - 1)
    else:
        result = db.deduct_credit(user["key"], "tag_suggest")
        credits_remaining = result["credits_remaining"] if result["success"] else user["credits_remaining"] - 1
    
    return SuggestTagsResponse(
        tags=tags,
        credits_remaining=credits_remaining
    )


@app.post("/api/v1/aurafocus/breakdown", response_model=AuraFocusChunkResponse)
async def aurafocus_breakdown(
    req: AuraFocusChunkRequest,
    user: Dict[str, Any] = Depends(get_license_user)
):
    """Deconstruct chaotic brain dumps into low-activation micro-tasks with dopamine scores using Claude."""
    import uuid

    dump_id = str(uuid.uuid4())
    tasks = []

    prompt = f"""You are an empathetic ADHD executive-function coach. The user is experiencing cognitive overwhelm from this brain dump:
"{req.raw_text}"

Deconstruct it into 2 to 5 ultra-actionable, low-activation-energy micro-steps.
Rules:
1. Each micro-step duration must be 3 to 15 minutes.
2. Assign a dopamine satisfaction score from 1 to 5.
3. Return STRICTLY a valid JSON array of objects. No markdown blocks, no intro, no outro.

Schema:
[
  {{"title": "Open document and write first line", "duration_minutes": 5, "dopamine_score": 4}}
]"""

    raw_response = None
    if anthropic_client:
        try:
            response = create_anthropic_message(
                max_tokens=500,
                temperature=0.2,
                messages=[{"role": "user", "content": prompt}]
            )
            if response and response.content:
                raw_response = response.content[0].text.strip()
        except Exception as e:
            print(f"Claude API error in AuraFocus breakdown: {e}")

    if raw_response:
        match = re.search(r"\[\s*\{[\s\S]*\}\s*\]", raw_response)
        if match:
            try:
                parsed = json.loads(match.group(0))
                for item in parsed:
                    tasks.append(AuraFocusSubTask(
                        id=str(uuid.uuid4()),
                        title=str(item.get("title", "Focus step")).strip(),
                        duration_minutes=max(3, min(30, int(item.get("duration_minutes", 5)))),
                        dopamine_score=max(1, min(5, int(item.get("dopamine_score", 3))))
                    ))
            except Exception as e:
                print(f"Error parsing Claude JSON: {e}")

    # Fallback heuristic if Claude key absent, model offline, or parse error
    if not tasks:
        chunks = [c.strip() for c in re.split(r"[,;.\n]+", req.raw_text) if len(c.strip()) > 2]
        if not chunks:
            chunks = [req.raw_text.strip()]
        for i, chunk in enumerate(chunks[:4]):
            tasks.append(AuraFocusSubTask(
                id=str(uuid.uuid4()),
                title=f"Step {i+1}: {chunk}",
                duration_minutes=(i + 1) * 5,
                dopamine_score=3
            ))

    credits_remaining = max(0, user.get("credits_remaining", 10) - 1)

    return AuraFocusChunkResponse(
        dump_id=dump_id,
        raw_text=req.raw_text,
        tasks=tasks,
        suggested_soundscape="lofi",
        credits_remaining=credits_remaining
    )


@app.post("/api/v1/aurafocus/draft-email", response_model=AuraFocusEmailDraftResponse)
async def aurafocus_draft_email(
    req: AuraFocusEmailDraftRequest,
    user: Dict[str, Any] = Depends(get_license_user)
):
    """
    Transforms blunt, anxious, or overdue communication bullets into a polished,
    empathetic, guilt-free ready-to-paste email draft using Claude AI.
    Engineered specifically to overcome ADHD Rejection Sensitive Dysphoria (RSD) and email paralysis.
    """
    subject = "Quick update"
    body = ""
    spoon_saver_tip = "Spoon Saver: You're human, and handling this directly is a win. Send without second-guessing!"

    prompt_tone_guide = {
        "professional_warm": "Warm, professional, appreciative, and calm. Acknowledge delays or incidents with poise and zero groveling.",
        "short_polite": "Ultra-brief (3-4 sentences max), polite, and direct. Gets straight to the point.",
        "executive_crisp": "Crisp, confident, structured with bullet points, action-oriented, zero fluff."
    }.get(req.tone, "Warm and professional without over-apologizing.")

    if anthropic_client is not None:
        try:
            system_prompt = (
                "You are an empathetic executive-communication assistant specializing in helping adults with ADHD "
                "overcome email initiation paralysis and Rejection Sensitive Dysphoria (RSD).\n"
                "The user will give you blunt, messy, anxious, or panic-laden notes/bullet points (such as late replies, "
                "accidents, missed deadlines, or catastrophic fears like 'please don't fire me').\n"
                "Transform these notes into a polished, professional, warm, and confident email draft.\n"
                "CRITICAL RULES:\n"
                "1. NEVER copy the user's anxious/catastrophic self-talk verbatim (e.g. NEVER include 'please don't fire me' or self-blame).\n"
                "2. Reframe accidents, mistakes, or delays with calm accountability, a pragmatic solution, and graceful brevity.\n"
                "3. DO NOT over-apologize or grovel. Normalize human error or minor delays gracefully.\n"
                "4. Produce a real, natural, ready-to-send email.\n"
                "Respond ONLY with valid JSON in this exact structure:\n"
                "{\n"
                '  "subject": "Clear, concise subject line",\n'
                '  "body": "Full email body text including greeting, paragraphs, and sign-off",\n'
                '  "spoon_saver_tip": "A 1-2 sentence reassuring ADHD spoon-saver tip acknowledging RSD and encouraging them to send without overthinking"\n'
                "}"
            )
            user_message = f"Tone: {req.tone} ({prompt_tone_guide})\nRecipient: {req.recipient_name or 'Recipient'}\nRaw notes:\n{req.notes}"

            response = create_anthropic_message(
                max_tokens=800,
                temperature=0.3,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}]
            )
            if response and response.content:
                raw_content = response.content[0].text
                json_match = re.search(r"\{[\s\S]*\}", raw_content)
                if json_match:
                    parsed = json.loads(json_match.group(0))
                    subject = parsed.get("subject", subject).strip()
                    body = parsed.get("body", "").strip()
                    spoon_saver_tip = parsed.get("spoon_saver_tip", spoon_saver_tip).strip()
        except Exception as e:
            print(f"Error generating email draft with Claude: {e}")

    is_ai = bool(body)

    # Fallback heuristic if Claude offline or no API key
    if not body:
        recipient = req.recipient_name or "there"
        clean_text = req.notes.strip()
        # Strip catastrophic panic phrases from raw notes
        sanitized = re.sub(r"(?i)\b(please\s+don'?t\s+fire\s+me|i'?m\s+terrible|i'?m\s+worthless|hate\s+myself)\b", "", clean_text).strip()
        sanitized = re.sub(r"\s{2,}", " ", sanitized)
        is_apology = any(w in sanitized.lower() for w in ["sorry", "late", "broke", "delay", "forgot", "accident", "missed"])
        
        if is_apology:
            subject = "Quick update regarding recent item"
            body = (
                f"Hi {recipient},\n\n"
                f"I wanted to reach out with a quick update. Regarding: {sanitized}.\n\n"
                f"I wanted to let you know right away so we can coordinate any next steps or solutions. "
                f"Thank you for your understanding, and please let me know what works best.\n\n"
                f"Best regards,"
            )
            spoon_saver_tip = "Spoon Saver: You addressed it honestly and directly. Take a breath and send it!"
        else:
            subject = "Quick update and next steps"
            body = (
                f"Hi {recipient},\n\n"
                f"I hope you're having a good week. Here is a quick update:\n\n"
                f"{sanitized}\n\n"
                f"Please let me know if you need any further information.\n\n"
                f"Best regards,"
            )
            spoon_saver_tip = "Spoon Saver: Clear and concise. Copy, paste, and send!"

    credits_remaining = max(0, user.get("credits_remaining", 10) - 1)
    return AuraFocusEmailDraftResponse(
        subject=subject,
        body=body,
        tone=req.tone,
        spoon_saver_tip=spoon_saver_tip,
        credits_remaining=credits_remaining,
        is_ai=is_ai
    )


@app.get("/api/v1/aurafocus/lofi/tracks", response_model=LofiTracksResponse)
async def get_lofi_tracks():
    """Returns all available open-domain lo-fi tracks."""
    music_dir = os.path.expanduser(os.getenv("LOFI_MUSIC_DIR", "/home/thedemiurge/Music/openlofi"))
    tracks = []
    if os.path.isdir(music_dir):
        for f in sorted(os.listdir(music_dir)):
            if f.lower().endswith((".mp3", ".ogg", ".wav")):
                clean_title = os.path.splitext(f)[0].replace("-", " ").replace("_", " ").title()
                tracks.append(LofiTrack(
                    id=f,
                    title=clean_title,
                    filename=f,
                    url=f"/api/v1/aurafocus/lofi/stream/{f}"
                ))
    return LofiTracksResponse(tracks=tracks, total=len(tracks))


@app.api_route("/api/v1/aurafocus/lofi/stream/{filename}", methods=["GET", "HEAD"])
async def stream_lofi_track(filename: str):
    """Stream an open-domain lo-fi audio track with range request support."""
    safe_filename = os.path.basename(filename)
    music_dir = os.path.expanduser(os.getenv("LOFI_MUSIC_DIR", "/home/thedemiurge/Music/openlofi"))
    file_path = os.path.join(music_dir, safe_filename)

    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="Track not found")

    media_type = "audio/mpeg"
    if safe_filename.endswith(".ogg"):
        media_type = "audio/ogg"
    elif safe_filename.endswith(".wav"):
        media_type = "audio/wav"

    return FileResponse(file_path, media_type=media_type, filename=safe_filename)


# ─── Stripe Checkout Routes ─────────────────────────────────────────────────



@app.post("/api/v1/devtools/diagnose", response_model=DevToolsDiagnoseResponse)
async def devtools_diagnose(
    req: DevToolsDiagnoseRequest,
    user: Dict[str, Any] = Depends(get_license_user)
):
    if user.get('key') in ('FREE', 'DEMO-FREE', 'ANONYMOUS'):
        raise HTTPException(status_code=401, detail='Update the extension to use a persistent free trial identity.')
    # Enforce credits only if not using BYOK
    is_byok = user.get("tier") == "power_byok" or bool(req.custom_api_key)
    if not is_byok and user.get("credits_remaining", 0) <= 0:
        raise HTTPException(status_code=402, detail="No Cloud AI credits remaining")

    credits_left = user.get('credits_remaining', 0)
    reserved_credit = False
    if not is_byok:
        reservation = db.deduct_credit(user['key'], action='devtools_audit')
        if not reservation.get('success'):
            raise HTTPException(status_code=402, detail='No Cloud AI credits remaining')
        credits_left = reservation['credits_remaining']
        reserved_credit = True
    try:
        system_prompt = """Analyze the page DOM and evidence for accessibility, form, runtime, network and metadata defects.
Return JSON with diagnostics (a string of concise root causes), fix_plan (3-6 items), and git_diff (suggested source patch for manual review).
Each fix_plan item contains title, description, category and operation. Choose operation only from:
fix-unlabeled-buttons, fix-unlabeled-links, fix-missing-alt, fix-main-landmark, fix-unlabelled-inputs, fix-insecure-blank, fix-locked-controls, fix-invalid-email-syntax.
These refer to fixed bundled repair functions. For unsupported fixes use operation null and explain the manual source change.
Do not supply remediation_code, remediation_script, safe_remediation_script, JavaScript to execute, selectors, expressions or executable parameters. Source patches are text for manual export only.
Labels, image meanings and application behavior need developer review; do not claim automatic WCAG compliance or zero risk.
"""

        # Enforce compact DOM size ceiling for rapid token processing
        safe_dom = (req.dom_snapshot or "")[:6000]

        evidence_summary = ""
        if req.evidence:
            evidence_summary = f"\n\nAudit Evidence Summary:\n" + json.dumps(req.evidence, indent=2)[:4000]

        error_summary = ""
        if req.error_logs:
            error_summary = f"\n\nError Logs:\n" + json.dumps(req.error_logs, indent=2)[:1500]

        user_message = f"DOM Snapshot (Interactive & Layout Excerpt):\n{safe_dom}{error_summary}{evidence_summary}"

        # Use BYOK custom API key if provided
        client_to_use = anthropic_client
        if req.custom_api_key and req.custom_api_key.startswith("sk-ant-"):
            try:
                import anthropic
                client_to_use = TrackedClient(anthropic.Anthropic(api_key=req.custom_api_key.strip()), "devtools", "byok")
            except Exception as e:
                print(f"Failed to initialize custom BYOK Anthropic client: {e}")

        raw_response = None
        if client_to_use:
            try:
                # Enable Anthropic ephemeral prompt caching on system prompt
                system_blocks = [
                    {
                        "type": "text",
                        "text": system_prompt,
                        "cache_control": {"type": "ephemeral"}
                    }
                ]
                if client_to_use == anthropic_client:
                    response = create_anthropic_message(
                        max_tokens=1800,
                        cache_control={"type": "ephemeral"},
                        system=system_blocks,
                        messages=[{"role": "user", "content": user_message}]
                    )
                else:
                    response = client_to_use.messages.create(
                        model=ANTHROPIC_MODELS_CASCADE[0],
                        max_tokens=1800,
                        cache_control={"type": "ephemeral"},
                        system=system_blocks,
                        messages=[{"role": "user", "content": user_message}]
                    )
                if response and response.content:
                    usage = getattr(response, "usage", None)
                    print("Anthropic cache usage: read=%s written=%s" % (getattr(usage, "cache_read_input_tokens", 0), getattr(usage, "cache_creation_input_tokens", 0)))
                    raw_response = response.content[0].text
            except Exception as e:
                print(f"Claude API error in DevTools diagnose: {e}")

        if not raw_response:
            raise HTTPException(status_code=500, detail="Claude backend failed to generate diagnostics.")

        diag_text = ""
        rem_script = None
        safe_rem_script = None
        fix_plan = None
        git_diff_text = None

        # Try clean JSON parse first
        try:
            clean_json = raw_response.strip()
            m_fence = re.search(r"```(?:json)?\s*(\{.*\})\s*```", clean_json, re.DOTALL)
            if m_fence:
                clean_json = m_fence.group(1).strip()
            else:
                m_brace = re.search(r"(\{.*\})", clean_json, re.DOTALL)
                if m_brace:
                    clean_json = m_brace.group(1).strip()
        
            parsed = json.loads(clean_json)
            diag_text = parsed.get("diagnostics", "")
            rem_script = parsed.get("remediation_script", None)
            safe_rem_script = parsed.get("safe_remediation_script", None)
            fix_plan = parsed.get("fix_plan", None)
            git_diff_text = parsed.get("git_diff", None)
        except Exception:
            # Fallback regex extraction
            m_script = re.search(r'"remediation_script"\s*:\s*"((?:[^"\\]|\\.)*)"', raw_response, re.DOTALL)
            if m_script:
                try:
                    rem_script = m_script.group(1).encode('utf-8').decode('unicode_escape')
                except Exception:
                    rem_script = m_script.group(1).replace('\\n', '\n').replace('\\"', '"')
        
            m_safe = re.search(r'"safe_remediation_script"\s*:\s*"((?:[^"\\]|\\.)*)"', raw_response, re.DOTALL)
            if m_safe:
                try:
                    safe_rem_script = m_safe.group(1).encode('utf-8').decode('unicode_escape')
                except Exception:
                    safe_rem_script = m_safe.group(1).replace('\\n', '\n').replace('\\"', '"')

            m_diff = re.search(r'"git_diff"\s*:\s*"((?:[^"\\]|\\.)*)"', raw_response, re.DOTALL)
            if m_diff:
                try:
                    git_diff_text = m_diff.group(1).encode('utf-8').decode('unicode_escape')
                except Exception:
                    git_diff_text = m_diff.group(1).replace('\\n', '\n').replace('\\"', '"')

            m_diag = re.search(r'"diagnostics"\s*:\s*"((?:[^"\\]|\\.)*)"', raw_response, re.DOTALL)
            if m_diag:
                try:
                    diag_text = m_diag.group(1).encode('utf-8').decode('unicode_escape')
                except Exception:
                    diag_text = m_diag.group(1).replace('\\n', '\n').replace('\\"', '"')
            else:
                # Strip outer markers from raw text
                cleaned = raw_response
                cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
                cleaned = re.sub(r"\s*```$", "", cleaned)
                cleaned = re.sub(r'^\s*\{\s*"diagnostics"\s*:\s*"?', "", cleaned)
                cleaned = re.sub(r'"\s*,\s*"remediation_script".*$', "", cleaned, flags=re.DOTALL)
                diag_text = cleaned.replace('\\n', '\n').replace('\\"', '"').strip()

        if not diag_text:
            diag_text = raw_response

        # Fallback git diff if none returned by model
        if not git_diff_text and rem_script:
            git_diff_text = (
                "--- a/src/Component.jsx\n"
                "+++ b/src/Component.jsx\n"
                "@@ Fix Assistant Source Patch @@\n"
                "// Permanent DOM repair:\n"
                f"{rem_script}"
            )

        # Fallback Fix Plan synthesis
        if not fix_plan or not isinstance(fix_plan, list):
            fix_plan = []
            if safe_rem_script or rem_script:
                fix_plan.append({
                    "id": "fix-safe-dom",
                    "title": "Automated Safe DOM Remediation",
                    "risk": "safe",
                    "category": "accessibility",
                    "description": "Applies non-destructive DOM accessibility attributes and label associations.",
                    "remediation_code": safe_rem_script or rem_script
                })
            if git_diff_text:
                fix_plan.append({
                    "id": "fix-source-patch",
                    "title": "Permanent Component Source Patch",
                    "risk": "manual",
                    "category": "javascript",
                    "description": "Unified git diff for updating source files in repository.",
                    "remediation_code": None
                })

        if not safe_rem_script and rem_script:
            safe_rem_script = rem_script

        if not isinstance(diag_text, str):
            diag_text = json.dumps(diag_text, ensure_ascii=False, indent=2)
        if git_diff_text is not None and not isinstance(git_diff_text, str):
            git_diff_text = json.dumps(git_diff_text, ensure_ascii=False, indent=2)

        allowed_operations = {'fix-unlabeled-buttons', 'fix-unlabeled-links', 'fix-missing-alt', 'fix-main-landmark', 'fix-unlabelled-inputs', 'fix-insecure-blank', 'fix-locked-controls', 'fix-invalid-email-syntax'}
        fix_plan = [{ 'title': str(item.get('title', 'Review finding'))[:200], 'description': str(item.get('description', ''))[:2000], 'category': str(item.get('category', 'manual'))[:100], 'operation': item.get('operation') if isinstance(item.get('operation'), str) and item.get('operation') in allowed_operations else None } for item in (fix_plan or []) if isinstance(item, dict)]
        rem_script = None
        safe_rem_script = None

        return DevToolsDiagnoseResponse(
            diagnostics=diag_text,
            fix_plan=fix_plan,
            safe_remediation_script=safe_rem_script,
            remediation_script=rem_script,
            git_diff=git_diff_text,
            credits_remaining=(db.get_license(user["key"])["credits_remaining"] if not is_byok else credits_left),
            tier=user.get("tier")
        )
    except Exception:
        if reserved_credit:
            with db.get_db() as conn:
                conn.execute('BEGIN IMMEDIATE')
                before = conn.execute('SELECT credits_remaining FROM licenses WHERE key = ?', (user['key'],)).fetchone()['credits_remaining']
                conn.execute("UPDATE licenses SET credits_remaining = credits_remaining + 1 WHERE key = ?", (user['key'],))
                conn.execute("INSERT INTO usage_logs (license_key, action, credits_before, credits_after, metadata) VALUES (?, 'devtools_audit_refund', ?, ?, '{}')", (user['key'], before, before + 1))
                conn.commit()
        raise

@app.post("/api/v1/stripe/create-checkout-session", response_model=CheckoutResponse)
async def create_checkout_session(req: CreateCheckoutRequest):
    """Create a Stripe checkout session for license purchase."""
    tier = normalize_tier(req.tier)
    
    if stripe_lib and STRIPE_SECRET_KEY:
        price_id = get_tier_price_id(tier)
        
        if not price_id:
            # Fall back to dynamic price creation with complete lifetime tiers
            prices = {
                "pro": int(os.getenv("STRIPE_PRICE_PRO_CENTS", 499)),
                "pro_plus": int(os.getenv("STRIPE_PRICE_PROPLUS_CENTS", 999)),
                "lifetime": int(os.getenv("STRIPE_PRICE_LIFETIME_CENTS", 2499)),
                "haiku_starter": int(os.getenv("STRIPE_PRICE_HAIKU_STARTER_CENTS", 4900)),
                "haiku_pro": int(os.getenv("STRIPE_PRICE_HAIKU_PRO_CENTS", 8900)),
                "power_byok": int(os.getenv("STRIPE_PRICE_POWER_BYOK_CENTS", 3900)),
            }
            product_info = {
                "haiku_starter": ("DevTools Fix Assistant — Haiku Starter", "Lifetime license with 200 AI audits/month"),
                "haiku_pro": ("DevTools Fix Assistant — Haiku Pro", "Lifetime license with 500 AI audits/month"),
                "power_byok": ("DevTools Fix Assistant — Power BYOK", "Lifetime license with unlimited local Ollama & Bring-Your-Own-Key"),
                "pro": ("Citation Capture — PRO", "Monthly Academic citation capture license"),
                "pro_plus": ("Citation Capture — PRO+", "Academic citation capture license with Cloud AI"),
                "lifetime": ("Citation Capture — LIFETIME", "Academic citation capture lifetime license with Cloud AI"),
            }
            p_name, p_desc = product_info.get(tier, (f"License — {tier.upper()}", "Software license"))
            
            try:
                session = stripe_lib.checkout.Session.create(
                    payment_method_types=["card"],
                    line_items=[{
                        "price_data": {
                            "currency": "usd",
                            "product_data": {
                                "name": p_name,
                                "description": p_desc,
                            },
                            "unit_amount": prices.get(tier, 4900),
                        },
                        "quantity": 1,
                    }],
                    mode="payment",
                    customer_email=req.customer_email,
                    metadata={"tier": tier},
                    success_url=req.success_url or f"{FRONTEND_URL}/success?session_id={{CHECKOUT_SESSION_ID}}",
                    cancel_url=req.cancel_url or f"{FRONTEND_URL}/cancel",
                )
                
                db.record_stripe_checkout(session.id, tier, req.customer_email)
                
                return CheckoutResponse(
                    checkout_url=session.url,
                    url=session.url,
                    session_id=session.id,
                    mode="live"
                )
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Stripe error: {str(e)}")
        else:
            # Use existing price ID
            try:
                session = stripe_lib.checkout.Session.create(
                    payment_method_types=["card"],
                    line_items=[{"price": price_id, "quantity": 1}],
                    mode="payment",
                    customer_email=req.customer_email,
                    metadata={"tier": tier},
                    success_url=req.success_url or f"{FRONTEND_URL}/success?session_id={{CHECKOUT_SESSION_ID}}",
                    cancel_url=req.cancel_url or f"{FRONTEND_URL}/cancel",
                )
                
                db.record_stripe_checkout(session.id, tier, req.customer_email)
                
                return CheckoutResponse(
                    checkout_url=session.url,
                    url=session.url,
                    session_id=session.id,
                    mode="live"
                )
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Stripe error: {str(e)}")
    else:
        raise HTTPException(status_code=503, detail='Payment service unavailable; no paid license issued.')

@app.get('/privacy', response_class=HTMLResponse)
async def privacy_policy():
    return FileResponse(os.path.join(os.path.dirname(__file__), 'privacy.html'), media_type='text/html')

@app.get('/success', response_class=HTMLResponse)
async def checkout_success():
    return HTMLResponse('<!doctype html><html><head><meta charset="utf-8"><title>DevTools License</title></head><body style="font:18px system-ui;max-width:700px;margin:60px auto;padding:20px"><h1>DevTools Fix Assistant License</h1><p id="status">Checking payment…</p><pre id="key"></pre><p>Copy your key into License &amp; Pricing in the Fix Assistant panel.</p><script>\nconst session = new URLSearchParams(location.search).get(\'session_id\');\nasync function check() {\n try {\n  const response = await fetch(\'api/v1/stripe/session-status?session_id=\' + encodeURIComponent(session || \'\'));\n  const data = await response.json();\n  if (!response.ok) throw new Error(data.detail || \'Unable to verify payment\');\n  if (data.status === \'complete\') { document.getElementById(\'status\').textContent = \'Payment confirmed. Your license key:\'; document.getElementById(\'key\').textContent = data.license_key; }\n  else { document.getElementById(\'status\').textContent = \'Payment is pending. Checking again…\'; setTimeout(check, 3000); }\n } catch (error) { document.getElementById(\'status\').textContent = error.message; }\n}\ncheck();\n</script></body></html>\n')

@app.get("/api/v1/stripe/session-status")
async def get_session_status(session_id: str):
    """Check checkout session status and return license key if completed."""
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id required")
    
    # 1. Check local database record first
    checkout_record = db.get_stripe_checkout(session_id)
    if checkout_record and checkout_record.get("license_key"):
        return {
            "status": "complete",
            "license_key": checkout_record["license_key"],
            "tier": checkout_record["tier"],
            "customer_email": checkout_record.get("customer_email")
        }
    
    # 2. Check Stripe API if available
    if stripe_lib and STRIPE_SECRET_KEY:
        try:
            session = stripe_lib.checkout.Session.retrieve(session_id)
            if session.payment_status == "paid":
                # Look up existing checkout record again
                checkout_record = db.get_stripe_checkout(session_id)
                if checkout_record and checkout_record.get("license_key"):
                    return {
                        "status": "complete",
                        "license_key": checkout_record["license_key"],
                        "tier": checkout_record["tier"],
                        "customer_email": checkout_record.get("customer_email")
                    }
                
                # Create license if not yet created (fallback if webhook was delayed)
                tier = session.get("metadata", {}).get("tier", "haiku_starter")
                customer_email = session.get("customer_details", {}).get("email") or session.get("customer_email")
                record = db.create_license(tier, customer_email, session_id, source="stripe_session_status")
                db.complete_stripe_checkout(session_id, record["key"])
                if customer_email:
                    send_license_email(customer_email, record["key"], record["tier"])
                return {
                    "status": "complete",
                    "license_key": record["key"],
                    "tier": record["tier"],
                    "customer_email": customer_email
                }
            return {"status": session.status, "payment_status": session.payment_status}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Stripe error: {str(e)}")
            
    raise HTTPException(status_code=404, detail="Session not found or payment pending")

@app.post("/api/v1/admin/reset-monthly-credits")
async def trigger_monthly_reset(admin_auth: str = Depends(verify_admin_auth)):
    """Trigger monthly credit reset for all active licenses (strictly expires unused balances)."""
    count = db.reset_monthly_credits()
    return {"status": "success", "reset_count": count, "reset_at": datetime.now().isoformat()}

def send_license_email(to_email: str, license_key: str, tier: str) -> bool:
    """Send license key to buyer via SMTP email."""
    if not to_email:
        return False
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    
    if not smtp_user or not smtp_pass:
        print(f"Warning: SMTP not configured. Cannot email key to {to_email}")
        return False
        
    tier_display = tier.replace("_", " ").upper()
    is_citation_capture = tier.lower() in ("pro", "pro_plus", "proplus", "lifetime", "team")
    product_name = "Obsidian Citation Capture" if is_citation_capture else "DevTools Fix Assistant"
    
    if is_citation_capture:
        steps_plain = """1. Open the Obsidian Citation Capture extension in Chrome
2. Click the settings icon (or open Extension Options)
3. Paste your license key into the 'Activate License' box
4. Click 'Activate'"""
        steps_html = """<li>Open the Obsidian Citation Capture extension in Chrome</li>
    <li>Click the <strong>settings icon</strong> (or open Extension Options)</li>
    <li>Paste your license key into the <strong>Activate License</strong> box</li>
    <li>Click <strong>Activate</strong></li>"""
        tagline = "Enjoy unlimited academic captures and AI-powered summaries!"
    else:
        steps_plain = """1. Open Chrome DevTools (Press F12 or Cmd+Option+I)
2. Select the 'Fix Assistant' tab
3. Click '💳 License & Pricing' in the top header
4. Paste your key and click 'Activate'"""
        steps_html = """<li>Open Chrome DevTools (<kbd style="background:#21262d; padding:2px 5px; border-radius:3px; color:#fff;">F12</kbd> or <kbd style="background:#21262d; padding:2px 5px; border-radius:3px; color:#fff;">Cmd+Option+I</kbd>)</li>
    <li>Select the <strong>Fix Assistant</strong> tab</li>
    <li>Click <strong>💳 License & Pricing</strong> in the header</li>
    <li>Paste your key and click <strong>Activate</strong></li>"""
        tagline = "Enjoy unlimited DOM fixes and AI-powered remediation!"
    
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Your {product_name} {tier_display} License Key"
    msg["From"] = smtp_user
    msg["To"] = to_email
    
    text_body = f"""Thank you for purchasing {product_name}!

Your license key: {license_key}
Tier: {tier_display}

How to activate:
{steps_plain}

{tagline}

— Scott @ ArchPanda (https://archpanda.xyz)
"""
    
    html_body = f"""<html><body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width:600px; margin:0 auto; padding:20px; background:#0d1117; color:#c9d1d9;">
<div style="text-align:center; padding: 20px 0;">
  <h2 style="color:#58a6ff; margin-bottom:6px;">Thank you for your purchase!</h2>
  <p style="color:#8b949e; font-size:14px;">Your {product_name} <strong>{tier_display}</strong> license key is ready:</p>
</div>
<div style="background:#161b22; border: 2px dashed #1f6feb; padding:20px; border-radius:10px; margin:20px 0; text-align:center;">
  <code style="font-size:1.4em; color:#79c0ff; font-weight:bold; letter-spacing:1px;">{license_key}</code>
</div>
<div style="background:#161b22; border-radius:8px; padding:16px; margin:20px 0;">
  <h3 style="color:#fff; margin-top:0; font-size:14px;">How to activate:</h3>
  <ol style="margin: 8px 0 0 16px; padding: 0; font-size:13px; line-height:1.6; color:#8b949e;">
    {steps_html}
  </ol>
</div>
<p style="color:#8b949e; font-size:12px; text-align:center;">Need help? Reply directly to this email or visit <a href="https://archpanda.xyz" style="color:#58a6ff;">archpanda.xyz</a>.</p>
</body></html>"""
    
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))
    
    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, to_email, msg.as_string())
        print(f"License email sent to {to_email} for {product_name} ({tier})")
        return True
    except Exception as e:
        print(f"Failed to send email to {to_email}: {e}")
        return False

@app.post("/api/v1/stripe/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    event = None
    if stripe_lib and STRIPE_WEBHOOK_SECRET and sig_header:
        try:
            event = stripe_lib.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid signature: {str(e)}")
    else:
        raise HTTPException(status_code=400, detail='A verified Stripe signature is required.')
    
    event_type = event.get("type", "")
    
    if event_type == "checkout.session.completed":
        session = event.get("data", {}).get("object", {})
        customer_email = (
            session.get("customer_details", {}).get("email")
            or session.get("customer_email")
        )
        tier = session.get("metadata", {}).get("tier", "haiku_starter")
        session_id = session.get("id")
        
        if session.get('payment_status') != 'paid':
            return {'status': 'ignored', 'reason': 'Payment not completed'}
        existing = db.get_stripe_checkout(session_id)
        if existing and existing.get('license_key'):
            return {'status': 'success', 'license_key': existing['license_key'], 'tier': existing['tier']}
        # Create license
        record = db.create_license(tier, customer_email, session_id, source="stripe")
        db.complete_stripe_checkout(session_id, record["key"])
        
        if customer_email:
            send_license_email(customer_email, record["key"], record["tier"])
        
        return {
            "status": "success",
            "license_key": record["key"],
            "tier": record["tier"],
            "customer_email": customer_email
        }
    
    return {"status": "ignored", "event_type": event_type}


# ─── Admin Routes (Protected) ────────────────────────────────────────────────

@app.post("/admin/licenses/generate", response_model=BatchGenerateResponse)
async def admin_generate_keys(
    req: BatchGenerateRequest,
    admin_key: str = Depends(verify_admin_auth)
):
    """Generate license keys in batch (admin only)."""
    tier = normalize_tier(req.tier)
    keys = []
    
    for _ in range(req.count):
        record = db.create_license(tier, req.customer_email, source="admin_batch")
        keys.append(record["key"])
    
    return BatchGenerateResponse(keys=keys, tier=tier, count=len(keys))

@app.get("/admin/licenses", response_model=AdminLicenseListResponse)
async def admin_list_licenses(
    tier: Optional[str] = None,
    status: Optional[str] = None,
    email: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    admin_key: str = Depends(verify_admin_auth)
):
    """List all licenses with filtering (admin only)."""
    licenses = db.list_licenses(
        tier=normalize_tier(tier) if tier else None,
        status=status,
        email=email,
        limit=limit,
        offset=offset
    )
    
    return AdminLicenseListResponse(
        licenses=licenses,
        total=len(licenses),
        page=offset // limit + 1,
        limit=limit
    )

@app.post("/admin/licenses/{key}/revoke")
async def admin_revoke_license(
    key: str,
    reason: str = "Admin revocation",
    admin_key: str = Depends(verify_admin_auth)
):
    """Revoke a license (admin only)."""
    success = db.revoke_license(key, reason)
    if not success:
        raise HTTPException(status_code=404, detail="License not found")
    return {"status": "revoked", "key": key.upper(), "reason": reason}

@app.get("/admin/stats")
async def admin_stats(
    days: int = 30,
    admin_key: str = Depends(verify_admin_auth)
):
    """Get usage statistics (admin only)."""
    return {
        "usage": db.get_usage_stats(days=days),
        "total_licenses": len(db.list_licenses(limit=10000)),
        "active_licenses": len(db.list_licenses(status="active", limit=10000)),
        "by_tier": {
            "pro": len(db.list_licenses(tier="pro", limit=10000)),
            "pro_plus": len(db.list_licenses(tier="pro_plus", limit=10000)),
            "lifetime": len(db.list_licenses(tier="lifetime", limit=10000))
        }
    }


# ─── Simple HTML Dashboard ─────────────────────────────────────────────────

@app.get("/dashboard", response_class=HTMLResponse)
async def simple_dashboard():
    """Simple HTML admin dashboard."""
    total = len(db.list_licenses(limit=10000))
    active = len(db.list_licenses(status="active", limit=10000))
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>ArchPanda License Server</title>
        <style>
            body {{ font-family: system-ui, sans-serif; max-width: 900px; margin: 40px auto; padding: 20px; }}
            .metric {{ display: inline-block; padding: 20px; margin: 10px; background: #f0f0f0; border-radius: 8px; }}
            .metric h2 {{ margin: 0; font-size: 2em; }}
            code {{ background: #e0e0e0; padding: 2px 6px; border-radius: 4px; }}
            .endpoint {{ margin: 10px 0; padding: 10px; background: #f8f8f8; border-left: 3px solid #007bff; }}
        </style>
    </head>
    <body>
        <h1>♜ ArchPanda License Server</h1>
        <p>Version 2.0.0 | Status: <span style="color: green;">● Online</span></p>
        
        <div class="metric"><h2>{total}</h2><p>Total Licenses</p></div>
        <div class="metric"><h2>{active}</h2><p>Active Licenses</p></div>
        
        <h2>API Endpoints</h2>
        <div class="endpoint"><code>GET /</code> — Health check</div>
        <div class="endpoint"><code>GET /api/v1/license/verify</code> — Verify license key</div>
        <div class="endpoint"><code>POST /api/v1/summarize</code> — AI summary (requires Pro+/Lifetime)</div>
        <div class="endpoint"><code>POST /api/v1/suggest-tags</code> — Tag suggestions (requires Pro+/Lifetime)</div>
        <div class="endpoint"><code>POST /api/v1/stripe/create-checkout-session</code> — Create payment session</div>
        <div class="endpoint"><code>POST /api/v1/stripe/webhook</code> — Stripe webhook handler</div>
        
        <h2>Admin Endpoints (Requires API Key)</h2>
        <div class="endpoint"><code>POST /admin/licenses/generate</code> — Batch generate keys</div>
        <div class="endpoint"><code>GET /admin/licenses</code> — List all licenses</div>
        <div class="endpoint"><code>POST /admin/licenses/&#123;key&#125;/revoke</code> — Revoke license</div>
        <div class="endpoint"><code>GET /admin/stats</code> — Usage statistics</div>
    </body>
    </html>
    """
    return html


# ─── Error Handlers ────────────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle unexpected errors gracefully."""
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "type": type(exc).__name__}
    )
