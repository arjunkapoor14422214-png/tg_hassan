from dotenv import load_dotenv
import os
import asyncio
import json
import random
import re
import sys
import requests
from html import escape
from telethon import TelegramClient
from telethon.sessions import StringSession

load_dotenv()

def parse_telegram_peer(value):
    value = (value or "").strip()
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    return value


def parse_telegram_peers(value):
    peers = []
    for item in re.split(r"[\s,]+", value or ""):
        item = (item or "").strip()
        if item:
            peers.append(parse_telegram_peer(item))
    return peers


def normalize_telegram_channel_id(value):
    value = str(value).strip()
    if value.startswith("-100") and value[4:].isdigit():
        return int(value[4:])
    if re.fullmatch(r"-?\d+", value):
        return abs(int(value))
    return None


API_ID = os.getenv("TG_API_ID")
API_HASH = os.getenv("TG_API_HASH")
SOURCE_CHANNEL = (os.getenv("SOURCE_CHANNEL") or "").strip()
TARGET_CHANNEL = (os.getenv("TARGET_CHANNEL") or "").strip()
TARGET_CHANNELS = parse_telegram_peers(os.getenv("TARGET_CHANNELS", ""))
if not TARGET_CHANNELS and TARGET_CHANNEL:
    TARGET_CHANNELS = [parse_telegram_peer(TARGET_CHANNEL)]
DEFAULT_TARGET_CHANNEL = TARGET_CHANNELS[0] if TARGET_CHANNELS else parse_telegram_peer(TARGET_CHANNEL)
SOURCE_CHANNEL_ENTITY = parse_telegram_peer(SOURCE_CHANNEL)
REVIEW_CHANNEL_ID = os.getenv("REVIEW_CHANNEL_ID", "").strip()
if REVIEW_CHANNEL_ID.startswith("100"):
    REVIEW_CHANNEL_ID = f"-{REVIEW_CHANNEL_ID}"
MODERATION_ENABLED = os.getenv("MODERATION_ENABLED", "false").strip().lower() == "true"
BOT_TOKEN = os.getenv("BOT_TOKEN")
SESSION_STRING = os.getenv("TG_SESSION_STRING", "").strip()
AI_ENABLED = os.getenv("AI_ENABLED", "false").strip().lower() == "true"
AI_API_KEY = os.getenv("AI_API_KEY", "").strip()
AI_MODEL = os.getenv("AI_MODEL", "gpt-4.1-mini").strip()
AI_STYLE_PROMPT = os.getenv(
    "AI_STYLE_PROMPT",
    (
        "Rewrite the source into polished Arabic Telegram copy for a betting and sports Telegram channel. "
        "Make it sound native, confident, clean, premium, and easy to read on mobile. "
        "Keep facts, odds, teams, injuries, and promo meaning accurate. "
        "If the source is promo or betting content, make it punchy and persuasive. "
        "If the source is sports news, keep it fast, sharp, and factual. "
        "Use short rhythmic lines, elegant Arabic wording, and selective emojis. "
        "Never mention the source channel, source attribution, or foreign partner brands. "
        "No hashtags, no markdown, no filler, and no fake claims."
    ),
).strip()
AI_TARGET_LANG = os.getenv("AI_TARGET_LANG", "").strip()
PROMOCODE_TEXT = os.getenv("PROMOCODE_TEXT", "PROMOCODE: NILE").strip() or "PROMOCODE: NILE"
APK_URL = os.getenv("APK_URL", "https://t.me/PLATINUM_APK").strip() or "https://t.me/PLATINUM_APK"
PRIMARY_PARTNER_ONLY_MODE = os.getenv("PRIMARY_PARTNER_ONLY_MODE", "false").strip().lower() in {"1", "true", "yes", "on"}

BUTTON1_TEXT = os.getenv("BUTTON1_TEXT")
BUTTON1_URL = os.getenv("BUTTON1_URL")
BUTTON2_TEXT = os.getenv("BUTTON2_TEXT")
BUTTON2_URL = os.getenv("BUTTON2_URL")
BUTTON3_TEXT = os.getenv("BUTTON3_TEXT", "LUCKYPARI BONUS").strip()
BUTTON3_URL = os.getenv("BUTTON3_URL", "https://lckypr.com/G4DtDxQ").strip()
BUTTON4_TEXT = os.getenv("BUTTON4_TEXT", "LINEBET BONUS").strip()
BUTTON4_URL = os.getenv("BUTTON4_URL", "https://lb-aff.com/L?tag=d_5445297m_22611c_site&site=5445297&ad=22611&r=registration").strip()

LUCKYPARI_APK_URL = os.getenv("LUCKYPARI_APK_URL", "https://lckypr.com/wW5nH61").strip()
ULTRAPARI_APK_URL = os.getenv("ULTRAPARI_APK_URL", "https://refpa42156.com/L?tag=d_5299306m_118431c_&site=5299306&ad=118431").strip()
WINWIN_APK_URL = os.getenv("WINWIN_APK_URL", "https://refpa712080.pro/L?tag=d_5343420m_68383c_&site=5343420&ad=68383").strip()
LINEBET_APK_URL = os.getenv("LINEBET_APK_URL", "https://lb-aff.com/L?tag=d_5445297m_66803c_apk1&site=5445297&ad=66803").strip()
ALBUM_CHANNEL_URL = os.getenv("ALBUM_CHANNEL_URL", "https://t.me/PLATINUM_APK").strip() or "https://t.me/PLATINUM_APK"
BONUS_BUTTON_MESSAGE = os.getenv("BONUS_BUTTON_MESSAGE", "Bonusni oling").strip() or "Bonusni oling"
REVIEW_MODE = MODERATION_ENABLED and bool(REVIEW_CHANNEL_ID)

TEXT_LINK_TOKENS = [
    ("[[APK1]]", "LuckyPari APK", LUCKYPARI_APK_URL),
    ("[[APK2]]", "UltraPari APK", ULTRAPARI_APK_URL),
    ("[[APK3]]", "WinWin APK", WINWIN_APK_URL),
    ("[[APK4]]", "Linebet APK", LINEBET_APK_URL),
]
TARGET_PARTNER_TOKEN_PATTERN = re.compile(r"\[\[PARTNER\d+\]\]")

ALL_BUTTON_LINKS = [
    (BUTTON1_TEXT, BUTTON1_URL),
    (BUTTON2_TEXT, BUTTON2_URL),
    (BUTTON3_TEXT, BUTTON3_URL),
    (BUTTON4_TEXT, BUTTON4_URL),
]
PRIMARY_BUTTON_LINKS = [(BUTTON3_TEXT, BUTTON3_URL)] if BUTTON3_TEXT and BUTTON3_URL else []
BUTTON_LINKS = PRIMARY_BUTTON_LINKS if PRIMARY_PARTNER_ONLY_MODE else ALL_BUTTON_LINKS

