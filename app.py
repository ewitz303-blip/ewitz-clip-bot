"""
====================================================
SHORT-FORM VIDEO EDITING AI — Setup Instructions
====================================================
1. pip3 install -r requirements.txt
2. Add your Anthropic API key to .env (ANTHROPIC_API_KEY=your_key_here)
3. python3 app.py
4. Open browser to http://localhost:5001
====================================================
"""

import os
import json
import re
import subprocess
import tempfile
from pathlib import Path

from flask import Flask, request, jsonify, render_template, send_file
from flask_cors import CORS
from dotenv import load_dotenv
import anthropic

load_dotenv(override=True)

app = Flask(__name__)
CORS(app)

def _find_ffmpeg():
    import shutil
    if p := os.environ.get("FFMPEG_PATH"):
        return p
    if p := shutil.which("ffmpeg"):
        return p
    for candidate in ["/usr/bin/ffmpeg", "/usr/local/bin/ffmpeg", "/nix/var/nix/profiles/default/bin/ffmpeg", "/opt/homebrew/bin/ffmpeg"]:
        if os.path.exists(candidate):
            return candidate
    return "ffmpeg"
FFMPEG = _find_ffmpeg()
CAPTION_OFFSET  = 0.75  # seconds to shift captions earlier (YouTube VTT lags speech)
DOWNLOADS = Path("downloads")
OUTPUTS   = Path("outputs")
DOWNLOADS.mkdir(exist_ok=True)
OUTPUTS.mkdir(exist_ok=True)

FONT_PATHS = [
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
]
FONT_FILE = next((f for f in FONT_PATHS if Path(f).exists()), None)

DEMO_MODE = not os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY") == "your_key_here"
client    = None if DEMO_MODE else anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

CAPTION_COLORS = {
    "white":  {"pil": (255, 255, 255), "ass": "&H00FFFFFF"},
    "yellow": {"pil": (255, 230, 0),   "ass": "&H0000E6FF"},
    "red":    {"pil": (255, 60, 60),   "ass": "&H003C3CFF"},
    "cyan":   {"pil": (0, 220, 255),   "ass": "&H00FFDC00"},
    "green":  {"pil": (0, 255, 120),   "ass": "&H0078FF00"},
    "pink":   {"pil": (255, 100, 200), "ass": "&H00C864FF"},
    "orange": {"pil": (255, 160, 0),   "ass": "&H0000A0FF"},
}

def strip_emojis(text):
    """Remove emoji characters from text for clean burned-in captions."""
    emoji_pattern = re.compile(
        "[\U0001F600-\U0001F64F"
        "\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F9FF"
        "\U0001FA00-\U0001FA9F"
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "\U0001f926-\U0001f937"
        "\U00010000-\U0010ffff"
        "\u2640-\u2642\u2600-\u2B55\u200d\u23cf\u23e9\u231a\ufe0f\u3030]+",
        flags=re.UNICODE
    )
    return emoji_pattern.sub("", text).strip()

# ─────────────────────────────────────────────
# MOOD CONFIGS
# ─────────────────────────────────────────────

MOOD_CONFIGS = {
    "auto": {
        "system": "You are an expert viral short-form content creator who identifies the best style for any video.",
        "focus":  "Decide what style fits this content best (funny, emotional, hype, etc.) and find the clips that would perform best in that style. Write captions that match the natural tone of the video."
    },
    "funny": {
        "system": "You are a viral comedy content creator who specializes in TikTok humor and meme culture.",
        "focus":  "Find the FUNNIEST moments — reactions, punchlines, bloopers, awkward pauses, WTF moments. Write captions in meme language that make people laugh out loud and immediately tag their friends."
    },
    "emotional": {
        "system": "You are a heartfelt storytelling creator who makes deeply moving short-form content.",
        "focus":  "Find the most emotionally powerful moments — vulnerability, genuine emotion, breakthrough moments, real human connection. Write captions that hit people in the chest and make them want to share."
    },
    "heartfelt": {
        "system": "You are a wholesome content creator who finds the warmth and humanity in every video.",
        "focus":  "Find moments of genuine kindness, love, connection, or positivity. Write warm sincere captions that make people smile and want to share something beautiful."
    },
    "hype": {
        "system": "You are a high-energy hype content creator for sports, action, and intensity.",
        "focus":  "Find the most intense, explosive, peak-energy moments. Write captions that pump people up and make them feel like they can run through a wall."
    },
    "motivational": {
        "system": "You are a motivational content creator who helps people unlock their potential.",
        "focus":  "Find the most inspiring, mindset-shifting moments. Write captions that make people want to get up and change their life right now."
    },
    "dramatic": {
        "system": "You are a dramatic storytelling creator who makes cinematic short-form content.",
        "focus":  "Find the most intense, surprising, or plot-twist moments. Write captions with dramatic flair that keep people on the edge of their seat."
    },
    "educational": {
        "system": "You are an educational content creator who makes learning viral and shareable.",
        "focus":  "Find the most mind-blowing 'I never knew that' moments. Write captions that make people feel smart and want to share the knowledge."
    },
}

