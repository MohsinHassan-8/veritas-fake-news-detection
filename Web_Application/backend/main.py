import os
from fastapi import FastAPI, HTTPException, Depends, Header # type: ignore
from fastapi.middleware.cors import CORSMiddleware # type: ignore
from pydantic import BaseModel # type: ignore
from typing import Optional
import firebase_admin # type: ignore
from firebase_admin import credentials, auth as firebase_auth # type: ignore
import os, json, tempfile


from database import (
    init_db, save_user, save_prediction, get_history, save_profile, get_profile,
    save_training_submission, save_community_submission, save_flagged_result
)
from router import classify_text

# ─────────────────────────────────────────────
# Initialize Firebase Admin SDK & Database
# ─────────────────────────────────────────────
 
# Read key from environment variable instead of file
key_json_str = os.environ.get('FIREBASE_KEY_JSON')
if key_json_str:
    key_data = json.loads(key_json_str)
    tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
    json.dump(key_data, tmp)
    tmp.flush()
    KEY_PATH = tmp.name
else:
    KEY_PATH = 'firebase-key.json'  # fallback for local dev


if not firebase_admin._apps:
    cred = credentials.Certificate(KEY_PATH)
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://fake-news-detection-adc5e-default-rtdb.asia-southeast1.firebasedatabase.app'
    })
    print("[SYSTEM] Firebase Admin SDK initialized successfully.")

init_db()

# ─────────────────────────────────────────────
# FastAPI
# ─────────────────────────────────────────────
app = FastAPI(title="VERITAS — Fake News Detection API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://veritas-full-stack.vercel.app"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def verify_token(authorization: str = Header(...)):
    try:
        token   = authorization.replace("Bearer ", "").strip()
        decoded = firebase_auth.verify_id_token(token)
        return decoded
    except Exception:
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid or expired token.")

class ClassifyRequest(BaseModel):
    text: str

class UserSyncRequest(BaseModel):
    email:    Optional[str] = None
    username: Optional[str] = None

class ProfileUpdateRequest(BaseModel):
    display_name: Optional[str] = None
    avatar_url:   Optional[str] = None  # base64 data URI

class TrainingSubmissionRequest(BaseModel):
    text:          str
    model_verdict: str
    user_label:    str
    confidence:    float
    domain:        Optional[str] = None

class CommunitySubmissionRequest(BaseModel):
    text:       str
    label:      str
    domain:     Optional[str] = None
    source_url: Optional[str] = None

class FlagResultRequest(BaseModel):
    text:          str
    model_verdict: str
    confidence:    float
    domain:        Optional[str] = None
    reason:        Optional[str] = None

LOW_CONFIDENCE_THRESHOLD = 65.0

# ─────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────

@app.get("/")
def root():
    return {"system": "VERITAS API", "status": "online", "models": 4, "version": "1.0.0"}

@app.post("/sync-user")
async def sync_user(req: UserSyncRequest, user=Depends(verify_token)):
    try:
        save_user(
            firebase_uid=user['uid'],
            email=req.email or user.get('email', ''),
            username=req.username
        )
    except Exception as e:
        print(f"[WARN] Could not sync user: {e}")
    return {"status": "ok", "uid": user['uid']}

@app.post("/profile")
async def update_profile(req: ProfileUpdateRequest, user=Depends(verify_token)):
    """Save display name and/or avatar to RTDB so they persist across all browsers."""
    try:
        save_profile(
            firebase_uid=user['uid'],
            display_name=req.display_name,
            avatar_url=req.avatar_url
        )
    except Exception as e:
        print(f"[WARN] Could not save profile: {e}")
        raise HTTPException(status_code=500, detail="Could not save profile.")
    return {"status": "ok"}

@app.get("/profile")
async def load_profile(user=Depends(verify_token)):
    """Load display name and avatar from RTDB on login."""
    try:
        data = get_profile(user['uid'])
        return data
    except Exception as e:
        print(f"[WARN] Could not load profile: {e}")
        return {"display_name": "", "avatar_url": "", "email": ""}

@app.post("/classify")
async def classify(req: ClassifyRequest, user=Depends(verify_token)):
    text = req.text.strip()
    if len(text) < 10:
        raise HTTPException(status_code=400, detail="Text is too short.")
    if len(text) > 5000:
        raise HTTPException(status_code=400, detail="Text exceeds 5000 character limit.")

    result = classify_text(text)

    if result.get('status') == 'success':
        result['low_confidence'] = result.get('confidence', 100) < LOW_CONFIDENCE_THRESHOLD
        try:
            save_prediction(user['uid'], text, result)
        except Exception as e:
            print(f"[WARN] Could not save prediction: {e}")

    return result

@app.get("/history")
async def history(user=Depends(verify_token)):
    try:
        records = get_history(user['uid'])
        return {"history": records}
    except Exception as e:
        print(f"[WARN] Could not load history: {e}")
        return {"history": []}

# ─────────────────────────────────────────────
# Training data collection endpoints
# ─────────────────────────────────────────────

@app.post("/submit-training")
async def submit_training(req: TrainingSubmissionRequest, user=Depends(verify_token)):
    """Saves a user-reported wrong verdict (model_verdict vs user_label) for review."""
    try:
        save_training_submission(
            firebase_uid=user['uid'],
            text=req.text,
            model_verdict=req.model_verdict,
            user_label=req.user_label,
            confidence=req.confidence,
            domain=req.domain
        )
    except Exception as e:
        print(f"[WARN] Could not save training submission: {e}")
        raise HTTPException(status_code=500, detail="Could not save submission.")
    return {"status": "ok"}

@app.post("/submit-community")
async def submit_community(req: CommunitySubmissionRequest, user=Depends(verify_token)):
    """Saves a community-submitted, manually labeled news article."""
    label = req.label.strip().upper()
    if label not in ("REAL", "FAKE"):
        raise HTTPException(status_code=400, detail="Label must be REAL or FAKE.")
    try:
        save_community_submission(
            firebase_uid=user['uid'],
            text=req.text,
            label=label,
            domain=req.domain,
            source_url=req.source_url
        )
    except Exception as e:
        print(f"[WARN] Could not save community submission: {e}")
        raise HTTPException(status_code=500, detail="Could not save submission.")
    return {"status": "ok"}

@app.post("/flag-result")
async def flag_result(req: FlagResultRequest, user=Depends(verify_token)):
    """Saves a flagged result — low confidence, unclassifiable, or marked outdated."""
    try:
        save_flagged_result(
            firebase_uid=user['uid'],
            text=req.text,
            model_verdict=req.model_verdict,
            confidence=req.confidence,
            domain=req.domain,
            reason=req.reason
        )
    except Exception as e:
        print(f"[WARN] Could not save flagged result: {e}")
        raise HTTPException(status_code=500, detail="Could not save flag.")
    return {"status": "ok"}