SOURCE_BRAND_PATTERN = re.compile(
    r"(?i)\b(mel\s*bet|1x\s*bet|pari\s*land|mega\s*pari|megapari|pariland)\b"
)
SOURCE_LINK_PATTERN = re.compile(r"https?://\S+", re.IGNORECASE)
SOURCE_PROMOCODE_PATTERN = re.compile(r"(?i)\bleg230\b")
PROMOCODE_ONLY_PATTERN = re.compile(
    r"(?im)^\s*(?:promo\s*code|promocode|كود(?:\s*البرومو)?|رمز(?:\s*البرومو)?|برومو\s*كود).*$"
)
PARTNER_LINE_KEYWORDS = (
    "سجل",
    "تسجيل",
    "register",
    "registration",
    "bonus",
    "promo",
    "promocode",
    "promo code",
    "برومو",
    "بونص",
    "ايداع",
    "إيداع",
)
REGISTRATION_LINE_KEYWORDS = (
    "سجل",
    "تسجيل",
    "register",
    "registration",
)
INLINE_CODE_PATTERN = re.compile(r"^[A-Z0-9]{5,8}$")


def normalize_company_name(text, fallback):
    value = (text or "").strip()
    if not value:
        return fallback
    value = re.sub(r"(?i)\bbonus\b", "", value).strip(" -")
    return value or fallback


ALL_TARGET_COMPANIES = [
    {
        "name": normalize_company_name(BUTTON3_TEXT, "LUCKYPARI"),
        "url": BUTTON3_URL,
        "emoji": "💛",
    },
    {
        "name": normalize_company_name(BUTTON2_TEXT, "WINWIN"),
        "url": BUTTON2_URL,
        "emoji": "🚀",
    },
    {
        "name": normalize_company_name(BUTTON1_TEXT, "ULTRAPARI"),
        "url": BUTTON1_URL,
        "emoji": "🔥",
    },
    {
        "name": normalize_company_name(BUTTON4_TEXT, "LINEBET"),
        "url": BUTTON4_URL,
        "emoji": "👑",
    },
]
TARGET_COMPANIES = ALL_TARGET_COMPANIES[:1] if PRIMARY_PARTNER_ONLY_MODE else ALL_TARGET_COMPANIES

SOURCE_BRAND_RULES = [
    (re.compile(r"(?i)\bmel\s*bet\b"), 0),
    (re.compile(r"(?i)\b1x\s*bet\b"), 1),
    (re.compile(r"(?i)\bpari\s*land\b"), 2),
    (re.compile(r"(?i)\bpariland\b"), 2),
    (re.compile(r"(?i)\bmega\s*pari\b"), 3),
    (re.compile(r"(?i)\bmegapari\b"), 3),
]
COMMON_FOREIGN_BOOKMAKER_PATTERN = re.compile(
    r"(?i)\b(?:bet365|1win|mostbet|parimatch|fonbet|marathonbet|leon|betwinner|vbet|stake|betano|betway|dafabet|roobet|pin[\s-]*up|pinup)\b"
)
GENERIC_PARTNER_BOOKMAKER_PATTERN = re.compile(
    r"(?i)\b(?:[a-z0-9]{2,}xbet|[a-z0-9]{2,}pari|[a-z0-9]{2,}bet)\b"
)

CYRILLIC_TITLES = [
    "ÐœÐ¾Ñ ÑÑ‚Ð°Ð²ÐºÐ° ÑÐµÐ³Ð¾Ð´Ð½Ñ:",
    "Ð¢Ð¾Ð¿ ÑÑ‚Ð°Ð²ÐºÐ° Ð´Ð½Ñ:",
    "Ð¡ÐµÐ³Ð¾Ð´Ð½Ñ Ð±ÐµÑ€Ñƒ Ð²Ð¾Ñ‚ ÑÑ‚Ð¾:",
    "Ð¡Ñ‚Ð°Ð²ÐºÐ° Ð½Ð° ÑÐµÐ³Ð¾Ð´Ð½Ñ:",
    "Ð—Ð°Ð±Ð¸Ñ€Ð°ÑŽ Ñ‚Ð°ÐºÐ¾Ð¹ Ð²Ð°Ñ€Ð¸Ð°Ð½Ñ‚:",
]

LATIN_TITLES = [
    "Bugungi top stavka:",
    "Bugun men shuni tanladim:",
    "Kun stavkasi:",
    "Mening bugungi tanlovim:",
    "Bugungi stavkam:",
]

STATE_FILE = "data/state.json"
PENDING_FILE = "data/pending.json"
CHECK_INTERVAL = 10


def safe_console_text(value):
    text = str(value)
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    return text.encode(encoding, errors="replace").decode(encoding, errors="replace")


def get_promocode_value():
    tokens = re.findall(r"[A-Za-z0-9_-]{3,}", PROMOCODE_TEXT or "")
    if tokens:
        return tokens[-1]
    return (PROMOCODE_TEXT or "").strip()


def get_source_signature(entity):
    source_name = (SOURCE_CHANNEL or "").strip().lower()
    entity_id = getattr(entity, "id", "")
    return f"{entity_id}:{source_name}"


def normalize_brand_key(value):
    return re.sub(r"[^a-z0-9]+", "", (value or "").lower())


def get_primary_target_company():
    for company in ALL_TARGET_COMPANIES:
        if (company.get("name") or "").strip() and (company.get("url") or "").strip():
            return company
    return {"name": "LUCKYPARI", "url": BUTTON3_URL, "emoji": "💛"}


TARGET_COMPANY_KEYS = {
    normalize_brand_key(company.get("name"))
    for company in TARGET_COMPANIES
    if normalize_brand_key(company.get("name"))
}
ALL_TARGET_COMPANY_KEYS = {
    normalize_brand_key(company.get("name"))
    for company in ALL_TARGET_COMPANIES
    if normalize_brand_key(company.get("name"))
}
KNOWN_SOURCE_BRAND_KEYS = {
    "melbet",
    "1xbet",
    "pariland",
    "megapari",
}


def build_partner_block():
    lines = []

    for index, company in enumerate(TARGET_COMPANIES, start=1):
        if not (company.get("name") or "").strip():
            continue

        token = f"[[PARTNER{index}]]"
        lines.append(token)

    return "\n\n".join(lines).strip()


def build_primary_partner_block():
    primary_company = get_primary_target_company()
    if not (primary_company.get("name") or "").strip():
        return ""
    return "[[PARTNER1]]"


def line_has_partner_context(line):
    lowered = (line or "").lower()
    return any(keyword in lowered for keyword in PARTNER_LINE_KEYWORDS)


def line_has_registration_context(line):
    lowered = (line or "").lower()
    return any(keyword in lowered for keyword in REGISTRATION_LINE_KEYWORDS)


def contains_target_company_reference(text):
    body = text or ""
    normalized_body = normalize_brand_key(body)
    if any(key in normalized_body for key in ALL_TARGET_COMPANY_KEYS):
        return True

    return any(
        (company.get("url") or "").strip()
        and (company.get("url") or "").strip() in body
        for company in ALL_TARGET_COMPANIES
    )


def is_target_partner_line(line):
    body = (line or "").strip()
    if not body:
        return False
    if not line_has_registration_context(body):
        return False
    return contains_target_company_reference(body)


def should_strip_partner_brand_line(line):
    body = (line or "").strip()
    if not body:
        return False

    if is_target_partner_line(body):
        return True

    if not PRIMARY_PARTNER_ONLY_MODE:
        return False

    if contains_target_company_reference(body):
        return True

    if source_mentions_brands(body):
        return True

    if line_has_foreign_bookmaker_mention(body, partner_fallback=True) and line_has_partner_context(body):
        return True

    return False


