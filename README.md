# Poe → Modal → n8n Trigger Bot (Server Bot)

This project creates a **Poe Server Bot** hosted on **Modal**.  
When a user sends a message to the bot in Poe, the bot forwards the message to an **n8n Webhook** to start an automation workflow, then returns n8n’s response back to the user in Poe.

---

## Architecture

```
User (Poe) → Poe Server Bot (Modal) → n8n Webhook Trigger → Workflow → JSON reply → Modal → Poe
```

**Security layers**
- **Poe → Modal:** authenticated with **Poe Access Key** (Bearer token)
- **Modal → n8n:** authenticated with a **shared secret header** (`x-poe-n8n-secret`)

---

## Prerequisites

- A Poe account (to create a Server Bot)
- A Modal account (to host the bot server)
- An n8n instance (self-hosted or cloud) reachable via HTTPS with a Production Webhook URL

---

## 1) Create the n8n Workflow

### 1.1 Add Webhook Trigger
1. In n8n create a new workflow
2. Add node: **Webhook**
   - Method: `POST`
   - Path: `poe/inbox` (example)
   - Response mode: **When Last Node Finishes** *(recommended while building)*

3. Activate the workflow (**Active = ON**)
4. Copy the **Production URL** from the Webhook node  
   Example:
   ```
   https://n8n.yourdomain.com/webhook/poe/inbox
   ```

### 1.2 Add Auth check (shared secret)
Add a **Code** node right after Webhook and validate a secret header:

```js
const EXPECTED = "YOUR_LONG_RANDOM_SECRET";
const got = $json.headers?.["x-poe-n8n-secret"] || $json.headers?.["X-Poe-N8n-Secret"];

if (!got || got !== EXPECTED) {
  throw new Error("Unauthorized: missing/invalid x-poe-secret");
}

return items;
```

> Note: Some n8n setups deny `$env` access inside Code nodes. This approach avoids `$env` entirely.

### 1.3 Return a reply to Modal/Poe
At the end of your workflow, ensure the final node returns JSON with a `reply` field:

```json
{ "reply": "✅ Saved." }
```

---

## 2) Create the Poe Server Bot

### 2.1 Register / Login
Go to Poe and login with your account.

### 2.2 Create a Server Bot
1. Create a new bot and choose **Server Bot**
2. Set a **Bot Name** (e.g. `MyInboxBot`)
3. Generate and copy the **Access Key** (a long secret string)

**Important:** The Access Key is used by your Modal server to validate Poe requests.
Store it securely (Modal secret).

---

## 3) Set up Modal

### 3.1 Install Modal CLI
```bash
pip install modal
```

### 3.2 Authenticate Modal
If you see “Token missing”, run:

```bash
modal token new
```

Verify:
```bash
modal whoami
```

### 3.3 Create a Modal Secret (recommended)
Create a secret in the **same Modal environment** you deploy to (often `main`).

```bash
modal secret create poe-n8n-bot \
  POE_ACCESS_KEY="YOUR_POE_ACCESS_KEY" \
  POE_BOT_NAME="YOUR_POE_BOT_NAME" \
  N8N_WEBHOOK_URL="https://n8n.yourdomain.com/webhook/poe/inbox" \
  POE_N8N_SHARED_SECRET="YOUR_LONG_RANDOM_SECRET"
```

List secrets:
```bash
modal secret list
```

> If you deploy in environment `main`, the secret must exist in `main`.  
> Modal secrets are **environment-scoped**.

---

---

## 4) Deploy to Modal

```bash
modal deploy main.py
```

Modal will output a public URL (your bot server endpoint).

---

## 5) Connect Poe → Modal

In Poe bot settings:
- Set **Server URL** to the Modal URL from deployment
- Ensure the **Access Key** in Poe matches `POE_ACCESS_KEY` stored in Modal secret

Save.

---

## ) Test End-to-End

### 7.1 Test n8n webhook directly (recommended)
```bash
curl -v -X POST "https://n8n.yourdomain.com/webhook/poe/inbox" \
  -H "Content-Type: application/json" \
  -H "x-poe-n8n-secret: YOUR_LONG_RANDOM_SECRET" \
  -d '{"text":"hello from curl"}'
```

Expected: JSON response containing `reply` or your workflow output.

### 7.2 Test Poe bot
Message your Poe bot:
- `Task: submit expenses by Friday`
- `Remind me to call mom`

Expected:
- Poe shows “Got it — sending to n8n…”
- then the `reply` returned by n8n

---

## Secrets & Token Handling (Best Practices)

### Modal token (local machine)
If you see “Token missing”, authenticate:
```bash
modal token new
```

### Modal secrets
- Secrets are **environment-scoped** (e.g., `main`, `dev`)
- If you deploy in `main`, the secret must exist in `main`
- Update secrets via dashboard or delete+recreate:

```bash
modal secret delete poe-bot
modal secret create poe-bot ...
```

### Never commit secrets
Do NOT commit secrets into git. Keep them in Modal secrets and/or local `.env`.

---

## Troubleshooting

### Poe says: “The bot encountered an unexpected issue”
Check Modal logs:
```bash
modal app logs -f poe-trigger-bot
```

### n8n webhook works with curl but not from Modal
This is usually Cloudflare/WAF/firewall blocking Modal IPs. Allow POST to `/webhook/*`.

### n8n error: “Unused Respond to Webhook node found”
- Either delete unused Respond nodes, OR
- Ensure every branch ends in a Respond to Webhook node if Webhook uses that response mode.

---

## License
Personal / educational use.
