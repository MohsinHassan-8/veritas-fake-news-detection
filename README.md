# VERITAS (Neural Fake News Detection System)

VERITAS is a full-stack, domain-specific news credibility verification system. It leverages fine-tuned transformer models (RoBERTa) to classify text statements and articles into REAL or FAKE categories across four critical news domains: COVID-19, GossipCop (entertainment/celebrity gossip), LIAR (short political statements), and PolitiFact (long-form political articles).

The project is split into two primary components:
1. Model Development: Extensive Exploratory Data Analysis (EDA) and experimental model training pipelines (N-Gram, TF-IDF, Word2Vec, GloVe, FastText, BERT, ALBERT, and RoBERTa) on domain-specific datasets.
2. Web Application: A real-time, production-ready web platform consisting of a Python (FastAPI) backend and a highly responsive, modern cyber-themed HTML/JS frontend integrated with Firebase Authentication and Realtime Database.

---

## Repository Architecture

```
VERITAS-PROJECT/
├── Model_Development/            # Model Research & Training Code
│   ├── COVID-19/                 # COVID-19 fake news dataset & notebooks
│   ├── GossipCop/                # GossipCop celebrity gossip dataset & notebooks
│   ├── LIAR/                     # LIAR political statements dataset & notebooks
│   └── PolitiFact/               # PolitiFact political articles dataset & notebooks
└── Web_Application/              # Full-Stack Web App Implementation
    ├── backend/                  # FastAPI Backend API
    │   ├── models/               # Fine-tuned RoBERTa models (local safetensors)
    │   │   ├── COVID RoBERTa/
    │   │   ├── GossipCOP RoBERTa/
    │   │   ├── LIAR RoBERTa/
    │   │   └── Politifact RoBERTa/
    │   ├── database.py           # Firebase Realtime DB connector
    │   ├── main.py               # Main API endpoints (FastAPI)
    │   ├── preprocess.py         # Text cleaning and preprocessing pipeline
    │   ├── router.py             # Domain routing logic & inference runner
    │   ├── requirements.txt      # Python dependencies
    │   └── Dockerfile            # Containerization instructions
    └── frontend/                 # Frontend Web Client
        ├── index.html            # Authentication Page (Login/Registration)
        ├── classify.html         # Interactive Analysis Terminal
        ├── app.js                # Core JS logic & Firebase client integration
        └── firebase_config.js    # Firebase App configuration details
```

---

## 1. Model Development (Model_Development/)

The Model Development module documents the process of analyzing, preprocessing, and training news classification models across the four domains:

* Domains & Datasets:
    * COVID-19: Balanced dataset containing health and pandemic-related articles (6,420 train, 2,140 validation, 2,140 test samples).
    * GossipCop: Entertainment news and celebrity gossip articles from FakeNewsNet (16,817 real, 5,323 fake samples).
    * LIAR: Short political statements (10,240 train, 1,284 validation, 1,267 test samples).
    * PolitiFact: Political articles and fact-checking statements from FakeNewsNet (624 real, 432 fake samples).

* Methodology & Feature Extraction:
    * Classical Text Representations: Bag of Words (BoW CountVectorizer), N-Grams (Uni + Bi-Gram combined features), TF-IDF (TfidfVectorizer), and POS-tag features combined with BoW.
    * Pre-trained Word Embeddings: Word2Vec (Google News 300D), FastText (cc.en.300.bin), and GloVe (100D and 300D).
    * Self-trained Embeddings: Skip-gram and CBOW Word2Vec architectures trained on the cleaned corpus.
    * Hybrid Embeddings: TF-IDF weighted Word2Vec.
    * Contextual/Transformer Embeddings: BERT-base-uncased (768D), ALBERT-base-v2 (768D), and RoBERTa-base (768D).