def line_has_foreign_bookmaker_mention(line, partner_fallback=False):
    body = line or ""
    if not body.strip():
        return False

    if COMMON_FOREIGN_BOOKMAKER_PATTERN.search(body):
        return True

    if not partner_fallback:
        return False

    for match in GENERIC_PARTNER_BOOKMAKER_PATTERN.finditer(body):
        brand_key = normalize_brand_key(match.group(0))
        if not brand_key:
            continue
        if brand_key in ALL_TARGET_COMPANY_KEYS or brand_key in KNOWN_SOURCE_BRAND_KEYS:
            continue
        return True

    return False


def source_mentions_brands(text):
    body = text or ""
    return any(pattern.search(body) for pattern, _ in SOURCE_BRAND_RULES)


def replace_foreign_bookmaker_mentions(text):
    primary_name = (get_primary_target_company().get("name") or "").strip() or "LUCKYPARI"
    return COMMON_FOREIGN_BOOKMAKER_PATTERN.sub(primary_name, text or "")


def replace_source_brand_mentions(text):
    body = replace_foreign_bookmaker_mentions(text)
    primary_name = (get_primary_target_company().get("name") or "").strip() or "LUCKYPARI"
    for pattern, target_index in SOURCE_BRAND_RULES:
        if PRIMARY_PARTNER_ONLY_MODE:
            replacement = primary_name
        else:
            replacement = (ALL_TARGET_COMPANIES[target_index].get("name") or "").strip() or primary_name
        body = pattern.sub(replacement, body)

    if PRIMARY_PARTNER_ONLY_MODE:
        for company in ALL_TARGET_COMPANIES[1:]:
            name = (company.get("name") or "").strip()
            if not name:
                continue
            body = re.sub(rf"(?i)\b{re.escape(name)}\b", primary_name, body)

    return body


def is_promocode_only_line(line):
    return bool(PROMOCODE_ONLY_PATTERN.match((line or "").strip()))


def has_source_partner_block(text):
    body = text or ""
    if not body.strip():
        return False

    if SOURCE_LINK_PATTERN.search(body):
        return True

    for raw_line in body.splitlines():
        line = (raw_line or "").strip()
        if not line:
            continue

        has_url = bool(SOURCE_LINK_PATTERN.search(line))
        has_brand = source_mentions_brands(line)

        if has_url and (has_brand or line_has_partner_context(line)):
            return True

        if has_brand and line_has_registration_context(line):
            return True

        if line_has_partner_context(line) and line_has_foreign_bookmaker_mention(line, partner_fallback=True):
            return True

    return False


def has_target_partner_block(text):
    body = text or ""
    if not body.strip():
        return False

    if TARGET_PARTNER_TOKEN_PATTERN.search(body):
        return True

    for raw_line in body.splitlines():
        line = (raw_line or "").strip()
        if not line:
            continue

        has_target_url = any(
            (company.get("url") or "").strip()
            and (company.get("url") or "").strip() in line
            for company in TARGET_COMPANIES
        )

        if has_target_url:
            return True

    return False


def has_company_mentions(text):
    return (
        source_mentions_brands(text)
        or line_has_foreign_bookmaker_mention(text)
        or contains_target_company_reference(text)
    )


def has_partner_mentions(text):
    return has_source_partner_block(text)


def should_use_primary_partner_fallback(text):
    if PRIMARY_PARTNER_ONLY_MODE:
        return True

    body = text or ""
    if not body.strip():
        return False

    for raw_line in body.splitlines():
        line = (raw_line or "").strip()
        if not line:
            continue

        if contains_target_company_reference(line):
            continue

        if line_has_partner_context(line) and line_has_foreign_bookmaker_mention(line, partner_fallback=True):
            return True

        if (
            SOURCE_LINK_PATTERN.search(line)
            and line_has_partner_context(line)
            and not source_mentions_brands(line)
            and not contains_target_company_reference(line)
        ):
            return True

    return False


def is_ignored_code_line(line):
    body = (line or "").strip()
    if not body:
        return False

    candidate = body.lstrip("•-–—").strip()
    if not candidate:
        return False

    parts = candidate.split(maxsplit=1)
    token = parts[0].strip("()[]{}")
    if not INLINE_CODE_PATTERN.fullmatch(token):
        return False

    target_names = {
        (company.get("name") or "").strip().upper()
        for company in TARGET_COMPANIES
        if (company.get("name") or "").strip()
    }
    if token in target_names:
        return False

    if len(parts) == 1:
        return True

    rest = parts[1].strip()
    if not rest:
        return True

    if any(char.isalpha() for char in rest):
        return False

    return True


def remove_ignored_code_lines(text):
    cleaned_lines = []

    for raw_line in (text or "").splitlines():
        if is_ignored_code_line(raw_line):
            continue
        cleaned_lines.append(raw_line)

    return "\n".join(cleaned_lines)


def strip_source_markers(text):
    body = remove_ignored_code_lines(text or "")
    body = re.sub(r"\[[^\]]+\]", "", body)
    body = re.sub(r"(?<!\S)@[A-Za-z0-9_]{3,}", "", body)
    body = SOURCE_PROMOCODE_PATTERN.sub(get_promocode_value(), body)
    return body


def prepare_text_for_ai(text, inline_partners=False):
    body = replace_source_brand_mentions(strip_source_markers(text))
    cleaned_lines = []

    for raw_line in body.splitlines():
        line = (raw_line or "").strip()
        if not line:
            cleaned_lines.append("")
            continue

        if should_strip_partner_brand_line(line):
            continue

        if SOURCE_LINK_PATTERN.search(line):
            continue

        if has_source_partner_block(line) or is_promocode_only_line(line):
            continue

        line = SOURCE_LINK_PATTERN.sub("", line)
        line = re.sub(r"[ ]{2,}", " ", line).strip()
        if line:
            cleaned_lines.append(line)

    prepared = "\n".join(cleaned_lines).strip()
    prepared = re.sub(r"\n{3,}", "\n\n", prepared)

    if prepared:
        return prepared

    if inline_partners or has_company_mentions(text):
        return "اكتب منشوراً عربياً قصيراً وأنيقاً عن العرض مع الحفاظ على نبرة ترويجية واضحة."

    return (text or "").strip()


def remove_source_brand_residue(text):
    body = strip_source_markers(text)
    body = SOURCE_LINK_PATTERN.sub("", body)
    body = replace_source_brand_mentions(body)

    cleaned_lines = []
    for raw_line in body.splitlines():
        line = (raw_line or "").strip()
        if should_strip_partner_brand_line(line):
            continue
        cleaned_lines.append(raw_line)

    body = "\n".join(cleaned_lines)
    body = re.sub(r"\n{3,}", "\n\n", body)
    return body.strip()


def post_contains_inline_partners(text):
    return has_target_partner_block(text)


async def resolve_source_entity(client):
    if not isinstance(SOURCE_CHANNEL_ENTITY, int):
        return await client.get_entity(SOURCE_CHANNEL_ENTITY)

    normalized_source_id = normalize_telegram_channel_id(SOURCE_CHANNEL_ENTITY)

    async for dialog in client.iter_dialogs():
        entity = getattr(dialog, "entity", None)
        if getattr(entity, "id", None) == normalized_source_id:
            return entity

    return await client.get_entity(SOURCE_CHANNEL_ENTITY)


def build_reply_markup():
    rows = []

    for text, url in BUTTON_LINKS:
        if text and url:
            rows.append([{"text": text, "url": url}])

    if not rows:
        return None

    return {"inline_keyboard": rows}


