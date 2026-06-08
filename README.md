# Telegram Copy Bot

Telegram bot that watches a source channel and publishes new posts to a target channel.

## Local run

1. Create a `.env` file from `.env.example`.
2. Install dependencies:

```powershell
pip install -r requirements.txt
```

3. Start the bot:

```powershell
python main.py
```

## Deploy on Render

This project is prepared for Render as a background worker with `render.yaml`.

Required environment variables:

- `BOT_TOKEN`
- `SOURCE_CHANNEL`
- `TARGET_CHANNEL`
- `TG_API_ID`
- `TG_API_HASH`
- `TG_SESSION_STRING`

Optional:

- `REVIEW_CHANNEL_ID`
- `AI_API_KEY`
- `CLONE_TEMPLATE_MEDIA_MODE`
- `TEMPLATE_IMAGE_LIVE`
- `TEMPLATE_IMAGE_GOAL`
- `CLONE_TARGET_CURRENCY`
- `CLONE_STAKE_TEMPLATES`

Notes:

- AI is enabled in config, but it requires a valid `AI_API_KEY`.
- The source channel can be a username like `@channel_name` or an ID like `-100...`.
- Runtime state is stored in the local `data/` folder. Without a persistent disk on Render, this state resets after redeploys or restarts.
- `CLONE_TEMPLATE_MEDIA_MODE=true` keeps the source text nearly unchanged, swaps promo/link to the target values, and replaces source media with local template images.
- `CLONE_TARGET_CURRENCY` and `CLONE_STAKE_TEMPLATES` let clone channels localize the stake line, for example changing `600CAD` into a Portuguese or Italian `EUR` phrase while keeping the same amount.
