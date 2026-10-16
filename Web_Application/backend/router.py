import os
import gc
import torch
from transformers import RobertaTokenizer, RobertaForSequenceClassification
from langdetect import detect, LangDetectException
from preprocess import preprocessing

MODEL_DIR = os.path.join(os.path.dirname(__file__), 'models')

# ─────────────────────────────────────────────
# Domain keyword scoring
# ─────────────────────────────────────────────
DOMAIN_KEYWORDS = {
    'covid': [
        'covid', 'coronavirus', 'vaccine', 'pandemic', 'virus', 'omicron',
        'delta', 'pfizer', 'moderna', 'astrazeneca', 'booster', 'lockdown',
        'quarantine', 'pcr', 'mask', 'social distancing', 'who', 'cdc',
        'epidemic', 'infection', 'hospitalization', 'icu', 'ventilator',
        'antibody', 'variant', 'outbreak', 'herd immunity', 'mrna'
    ],
    'gossip': [
        # Celebrity names - FAKE top words
        'jennifer', 'brad', 'kardashian', 'justin', 'jenner', 'pitt',
        'angelina', 'kim', 'selena', 'aniston', 'jolie', 'meghan',
        'gomez', 'blake', 'bieber', 'kylie', 'prince', 'taylor', 'peter', 'tony', 'andrew',
        'emma','tom','nolan',
        # Celebrity names - REAL top words
        'awards', 'star', 'wedding', 'reveals', 'season', 'watch',
        # Bigram keywords - FAKE
        'royal', 'pregnancy', 'heather', 'locklear', 'dakota',
        'instagram', 'unfollowing', 'hospitalized',
        # Bigram keywords - REAL
        'mirrorball', 'apologizes', 'embarrasses', 'screaming',
        'colbert', 'nightmares', 'alba',
        # General entertainment
        'celebrity', 'hollywood', 'actress', 'actor', 'singer',
        'divorce', 'engaged', 'married', 'pregnant', 'baby',
        'music', 'album', 'tour', 'movie', 'film', 'tv', 'show',
        'grammy', 'oscar', 'emmy', 'billboard', 'netflix',
        'breakup', 'dating', 'relationship', 'couple', 'split',
        'paparazzi', 'tabloid', 'gossip', 'rumor', 'scandal',
    ],
    'political': [
        'president', 'senator', 'congress', 'democrat', 'republican',
        'election', 'vote', 'policy', 'government', 'white house',
        'supreme court', 'biden', 'trump', 'obama', 'legislation', 'bill',
        'tax', 'immigration', 'foreign policy', 'military', 'nato',
        'parliament', 'minister', 'campaign', 'ballot', 'political party',
        'debate', 'constitution', 'federal', 'state', 'governor', 'mayor',
        'liberal', 'conservative', 'house'
    ],
}

MODEL_DISPLAY_NAMES = {
    'covid':     'COVID RoBERTa (Safetensors)',
    'gossip':    'GossipCOP RoBERTa (Safetensors)',
    'liar':      'LIAR RoBERTa (Safetensors)',
    'political': 'Politifact RoBERTa (Safetensors)',
}

# Maps domain key → actual folder name inside backend/models/
MODEL_FOLDER_NAMES = {
    'covid':     'COVID RoBERTa',
    'gossip':    'GossipCOP RoBERTa',
    'liar':      'LIAR RoBERTa',
    'political': 'Politifact RoBERTa',
}

DOMAIN_DISPLAY_LABELS = {
    'covid':     'Health / COVID-19',
    'gossip':    'Entertainment / Gossip',
    'liar':      'Political Statement',
    'political': 'Political Article',
}

def detect_language(text: str) -> str:
    try:
        word_count = len(text.strip().split())
        if word_count < 5:
            return 'en'  # assume English for very short texts
        return detect(text)
    except LangDetectException:
        return 'en'  # assume English if detection fails

def detect_domain(text: str):
    text_lower = text.lower()
    scores = {domain: 0 for domain in DOMAIN_KEYWORDS}

    for domain, keywords in DOMAIN_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                scores[domain] += 1

    best_domain = max(scores, key=scores.get)
    best_score  = scores[best_domain]

    if best_score == 0:
        return None

    if best_domain == 'political':
        word_count = len(text.split())
        return 'liar' if word_count < 80 else 'political'

    return best_domain

def load_model(domain: str):
    """
    Loads model from backend/models/<folder_name>/
    Folder names match VS Code explorer: 'COVID RoBERTa', 'GossipCOP RoBERTa', etc.
    """
    folder_name   = MODEL_FOLDER_NAMES[domain]
    domain_folder = os.path.join(MODEL_DIR, folder_name)

    if not os.path.exists(domain_folder):
        raise FileNotFoundError(f"Model directory missing: '{domain_folder}'")

    safetensors_file = os.path.join(domain_folder, "model.safetensors")
    if not os.path.exists(safetensors_file):
        raise FileNotFoundError(f"Missing 'model.safetensors' inside '{domain_folder}'")

    print(f"[ROUTER] Loading {MODEL_DISPLAY_NAMES[domain]} from local nested safetensors...")
    tokenizer = RobertaTokenizer.from_pretrained(domain_folder)
    model = RobertaForSequenceClassification.from_pretrained(domain_folder, use_safetensors=True)
    model.eval()
    return model, tokenizer

def run_inference(model, tokenizer, text: str):
    inputs = tokenizer(text, return_tensors='pt', truncation=True, max_length=512, padding=True)
    with torch.no_grad():
        outputs = model(**inputs)

    probs      = torch.softmax(outputs.logits, dim=1)
    label_idx  = torch.argmax(probs).item()
    confidence = round(probs[0][label_idx].item() * 100, 1)
    
    label      = 'REAL' if label_idx == 1 else 'FAKE'
    return label, confidence

def classify_text(raw_text: str) -> dict:
    lang = detect_language(raw_text)
    if lang != 'en':
        return {'status': 'error', 'message': 'Only English text is supported.'}

    try:
        clean_text = preprocessing(raw_text)
    except ValueError as e:
        return {'status': 'error', 'message': str(e)}

    domain = detect_domain(raw_text.lower())
    if domain is None:
        return {
            'status':  'error',
            'message': 'Topic not covered by our models. Please enter COVID-19, political, or entertainment news.'
        }

    try:
        model, tokenizer  = load_model(domain)
        label, confidence = run_inference(model, tokenizer, clean_text)
        del model, tokenizer
        gc.collect()
    except FileNotFoundError as e:
        return {'status': 'error', 'message': str(e)}
    except Exception as e:
        return {'status': 'error', 'message': f'Inference error: {str(e)}'}

    return {
        'status':     'success',
        'domain':     DOMAIN_DISPLAY_LABELS[domain],
        'model_used': MODEL_DISPLAY_NAMES[domain],
        'label':      label,
        'confidence': confidence,
    }