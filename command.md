# cost? and diagram of each 4 layers how they work in dashboard? and ablation 
Step 1 — Create ClearMint prospect + send initial email


curl -s -X POST http://127.0.0.1:8000/pipeline/run \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "ClearMint",
    "company_domain": "clearmint.io",
    "contact_name": "Amara Cole",
    "contact_email": "nurye.nigus.me@gmail.com",
    "contact_phone": "+251929404324"
  }' | python3 -m json.tool | grep prospect_id
Step 2 — Pricing question → professional pricing reply


curl -s -X POST http://127.0.0.1:8000/conversations/reply \
  -H "Content-Type: application/json" \
  -d '{
    "prospect_id": "PROSPECT_ID",
    "contact_email": "nurye.nigus.me@gmail.com",
    "contact_phone": "+251929404324",
    "channel": "email",
    "body": "What are your rates? How much does this cost?"
  }' | python3 -m json.tool | grep -E "next_action|risk_flags"
Step 3 — Meeting request → booking link via email + SMS to AT simulator


curl -s -X POST http://127.0.0.1:8000/conversations/reply \
  -H "Content-Type: application/json" \
  -d '{
    "prospect_id": "PROSPECT_ID",
    "contact_email": "nurye.nigus.me@gmail.com",
    "contact_phone": "+251929404324",
    "channel": "email",
    "body": "I would like to schedule a discovery call"
  }' | python3 -m json.tool | grep -E "next_action|risk_flags"
Step 4 — General follow-up → professional follow-up reply only


curl -s -X POST http://127.0.0.1:8000/conversations/reply \
  -H "Content-Type: application/json" \
  -d '{
    "prospect_id": "PROSPECT_ID",
    "contact_email": "nurye.nigus.me@gmail.com",
    "contact_phone": "+251929404324",
    "channel": "email",
    "body": "Thanks for the context, just checking in"
  }' | python3 -m json.tool | grep -E "next_action|risk_flags"
Step 5 — Prospect asks to be texted → auto SMS booking link


curl -s -X POST http://127.0.0.1:8000/conversations/reply \
  -H "Content-Type: application/json" \
  -d '{
    "prospect_id": "PROSPECT_ID",
    "contact_email": "nurye.nigus.me@gmail.com",
    "contact_phone": "+251929404324",
    "channel": "email",
    "body": "Can you text me the booking details?"
  }' | python3 -m json.tool | grep -E "next_action|risk_flags"
Step 6 — Stop → professional unsubscribe email


curl -s -X POST http://127.0.0.1:8000/conversations/reply \
  -H "Content-Type: application/json" \
  -d '{
    "prospect_id": "PROSPECT_ID",
    "contact_email": "nurye.nigus.me@gmail.com",
    "contact_phone": "+251929404324",
    "channel": "email",
    "body": "stop"
  }' | python3 -m json.tool | grep -E "next_action|needs_human|reply_draft"