def build_moderation_markup(post_key):
    return {
        "inline_keyboard": [
            [
                {"text": "Approve", "callback_data": f"approve:{post_key}"},
                {"text": "Reject", "callback_data": f"reject:{post_key}"},
            ]
        ]
    }


def apply_promocode_rule(text):
    text = (text or "").strip()
    if not text:
        return PROMOCODE_TEXT

    if PROMOCODE_ONLY_PATTERN.search(text):
        return PROMOCODE_ONLY_PATTERN.sub(PROMOCODE_TEXT, text).strip()

    return f"{text}\n\n{PROMOCODE_TEXT}"


def prepare_telegram_text(text, limit=None):
    text = text if text else "[Ð±ÐµÐ· Ñ‚ÐµÐºÑÑ‚Ð°]"
    if limit:
        text = text[:limit]

    safe_text = escape(text)
    apk_link = f'<a href="{escape(APK_URL, quote=True)}">APK</a>'
    safe_text = re.sub(r"\bAPK\b", apk_link, safe_text, flags=re.IGNORECASE)

    for token, label, url in TEXT_LINK_TOKENS:
        safe_text = safe_text.replace(
            escape(token),
            f'<a href="{escape(url, quote=True)}">{escape(label)}</a>',
        )

    for index, company in enumerate(TARGET_COMPANIES, start=1):
        token = f"[[PARTNER{index}]]"
        name = (company.get("name") or "").strip()
        url = (company.get("url") or "").strip()
        emoji = (company.get("emoji") or "").strip()
        if not name or not url:
            continue

        link_label = f"سجل {name}{emoji}" if emoji else f"سجل {name}"
        safe_text = safe_text.replace(
            escape(token),
            f'<a href="{escape(url, quote=True)}">{escape(link_label)}</a>',
        )

    return safe_text


def detect_text_language(text):
    cyrillic_count = sum(1 for char in text.lower() if "Ð°" <= char <= "Ñ" or char == "Ñ‘")
    latin_count = sum(1 for char in text.lower() if "a" <= char <= "z")
    return "cyrillic" if cyrillic_count > latin_count else "latin"


def build_post_title(text):
    titles = CYRILLIC_TITLES if detect_text_language(text) == "cyrillic" else LATIN_TITLES
    return random.choice(titles)


def add_offer_footer(text):
    footer_tokens = [token for token, _, _ in TEXT_LINK_TOKENS]

    if any(token in text for token in footer_tokens):
        return text

    footer_block = "\n".join(footer_tokens)
    return f"{text}\n\n{footer_block}".strip()


def add_album_footer(text):
    body = (text or "").strip()

    if ALBUM_CHANNEL_URL in body:
        return body

    if not body:
        return ALBUM_CHANNEL_URL

    return f"{body}\n\n{ALBUM_CHANNEL_URL}".strip()


def finalize_post_text(text, is_album=False):
    body = (text or "").strip()

    body = apply_promocode_rule(body)
    return body


def has_visible_emoji(line):
    return bool(re.match(r"^[\W_]*[\U0001F300-\U0001FAFF]", line or ""))


def choose_line_emoji(line):
    lowered = (line or "").lower()

    if (
        "ربح" in lowered
        or "فوز" in lowered
        or "won" in lowered
        or "win" in lowered
        or "winnings" in lowered
        or "paid out" in lowered
        or "profit" in lowered
        or "$" in lowered
        or " دولار" in lowered
        or "دولار " in lowered
        or "ريال" in lowered
        or "ايداع" in lowered
        or "إيداع" in lowered
    ):
        return "💸"
    if "apk" in lowered or "تحميل" in lowered or "تنزيل" in lowered or "تطبيق" in lowered or "اندرويد" in lowered or "أندرويد" in lowered:
        return "📲"
    if (
        "bonus" in lowered
        or "promo" in lowered
        or "promocode" in lowered
        or "promokod" in lowered
        or "بونص" in lowered
        or "مكاف" in lowered
        or "برومو" in lowered
        or "كود" in lowered
    ):
        return "🎁"
    if "1xbet" in lowered or "linebet" in lowered or "dbbet" in lowered or "betkom" in lowered:
        return "🔥"
    if (
        "stavka" in lowered
        or "ставк" in lowered
        or "express" in lowered
        or "экспресс" in lowered
        or "رهان" in lowered
        or "ترشيح" in lowered
        or "اختيار" in lowered
        or "توقع" in lowered
    ):
        return "🎯"
    if "futbol" in lowered or "football" in lowered or "футбол" in lowered or "كرة القدم" in lowered or "مباراة" in lowered:
        return "⚽"
    if "tennis" in lowered or "теннис" in lowered or "تنس" in lowered:
        return "🎾"
    if "basket" in lowered or "баскет" in lowered or "كرة السلة" in lowered or "سلة" in lowered:
        return "🏀"
    if "yuklab" in lowered or "скач" in lowered or "download" in lowered or "تحميل" in lowered or "تنزيل" in lowered:
        return "⬇️"
    if "koeff" in lowered or "коэфф" in lowered or "kf" in lowered or "اودز" in lowered or "أودز" in lowered or "معامل" in lowered:
        return "💎"
    return ""


def choose_opening_emojis(line):
    lowered = (line or "").lower()

    if (
        "bonus" in lowered
        or "promo" in lowered
        or "promocode" in lowered
        or "بونص" in lowered
        or "برومو" in lowered
        or "كود" in lowered
    ):
        return "🎁🔥"
    if (
        "ربح" in lowered
        or "فوز" in lowered
        or "won" in lowered
        or "win" in lowered
        or "winnings" in lowered
        or "paid out" in lowered
        or "profit" in lowered
        or "$" in lowered
        or " دولار" in lowered
        or "دولار " in lowered
    ):
        return "💸🔥"
    if "اود" in lowered or "أود" in lowered or "odds" in lowered or "single" in lowered:
        return "🔥💎"
    if "tennis" in lowered or "تنس" in lowered:
        return "🎾🔥"
    if "basket" in lowered or "سلة" in lowered or "كرة السلة" in lowered:
        return "🏀🔥"
    if "football" in lowered or "futbol" in lowered or "كرة القدم" in lowered or "مباراة" in lowered or re.search(r"\b(?:vs|v)\b", lowered):
        return "⚽🔥"
    if "عاجل" in lowered or "urgent" in lowered or "إصابة" in lowered or "اصابة" in lowered:
        return "🚨🔥"

    line_emoji = choose_line_emoji(line)
    if line_emoji:
        return f"{line_emoji}🔥" if line_emoji != "🔥" else "🔥🚀"
    return ""


def add_thematic_emojis(text):
    lines = [(line or "").strip() for line in (text or "").splitlines()]
    styled_lines = []

    for index, line in enumerate(lines):
        if not line:
            continue
        if has_visible_emoji(line):
            styled_lines.append(line)
            continue
        if index == 0:
            opening_emojis = choose_opening_emojis(line)
            if opening_emojis:
                styled_lines.append(f"{opening_emojis} {line}")
                continue
        emoji = choose_line_emoji(line)
        if emoji:
            styled_lines.append(f"{emoji} {line}")
        else:
            styled_lines.append(line)

    return "\n".join(styled_lines).strip()


