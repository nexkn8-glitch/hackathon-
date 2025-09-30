# Insecure Web App (DVWA-like) — For Hackathons & Training

**WARNING: This app is intentionally vulnerable. Do NOT expose it to the public internet without strict controls.**
Use in isolated lab VMs or cloud with firewall rules.

## Features & Vulnerabilities Included
- **Weak Authentication & MD5 Passwords**
- **SQL Injection** in `/login` and `/register` and `/profile` queries
- **Stored XSS** in comments on `/dashboard`
- **Reflected XSS** via `?q=` on `/`
- **IDOR** on `/profile?id=` and weak admin gate on `/admin?admin=1`
- **Insecure File Upload** at `/upload` (serves uploaded files directly)
- **Command Injection** at `/ping` (shell=True)
- **SSRF** at `/fetch` (arbitrary URL fetch)
- **Missing CSRF** across forms
- **Insecure Cookies & Headers**

Seeded users (MD5-hashed):
- `admin` / `admin123` (is_admin=1)
- `alice` / `password`
- `bob` / `123456`

Hidden flags (example scoring):
- `FLAG{IDOR_LEAK_ALICE}` — view Alice's secret via `/profile?id=2`
- `FLAG{IDOR_LEAK_BOB}` — view Bob's secret via `/profile?id=3`

## Quick Start (Local)
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python app.py
# Visit http://127.0.0.1:5000
```

## Docker
```bash
docker build -t insecure-webapp .
docker run -p 5000:5000 insecure-webapp
```

## Docker Compose
```bash
docker-compose up --build
```

## Cloud Deployment (Single VM)
1. Create Ubuntu VM (AWS/Azure/GCP/Oracle).
2. Install Docker & Docker Compose.
3. `git clone` this repo to the VM.
4. `docker-compose up -d --build`
5. Point DNS (e.g., `hack.yourdomain.com`) to the VM's public IP.
6. **Firewall:** Allow TCP/5000 only for student IP ranges if possible.

## Safety Notes
- Reset or destroy the VM after your event.
- Never reuse this VM for production.
- Consider putting it behind a reverse proxy that can block DoS.
- Optional: snapshot the VM so you can restore between rounds.

## Customization Tips (to prevent copy-paste reports)
- Change seeded usernames/passwords.
- Edit templates text/branding.
- Add or remove routes.
- Hide extra flags or change their names/content.
- Add simple WAF-style challenges (e.g., naive regex filters) and let students bypass them.

## Routes Overview
- `/` — Home + reflected XSS via `?q=`
- `/register` — Register (SQLi)
- `/login` — Login (SQLi)
- `/logout` — Logout
- `/dashboard` — Post/read comments (Stored XSS)
- `/profile?id=` — View profiles (IDOR + secret notes)
- `/upload` — Insecure upload (serves files at `/static/uploads/<file>`)
- `/ping` — Command injection
- `/fetch` — SSRF
- `/admin` — Admin panel (weak gate; `?admin=1` bypass)

## Educational Use
- Have students find, exploit, and **write a report** with: description, PoC, impact, mitigation.
- Score by severity + report quality.
