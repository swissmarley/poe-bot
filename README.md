# Poe Server Bot on Modal (Quick Setup)

This guide covers only the **Poe + Modal** setup to run a Poe **Server Bot** deployed on **Modal**.

---

## 1) Create the Poe Server Bot

1. In Poe, go to **Create Bot** → choose **Server Bot**.
2. Set your **Bot Name** (example: `MyInboxBot`).
3. Create/Copy the **Access Key** (keep it secret).
4. Leave **Server URL** empty for now (you’ll paste the Modal URL after deploy).

> Poe authenticates requests to your server with: `Authorization: Bearer <ACCESS_KEY>`.

---

## 2) Install + Authenticate Modal (CLI)

Install:
```bash
pip install modal
```

Login (fixes “Token missing”):
```bash
modal token new
```

Verify:
```bash
modal whoami
```

---

## 3) Create Modal Secret (stores Poe key + config)

Create a Modal secret in the same Modal environment you deploy to (usually `main`):

```bash
modal secret create poe-n8n-bot   POE_ACCESS_KEY="YOUR_POE_ACCESS_KEY"   POE_BOT_NAME="YOUR_POE_BOT_NAME"   N8N_WEBHOOK_URL="https://YOUR_N8N_DOMAIN/webhook/poe/inbox"   POE_N8N_SHARED_SECRET="YOUR_LONG_RANDOM_SECRET"
```

List secrets:
```bash
modal secret list
```

Update values (safe approach):
```bash
modal secret delete poe-n8n-bot
modal secret create poe-n8n-bot ...
```

---

## 4) Deploy the bot to Modal

From the folder that contains `main.py`:

```bash
modal deploy main.py
```

Modal prints a public HTTPS URL for your server.

(Optional) View logs:
```bash
modal app logs -f poe-n8n-trigger-bot
```

---

## 5) Connect Poe to Modal

Back in Poe bot settings:

- **Server URL** = Modal URL printed by `modal deploy`
- **Access Key** = must match `POE_ACCESS_KEY` stored in the Modal secret

Save the bot.

---

## 6) Quick Troubleshooting

- **“Token missing” (Modal):**
  ```bash
  modal token new
  ```

- **Poe shows “unexpected issue”:**
  ```bash
  modal app logs -f poe-n8n-trigger-bot
  ```

- **Secret not found in environment `main`:**
  Create the secret in `main` (or switch environment) and redeploy.

---