def normalize_ai_text(text):
    body = (text or "").strip()
    if not body:
        return body

    body = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", body)
    body = re.sub(r"\s*```$", "", body)
    body = body.strip().strip('"').strip("'").strip()
    body = body.replace("\r\n", "\n")
    body = re.sub(r"\n{3,}", "\n\n", body)
    body = remove_source_brand_residue(body)
    return body


def process_text_with_ai(text):
    if not text:
        return text

    if not AI_ENABLED:
        return text

    if not AI_API_KEY:
        print("AI Ð²Ñ‹ÐºÐ»ÑŽÑ‡ÐµÐ½: Ð½Ðµ Ð½Ð°Ð¹Ð´ÐµÐ½ AI_API_KEY, Ð¾Ñ‚Ð¿Ñ€Ð°Ð²Ð»ÑÑŽ Ð¸ÑÑ…Ð¾Ð´Ð½Ñ‹Ð¹ Ñ‚ÐµÐºÑÑ‚")
        return text

    user_prompt = text
    if AI_TARGET_LANG:
        user_prompt = f"Target language: {AI_TARGET_LANG}\n\n{text}"

    system_prompt = (
        f"{AI_STYLE_PROMPT}\n\n"
        "Write only the final Telegram post body. "
        "Output in the requested target language when it is provided. "
        "Keep facts, teams, odds, promo details, and intent accurate. "
        "Do not invent scores, odds, claims, or urgency. "
        "Use natural Arabic that reads like a real channel post, not a literal translation. "
        "Make the text compact, stylish, and easy to scan in Telegram. "
        "Prefer 3 to 7 short lines with good rhythm. "
        "Use clean unicode emojis with taste. "
        "The opening line should usually include 1 or 2 strong contextual emojis. "
        "Promo, winnings, odds, and key sports lines can use money, fire, rocket, gift, or sports emojis when they fit. "
        "Do not overload every line. "
        "Keep target brand names only when they already appear in the source text you receive. "
        "Never mention the source channel, source attribution, or source betting brands. "
        "Do not add hashtags, markdown, bullet lists, explanations, or quotation marks around the answer. "
        "Do not add footer links or button labels. "
        "Return only the rewritten body."
    )

    payload = {
        "model": AI_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }

    headers = {
        "Authorization": f"Bearer {AI_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=90,
        )
        data = response.json()

        if response.status_code != 200:
            print("AI Ð¾ÑˆÐ¸Ð±ÐºÐ°:", response.status_code, data)
            return text

        ai_text = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )
        ai_text = normalize_ai_text(ai_text)

        if not ai_text:
            print("AI Ð²ÐµÑ€Ð½ÑƒÐ» Ð¿ÑƒÑÑ‚Ð¾Ð¹ Ñ‚ÐµÐºÑÑ‚, Ð¾Ñ‚Ð¿Ñ€Ð°Ð²Ð»ÑÑŽ Ð¸ÑÑ…Ð¾Ð´Ð½Ñ‹Ð¹")
            return text

        print("AI Ñ‚ÐµÐºÑÑ‚ Ð¿Ð¾Ð´Ð³Ð¾Ñ‚Ð¾Ð²Ð»ÐµÐ½")
        return ai_text

    except Exception as e:
        print("AI Ð¾ÑˆÐ¸Ð±ÐºÐ°:", str(e))
        return text


def build_final_text(post_data, use_ai=True):
    source_text = post_data.get("text", "")
    inline_partners = bool(post_data.get("inline_partners"))
    primary_partner_only = bool(post_data.get("primary_partner_only"))
    ai_input = prepare_text_for_ai(source_text, inline_partners=inline_partners)

    text = post_data.get("processed_text")
    if text is None:
        text = process_text_with_ai(ai_input) if use_ai else ai_input

    text = remove_source_brand_residue(text)
    text = add_thematic_emojis(text)

    if inline_partners and not has_target_partner_block(text):
        partner_block = build_primary_partner_block() if primary_partner_only else build_partner_block()
        if partner_block:
            text = f"{text}\n\n{partner_block}".strip()

    media_count = post_data.get("media_count", len(post_data.get("media_items", [])))
    return finalize_post_text(text, is_album=media_count > 1)



