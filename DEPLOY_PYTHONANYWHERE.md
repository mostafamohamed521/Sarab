# Deploying Sarab to PythonAnywhere (step by step)

Works on a **free "Beginner" account** (SQLite, no card needed). Use Python **3.10 – 3.12**
(Django 4.2 is not certified for 3.13). Replace `YOUR_USERNAME` everywhere.

## 0. What the project needs
| Thing | Where | Notes |
|---|---|---|
| Django site | this folder | `config.settings`, SQLite by default |
| AI chat backend | n8n (cloud/self-hosted) | import `n8n/sarab-support-workflow.json` — see `n8n/README.md` |
| Settings | `.env` next to `manage.py` | loaded automatically, copy from `.env.example` |

## 1. Upload the code
- **Files** tab → *Upload a file* → `sarab.zip`, then in a **Bash console**:
  ```bash
  cd ~ && unzip -q sarab.zip && cd sarab      # (if the zip made a folder, cd into it)
  ```
  (or `git clone <your-repo> sarab` if you push it to GitHub.)

## 2. Configure & install (Bash console, inside `~/sarab`)
```bash
cp .env.example .env
nano .env          # set DJANGO_SECRET_KEY, DJANGO_ALLOWED_HOSTS, N8N_WEBHOOK_URL, SUPPORT_CHAT_MODE ...
PYVER=3.12 bash deploy/pa_setup.sh
```
Generate a secret key with: `python -c "import secrets; print(secrets.token_urlsafe(50))"`

The script creates the virtualenv `~/.virtualenvs/sarab`, installs `requirements.txt`, runs `migrate`
and `collectstatic`. Then, **first time only**:
```bash
source ~/.virtualenvs/sarab/bin/activate
python manage.py seed_data          # demo menu, categories, promo codes (optional)
python manage.py createsuperuser    # your own admin login
```
> ⚠️ `seed_data` also creates demo accounts with public passwords (e.g. `admin@sarab.com / admin123`).
> On a public site **change those passwords or delete the accounts** in `/admin/`.

## 3. Web tab
1. **Add a new web app → Manual configuration →** same Python version as `PYVER`.
2. **Source code:** `/home/YOUR_USERNAME/sarab`  ·  **Working directory:** same.
3. **Virtualenv:** `/home/YOUR_USERNAME/.virtualenvs/sarab`
4. **WSGI configuration file:** replace its content with `deploy/pythonanywhere_wsgi.py`
   (edit `YOUR_USERNAME`).
5. **Static files** (two rows):
   | URL | Directory |
   |---|---|
   | `/static/` | `/home/YOUR_USERNAME/sarab/staticfiles` |
   | `/media/`  | `/home/YOUR_USERNAME/sarab/media` |
6. Turn on **Force HTTPS**, then press the green **Reload** button.

Open `https://YOUR_USERNAME.pythonanywhere.com` — done.

## 4. AI support chat: free vs paid accounts (important)
Free PythonAnywhere accounts can only call an allow-listed set of sites **from the server**, and
`*.n8n.cloud` is not on it. So:

| Your plan | Set in `.env` | What happens |
|---|---|---|
| **Free** | `SUPPORT_CHAT_MODE=browser` | The visitor's browser calls the n8n webhook directly (CORS is enabled in the workflow). Works out of the box. |
| **Paid** | `SUPPORT_CHAT_MODE=server` | Browser → Django `/pages/support/chat/` → n8n. Keeps the webhook URL private and adds a per-IP rate limit. |

Also remember n8n must reach **your** site for the order/reservation tools — that direction
(n8n → PythonAnywhere) always works.

After changing `.env` press **Reload** on the Web tab.

## 5. Smoke test (2 minutes)
- [ ] Home page loads with styles/images (if not: static mapping / `collectstatic`).
- [ ] Open the site on your phone (or Chrome DevTools → device toolbar): no sideways scrolling, menu opens, cart drawer fits.
- [ ] *Pages ▸ Customer Support* (also in the footer) opens the chat; click a suggestion chip → bubble + AI answer.
- [ ] Ask a follow-up ("and on Fridays?") → agent remembers the context (session memory).
- [ ] Ask something off-topic → politely declined.
- [ ] Log in, ask "where is my last order?" → answer uses your real order.

## 6. Updating the site later
```bash
cd ~/sarab && git pull            # or upload/unzip the new files
bash deploy/pa_setup.sh           # installs deps, migrates, collects static
```
then **Reload** the web app.

## Troubleshooting
| Symptom | Fix |
|---|---|
| `DisallowedHost` / Bad Request (400) | add the domain to `DJANGO_ALLOWED_HOSTS` in `.env`, Reload |
| CSRF verification failed on login/chat | set `DJANGO_CSRF_TRUSTED_ORIGINS=https://YOUR_USERNAME.pythonanywhere.com` |
| Site unstyled / images missing | Web-tab static mapping wrong, or `collectstatic` not run |
| Chat says *problem connecting…* (server mode) | free plan can't reach n8n → use `SUPPORT_CHAT_MODE=browser`, or check the workflow is **Active** and the URL is the *Production* one |
| Chat says *Network error* (browser mode) | CORS: Webhook node → Options → Allowed Origins must include your site; workflow must be Active |
| Anything else | Web tab → **Error log** (and Server log) — the last lines name the problem |
| Free app "expired" | Web tab → *Run until 3 months from today* (free apps need a periodic click) |
| Stripe payments fail on free plan | outbound calls to Stripe are blocked on free accounts — use Cash on Delivery for the demo, or upgrade |

## Security notes
- Never commit `.env` (already in `.gitignore`); `DJANGO_DEBUG` must stay `False` in production.
- Django 4.2 LTS reached end-of-life in April 2026 (see `CHANGELOG.md`, section A06) — plan an upgrade to
  Django 5.2 LTS for long-lived deployments; it's fine for a course/demo site.