* Model Evaluation (5-Fold Cross-Validation):
    * Classical algorithms: Logistic Regression (LR), Support Vector Machine (SVM with Linear and RBF kernels), Naive Bayes (MNB), and Random Forest (RF).
    * Fine-tuned transformer models: BERT, ALBERT, and RoBERTa (trained with learning rate 2e-5, batch size 16, AdamW optimizer, early stopping).
    * Findings: Fine-tuned RoBERTa models achieved the highest accuracy across three of the four datasets: COVID-19 (97.71% accuracy), LIAR (66.19% accuracy), and GossipCop (80.30% accuracy). For PolitiFact, RoBERTa achieved 90.00% accuracy.

---

## 2. Web Application (Web_Application/)

### Backend API (Web_Application/backend/)

The backend is built with FastAPI to support asynchronous, high-throughput model inference.

* Text Preprocessing (preprocess.py): Before running inference, text goes through a clean-up pipeline:
    * Lowercasing, stripping, HTML tag removal, and URL removal.
    * Punctuation removal and translation of emojis to text using the emoji library.
    * Replacing slang terms via internet-words-remover.
    * Stopword removal (nltk) and double-check lemmatization (verb + noun forms) via WordNetLemmatizer.
* Domain Routing (router.py): Underneath a single /classify endpoint, the system automatically routes the text to the correct model:
    * Uses keyword heuristic scoring for COVID-19, GossipCop, and Political classes.
    * If political, short statements (under 80 words) are routed to the LIAR RoBERTa model, while longer articles are routed to the Politifact RoBERTa model.
    * Loads models locally via transformers from the models/ directory in safetensors format, runs PyTorch inference, and collects memory garbage immediately post-inference.
* Firebase Integration (database.py & main.py):
    * Secured via Firebase Admin SDK (verifies Firebase ID Tokens).
    * Keeps track of:
        * User credentials & profile syncing (/sync-user, /profile).
        * Classification History (/history) pushed to Firebase Realtime Database.
        * Training dataset submissions (/submit-training), crowdsourced community submissions (/submit-community), and flaggings (/flag-result).
* Deployment: Dockerized (Dockerfile) for easy container deployment.

### Frontend Client (Web_Application/frontend/)

A single-page-app feel styled with custom cyber/futuristic aesthetics (support for Dark Mode and Light Mode).

* index.html: Entry point handling user sessions, logins, and registrations. Supports Email/Password authentication as well as Sign in with Google via Firebase Auth.
* classify.html: The main Analysis Terminal:
    * Features a character counter and real-time character limit enforcement (up to 5000 characters).
    * Simulates pipeline execution steps (Preprocessing, Language Check, Domain Detection, Inference) using animations.
    * Visualizes model outputs with custom confidence gauges.
    * Includes interactive crowdsourcing controls: flagging inaccurate verdicts, marking articles as outdated, or contributing new labeled articles to the dataset.
* app.js: Orchestrates state changes, connects directly to the backend API (https://veritas-api.mooo.com), and handles the Firebase SDK initialization.

---

## Tech Stack Summary

* Machine Learning: PyTorch, Transformers (Hugging Face), NLTK, Scikit-learn, ALBERT, RoBERTa.
* Backend API: FastAPI, Uvicorn, Pydantic, Firebase Admin SDK.
* Database: Firebase Realtime Database (RTDB).
* Frontend: HTML5 (Vanilla), CSS3 (Custom Variables, Keyframe Animations), ES6 JavaScript (Firebase Client SDK v10.12).
* Deployment: Docker.

---

## How to Get Started

### Prerequisites
* Python 3.10+

### Running the Backend Local Server
1. Navigate to the backend folder:
   ```bash
   cd Web_Application/backend
   ```
2. Set up a virtual environment and activate it:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Place your Firebase private key JSON file inside the backend/ directory named as firebase-key.json.
5. Run the FastAPI development server:
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

### Running the Frontend Local Server
1. Serve the frontend static files using a simple HTTP server:
   ```bash
   cd Web_Application/frontend
   python -m http.server 3000
   ```
2. Open http://localhost:3000 in your web browser. Ensure the API endpoint in app.js is set to point to your local backend (http://localhost:8000) if running locally.