def send_text(text, with_buttons=False, chat_id=None, reply_markup=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    normalized_text = text

    if text in {"ðŸ‘‡ Ð‘Ð¾Ð½ÑƒÑÐ½Ñ‹Ðµ ÑÑÑ‹Ð»ÐºÐ¸", "Ã°Å¸â€˜â€¡ Ãâ€˜ÃÂ¾ÃÂ½Ã‘Æ’Ã‘ÂÃÂ½Ã‘â€¹ÃÂµ Ã‘ÂÃ‘ÂÃ‘â€¹ÃÂ»ÃÂºÃÂ¸"}:
        normalized_text = BONUS_BUTTON_MESSAGE

    payload = {
        "chat_id": chat_id or TARGET_CHANNEL,
        "text": prepare_telegram_text(normalized_text),
        "disable_web_page_preview": True,
        "parse_mode": "HTML",
    }

    if reply_markup:
        payload["reply_markup"] = reply_markup
    elif with_buttons:
        button_markup = build_reply_markup()
        if button_markup:
            payload["reply_markup"] = button_markup

    return requests.post(url, json=payload, timeout=60)



def send_one_photo(photo_path, caption, with_buttons=False, chat_id=None, reply_markup=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"

    data = {
        "chat_id": chat_id or TARGET_CHANNEL,
        "caption": prepare_telegram_text(caption, limit=1024),
        "parse_mode": "HTML",
    }

    if reply_markup:
        data["reply_markup"] = json.dumps(reply_markup, ensure_ascii=False)
    elif with_buttons:
        button_markup = build_reply_markup()
        if button_markup:
            data["reply_markup"] = json.dumps(button_markup, ensure_ascii=False)

    with open(photo_path, "rb") as photo_file:
        files = {"photo": photo_file}
        return requests.post(url, data=data, files=files, timeout=120)


def send_one_video(video_path, caption, with_buttons=False, chat_id=None, reply_markup=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendVideo"

    data = {
        "chat_id": chat_id or TARGET_CHANNEL,
        "caption": prepare_telegram_text(caption, limit=1024),
        "parse_mode": "HTML",
        "supports_streaming": True,
    }

    if reply_markup:
        data["reply_markup"] = json.dumps(reply_markup, ensure_ascii=False)
    elif with_buttons:
        button_markup = build_reply_markup()
        if button_markup:
            data["reply_markup"] = json.dumps(button_markup, ensure_ascii=False)

    with open(video_path, "rb") as video_file:
        files = {"video": video_file}
        return requests.post(url, data=data, files=files, timeout=180)


def send_media_group(media_items, caption, chat_id=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMediaGroup"

    media = []
    opened_files = {}

    try:
        for i, media_item in enumerate(media_items):
            media_type = media_item.get("type", "photo")
            media_path = media_item.get("path")
            file_key = f"media{i}"
            opened_files[file_key] = open(media_path, "rb")

            item = {
                "type": media_type,
                "media": f"attach://{file_key}",
            }

            if i == 0 and caption:
                item["caption"] = prepare_telegram_text(caption, limit=1024)
                item["parse_mode"] = "HTML"
            if media_type == "video":
                item["supports_streaming"] = True

            media.append(item)

        data = {
            "chat_id": chat_id or TARGET_CHANNEL,
            "media": json.dumps(media, ensure_ascii=False),
        }

        return requests.post(url, data=data, files=opened_files, timeout=180)

    finally:
        for f in opened_files.values():
            f.close()


def send_poll(question, options, chat_id=None, is_anonymous=False, allows_multiple_answers=False):
    payload = {
        "chat_id": chat_id or TARGET_CHANNEL,
        "question": question[:300],
        "options": options[:10],
        "is_anonymous": is_anonymous,
        "allows_multiple_answers": allows_multiple_answers,
    }
    return bot_api("sendPoll", payload)



def load_state():
    if not os.path.exists(STATE_FILE):
        return {}

    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}



def save_state(state):
    os.makedirs("data", exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def load_pending():
    if not os.path.exists(PENDING_FILE):
        return {}

    try:
        with open(PENDING_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_pending(pending):
    os.makedirs("data", exist_ok=True)
    with open(PENDING_FILE, "w", encoding="utf-8") as f:
        json.dump(pending, f, ensure_ascii=False, indent=2)


def bot_api(method, payload):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    return requests.post(url, json=payload, timeout=60)



def get_post_key(message):
    if message.grouped_id:
        return f"group_{message.grouped_id}"
    return f"msg_{message.id}"


def utf16_offset_to_index(text, offset):
    if offset <= 0:
        return 0

    units_seen = 0
    for index, char in enumerate(text):
        char_units = 2 if ord(char) > 0xFFFF else 1
        if units_seen + char_units > offset:
            return index
        units_seen += char_units
        if units_seen == offset:
            return index + 1

    return len(text)


def contains_flag_emoji(text):
    for char in text or "":
        codepoint = ord(char)
        if 0x1F1E6 <= codepoint <= 0x1F1FF:
            return True
    return False


def choose_custom_emoji_replacement(text, index):
    line_start = text.rfind("\n", 0, index) + 1
    line_end = text.find("\n", index)
    if line_end == -1:
        line_end = len(text)

    line = text[line_start:line_end].lower()

    if "express" in line or "ekspress" in line or "ÑÐºÑÐ¿Ñ€ÐµÑÑ" in line:
        return "🔥"
    if "vip" in line:
        return "👑"
    if "1xbet" in line or "1x" in line:
        return "💙"
    if "dbbet" in line or "db bet" in line:
        return "🖤"
    if "betkom" in line:
        return "🟢"
    if "promo" in line or "promokod" in line or "kod:" in line or "ÐºÐ¾Ð´" in line:
        return "🎟️"
    if "bonus" in line or "aksiya" in line or "akciya" in line or "Ð°ÐºÑ†Ð¸Ñ" in line:
        return "🎁"
    if "apk" in line:
        return "📲"
    if "football" in line or "futbol" in line or "Ñ„ÑƒÑ‚Ð±Ð¾Ð»" in line:
        return "⚽"
    if "basket" in line or "Ð±Ð°ÑÐºÐµÑ‚" in line:
        return "🏀"
    if "tennis" in line or "Ñ‚ÐµÐ½Ð½Ð¸Ñ" in line:
        return "🎾"

    return ""


def replace_custom_emojis(text, entities):
    if not text or not entities:
        return text

    replacements = []
    for entity in entities:
        if entity.__class__.__name__ != "MessageEntityCustomEmoji":
            continue

        start = utf16_offset_to_index(text, entity.offset)
        end = utf16_offset_to_index(text, entity.offset + entity.length)
        original_fragment = text[start:end]
        if contains_flag_emoji(original_fragment):
            replacement = original_fragment
        else:
            replacement = choose_custom_emoji_replacement(text, start) or original_fragment
        replacements.append((start, end, replacement))

    if not replacements:
        return text

    for start, end, replacement in sorted(replacements, reverse=True):
        before = text[:start]
        after = text[end:]
        prefix = "" if not before or before.endswith((" ", "\n")) else " "
        suffix = "" if not after or after.startswith((" ", "\n", ".", ",", ":", ";", "!", "?")) else " "
        text = before + prefix + replacement + suffix + after

    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    print("Custom emoji replaced:", len(replacements))
    return text


def get_message_text(message):
    text = message.raw_text or ""
    return replace_custom_emojis(text, getattr(message, "entities", None))


def is_service_message(message):
    return getattr(message, "action", None) is not None


def get_poll_data(message):
    media = getattr(message, "media", None)
    poll_wrapper = getattr(media, "poll", None)
    poll = getattr(poll_wrapper, "poll", None)

    if not poll:
        return None

    answers = []
    for answer in getattr(poll, "answers", []) or []:
        answer_text = getattr(answer, "text", "")
        if answer_text:
            answers.append(answer_text)

    if len(answers) < 2:
        return None

    question = getattr(poll, "question", "") or ""
    return {
        "question": question,
        "options": answers,
        "multiple_choice": bool(getattr(poll, "multiple_choice", False)),
        "is_quiz": bool(getattr(poll, "quiz", False)),
    }


def has_video_media(message):
    if getattr(message, "video", None):
        return True

    media = getattr(message, "media", None)
    document = getattr(media, "document", None)
    mime_type = getattr(document, "mime_type", "") if document else ""
    return mime_type.startswith("video/")


def has_downloadable_image(message):
    if getattr(message, "photo", None):
        return True

    media = getattr(message, "media", None)
    document = getattr(media, "document", None)
    mime_type = getattr(document, "mime_type", "") if document else ""
    return mime_type.startswith("image/")


def get_supported_media_type(message):
    if has_downloadable_image(message):
        return "photo"
    if has_video_media(message):
        return "video"
    return None


def has_file_media(message):
    media = getattr(message, "media", None)
    document = getattr(media, "document", None)
    if not document:
        return False

    mime_type = getattr(document, "mime_type", "") or ""
    if mime_type.startswith("image/") or mime_type.startswith("video/"):
        return False
    return True


def should_skip_post(messages):
    post_messages = messages or []
    if not post_messages:
        return True

    if any(is_service_message(message) for message in post_messages):
        print("Skip reason: service message")
        return True

    if any(get_poll_data(message) for message in post_messages):
        print("Skip reason: poll")
        return True

    if any(has_file_media(message) for message in post_messages):
        print("Skip reason: file")
        return True

    has_text = any(get_message_text(message).strip() for message in post_messages)
    if count_supported_media(post_messages) == 0 and not has_text:
        print("Skip reason: no supported content")
        return True

    return False


def cleanup_media_items(media_items):
    for media_item in media_items or []:
        media_path = media_item.get("path")
        if not media_path:
            continue
        try:
            if os.path.exists(media_path):
                os.remove(media_path)
        except Exception as e:
            print("Cleanup warning:", str(e))


def cleanup_temp_media_dir():
    os.makedirs("data", exist_ok=True)
    temp_prefixes = ("photo_", "document_")
    temp_suffixes = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".mp4")

    for file_name in os.listdir("data"):
        if not file_name.startswith(temp_prefixes):
            continue
        if not file_name.lower().endswith(temp_suffixes):
            continue

        file_path = os.path.join("data", file_name)
        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
        except Exception as e:
            print("Startup cleanup warning:", str(e))


async def get_latest_post_key(client, entity):
    messages = await client.get_messages(entity, limit=1)
    if not messages:
        return None
    return get_post_key(messages[0])


async def ensure_client_connected(client):
    if client.is_connected():
        return True

    print("Telethon disconnected, trying to reconnect...")

    try:
        await client.connect()
        if not await client.is_user_authorized():
            print("Reconnect failed: session is not authorized")
            return False

        print("Telethon reconnected")
        return True
    except Exception as e:
        print("Reconnect error:", str(e))
        return False


async def rebuild_post_media(client, entity, post_data):
    media_items = post_data.get("media_items")
    if media_items is None:
        media_items = [
            {"type": "photo", "path": path}
            for path in (post_data.get("photo_paths") or [])
        ]

    if media_items and all(os.path.exists(item.get("path", "")) for item in media_items):
        return post_data

    message_id = post_data.get("source_message_id")
    if not message_id:
        return post_data

    source_message = await client.get_messages(entity, ids=message_id)
    if not source_message:
        return post_data

    post_messages = [source_message]
    if source_message.grouped_id:
        nearby_ids = list(range(max(1, message_id - 10), message_id + 11))
        nearby_messages = await client.get_messages(entity, ids=nearby_ids)
        album_messages = [
            message
            for message in nearby_messages
            if message and message.grouped_id == source_message.grouped_id
        ]
        if album_messages:
            album_messages.sort(key=lambda message: message.id)
            post_messages = album_messages

    rebuilt_media_items = []
    for message in post_messages:
        media_type = get_supported_media_type(message)
        if not media_type:
            continue

        media_path = await client.download_media(message, file="data/")
        if media_path:
            rebuilt_media_items.append({"type": media_type, "path": media_path})

    rebuilt_post = dict(post_data)
    rebuilt_post["media_items"] = rebuilt_media_items
    rebuilt_post["photo_paths"] = []
    return rebuilt_post


def count_supported_media(messages):
    return sum(1 for message in messages if get_supported_media_type(message))



async def get_post_data(client, entity):
    messages = await client.get_messages(entity, limit=1)

    if not messages:
        return None

    last_msg = messages[0]
    post_messages = [last_msg]
    text = get_message_text(last_msg)

    if last_msg.grouped_id:
        recent_messages = await client.get_messages(entity, limit=20)
        album_messages = [m for m in recent_messages if m.grouped_id == last_msg.grouped_id]
        album_messages.sort(key=lambda m: m.id)

        if album_messages:
            post_messages = album_messages
            for m in album_messages:
                if m.raw_text:
                    text = get_message_text(m)
                    break

    if should_skip_post(post_messages):
        return None

    inline_partners = has_partner_mentions(text)
    has_companies = has_company_mentions(text)
    if PRIMARY_PARTNER_ONLY_MODE and has_companies:
        inline_partners = True
    primary_partner_only = should_use_primary_partner_fallback(text)

    return {
        "key": get_post_key(last_msg),
        "text": text,
        "media_items": [],
        "photo_paths": [],
        "media_count": count_supported_media(post_messages),
        "source_message_id": last_msg.id,
        "inline_partners": inline_partners,
        "primary_partner_only": primary_partner_only,
        "with_buttons": not inline_partners and not has_companies,
    }


async def build_post_data_from_messages(client, messages):
    if not messages:
        return None

    post_messages = sorted(messages, key=lambda m: m.id)
    last_msg = post_messages[-1]
    text = ""

    if should_skip_post(post_messages):
        return None

    for message in post_messages:
        if message.raw_text:
            text = get_message_text(message)
            break

    if not text:
        text = get_message_text(last_msg)

    inline_partners = has_partner_mentions(text)
    has_companies = has_company_mentions(text)
    if PRIMARY_PARTNER_ONLY_MODE and has_companies:
        inline_partners = True
    primary_partner_only = should_use_primary_partner_fallback(text)

    return {
        "key": get_post_key(last_msg),
        "text": text,
        "media_items": [],
        "photo_paths": [],
        "media_count": count_supported_media(post_messages),
        "source_message_id": last_msg.id,
        "inline_partners": inline_partners,
        "primary_partner_only": primary_partner_only,
        "with_buttons": not inline_partners and not has_companies,
    }


async def get_new_posts_data(client, entity, last_post_key=None, limit=50):
    messages = await client.get_messages(entity, limit=limit)

    if not messages:
        return []

    grouped_messages = {}
    ordered_keys = []

    for message in messages:
        post_key = get_post_key(message)
        if post_key not in grouped_messages:
            grouped_messages[post_key] = []
            ordered_keys.append(post_key)
        grouped_messages[post_key].append(message)

    new_keys = []
    for post_key in ordered_keys:
        if last_post_key and post_key == last_post_key:
            break
        new_keys.append(post_key)

    new_keys.reverse()

    posts = []
    for post_key in new_keys:
        post_data = await build_post_data_from_messages(client, grouped_messages[post_key])
        if post_data:
            posts.append(post_data)

    posts.sort(key=lambda post: post.get("source_message_id", 0))
    return posts

def response_ok(response):
    try:
        data = response.json()
        return response.status_code == 200 and data.get("ok") is True
    except Exception:
        return response.status_code == 200

def publish_post_to_channel(post_data, chat_id):
    text = post_data.get("processed_text", "")
    media_items = post_data.get("media_items")
    if media_items is None:
        media_items = [
            {"type": "photo", "path": path}
            for path in (post_data.get("photo_paths") or [])
        ]

    with_buttons = bool(post_data.get("with_buttons")) and not post_contains_inline_partners(text)

    if len(media_items) == 0:
        response = send_text(text, with_buttons=with_buttons, chat_id=chat_id)
        print(f"Text sent to {safe_console_text(chat_id)}:", response.status_code)
        print(response.text)
        return response_ok(response)

    elif len(media_items) == 1:
        media_item = media_items[0]
        if media_item.get("type") == "video":
            response = send_one_video(media_item["path"], text, with_buttons=with_buttons, chat_id=chat_id)
            print(f"One video sent to {safe_console_text(chat_id)}:", response.status_code)
        else:
            response = send_one_photo(media_item["path"], text, with_buttons=with_buttons, chat_id=chat_id)
            print(f"One photo sent to {safe_console_text(chat_id)}:", response.status_code)
        print(response.text)
        return response_ok(response)

    else:
        response = send_media_group(media_items, text, chat_id=chat_id)
        print(f"Album sent to {safe_console_text(chat_id)} ({len(media_items)} media):", response.status_code)
        print(response.text)

        if not response_ok(response):
            return False

        if not with_buttons:
            return True

        buttons_response = send_text("ðŸ‘‡ Ð‘Ð¾Ð½ÑƒÑÐ½Ñ‹Ðµ ÑÑÑ‹Ð»ÐºÐ¸", with_buttons=True, chat_id=chat_id)
        print(f"Buttons sent to {safe_console_text(chat_id)}:", buttons_response.status_code)
        print(buttons_response.text)
        return response_ok(buttons_response)


def publish_post(post_data, use_ai=True):
    prepared_post = dict(post_data)
    prepared_post["processed_text"] = build_final_text(prepared_post, use_ai=use_ai)

    if not TARGET_CHANNELS:
        print("Error: TARGET_CHANNEL or TARGET_CHANNELS is missing")
        return False

    for chat_id in TARGET_CHANNELS:
        print("Publishing to target:", safe_console_text(chat_id))
        if not publish_post_to_channel(prepared_post, chat_id):
            return False

    return True


def send_post_to_review(post_data):
    if not REVIEW_MODE:
        return False

    text = build_final_text(post_data, use_ai=False)
    media_items = post_data.get("media_items")
    if media_items is None:
        media_items = [
            {"type": "photo", "path": path}
            for path in (post_data.get("photo_paths") or [])
        ]
    moderation_markup = build_moderation_markup(post_data["key"])

    if len(media_items) == 0:
        response = send_text(
            text,
            chat_id=REVIEW_CHANNEL_ID,
            reply_markup=moderation_markup,
        )
        print("Review text sent:", response.status_code)
        print(response.text)
        return response_ok(response)

    if len(media_items) == 1:
        media_item = media_items[0]
        if media_item.get("type") == "video":
            response = send_one_video(
                media_item["path"],
                text,
                chat_id=REVIEW_CHANNEL_ID,
                reply_markup=moderation_markup,
            )
            print("Review video sent:", response.status_code)
        else:
            response = send_one_photo(
                media_item["path"],
                text,
                chat_id=REVIEW_CHANNEL_ID,
                reply_markup=moderation_markup,
            )
            print("Review photo sent:", response.status_code)
        print(response.text)
        return response_ok(response)

    response = send_media_group(media_items, text, chat_id=REVIEW_CHANNEL_ID)
    print("Review album sent:", response.status_code)
    print(response.text)

    if not response_ok(response):
        return False

    buttons_response = send_text(
        f"Moderation for {post_data['key']}",
        chat_id=REVIEW_CHANNEL_ID,
        reply_markup=moderation_markup,
    )
    print("Review buttons sent:", buttons_response.status_code)
    print(buttons_response.text)
    return response_ok(buttons_response)


def queue_post_for_review(post_data):
    pending = load_pending()
    prepared_post = dict(post_data)
    ai_input = prepare_text_for_ai(
        post_data.get("text", ""),
        inline_partners=bool(post_data.get("inline_partners")),
    )
    prepared_post["processed_text"] = process_text_with_ai(ai_input)
    prepared_post["status"] = "pending"

    success = send_post_to_review(prepared_post)
    cleanup_media_items(prepared_post.get("media_items") or [])
    if not success:
        return False

    prepared_post["media_items"] = []
    prepared_post["photo_paths"] = []
    pending[prepared_post["key"]] = prepared_post
    save_pending(pending)
    return True


def answer_callback(callback_query_id, text):
    bot_api("answerCallbackQuery", {
        "callback_query_id": callback_query_id,
        "text": text,
    })


async def handle_moderation_updates(client, entity, state):
    if not REVIEW_MODE:
        return

    payload = {
        "timeout": 1,
        "allowed_updates": ["callback_query"],
    }

    if state.get("bot_update_offset"):
        payload["offset"] = state["bot_update_offset"]

    response = bot_api("getUpdates", payload)
    if not response_ok(response):
        print("getUpdates error:", response.status_code, response.text)
        return

    updates = response.json().get("result", [])
    if not updates:
        return

    pending = load_pending()

    for update in updates:
        state["bot_update_offset"] = update["update_id"] + 1
        callback = update.get("callback_query")
        if not callback:
            continue

        action_data = callback.get("data", "")
        if ":" not in action_data:
            continue

        action, post_key = action_data.split(":", 1)
        post_data = pending.get(post_key)

        if not post_data:
            answer_callback(callback["id"], "Post not found")
            continue

        if post_data.get("status") != "pending":
            answer_callback(callback["id"], f"Already {post_data.get('status')}")
            continue

        if action == "approve":
            prepared_post = await rebuild_post_media(client, entity, post_data)
            success = publish_post(prepared_post, use_ai=False)
            cleanup_media_items(prepared_post.get("media_items") or [])
            if success:
                post_data["status"] = "approved"
                post_data["media_items"] = []
                post_data["photo_paths"] = []
                pending[post_key] = post_data
                save_pending(pending)
                answer_callback(callback["id"], "Approved and published")
            else:
                answer_callback(callback["id"], "Publish error")

        elif action == "reject":
            post_data["status"] = "rejected"
            cleanup_media_items(post_data.get("media_items") or [])
            post_data["media_items"] = []
            post_data["photo_paths"] = []
            pending[post_key] = post_data
            save_pending(pending)
            answer_callback(callback["id"], "Rejected")

    save_state(state)



async def main():
    if not API_ID:
        print("Error: TG_API_ID is missing")
        return

    if not API_HASH:
        print("Error: TG_API_HASH is missing")
        return

    if not SOURCE_CHANNEL:
        print("Error: SOURCE_CHANNEL is missing")
        return

    if not TARGET_CHANNELS:
        print("Error: TARGET_CHANNEL or TARGET_CHANNELS is missing")
        return

    if not BOT_TOKEN:
        print("Error: BOT_TOKEN is missing")
        return

    if SESSION_STRING:
        client = TelegramClient(StringSession(SESSION_STRING), int(API_ID), API_HASH)
    else:
        client = TelegramClient("data/session_name", int(API_ID), API_HASH)

    await client.start()
    cleanup_temp_media_dir()
    print("Telethon connected")
    print("Auto mode started")
    print("Review mode:", "ON" if REVIEW_MODE else "OFF")
    if REVIEW_MODE:
        print("Review channel:", safe_console_text(REVIEW_CHANNEL_ID))
    print("Target channels:", ", ".join(safe_console_text(chat_id) for chat_id in TARGET_CHANNELS))

    entity = await resolve_source_entity(client)
    print("SOURCE_CHANNEL:", safe_console_text(SOURCE_CHANNEL))
    print("Source found:", safe_console_text(getattr(entity, "title", "no title")))
    state = load_state()

    try:
        first_post_key = await get_latest_post_key(client, entity)
        current_source_signature = get_source_signature(entity)

        if not first_post_key:
            print("No messages in source channel")
            await client.disconnect()
            return

        if state.get("source_signature") != current_source_signature:
            state["source_signature"] = current_source_signature
            state["last_post_key"] = first_post_key
            save_state(state)
            save_pending({})
            print("Source changed: current last post saved, waiting for new posts")

        if not state.get("last_post_key"):
            state["last_post_key"] = first_post_key
            state["source_signature"] = current_source_signature
            save_state(state)
            print("First start: current last post saved, waiting for new posts")

        while True:
            try:
                if not await ensure_client_connected(client):
                    await asyncio.sleep(CHECK_INTERVAL)
                    continue

                await handle_moderation_updates(client, entity, state)
                new_posts = await get_new_posts_data(client, entity, state.get("last_post_key"))
                print("New posts found:", len(new_posts))
                print("State key:", state.get("last_post_key"))

                if not new_posts:
                    print("No new posts")
                    await asyncio.sleep(CHECK_INTERVAL)
                    continue

                for post_data in new_posts:
                    print(f"Processing post: {post_data['key']}")
                    if REVIEW_MODE:
                        print("Route: review channel")
                        prepared_post = await rebuild_post_media(client, entity, post_data)
                        success = queue_post_for_review(prepared_post)
                    else:
                        print("Route: target channels")
                        prepared_post = await rebuild_post_media(client, entity, post_data)
                        success = publish_post(prepared_post)
                        cleanup_media_items(prepared_post.get("media_items") or [])

                    if success:
                        state["last_post_key"] = post_data["key"]
                        save_state(state)
                        print("Post sent and state updated")
                    else:
                        print("Send error: state.json not updated")
                        break

            except Exception as e:
                print("Loop error:", str(e))

            await asyncio.sleep(CHECK_INTERVAL)

    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
