// ─────────────────────────────────────────────
// VERITAS — app.js
// ─────────────────────────────────────────────
import { initializeApp }          from "https://www.gstatic.com/firebasejs/10.12.0/firebase-app.js";
import { getAuth,
         signInWithEmailAndPassword,
         createUserWithEmailAndPassword,
         signInWithPopup,
         GoogleAuthProvider,
         updateProfile,
         signOut,
         onAuthStateChanged }     from "https://www.gstatic.com/firebasejs/10.12.0/firebase-auth.js";

const firebaseConfig = {
  apiKey:            "AIzaSyDbnEQbZ7QrK3nAKub8D3VzN3Xl66kekeU",
  authDomain:        "fake-news-detection-adc5e.firebaseapp.com",
  projectId:         "fake-news-detection-adc5e",
  storageBucket:     "fake-news-detection-adc5e.firebasestorage.app",
  messagingSenderId: "671109739686",
  appId:             "1:671109739686:web:03213466ec13ae3dd87067",
  measurementId:     "G-KNEN46W67C"
};

const firebaseApp = initializeApp(firebaseConfig);
const auth        = getAuth(firebaseApp);
const provider    = new GoogleAuthProvider();
const API         = "https://veritas-api.mooo.com";

const isLoginPage    = document.getElementById('login')     !== null;
const isClassifyPage = document.getElementById('inputText') !== null;

// ─────────────────────────────────────────────
// Auth helpers
// ─────────────────────────────────────────────
async function getToken() {
  const user = auth.currentUser;
  if (!user) throw new Error("Not authenticated");
  return await user.getIdToken(true);
}