DEMO_ANALYSIS = {
    "clips": [
        {
            "id": 1, "start": "00:00:08", "end": "00:00:38",
            "reason": "Peak reaction moment — genuine shock face that's instant meme material.",
            "hook_text": "nobody saw that coming 💀",
            "caption": "nobody saw that coming 💀\n\nbro really said that out loud\n\nthe internet is not ready\n\n#fyp #comedy #viral #lmao",
            "post_description": "This reaction clip is pure gold. The timing is perfect and the expression is instantly meme-able. People will tag friends immediately.",
            "transition_in": "jump cut", "transition_out": "zoom punch",
            "confidence": 9, "virality": "viral", "mood_type": "funny"
        },
        {
            "id": 2, "start": "00:01:12", "end": "00:01:50",
            "reason": "The pause before the punchline creates perfect comedic tension.",
            "hook_text": "the pause before this 😭",
            "caption": "the pause before this 😭\n\neveryone watching: 👁👄👁\n\nhow is this even real\n\n#comedy #trending #foryou",
            "post_description": "Comedic timing is chefs kiss here. The payoff after the pause is hilarious. High save and share potential.",
            "transition_in": "whip pan", "transition_out": "zoom punch",
            "confidence": 8, "virality": "high", "mood_type": "funny"
        },
        {
            "id": 3, "start": "00:02:30", "end": "00:03:05",
            "reason": "Most relatable moment in the video — everyone has been here.",
            "hook_text": "we've all been this person 😂",
            "caption": "we've all been this person 😂\n\nno shame in the game\n\ntag someone who needs to see this\n\n#relatable #fyp #funny",
            "post_description": "Peak relatability content. People screenshot and send this in group chats saying 'THIS IS YOU.'",
            "transition_in": "cut", "transition_out": "fade",
            "confidence": 7, "virality": "high", "mood_type": "funny"
        }
    ],
    "music_suggestions": [
        {"genre": "phonk", "energy": "high", "vibe": "hard-hitting beat that builds suspense before the punchline"},
        {"genre": "meme audio", "energy": "chaotic", "vibe": "something everyone recognizes that adds to the comedy"}
    ],
    "content_score": 9,
    "score_reason": "Genuinely funny moments with strong meme potential — the kind of content reshared for days."
}


# ─────────────────────────────────────────────
# VTT SUBTITLE PARSER
# ─────────────────────────────────────────────

def parse_vtt(content):
    """Parse WebVTT file into timestamped transcript lines."""
    out   = []
    start = None

    for line in content.split("\n"):
        line = line.strip()
        if not line or line.startswith("WEBVTT") or re.match(r"^(Kind|Language|NOTE):", line):
            continue
        if re.match(r"^\d+$", line):
            continue

        # Timestamp line
        m = re.match(r"^(\d{1,2}:\d{2}:\d{2}[.,]\d+|\d{1,2}:\d{2}[.,]\d+)\s*-->", line)
        if m:
            ts    = m.group(1).replace(",", ".")
            parts = ts.split(":")
            if len(parts) == 2:
                start = f"00:{int(parts[0]):02d}:{int(float(parts[1])):02d}"
            else:
                start = f"{int(parts[0]):02d}:{int(parts[1]):02d}:{int(float(parts[2])):02d}"
            continue

        # Text line
        if start and line:
            clean = re.sub(r"<[^>]+>", "", line)
            clean = re.sub(r"\s+", " ", clean).strip()
            if clean:
                out.append(f"[{start}] {clean}")
                start = None

    # Deduplicate
    seen, unique = set(), []
    for l in out:
        text = re.sub(r"\[[\d:]+\]\s*", "", l)
        if text not in seen:
            seen.add(text)
            unique.append(l)

    return "\n".join(unique[:400])


