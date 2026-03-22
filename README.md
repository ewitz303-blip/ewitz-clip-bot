# Ewitz Clip Bot

AI short-form video editor. Paste a YouTube link, pick a vibe, get viral-ready clips with live synced captions — built for TikTok and Instagram Reels.

---

## How to start

Double-click **start.command** in this folder.

That's it. A terminal opens, the app starts, your ngrok URL prints. Send that URL to anyone — works from any device anywhere.

---

## Folder structure

```
ewitz-clip-bot/
├── start.command        ← launch the app (double-click this)
├── app.py               ← all the backend logic
├── requirements.txt     ← Python packages needed
├── .env                 ← your Anthropic API key (keep this private)
├── templates/
│   └── index.html       ← the UI
├── downloads/           ← YouTube videos download here (auto-managed)
└── outputs/             ← your rendered clips save here
```

---

## First time setup (if starting fresh)

```bash
cd ~/CLaude\ Learning/ewitz-clip-bot
pip3 install -r requirements.txt
```

Make sure `.env` has your Anthropic API key:
```
ANTHROPIC_API_KEY=your_key_here
```

---

## What it does

- Downloads any YouTube video + subtitles
- Reads YouTube's most-replayed heatmap to find peak moments
- Claude AI picks the best 8–15 clips based on your selected mood
- Flips video horizontally (copyright bypass)
- Blur bars format — full video visible, 9:16 vertical
- Live synced captions burned into every clip
- Preview and download each clip individually