async function apiFetch(path, options = {}) {
  const token = await getToken();
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 120000); // 2 minutes
  try {
    const res = await fetch(`${API}${path}`, {
      ...options,
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`,
        ...(options.headers || {})
      }
    });
    clearTimeout(timeout);
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    return res.json();
  } catch (e) {
    clearTimeout(timeout);
    throw e;
  }
}

async function syncUserToBackend(user) {
  try {
    const token = await user.getIdToken(true);
    await fetch(`${API}/sync-user`, {
      method:  "POST",
      headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
      body: JSON.stringify({
        email:    user.email,
        username: user.displayName || user.email.split('@')[0]
      })
    });
  } catch (e) {
    console.warn("[VERITAS] Could not sync user:", e);
  }
}

function showFormError(id, msg) {
  const el = document.getElementById(id);
  if (el) { el.textContent = "⚠ " + msg; el.style.display = "block"; }
}
function hideFormError(id) {
  const el = document.getElementById(id);
  if (el) el.style.display = "none";
}

// ─────────────────────────────────────────────
// INDEX.HTML
// ─────────────────────────────────────────────
if (isLoginPage) {
  onAuthStateChanged(auth, user => { if (user) window.location.href = "classify.html"; });

  window.handleLogin = async function () {
    hideFormError('login-err');
    const email = document.getElementById('login-email').value.trim();
    const pass  = document.getElementById('login-pass').value;
    if (!email || !pass) { showFormError('login-err', 'Please fill in all fields.'); return; }
    try {
      const result = await signInWithEmailAndPassword(auth, email, pass);
      await syncUserToBackend(result.user);
      window.location.href = "classify.html";
    } catch (e) {
      showFormError('login-err', e.code === 'auth/invalid-credential'
        ? 'Invalid email or password.' : 'Login failed. Try again.');
    }
  };

  window.handleRegister = async function () {
    hideFormError('reg-err');
    const username = document.getElementById('reg-user').value.trim();
    const email    = document.getElementById('reg-email').value.trim();
    const pass     = document.getElementById('reg-pass').value;
    if (!username || !email || pass.length < 8) {
      showFormError('reg-err', 'Fill all fields. Password min 8 chars.'); return;
    }
    try {
      const result = await createUserWithEmailAndPassword(auth, email, pass);
      await updateProfile(result.user, { displayName: username });
      await syncUserToBackend(result.user);
      window.location.href = "classify.html";
    } catch (e) {
      showFormError('reg-err', e.code === 'auth/email-already-in-use'
        ? 'Email already registered.' : 'Registration failed. Try again.');
    }
  };

  window.handleGoogle = async function () {
    try {
      const result = await signInWithPopup(auth, provider);
      await syncUserToBackend(result.user);
      window.location.href = "classify.html";
    } catch (e) {
      showFormError('login-err', 'Google sign-in failed. Try again.');
    }
  };
}

// ─────────────────────────────────────────────
// CLASSIFY.HTML
// ─────────────────────────────────────────────
if (isClassifyPage) {

  // Cached profile data loaded from RTDB on login
  let cachedProfile = { display_name: '', avatar_url: '' };

  onAuthStateChanged(auth, async user => {
    if (!user) {
      window.location.href = "index.html";
    } else {
      // Load profile from RTDB first, then update UI
      try {
        cachedProfile = await apiFetch('/profile');
      } catch (e) {
        console.warn("[VERITAS] Could not load profile:", e);
      }
      refreshNavUser(user);
      loadHistory();
    }
  });

  // ── Update navbar + avatar from RTDB profile ──
  function refreshNavUser(user) {
    const name = cachedProfile.display_name || user.displayName || user.email.split('@')[0];
    const navUser = document.getElementById('navUser');
    if (navUser) navUser.textContent = `⬡ ${name.toUpperCase()}`;

    const avatar = document.getElementById('profileAvatar');
    if (avatar) setAvatarEl(avatar, name, cachedProfile.avatar_url);
  }

  function setAvatarEl(el, name, avatarUrl) {
    if (avatarUrl) {
      el.innerHTML = `<img src="${avatarUrl}" style="width:100%;height:100%;object-fit:cover;border-radius:50%;">`;
    } else {
      el.textContent = (name || '?').charAt(0).toUpperCase();
    }
  }

  // ── Open profile modal ──
  window.openProfile = function () {
    const user = auth.currentUser;
    if (!user) return;

    const name = cachedProfile.display_name || user.displayName || user.email.split('@')[0];

    document.getElementById('profileDisplayName').textContent = name.toUpperCase();
    document.getElementById('profileEmail').textContent       = user.email;
    document.getElementById('editUsername').value             = name;

    const avatar = document.getElementById('profileAvatar');
    setAvatarEl(avatar, name, cachedProfile.avatar_url);

    // Add pfp upload area once
    if (!document.getElementById('pfpUploadArea')) {
      const uploadHTML = `
        <div id="pfpUploadArea" style="text-align:center;margin-bottom:1rem;">
          <label for="pfpInput" style="
            display:inline-block;cursor:pointer;
            font-family:'Share Tech Mono',monospace;font-size:0.65rem;
            letter-spacing:0.15em;color:var(--dim);
            border:1px dashed var(--border);padding:0.5rem 1rem;transition:all 0.3s;
          " onmouseover="this.style.borderColor='var(--cyan)';this.style.color='var(--cyan)'"
             onmouseout="this.style.borderColor='var(--border)';this.style.color='var(--dim)'">
            ⬡ UPLOAD PROFILE IMAGE
          </label>
          <input type="file" id="pfpInput" accept="image/*" style="display:none;">
          <div id="pfpMsg" style="font-family:'Share Tech Mono',monospace;font-size:0.6rem;color:var(--dim);margin-top:0.4rem;"></div>
        </div>`;
      document.querySelector('.edit-field').insertAdjacentHTML('beforebegin', uploadHTML);
      document.getElementById('pfpInput').addEventListener('change', handlePfpSelect);
    }

    document.getElementById('saveMsg').style.display = 'none';
    document.getElementById('profileOverlay').classList.add('open');
    document.getElementById('profileMenu').classList.remove('open');
  };

  // Holds the newly selected image until Save is clicked
  let pendingAvatarBase64 = null;

  function handlePfpSelect(e) {
    const file = e.target.files[0];
    if (!file) return;
    if (file.size > 2 * 1024 * 1024) {
      document.getElementById('pfpMsg').textContent = '⚠ Image must be under 2MB';
      document.getElementById('pfpMsg').style.color = 'var(--magenta)';
      return;
    }
    const reader = new FileReader();
    reader.onload = ev => {
      pendingAvatarBase64 = ev.target.result;
      // Preview immediately
      const avatar = document.getElementById('profileAvatar');
      avatar.innerHTML = `<img src="${pendingAvatarBase64}" style="width:100%;height:100%;object-fit:cover;border-radius:50%;">`;
      document.getElementById('pfpMsg').textContent = '✓ Image selected — click Save Changes';
      document.getElementById('pfpMsg').style.color = 'var(--cyan)';
    };
    reader.readAsDataURL(file);
  }

  // ── Save profile to RTDB via backend ──
  window.saveProfile = async function () {
    const user    = auth.currentUser;
    if (!user) return;

    const newName = document.getElementById('editUsername').value.trim();
    const saveMsg = document.getElementById('saveMsg');

    if (!newName) {
      saveMsg.textContent   = '⚠ Display name cannot be empty';
      saveMsg.style.color   = 'var(--magenta)';
      saveMsg.style.display = 'block';
      return;
    }

    try {
      // Save to RTDB via backend
      await apiFetch('/profile', {
        method: 'POST',
        body: JSON.stringify({
          display_name: newName,
          avatar_url:   pendingAvatarBase64 ?? cachedProfile.avatar_url
        })
      });

      // Also update Firebase Auth displayName
      await updateProfile(user, { displayName: newName });

      // Update local cache
      cachedProfile.display_name = newName;
      if (pendingAvatarBase64) cachedProfile.avatar_url = pendingAvatarBase64;
      pendingAvatarBase64 = null;

      // Refresh UI
      document.getElementById('profileDisplayName').textContent = newName.toUpperCase();
      refreshNavUser(user);

      saveMsg.textContent   = '✓ Profile saved — persists across all browsers';
      saveMsg.style.color   = 'var(--green)';
      saveMsg.style.display = 'block';
      setTimeout(() => saveMsg.style.display = 'none', 3000);

    } catch (e) {
      saveMsg.textContent   = '⚠ Failed to save: ' + e.message;
      saveMsg.style.color   = 'var(--magenta)';
      saveMsg.style.display = 'block';
    }
  };

  // ── Logout ──
  window.doLogout = async function () {
    await signOut(auth);
    window.location.href = "index.html";
  };
  window.logout = window.doLogout;

  // ── Classify ──
  window.analyze = async function () {
    const text = document.getElementById('inputText').value.trim();
    if (!text) return;

    document.getElementById('analyzeBtn').disabled = true;
    document.getElementById('resultTag').textContent = 'PROCESSING...';
    showState('loading');
    animateLoading();

    try {
      const result = await apiFetch('/classify', {
        method: "POST",
        body:   JSON.stringify({ text })
      });
      if (result.status === 'success') {
        showResult(result, text);
        addHistory(text, result);
      } else {
        showError(result.message || result.detail || 'Unknown error from model.');
      }
    } catch (e) {
      console.error("[VERITAS] Classify error:", e);
      showError(e.message.includes('fetch')
        ? 'Cannot connect to VERITAS backend. Is the server running on localhost:8000?'
        : e.message);
    }

    document.getElementById('analyzeBtn').disabled = false;
  };

  // ── Training data collection: feedback endpoints ──
  window.apiSubmitTraining = function (payload) {
    return apiFetch('/submit-training', { method: 'POST', body: JSON.stringify(payload) });
  };
  window.apiSubmitCommunity = function (payload) {
    return apiFetch('/submit-community', { method: 'POST', body: JSON.stringify(payload) });
  };
  window.apiFlag = function (payload) {
    return apiFetch('/flag-result', { method: 'POST', body: JSON.stringify(payload) });
  };

  // ── Load history ──
  async function loadHistory() {
    try {
      const data = await apiFetch('/history');
      if (data.history && data.history.length > 0) {
        data.history.forEach(h => addHistory(h.text, {
          domain: h.domain, label: h.label, confidence: h.confidence
        }));
      }
    } catch (e) {
      console.warn("[VERITAS] Could not load history:", e);
    }
  }
}