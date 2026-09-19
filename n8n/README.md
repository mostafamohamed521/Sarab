# n8n workflow — Sarab AI support agent

`sarab-support-workflow.json` is the complete backend for the chat page (`/pages/support/`).

```
Webhook (POST) ──► AI Agent ──► Respond to Webhook  → { "reply": "..." }
                    ├─ OpenAI Chat Model   (LLM)
                    ├─ Window Buffer Memory (keyed by session_id → remembers the conversation)
                    └─ Tools: get_my_orders · get_my_reservations · search_menu
```

## Import & configure (5 minutes)
1. n8n → **Workflows → Import from file** → pick `sarab-support-workflow.json`.
2. Open **OpenAI Chat Model** → choose/create your OpenAI credential. (Any chat-model node works:
   delete this node and connect e.g. an Anthropic Chat Model to the agent's *Chat Model* input.)
3. In the three tool nodes (`get_my_orders`, `get_my_reservations`, `search_menu`) replace
   `YOUR-USERNAME.pythonanywhere.com` with your real site address.
4. **Activate** the workflow (top-right toggle). Only the *Production URL* works when active —
   the *Test URL* only works while you click "Listen for test event".
5. Copy the Webhook's **Production URL** into the site's `.env`:
   `N8N_WEBHOOK_URL=https://<your-instance>/webhook/sarab-support`

## Request / response contract
Request (POST, JSON):
```json
{ "message": "Where is my order?", "session_id": "k3j2…", "auth_token": "optional", "user_name": "optional" }
```
Response: `{ "reply": "…" }`

`auth_token` / `user_name` are only sent for logged-in customers; the agent then calls the site's own
REST API **as that customer** (`Authorization: Token …`), so it can only ever see their own orders.
Guests are asked to log in for account questions.

## Quick test (from any terminal)
```bash
curl -X POST "https://<your-instance>/webhook/sarab-support" \
  -H "Content-Type: application/json" \
  -d '{"message":"What are your delivery hours?","session_id":"test-1"}'
# follow-up in the same session — the agent should remember the context:
curl -X POST "https://<your-instance>/webhook/sarab-support" \
  -H "Content-Type: application/json" \
  -d '{"message":"and on Fridays?","session_id":"test-1"}'
# off-topic — should be politely declined:
curl -X POST "https://<your-instance>/webhook/sarab-support" \
  -H "Content-Type: application/json" \
  -d '{"message":"Write me a poem about the moon","session_id":"test-1"}'
```

## CORS (needed only for `SUPPORT_CHAT_MODE=browser`)
The Webhook node is imported with **Options → Allowed Origins = `*`**. For production change it to your
site origin, e.g. `https://YOUR-USERNAME.pythonanywhere.com`, and keep the
`Access-Control-Allow-Origin` header on the *Respond to Webhook* node in sync.