def vtt_ts_to_sec(ts):
    ts = ts.replace(",", ".")
    parts = ts.split(":")
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    return int(parts[0]) * 60 + float(parts[1])

def secs_to_ass(s):
    s = max(0.0, float(s))
    h = int(s // 3600)
    m = int((s % 3600) // 60)
    sec = s % 60
    cs = int((sec - int(sec)) * 100)
    return f"{h}:{m:02d}:{int(sec):02d}.{cs:02d}"

def parse_vtt_segments(content):
    """Parse VTT into [(start_sec, end_sec, text)] — used for active subtitle burn-in."""
    segments = []
    start_s = end_s = None
    for line in content.split("\n"):
        line = line.strip()
        if not line or line.startswith("WEBVTT") or re.match(r"^(Kind|Language|NOTE):", line):
            continue
        if re.match(r"^\d+$", line):
            continue
        m = re.match(r"^(\S+)\s*-->\s*(\S+)", line)
        if m:
            try:
                start_s = vtt_ts_to_sec(m.group(1))
                end_s   = vtt_ts_to_sec(m.group(2))
            except Exception:
                start_s = end_s = None
            continue
        if start_s is not None and line:
            clean = re.sub(r"<[^>]+>", "", line).strip()
            if clean:
                segments.append((start_s, end_s or start_s + 2.0, clean))
                start_s = end_s = None
    return segments

def build_caption_overlays(vtt_path, clip_start, clip_duration):
    """Render each VTT caption line as a transparent PNG for PIL-based overlay.
    Returns list of (png_path, adj_start, adj_end)."""
    from PIL import Image, ImageDraw, ImageFont

    try:
        content  = Path(vtt_path).read_text(encoding="utf-8", errors="ignore")
        segments = parse_vtt_segments(content)
    except Exception:
        return []

    clip_end  = clip_start + clip_duration
    font_size = 56
    font      = None
    for fp in FONT_PATHS:
        try:
            font = ImageFont.truetype(fp, font_size)
            break
        except Exception:
            pass
    if font is None:
        font = ImageFont.load_default()

    results = []
    for (start, end, text) in segments:
        if end < clip_start or start > clip_end:
            continue
        adj_start = max(0.0, start - clip_start - CAPTION_OFFSET)
        adj_end   = max(adj_start + 0.1, min(clip_duration, end - clip_start - CAPTION_OFFSET))
        if adj_end - adj_start < 0.1:
            continue

        clean = strip_emojis(text)
        if not clean.strip():
            continue

        img  = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Word-wrap at 85% width
        max_w  = int(1080 * 0.85)
        words  = clean.split()
        lines, cur = [], []
        for word in words:
            test = " ".join(cur + [word])
            bbox = draw.textbbox((0, 0), test, font=font)
            if (bbox[2] - bbox[0]) > max_w and cur:
                lines.append(" ".join(cur))
                cur = [word]
            else:
                cur.append(word)
        if cur:
            lines.append(" ".join(cur))

        line_h  = int(font_size * 1.3)
        total_h = len(lines) * line_h
        start_y = int(1920 * 0.84) - total_h // 2  # bottom area
        stroke  = max(3, font_size // 14)

        for i, line in enumerate(lines):
            bbox = draw.textbbox((0, 0), line, font=font)
            tw   = bbox[2] - bbox[0]
            x    = (1080 - tw) // 2
            y    = start_y + i * line_h
            draw.text((x, y), line, font=font,
                      fill=(255, 255, 255, 255),
                      stroke_width=stroke, stroke_fill=(0, 0, 0, 255))

        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        img.save(tmp.name, "PNG")
        results.append((tmp.name, adj_start, adj_end))

    return results


# ─────────────────────────────────────────────
# VIDEO DOWNLOAD
# ─────────────────────────────────────────────

def _yt_dlp_base_args():
    """Base yt-dlp args — tv_embedded bypasses bot detection without cookies or JS."""
    return ["--extractor-args", "youtube:player_client=tv_embedded,ios"]

def download_video(url):
    base = _yt_dlp_base_args()

    # Metadata
    meta_res = subprocess.run(
        ["python3", "-m", "yt_dlp", "--dump-json", "--no-playlist"] + base + [url],
        capture_output=True, text=True, timeout=60
    )
    meta     = json.loads(meta_res.stdout) if meta_res.returncode == 0 else {}
    video_id = meta.get("id", "")

    # Download video
    out_tpl = str(DOWNLOADS / "%(id)s.%(ext)s")
    dl = subprocess.run(
        [
            "python3", "-m", "yt_dlp",
            "--no-playlist",
            "-f", "bestvideo[height<=720]+bestaudio/bestvideo+bestaudio/best",
            "--merge-output-format", "mp4",
            "-o", out_tpl,
        ] + base + [url],
        capture_output=True, text=True, timeout=300
    )
    if dl.returncode != 0:
        raise RuntimeError(dl.stderr or "yt-dlp download failed")

    # Download auto-generated subtitles (for accurate timestamps)
    subprocess.run(
        [
            "python3", "-m", "yt_dlp",
            "--no-playlist",
            "--write-auto-sub", "--write-sub",
            "--sub-lang", "en",
            "--sub-format", "vtt",
            "--skip-download",
            "-o", str(DOWNLOADS / "%(id)s.%(ext)s"),
        ] + base + [url],
        capture_output=True, text=True, timeout=60
    )

    # Find downloaded file — try by video_id first, then most recent mp4
    exact    = list(DOWNLOADS.glob(f"{video_id}.mp4")) if video_id else []
    any_mp4  = [f for f in DOWNLOADS.glob(f"{video_id}*.mp4")] if video_id else []
    all_vid  = [f for f in DOWNLOADS.glob(f"{video_id}.*") if f.suffix in (".mp4", ".mkv", ".webm")] if video_id else []
    # Fallback: most recently modified mp4 in downloads
    recent   = sorted(DOWNLOADS.glob("*.mp4"), key=lambda f: f.stat().st_mtime, reverse=True)
    matches  = exact or any_mp4 or all_vid or recent

    if not matches:
        raise RuntimeError("Downloaded file not found")
    return str(matches[0]), meta


# ─────────────────────────────────────────────
# TRANSCRIPT
# ─────────────────────────────────────────────

def extract_transcript(video_path, meta):
    video_id = Path(video_path).stem.split(".")[0]

    # 1. Try VTT subtitles (best — has real timestamps)
    vtt_files = list(DOWNLOADS.glob(f"{video_id}*.vtt"))
    if vtt_files:
        try:
            content = vtt_files[0].read_text(encoding="utf-8", errors="ignore")
            parsed  = parse_vtt(content)
            if parsed.strip():
                return f"[Timestamped transcript from subtitles]\n{parsed}"
        except Exception:
            pass

    # 2. Try Whisper
    try:
        import whisper
        model  = whisper.load_model("base")
        result = model.transcribe(video_path)
        return result["text"]
    except Exception:
        pass

    # 3. Fallback to metadata
    title       = meta.get("title", "")
    description = meta.get("description", "")
    tags        = ", ".join(meta.get("tags", [])[:10])
    duration    = meta.get("duration", 0)
    return (
        f"[No transcript — using metadata only. Suggest clips based on likely content structure.]\n"
        f"Title: {title}\nDuration: {duration}s\n"
        f"Description: {description[:600]}\nTags: {tags}"
    )


# ─────────────────────────────────────────────
# TREND RESEARCH
# ─────────────────────────────────────────────

def extract_heatmap_peaks(meta):
    """Pull YouTube's most-replayed heatmap data and return the top moments as a string."""
    heatmap = meta.get("heatmap") or []
    if not heatmap:
        return ""

    # Top 10 by replay value, sorted back chronologically
    top = sorted(heatmap, key=lambda x: x.get("value", 0), reverse=True)[:10]
    top.sort(key=lambda x: x.get("start_time", 0))

    lines = []
    for seg in top:
        t   = seg.get("start_time", 0)
        end = seg.get("end_time", t + 10)
        pct = int(seg.get("value", 0) * 100)
        h   = int(t // 3600)
        m   = int((t % 3600) // 60)
        s   = int(t % 60)
        ts  = f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"
        lines.append(f"  {ts} – {int(end - t)}s – {pct}% replay intensity")

    return (
        "MOST REPLAYED MOMENTS (YouTube heatmap — viewers rewatch these parts most):\n"
        + "\n".join(lines)
    )


def research_trends(meta):
    """Search YouTube for similar trending videos to inform clip selection."""
    title = meta.get("title", "")
    tags  = meta.get("tags", [])[:3]
    query = title[:60] if title else " ".join(tags)
    if not query:
        return ""

    try:
        result = subprocess.run(
            [
                "python3", "-m", "yt_dlp",
                f"ytsearch8:{query}",
                "--dump-json", "--no-playlist", "--flat-playlist",
            ],
            capture_output=True, text=True, timeout=45
        )
        if result.returncode != 0:
            return ""

        trends = []
        for line in result.stdout.strip().split("\n"):
            if not line.strip():
                continue
            try:
                v      = json.loads(line)
                vtitle = v.get("title", "")
                views  = v.get("view_count", 0)
                dur    = v.get("duration", 0)
                if vtitle and views and views > 10000:
                    trends.append(f"- \"{vtitle}\" — {views:,} views, {dur}s long")
            except Exception:
                pass

        if trends:
            return "TRENDING SIMILAR CONTENT (YouTube search results):\n" + "\n".join(trends[:6])
    except Exception:
        pass
    return ""


# ─────────────────────────────────────────────
# AI ANALYSIS
# ─────────────────────────────────────────────

def analyze_with_claude(transcript, meta, mood="auto", trends="", custom_prompt=""):
    title    = meta.get("title", "Unknown")
    duration = meta.get("duration", 0)
    cfg      = MOOD_CONFIGS.get(mood, MOOD_CONFIGS["auto"])

    trends_block  = f"\n{trends}\n" if trends else ""
    heatmap_block = f"\n{extract_heatmap_peaks(meta)}\n" if meta.get("heatmap") else ""
    custom_block  = f"\nUSER INSTRUCTIONS (highest priority — follow these exactly):\n{custom_prompt}\n" if custom_prompt else ""

    user_message = (
        f"Video title: {title}\n"
        f"Duration: {duration} seconds\n"
        f"{heatmap_block}"
        f"{trends_block}"
        f"{custom_block}\n"
        f"TRANSCRIPT WITH TIMESTAMPS:\n{transcript}\n\n"
        f"EDITING STYLE: {mood.upper()}\n"
        f"GOAL: {cfg['focus']}\n\n"
        "IMPORTANT: The transcript has timestamps like [00:01:23]. You MUST use these to pick "
        "accurate start/end times for each clip. The clip times must match where that content "
        "actually appears in the transcript. Do not guess or invent timestamps.\n\n"

        "CAPTION & HOOK TEXT RULES — this is what stops the scroll:\n"
        "- hook_text (burned into top of video): max 6 words, NO emojis, written like a TikTok hook. "
        "  Must create instant curiosity, shock, or FOMO. Think: 'he actually said this', "
        "  'nobody talks about this', 'this changes everything', 'wait for it'. "
        "  Write for someone scrolling at 2am who needs a reason to stop in 0.5 seconds.\n"
        "- caption (post text): line 1 = re-state the hook with more context to pull them in. "
        "  line 2 = add a relatable or shocking detail that makes them want to save/share. "
        "  line 3 = call to action or cliffhanger. Then 3-5 high-traffic hashtags. "
        "  Write like a viral creator, not a marketer. Conversational, lowercase, punchy.\n"
        "- Pick clips where the FIRST 2 SECONDS are strong — the algorithm kills anything with a slow open.\n\n"

        "Return ONLY this exact JSON, no extra text, no markdown:\n"
        '{"clips":[{"id":1,"start":"00:00:15","end":"00:00:35","reason":"why this moment works","hook_text":"stops scroll in 0.5s NO EMOJIS","caption":"line 1\\n\\nline 2\\n\\n#tag1 #tag2 #tag3","post_description":"why this will perform algorithmically","transition_in":"jump cut","transition_out":"zoom punch","confidence":9,"virality":"viral","mood_type":"funny"}],'
        '"music_suggestions":[{"genre":"phonk","energy":"high","vibe":"sound description"}],'
        '"content_score":9,"score_reason":"one punchy line"}\n\n'
        f"Rules: exact field names, minimum 8 clips — scale up for longer videos "
        f"(~8 for <10min, ~12 for 10-30min, ~15+ for 30min+). "
        f"Each clip 15-30 seconds MAX. "
        f"Strongly prioritize most-replayed heatmap timestamps — real viewer data beats everything. "
        f"HH:MM:SS times, confidence 1-10, virality = low/medium/high/viral, "
        f"mood_type matches editing style. hook_text: NO emojis, plain text only."
    )

    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8000,
        system=cfg["system"] + " You MUST return ONLY raw valid JSON using the exact field names given. No markdown, no explanation.",
        messages=[{"role": "user", "content": user_message}]
    )

    raw = msg.content[0].text.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return json.loads(raw)


# ─────────────────────────────────────────────
# VIDEO EFFECTS + TIKTOK CAPTION
# ─────────────────────────────────────────────

def get_video_dimensions(video_path):
    result = subprocess.run([FFMPEG, "-i", video_path], capture_output=True, text=True)
    m = re.search(r"(\d{3,4})x(\d{3,4})", result.stderr)
    return (int(m.group(1)), int(m.group(2))) if m else (1280, 720)


def create_tiktok_caption(hook_text, width, height, color_name="white", position="top"):
    """Generate TikTok-style caption: centered colored text, thick black stroke, no box."""
    from PIL import Image, ImageDraw, ImageFont

    img       = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw      = ImageDraw.Draw(img)
    color_rgb = CAPTION_COLORS.get(color_name, CAPTION_COLORS["white"])["pil"]

    # Font — bold, larger for blur bars layout
    font_size = max(60, height // 20)
    font = None
    for fp in FONT_PATHS:
        try:
            font = ImageFont.truetype(fp, font_size)
            break
        except Exception:
            pass
    if font is None:
        font = ImageFont.load_default()

    # Word wrap to 82% of width
    max_w  = int(width * 0.82)
    words  = hook_text.split()
    lines  = []
    cur    = []

    for word in words:
        test = " ".join(cur + [word])
        bbox = draw.textbbox((0, 0), test, font=font)
        if (bbox[2] - bbox[0]) > max_w and cur:
            lines.append(" ".join(cur))
            cur = [word]
        else:
            cur.append(word)
    if cur:
        lines.append(" ".join(cur))

    line_h  = int(font_size * 1.25)
    total_h = len(lines) * line_h
    if position == "bottom":
        start_y = int(height * 0.82) - total_h // 2
    else:
        start_y = int(height * 0.18) - total_h // 2
    stroke_w  = max(4, font_size // 12)

    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        tw   = bbox[2] - bbox[0]
        x    = (width - tw) // 2
        y    = start_y + i * line_h

        draw.text((x, y), line, font=font,
                  fill=(*color_rgb, 255),
                  stroke_width=stroke_w,
                  stroke_fill=(0, 0, 0, 255))

    return img


def build_clip(video_path, start_sec, duration, out_path,
               hook_text=None, caption_color="white", caption_position="top", active_subs=False):
    """Trim + effects: blur bars, hflip, color boost, fade, caption overlay."""
    vw, vh = get_video_dimensions(video_path)

    # Blur bars: full video visible, blurred version fills 9:16 background
    fade_dur = min(0.35, duration * 0.08)
    color_eq = "eq=saturation=1.3:contrast=1.06:brightness=0.02"
    blur_bg  = (
        f"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,"
        f"crop=1080:1920,hflip,boxblur=25:5,{color_eq}[bg];"
        f"[0:v]scale=1080:1920:force_original_aspect_ratio=decrease,"
        f"hflip,format=yuv420p,{color_eq},"
        f"fade=t=in:st=0:d={fade_dur:.2f}[fg];"
        f"[bg][fg]overlay=(W-w)/2:(H-h)/2[composited]"
    )

    # Build PIL-based caption overlays from VTT
    caption_pngs = []  # list of (png_path, adj_start, adj_end)
    if active_subs:
        stem      = Path(video_path).stem.split(".")[0]
        vtt_files = list(DOWNLOADS.glob(f"{stem}*.vtt"))
        if vtt_files:
            try:
                caption_pngs = build_caption_overlays(str(vtt_files[0]), start_sec, duration)
            except Exception:
                caption_pngs = []

    # Hook text overlay PNG
    overlay_path = None
    if hook_text and hook_text.strip():
        try:
            img = create_tiktok_caption(
                strip_emojis(hook_text.strip()), 1080, 1920, caption_color, caption_position
            )
            tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            img.save(tmp.name, "PNG")
            overlay_path = tmp.name
        except Exception:
            overlay_path = None

    try:
        # Inputs: [0]=video, [1..N]=caption PNGs, [N+1]=hook PNG
        inputs = ["-ss", str(start_sec), "-i", video_path]
        for png_path, _, _ in caption_pngs:
            inputs += ["-i", png_path]
        if overlay_path:
            inputs += ["-i", overlay_path]

        # Filtergraph: blur_bg → caption overlays (timed) → hook overlay
        filter_parts = [blur_bg]
        current = "composited"

        for j, (_, cap_s, cap_e) in enumerate(caption_pngs):
            in_idx   = 1 + j
            next_lbl = f"cv{j}"
            filter_parts.append(
                f"[{current}][{in_idx}:v]overlay=0:0"
                f":enable='between(t,{cap_s:.3f},{cap_e:.3f})'[{next_lbl}]"
            )
            current = next_lbl

        if overlay_path:
            hook_idx = 1 + len(caption_pngs)
            filter_parts.append(f"[{current}][{hook_idx}:v]overlay=0:0[out]")
            final_map = "[out]"
        else:
            final_map = f"[{current}]"

        filter_complex = ";".join(filter_parts)

        cmd = [FFMPEG, "-y"] + inputs + [
            "-t", str(duration),
            "-filter_complex", filter_complex,
            "-map", final_map, "-map", "0:a",
            "-c:v", "libx264", "-c:a", "aac", "-movflags", "+faststart",
            str(out_path)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            raise RuntimeError(result.stderr[-600:])
    finally:
        for png_path, _, _ in caption_pngs:
            try: os.unlink(png_path)
            except: pass
        if overlay_path:
            try: os.unlink(overlay_path)
            except: pass

    return out_path


def timecode_to_seconds(tc):
    parts = [float(p) for p in str(tc).strip().split(":")]
    if len(parts) == 3: return parts[0] * 3600 + parts[1] * 60 + parts[2]
    if len(parts) == 2: return parts[0] * 60 + parts[1]
    return parts[0]


# ─────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    try:
        data          = request.get_json()
        url           = data.get("url", "").strip()
        mood          = data.get("mood", "auto")
        custom_prompt = data.get("custom_prompt", "").strip()

        if not url:
            return jsonify({"error": "Paste a URL first!"}), 400

        if DEMO_MODE:
            return jsonify({
                "success": True, "video_path": "demo",
                "title": "Demo — Add your API key to analyze real videos",
                "duration": 180, "mood": mood, "analysis": DEMO_ANALYSIS
            })

        video_path, meta = download_video(url)
        transcript       = extract_transcript(video_path, meta)
        trends           = research_trends(meta)
        analysis         = analyze_with_claude(transcript, meta, mood, trends, custom_prompt)

        return jsonify({
            "success":    True,
            "video_path": video_path,
            "title":      meta.get("title", ""),
            "duration":   meta.get("duration", 0),
            "mood":       mood,
            "analysis":   analysis
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/preview", methods=["POST"])
def preview():
    if DEMO_MODE:
        return jsonify({"error": "Add your API key to preview clips!"}), 400
    try:
        data             = request.get_json()
        vpath            = data.get("video_path")
        start            = data.get("start", "00:00:00")
        end              = data.get("end",   "00:00:30")
        clip_id          = data.get("clip_id", "preview")
        hook_text        = data.get("hook_text", "")
        caption_color    = data.get("caption_color", "white")
        caption_position = data.get("caption_position", "top")
        active_subs      = data.get("active_subs", False)

        start_sec = timecode_to_seconds(start)
        end_sec   = timecode_to_seconds(end)
        duration  = max(1, end_sec - start_sec)

        out_path = OUTPUTS / f"preview_{clip_id}.mp4"
        build_clip(vpath, start_sec, duration, out_path, hook_text or None,
                   caption_color, caption_position, active_subs)
        return send_file(str(out_path), mimetype="video/mp4")

    except subprocess.TimeoutExpired:
        return jsonify({"error": "FFmpeg timed out"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/download-clip", methods=["POST"])
def download_clip():
    if DEMO_MODE:
        return jsonify({"error": "Add your API key to download clips!"}), 400
    try:
        data             = request.get_json()
        vpath            = data.get("video_path")
        start            = data.get("start", "00:00:00")
        end              = data.get("end",   "00:00:30")
        clip_id          = data.get("clip_id", "clip")
        hook_text        = data.get("hook_text", "")
        caption_color    = data.get("caption_color", "white")
        caption_position = data.get("caption_position", "top")
        active_subs      = data.get("active_subs", False)

        start_sec = timecode_to_seconds(start)
        end_sec   = timecode_to_seconds(end)
        duration  = max(1, end_sec - start_sec)

        out_path = OUTPUTS / f"clip_{clip_id}.mp4"
        build_clip(vpath, start_sec, duration, out_path, hook_text or None,
                   caption_color, caption_position, active_subs)
        return send_file(str(out_path), as_attachment=True, download_name=f"clip_{clip_id}.mp4")

    except subprocess.TimeoutExpired:
        return jsonify({"error": "FFmpeg timed out"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/download-plan", methods=["POST"])
def download_plan():
    try:
        data     = request.get_json()
        title    = data.get("title", "Untitled")
        analysis = data.get("analysis", {})

        lines = [
            f"EDIT PLAN — {title}", "=" * 50,
            f"Content Score: {analysis.get('content_score','?')}/10",
            f"Score Reason:  {analysis.get('score_reason','')}",
            "", "MUSIC SUGGESTIONS", "-" * 30,
        ]
        for m in analysis.get("music_suggestions", []):
            lines.append(f"Genre: {m.get('genre')} | Energy: {m.get('energy')} | Vibe: {m.get('vibe')}")

        lines += ["", "CLIPS", "-" * 30]
        for clip in analysis.get("clips", []):
            lines += [
                f"\nClip {clip.get('id')} — {clip.get('start')} to {clip.get('end')}",
                f"Confidence: {clip.get('confidence','?')}/10 | Virality: {clip.get('virality','?')} | Mood: {clip.get('mood_type','?')}",
                f"Hook Text (burned in): {clip.get('hook_text','')}",
                f"Why it works: {clip.get('reason','')}",
                f"Post Description: {clip.get('post_description','')}",
                f"Transitions: {clip.get('transition_in','')} → {clip.get('transition_out','')}",
                f"Caption:\n{clip.get('caption','')}",
                "-" * 30,
            ]

        out_path = OUTPUTS / "edit_plan.txt"
        out_path.write_text("\n".join(lines))
        return send_file(str(out_path), as_attachment=True, download_name="edit_plan.txt")
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(debug=False, host="0.0.0.0", port=port)
