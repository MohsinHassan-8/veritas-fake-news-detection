import os
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db

KEY_PATH = os.path.join(os.path.dirname(__file__), 'firebase-key.json')

def init_db():
    if not firebase_admin._apps:
        cred = credentials.Certificate(KEY_PATH)
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://fake-news-detection-adc5e-default-rtdb.asia-southeast1.firebasedatabase.app'
        })
    print("[DB] Firebase Realtime Database connected successfully.")

def save_user(firebase_uid, email, username=None):
    """Creates user profile only if it doesn't exist yet."""
    init_db()
    ref = db.reference(f'users/{firebase_uid}')
    if not ref.get():
        ref.set({
            'username': username or email.split('@')[0],
            'email': email,
            'display_name': username or email.split('@')[0],
            'avatar_url': '',
            'created_at': {'.sv': 'timestamp'}
        })
        print(f"[DB] Saved new user profile: {firebase_uid}")

def save_profile(firebase_uid, display_name=None, avatar_url=None):
    """Updates display name and/or avatar URL in RTDB — persists across all browsers."""
    init_db()
    ref = db.reference(f'users/{firebase_uid}')
    updates = {}
    if display_name is not None:
        updates['display_name'] = display_name
    if avatar_url is not None:
        updates['avatar_url'] = avatar_url
    if updates:
        ref.update(updates)
        print(f"[DB] Updated profile for {firebase_uid}: {list(updates.keys())}")

def get_profile(firebase_uid):
    """Returns saved display_name and avatar_url from RTDB."""
    init_db()
    ref = db.reference(f'users/{firebase_uid}')
    data = ref.get()
    if not data:
        return {}
    return {
        'display_name': data.get('display_name', ''),
        'avatar_url':   data.get('avatar_url', ''),
        'email':        data.get('email', '')
    }

def save_prediction(firebase_uid, text, result):
    init_db()
    ref = db.reference(f'users/{firebase_uid}/history')
    ref.push({
        'input_text': text[:1000],
        'domain':     result.get('domain'),
        'model_used': result.get('model_used'),
        'label':      result.get('label'),
        'confidence': result.get('confidence'),
        'created_at': {'.sv': 'timestamp'}
    })
    print(f"[DB] Appended prediction history to user profile: {firebase_uid}")

def get_history(firebase_uid):
    init_db()
    ref = db.reference(f'users/{firebase_uid}/history')
    snapshot = ref.order_by_child('created_at').get()
    if not snapshot:
        return []
    history = []
    for key, val in snapshot.items():
        input_text = val.get('input_text', '')
        history.append({
            'text':       input_text[:80] + ('...' if len(input_text) > 80 else ''),
            'domain':     val.get('domain'),
            'model_used': val.get('model_used'),
            'label':      val.get('label'),
            'confidence': val.get('confidence'),
            'created_at': val.get('created_at')
        })
    history.reverse()
    return history

# ─────────────────────────────────────────────
# Training data collection features
# ─────────────────────────────────────────────

def save_training_submission(firebase_uid, text, model_verdict, user_label, confidence, domain=None):
    """Saves a user-reported wrong verdict for dataset review."""
    init_db()
    ref = db.reference(f'training_submissions/{firebase_uid}')
    ref.push({
        'text':           text[:1000],
        'model_verdict':  model_verdict,
        'user_label':     user_label,
        'confidence':     confidence,
        'domain':         domain,
        'created_at':     {'.sv': 'timestamp'}
    })
    print(f"[DB] Saved training submission from {firebase_uid}")

def save_community_submission(firebase_uid, text, label, domain=None, source_url=None):
    """Saves a community-submitted, manually labeled news article."""
    init_db()
    ref = db.reference('community_submissions')
    ref.push({
        'text':         text[:5000],
        'label':        label,
        'domain':       domain,
        'source_url':   source_url,
        'submitted_by': firebase_uid,
        'created_at':   {'.sv': 'timestamp'}
    })
    print(f"[DB] Saved community submission from {firebase_uid}")

def save_flagged_result(firebase_uid, text, model_verdict, confidence, domain=None, reason=None):
    """Saves a flagged result — low confidence, unclassifiable, or marked outdated."""
    init_db()
    ref = db.reference('flagged_results')
    ref.push({
        'text':          text[:1000],
        'model_verdict': model_verdict,
        'confidence':    confidence,
        'domain':        domain,
        'reason':        reason,
        'flagged_by':    firebase_uid,
        'created_at':    {'.sv': 'timestamp'}
    })
    print(f"[DB] Saved flagged result from {firebase_uid}")