from dotenv import load_dotenv
import os
import asyncio
import json
import random
import re
import sys
import time
import requests
from datetime import datetime
from html import escape
from telethon import TelegramClient
from telethon.sessions import StringSession
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

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


def env_flag(key, default=False):
    value = os.getenv(key)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def route_env_prefix(route_id):
    return re.sub(r"[^A-Z0-9]+", "_", (route_id or "").upper()).strip("_")


def route_backfill_latest_once_enabled(route_id):
    if not route_id:
        return False
    return env_flag(f"{route_env_prefix(route_id)}_BACKFILL_LATEST_ONCE", False)


def route_skip_to_latest_once_enabled(route_id):
    if not route_id:
        return False
    return env_flag(f"{route_env_prefix(route_id)}_SKIP_TO_LATEST_ONCE", False)


def route_startup_skip_backlog_enabled(route_id):
    if route_id:
        scoped_value = os.getenv(f"{route_env_prefix(route_id)}_SKIP_BACKLOG_ON_STARTUP")
        if scoped_value is not None:
            return scoped_value.strip().lower() in {"1", "true", "yes", "on"}
    return env_flag("SKIP_BACKLOG_ON_STARTUP", True)


def route_min_source_message_id(route_id):
    if not route_id:
        return None

    value = (os.getenv(f"{route_env_prefix(route_id)}_MIN_SOURCE_MESSAGE_ID") or "").strip()
    if not value or not value.isdigit():
        return None
    return int(value)


def route_daily_post_limit(route_id):
    if route_id:
        scoped_value = (os.getenv(f"{route_env_prefix(route_id)}_DAILY_POST_LIMIT") or "").strip()
        if scoped_value.isdigit():
            return max(0, int(scoped_value))

    value = (os.getenv("DAILY_POST_LIMIT") or "5").strip()
    if value.isdigit():
        return max(0, int(value))
    return 5


def route_daily_limit_timezone():
    return (os.getenv("DAILY_LIMIT_TIMEZONE") or "Europe/Warsaw").strip() or "Europe/Warsaw"


API_ID = os.getenv("TG_API_ID")
API_HASH = os.getenv("TG_API_HASH")
SOURCE_CHANNEL = (os.getenv("SOURCE_CHANNEL") or "").strip()
TARGET_CHANNEL = (os.getenv("TARGET_CHANNEL") or "").strip()
TARGET_CHANNELS = parse_telegram_peers(os.getenv("TARGET_CHANNELS", ""))
if not TARGET_CHANNELS and TARGET_CHANNEL:
    TARGET_CHANNELS = [parse_telegram_peer(TARGET_CHANNEL)]
DEFAULT_TARGET_CHANNEL = TARGET_CHANNELS[0] if TARGET_CHANNELS else parse_telegram_peer(TARGET_CHANNEL)
SOURCE_CHANNEL_2 = (os.getenv("SOURCE_CHANNEL_2") or "").strip()
TARGET_CHANNEL_2 = (os.getenv("TARGET_CHANNEL_2") or "").strip()
TARGET_CHANNELS_2 = parse_telegram_peers(os.getenv("TARGET_CHANNELS_2", ""))
if not TARGET_CHANNELS_2 and TARGET_CHANNEL_2:
    TARGET_CHANNELS_2 = [parse_telegram_peer(TARGET_CHANNEL_2)]
SOURCE_CHANNEL_3 = (os.getenv("SOURCE_CHANNEL_3") or "").strip()
TARGET_CHANNEL_3 = (os.getenv("TARGET_CHANNEL_3") or "").strip()
TARGET_CHANNELS_3 = parse_telegram_peers(os.getenv("TARGET_CHANNELS_3", ""))
if not TARGET_CHANNELS_3 and TARGET_CHANNEL_3:
    TARGET_CHANNELS_3 = [parse_telegram_peer(TARGET_CHANNEL_3)]
REVIEW_CHANNEL_ID = os.getenv("REVIEW_CHANNEL_ID", "").strip()
if REVIEW_CHANNEL_ID.startswith("100"):
    REVIEW_CHANNEL_ID = f"-{REVIEW_CHANNEL_ID}"
MODERATION_ENABLED = env_flag("MODERATION_ENABLED", False)
BOT_TOKEN = os.getenv("BOT_TOKEN")
SESSION_STRING = os.getenv("TG_SESSION_STRING", "").strip()
AI_ENABLED = env_flag("AI_ENABLED", False)
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
PRIMARY_PARTNER_ONLY_MODE = env_flag("PRIMARY_PARTNER_ONLY_MODE", False)

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
PROCESS_BOOT_ID = str(int(time.time()))
try:
    DAILY_LIMIT_TZ = ZoneInfo(route_daily_limit_timezone())
except ZoneInfoNotFoundError:
    DAILY_LIMIT_TZ = datetime.now().astimezone().tzinfo

TEXT_LINK_TOKENS = [
    ("[[APK1]]", "LuckyPari APK", LUCKYPARI_APK_URL),
    ("[[APK2]]", "UltraPari APK", ULTRAPARI_APK_URL),
    ("[[APK3]]", "WinWin APK", WINWIN_APK_URL),
    ("[[APK4]]", "Linebet APK", LINEBET_APK_URL),
]
TARGET_PARTNER_TOKEN_PATTERN = re.compile(r"\[\[PARTNER\d+\]\]")
INLINE_LINK_TOKEN_PATTERN = re.compile(r"\[\[(?:PARTNER|APK)\d+\]\]")

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
PROMOCODE_MARKER_PATTERN = re.compile(
    r"(?i)\b(?:promo\s*code|promocode|code\s*promo|promo\s*cod(?:e)?|كود(?:\s*(?:البرومو|العرض))?|رمز(?:\s*البرومو)?|برومو\s*كود)\b"
)
PROMOCODE_LINE_VALUE_PATTERN = re.compile(
    r"(?is)^(?P<prefix>\s*(?:[^\w\u0600-\u06FF]+?\s*)?(?:promo\s*code|promocode|code\s*promo|promo\s*cod(?:e)?|كود(?:\s*(?:البرومو|العرض))?|رمز(?:\s*البرومو)?|برومو\s*كود)\s*[:：\-–—]?\s*)(?P<code>[A-Za-z0-9_-]{3,})(?P<suffix>.*)$"
)
PROMOCODE_ONLY_PATTERN = re.compile(
    r"(?im)^\s*(?:[^\w\u0600-\u06FF]+?\s*)?(?:promo\s*code|promocode|code\s*promo|promo\s*cod(?:e)?|كود(?:\s*(?:البرومو|العرض))?|رمز(?:\s*البرومو)?|برومو\s*كود)\b.*$"
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
NEW_POST_SCAN_LIMIT = 200
TELEGRAM_REQUEST_RETRIES = 3
MEDIA_DOWNLOAD_RETRIES = 3
RETRY_DELAY_SECONDS = 2


def safe_console_text(value):
    text = str(value)
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    return text.encode(encoding, errors="replace").decode(encoding, errors="replace")


def get_target_channel_env_suffix(chat_id):
    suffix = re.sub(r"\D+", "", str(chat_id or ""))
    return suffix or None


def get_target_channel_override(chat_id=None):
    suffix = get_target_channel_env_suffix(chat_id)
    if not suffix:
        return {}

    override = {}
    promocode_text = os.getenv(f"TARGET_PROMOCODE_{suffix}", "").strip()
    button3_text = os.getenv(f"TARGET_BUTTON3_TEXT_{suffix}", "").strip()
    button3_url = os.getenv(f"TARGET_BUTTON3_URL_{suffix}", "").strip()

    if promocode_text:
        override["promocode_text"] = promocode_text
    if button3_text:
        override["button3_text"] = button3_text
    if button3_url:
        override["button3_url"] = button3_url

    return override


def get_target_promocode_text(chat_id=None):
    override = get_target_channel_override(chat_id)
    return override.get("promocode_text") or PROMOCODE_TEXT


def get_target_companies(chat_id=None):
    override = get_target_channel_override(chat_id)
    companies = [dict(company) for company in ALL_TARGET_COMPANIES]

    if companies:
        if override.get("button3_text"):
            companies[0]["name"] = normalize_company_name(override["button3_text"], companies[0].get("name") or "LUCKYPARI")
        if override.get("button3_url"):
            companies[0]["url"] = override["button3_url"]

    return companies[:1] if PRIMARY_PARTNER_ONLY_MODE else companies


def get_button_links(chat_id=None):
    override = get_target_channel_override(chat_id)
    all_button_links = [
        (BUTTON1_TEXT, BUTTON1_URL),
        (BUTTON2_TEXT, BUTTON2_URL),
        (
            override.get("button3_text") or BUTTON3_TEXT,
            override.get("button3_url") or BUTTON3_URL,
        ),
        (BUTTON4_TEXT, BUTTON4_URL),
    ]
    primary_button_links = [all_button_links[2]] if all_button_links[2][0] and all_button_links[2][1] else []
    return primary_button_links if PRIMARY_PARTNER_ONLY_MODE else all_button_links


def get_promocode_value(chat_id=None):
    tokens = re.findall(r"[A-Za-z0-9_-]{3,}", get_target_promocode_text(chat_id) or "")
    if tokens:
        return tokens[-1]
    return (get_target_promocode_text(chat_id) or "").strip()


def get_source_signature(source_channel, entity):
    source_name = (source_channel or "").strip().lower()
    entity_id = getattr(entity, "id", "")
    return f"{entity_id}:{source_name}"


def normalize_brand_key(value):
    return re.sub(r"[^a-z0-9]+", "", (value or "").lower())


def get_primary_target_company(chat_id=None):
    for company in get_target_companies(chat_id):
        if (company.get("name") or "").strip() and (company.get("url") or "").strip():
            return company
    return {"name": "LUCKYPARI", "url": get_target_channel_override(chat_id).get("button3_url") or BUTTON3_URL, "emoji": "💛"}


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


def build_route(route_id, source_channel, target_channels):
    source_value = (source_channel or "").strip()
    targets = [chat_id for chat_id in (target_channels or []) if str(chat_id).strip()]
    if not source_value or not targets:
        return None

    return {
        "id": route_id,
        "source_channel": source_value,
        "source_entity": parse_telegram_peer(source_value),
        "target_channels": targets,
        "default_target_channel": targets[0],
    }


ROUTES = [
    route
    for route in [
        build_route("route_1", SOURCE_CHANNEL, TARGET_CHANNELS),
        build_route("route_2", SOURCE_CHANNEL_2, TARGET_CHANNELS_2),
        build_route("route_3", SOURCE_CHANNEL_3, TARGET_CHANNELS_3),
    ]
    if route
]


def build_partner_block(chat_id=None):
    lines = []

    for index, company in enumerate(get_target_companies(chat_id), start=1):
        if not (company.get("name") or "").strip():
            continue

        token = f"[[PARTNER{index}]]"
        lines.append(token)

    return "\n\n".join(lines).strip()


def build_primary_partner_block(chat_id=None):
    primary_company = get_primary_target_company(chat_id)
    if not (primary_company.get("name") or "").strip():
        return ""
    return "[[PARTNER1]]"


def line_has_partner_context(line):
    lowered = (line or "").lower()
    return any(keyword in lowered for keyword in PARTNER_LINE_KEYWORDS)


def line_has_registration_context(line):
    lowered = (line or "").lower()
    return any(keyword in lowered for keyword in REGISTRATION_LINE_KEYWORDS)


def contains_target_company_reference(text, chat_id=None):
    body = text or ""
    target_companies = get_target_companies(chat_id)
    target_company_keys = {
        normalize_brand_key(company.get("name"))
        for company in target_companies
        if normalize_brand_key(company.get("name"))
    }

    normalized_body = normalize_brand_key(body)
    if any(key in normalized_body for key in target_company_keys):
        return True

    return any(
        (company.get("url") or "").strip()
        and (company.get("url") or "").strip() in body
        for company in target_companies
    )


def is_target_partner_line(line, chat_id=None):
    body = (line or "").strip()
    if not body:
        return False
    if not line_has_registration_context(body):
        return False
    return contains_target_company_reference(body, chat_id=chat_id)


def should_strip_partner_brand_line(line, chat_id=None):
    body = (line or "").strip()
    if not body:
        return False

    if is_target_partner_line(body, chat_id=chat_id):
        return True

    if not PRIMARY_PARTNER_ONLY_MODE:
        return False

    if contains_target_company_reference(body, chat_id=chat_id):
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


def replace_foreign_bookmaker_mentions(text, chat_id=None):
    primary_name = (get_primary_target_company(chat_id).get("name") or "").strip() or "LUCKYPARI"
    return COMMON_FOREIGN_BOOKMAKER_PATTERN.sub(primary_name, text or "")


def replace_source_brand_mentions(text, chat_id=None):
    body = replace_foreign_bookmaker_mentions(text, chat_id=chat_id)
    primary_name = (get_primary_target_company(chat_id).get("name") or "").strip() or "LUCKYPARI"
    target_companies = get_target_companies(chat_id)
    for pattern, target_index in SOURCE_BRAND_RULES:
        if PRIMARY_PARTNER_ONLY_MODE:
            replacement = primary_name
        else:
            replacement = (target_companies[target_index].get("name") or "").strip() or primary_name
        body = pattern.sub(replacement, body)

    if PRIMARY_PARTNER_ONLY_MODE:
        for company in target_companies[1:]:
            name = (company.get("name") or "").strip()
            if not name:
                continue
            body = re.sub(rf"(?i)\b{re.escape(name)}\b", primary_name, body)

    return body


def is_promocode_only_line(line):
    return bool(PROMOCODE_ONLY_PATTERN.match((line or "").strip()))


def rewrite_promocode_line(line, chat_id=None):
    body = (line or "").strip()
    if not body:
        return body

    match = PROMOCODE_LINE_VALUE_PATTERN.match(body)
    if not match:
        return get_target_promocode_text(chat_id)

    prefix = match.group("prefix") or ""
    suffix = match.group("suffix") or ""
    target_code = get_promocode_value(chat_id)
    rewritten = f"{prefix}{target_code}{suffix}".strip()
    return rewritten or get_target_promocode_text(chat_id)


def normalize_promocode_lines(text, chat_id=None):
    normalized_lines = []
    promocode_added = False

    for raw_line in (text or "").splitlines():
        if is_promocode_only_line(raw_line):
            if not promocode_added:
                normalized_lines.append(rewrite_promocode_line(raw_line, chat_id=chat_id))
                promocode_added = True
            continue
        normalized_lines.append(raw_line)

    return "\n".join(normalized_lines)


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


def has_target_partner_block(text, chat_id=None):
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
            for company in get_target_companies(chat_id)
        )

        if has_target_url:
            return True

    return False


def has_company_mentions(text, chat_id=None):
    return (
        source_mentions_brands(text)
        or line_has_foreign_bookmaker_mention(text)
        or contains_target_company_reference(text, chat_id=chat_id)
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


def is_ignored_code_line(line, chat_id=None):
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
        for company in get_target_companies(chat_id)
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


def remove_ignored_code_lines(text, chat_id=None):
    cleaned_lines = []

    for raw_line in (text or "").splitlines():
        if is_ignored_code_line(raw_line, chat_id=chat_id):
            continue
        cleaned_lines.append(raw_line)

    return "\n".join(cleaned_lines)


def strip_source_markers(text, chat_id=None):
    body = normalize_promocode_lines(remove_ignored_code_lines(text or "", chat_id=chat_id), chat_id=chat_id)
    body = re.sub(r"\[[^\]]+\]", "", body)
    body = re.sub(r"(?<!\S)@[A-Za-z0-9_]{3,}", "", body)
    body = SOURCE_PROMOCODE_PATTERN.sub(get_promocode_value(chat_id), body)
    return body


def prepare_text_for_ai(text, inline_partners=False, chat_id=None):
    body = replace_source_brand_mentions(strip_source_markers(text, chat_id=chat_id), chat_id=chat_id)
    cleaned_lines = []

    for raw_line in body.splitlines():
        line = (raw_line or "").strip()
        if not line:
            cleaned_lines.append("")
            continue

        if should_strip_partner_brand_line(line, chat_id=chat_id):
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

    if inline_partners or has_company_mentions(text, chat_id=chat_id):
        return "اكتب منشوراً عربياً قصيراً وأنيقاً عن العرض مع الحفاظ على نبرة ترويجية واضحة."

    return (text or "").strip()


def remove_source_brand_residue(text, chat_id=None):
    body = strip_source_markers(text, chat_id=chat_id)
    body = SOURCE_LINK_PATTERN.sub("", body)
    body = replace_source_brand_mentions(body, chat_id=chat_id)
    body = normalize_promocode_lines(body, chat_id=chat_id)

    cleaned_lines = []
    for raw_line in body.splitlines():
        line = (raw_line or "").strip()
        if should_strip_partner_brand_line(line, chat_id=chat_id):
            continue
        cleaned_lines.append(raw_line)

    body = "\n".join(cleaned_lines)
    body = re.sub(r"\n{3,}", "\n\n", body)
    return body.strip()


def post_contains_inline_partners(text, chat_id=None):
    return has_target_partner_block(text, chat_id=chat_id)


async def resolve_source_entity(client, source_entity):
    if not isinstance(source_entity, int):
        return await client.get_entity(source_entity)

    normalized_source_id = normalize_telegram_channel_id(source_entity)

    async for dialog in client.iter_dialogs():
        entity = getattr(dialog, "entity", None)
        if getattr(entity, "id", None) == normalized_source_id:
            return entity

    return await client.get_entity(source_entity)


def build_reply_markup(chat_id=None):
    rows = []

    for text, url in get_button_links(chat_id):
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


def apply_promocode_rule(text, chat_id=None):
    text = normalize_promocode_lines((text or "").strip(), chat_id=chat_id)
    promocode_text = get_target_promocode_text(chat_id)
    if not text:
        return promocode_text

    if PROMOCODE_ONLY_PATTERN.search(text):
        return text.strip()

    return f"{text}\n\n{promocode_text}"


def escape_and_bold_numbers(text):
    escaped = escape(text or "")
    return re.sub(r"(?<![\w>])(\d+(?:[.,:/-]\d+)*)", r"<b>\1</b>", escaped)


def has_letter_content(text):
    return bool(re.search(r"[A-Za-z\u0600-\u06FF\u0400-\u04FF]", text or ""))


def build_vs_line_html(line):
    match = re.match(r"^(?P<left>.+?)\s+(?P<sep>(?:VS|Vs|vs|V|v))\s+(?P<right>.+)$", (line or "").strip())
    if not match:
        return None

    left = match.group("left").strip()
    right = match.group("right").strip()
    sep = match.group("sep")
    if not has_letter_content(left) or not has_letter_content(right):
        return None
    if SOURCE_LINK_PATTERN.search(left) or SOURCE_LINK_PATTERN.search(right):
        return None

    return f"<b>{escape(left)}</b> {escape(sep)} <b>{escape(right)}</b>"


def build_score_line_html(line):
    match = re.match(r"^(?P<left>.+?)\s+(?P<score>\d+(?:\s*[:\-]\s*\d+)+)\s+(?P<right>.+)$", (line or "").strip())
    if not match:
        return None

    left = match.group("left").strip()
    score = match.group("score").strip()
    right = match.group("right").strip()
    if not has_letter_content(left) or not has_letter_content(right):
        return None
    if SOURCE_LINK_PATTERN.search(left) or SOURCE_LINK_PATTERN.search(right):
        return None

    return f"<b>{escape(left)}</b> <b>{escape(score)}</b> <b>{escape(right)}</b>"


def render_text_segment_html(segment):
    if not segment:
        return ""

    rendered_parts = []
    last_index = 0

    for match in INLINE_LINK_TOKEN_PATTERN.finditer(segment):
        if match.start() > last_index:
            rendered_parts.append(escape_and_bold_numbers(segment[last_index:match.start()]))
        rendered_parts.append(escape(match.group(0)))
        last_index = match.end()

    if last_index < len(segment):
        rendered_parts.append(escape_and_bold_numbers(segment[last_index:]))

    return "".join(rendered_parts)


def render_line_html(line, chat_id=None):
    raw_line = line or ""
    if is_promocode_only_line(raw_line):
        return f"<b>{escape(raw_line)}</b>"

    special_line = build_score_line_html(raw_line) or build_vs_line_html(raw_line)
    if special_line:
        return special_line

    rendered_parts = []
    last_index = 0
    for match in SOURCE_LINK_PATTERN.finditer(raw_line):
        if match.start() > last_index:
            rendered_parts.append(render_text_segment_html(raw_line[last_index:match.start()]))
        rendered_parts.append(f"<b>{escape(match.group(0))}</b>")
        last_index = match.end()

    if last_index < len(raw_line):
        rendered_parts.append(render_text_segment_html(raw_line[last_index:]))

    return "".join(rendered_parts) if rendered_parts else render_text_segment_html(raw_line)


def prepare_telegram_text(text, limit=None, chat_id=None):
    text = text if text else "[Ð±ÐµÐ· Ñ‚ÐµÐºÑÑ‚Ð°]"
    if limit:
        text = text[:limit]

    safe_lines = []
    for raw_line in text.splitlines():
        safe_lines.append(render_line_html(raw_line or "", chat_id=chat_id))

    safe_text = "\n".join(safe_lines)
    apk_link = f'<a href="{escape(APK_URL, quote=True)}">APK</a>'
    safe_text = re.sub(r"\bAPK\b", apk_link, safe_text, flags=re.IGNORECASE)

    for token, label, url in TEXT_LINK_TOKENS:
        safe_text = safe_text.replace(
            escape(token),
            f'<a href="{escape(url, quote=True)}">{escape(label)}</a>',
        )

    for index, company in enumerate(get_target_companies(chat_id), start=1):
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


def split_long_line(line, max_length=95):
    body = (line or "").strip()
    if len(body) <= max_length:
        return [body] if body else []

    split_patterns = [
        r"(?<=[.!?؟])\s+",
        r"\s*[,:;،]\s+",
        r"\s+(?=لكن|لأن|مع|بعد|قبل|واليوم|وايضا|وأيضا|أيضا|while|and|but|because\b)",
    ]

    for pattern in split_patterns:
        parts = [part.strip() for part in re.split(pattern, body) if part.strip()]
        if len(parts) > 1 and max(len(part) for part in parts) < len(body):
            expanded_parts = []
            for part in parts:
                if len(part) > max_length and part != body:
                    expanded_parts.extend(split_long_line(part, max_length=max_length))
                else:
                    expanded_parts.append(part)
            return expanded_parts

    words = body.split()
    if len(words) < 6:
        return [body]

    chunks = []
    current = []
    for word in words:
        candidate = " ".join(current + [word]).strip()
        if current and len(candidate) > max_length:
            chunks.append(" ".join(current).strip())
            current = [word]
        else:
            current.append(word)

    if current:
        chunks.append(" ".join(current).strip())

    return chunks or [body]


def should_keep_line_isolated(line):
    body = (line or "").strip()
    if not body:
        return False

    if body.startswith("[[PARTNER") or body.startswith("[[APK"):
        return True
    if PROMOCODE_ONLY_PATTERN.match(body):
        return True
    if re.search(r"https?://", body):
        return True
    if len(body) <= 28:
        return True
    if body.endswith(":"):
        return True
    return False


def format_visual_post(text):
    body = (text or "").replace("\r\n", "\n").strip()
    if not body:
        return body

    raw_lines = [line.strip() for line in body.splitlines() if line.strip()]
    if not raw_lines:
        return ""

    expanded_lines = []
    for raw_line in raw_lines:
        if should_keep_line_isolated(raw_line):
            expanded_lines.append(raw_line)
            continue
        expanded_lines.extend(split_long_line(raw_line))

    blocks = []
    current_block = []
    for line in expanded_lines:
        if should_keep_line_isolated(line):
            if current_block:
                blocks.append("\n".join(current_block).strip())
                current_block = []
            blocks.append(line)
            continue

        current_block.append(line)
        if len(current_block) >= 2:
            blocks.append("\n".join(current_block).strip())
            current_block = []

    if current_block:
        blocks.append("\n".join(current_block).strip())

    formatted = "\n\n".join(block for block in blocks if block.strip())
    formatted = re.sub(r"\n{3,}", "\n\n", formatted)
    return formatted.strip()


def finalize_post_text(text, is_album=False, chat_id=None):
    body = format_visual_post((text or "").strip())

    body = apply_promocode_rule(body, chat_id=chat_id)
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
        "Use 2 to 4 short visual paragraphs separated by blank lines. "
        "Most paragraphs should be 1 or 2 short lines, not one dense block. "
        "Prefer 4 to 8 short lines overall with good rhythm. "
        "Use clean unicode emojis with taste. "
        "The opening line should usually include 1 or 2 strong contextual emojis. "
        "Promo, winnings, odds, and key sports lines can use money, fire, rocket, gift, or sports emojis when they fit. "
        "Do not overload every line. "
        "Keep target brand names only when they already appear in the source text you receive. "
        "If the source contains a promo code or code promo line, never keep the original code value. "
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
        response = perform_post_request(
            "https://api.openai.com/v1/chat/completions",
            request_name="OpenAI chat completion",
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


def build_final_text(post_data, use_ai=True, chat_id=None):
    source_text = post_data.get("text", "")
    inline_partners = bool(post_data.get("inline_partners"))
    primary_partner_only = bool(post_data.get("primary_partner_only"))
    ai_input = prepare_text_for_ai(source_text, inline_partners=inline_partners, chat_id=chat_id)

    text = post_data.get("processed_text")
    if text is None:
        text = process_text_with_ai(ai_input) if use_ai else ai_input

    text = remove_source_brand_residue(text, chat_id=chat_id)
    text = add_thematic_emojis(text)

    if inline_partners and not has_target_partner_block(text, chat_id=chat_id):
        partner_block = build_primary_partner_block(chat_id=chat_id) if primary_partner_only else build_partner_block(chat_id=chat_id)
        if partner_block:
            text = f"{text}\n\n{partner_block}".strip()

    media_count = post_data.get("media_count", len(post_data.get("media_items", [])))
    return finalize_post_text(text, is_album=media_count > 1, chat_id=chat_id)


def perform_post_request(url, request_name="request", timeout=60, **kwargs):
    last_response = None

    for attempt in range(1, TELEGRAM_REQUEST_RETRIES + 1):
        try:
            response = requests.post(url, timeout=timeout, **kwargs)
        except requests.RequestException as e:
            print(f"{request_name} network error ({attempt}/{TELEGRAM_REQUEST_RETRIES}):", str(e))
            if attempt < TELEGRAM_REQUEST_RETRIES:
                time.sleep(RETRY_DELAY_SECONDS * attempt)
            else:
                raise
            continue

        last_response = response
        if response.status_code in {429, 500, 502, 503, 504}:
            print(
                f"{request_name} temporary error ({attempt}/{TELEGRAM_REQUEST_RETRIES}):",
                response.status_code,
                safe_console_text(response.text),
            )
            if attempt < TELEGRAM_REQUEST_RETRIES:
                time.sleep(RETRY_DELAY_SECONDS * attempt)
                continue

        return response

    return last_response



def send_text(text, with_buttons=False, chat_id=None, reply_markup=None, reply_to_message_id=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    normalized_text = text

    if text in {"ðŸ‘‡ Ð‘Ð¾Ð½ÑƒÑÐ½Ñ‹Ðµ ÑÑÑ‹Ð»ÐºÐ¸", "Ã°Å¸â€˜â€¡ Ãâ€˜ÃÂ¾ÃÂ½Ã‘Æ’Ã‘ÂÃÂ½Ã‘â€¹ÃÂµ Ã‘ÂÃ‘ÂÃ‘â€¹ÃÂ»ÃÂºÃÂ¸"}:
        normalized_text = BONUS_BUTTON_MESSAGE

    payload = {
        "chat_id": chat_id or TARGET_CHANNEL,
        "text": prepare_telegram_text(normalized_text, chat_id=chat_id),
        "disable_web_page_preview": True,
        "parse_mode": "HTML",
    }

    if reply_to_message_id:
        payload["reply_parameters"] = {"message_id": int(reply_to_message_id)}

    if reply_markup:
        payload["reply_markup"] = reply_markup
    elif with_buttons:
        button_markup = build_reply_markup(chat_id=chat_id)
        if button_markup:
            payload["reply_markup"] = button_markup

    return perform_post_request(url, request_name="sendMessage", json=payload, timeout=60)



def send_one_photo(photo_path, caption, with_buttons=False, chat_id=None, reply_markup=None, reply_to_message_id=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"

    data = {
        "chat_id": chat_id or TARGET_CHANNEL,
        "caption": prepare_telegram_text(caption, limit=1024, chat_id=chat_id),
        "parse_mode": "HTML",
    }

    if reply_to_message_id:
        data["reply_parameters"] = json.dumps({"message_id": int(reply_to_message_id)}, ensure_ascii=False)

    if reply_markup:
        data["reply_markup"] = json.dumps(reply_markup, ensure_ascii=False)
    elif with_buttons:
        button_markup = build_reply_markup(chat_id=chat_id)
        if button_markup:
            data["reply_markup"] = json.dumps(button_markup, ensure_ascii=False)

    with open(photo_path, "rb") as photo_file:
        files = {"photo": photo_file}
        return perform_post_request(
            url,
            request_name="sendPhoto",
            data=data,
            files=files,
            timeout=120,
        )


def send_one_video(video_path, caption, with_buttons=False, chat_id=None, reply_markup=None, reply_to_message_id=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendVideo"

    data = {
        "chat_id": chat_id or TARGET_CHANNEL,
        "caption": prepare_telegram_text(caption, limit=1024, chat_id=chat_id),
        "parse_mode": "HTML",
        "supports_streaming": True,
    }

    if reply_to_message_id:
        data["reply_parameters"] = json.dumps({"message_id": int(reply_to_message_id)}, ensure_ascii=False)

    if reply_markup:
        data["reply_markup"] = json.dumps(reply_markup, ensure_ascii=False)
    elif with_buttons:
        button_markup = build_reply_markup(chat_id=chat_id)
        if button_markup:
            data["reply_markup"] = json.dumps(button_markup, ensure_ascii=False)

    with open(video_path, "rb") as video_file:
        files = {"video": video_file}
        return perform_post_request(
            url,
            request_name="sendVideo",
            data=data,
            files=files,
            timeout=180,
        )


def send_media_group(media_items, caption, chat_id=None, reply_to_message_id=None):
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
                item["caption"] = prepare_telegram_text(caption, limit=1024, chat_id=chat_id)
                item["parse_mode"] = "HTML"
            if media_type == "video":
                item["supports_streaming"] = True

            media.append(item)

        data = {
            "chat_id": chat_id or TARGET_CHANNEL,
            "media": json.dumps(media, ensure_ascii=False),
        }

        if reply_to_message_id:
            data["reply_parameters"] = json.dumps({"message_id": int(reply_to_message_id)}, ensure_ascii=False)

        return perform_post_request(
            url,
            request_name="sendMediaGroup",
            data=data,
            files=opened_files,
            timeout=180,
        )

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


def get_routes_state(state):
    routes_state = state.get("routes")
    if isinstance(routes_state, dict):
        return routes_state

    routes_state = {}
    state["routes"] = routes_state
    return routes_state


def get_route_state(state, route_id):
    routes_state = get_routes_state(state)
    route_state = routes_state.get(route_id)
    if isinstance(route_state, dict):
        return route_state

    route_state = {}
    routes_state[route_id] = route_state
    return route_state


def get_route_min_source_message_id(state, route_id):
    route_state = get_route_state(state, route_id)
    stored_value = route_state.get("min_source_message_id")
    if isinstance(stored_value, int):
        return stored_value
    if isinstance(stored_value, str) and stored_value.isdigit():
        return int(stored_value)

    env_value = route_min_source_message_id(route_id)
    if isinstance(env_value, int):
        route_state["min_source_message_id"] = env_value
        return env_value

    return None


def set_route_min_source_message_id(state, route_id, message_id):
    if state is None or not route_id or not message_id:
        return
    route_state = get_route_state(state, route_id)
    route_state["min_source_message_id"] = int(message_id)


def get_current_day_key():
    return datetime.now(DAILY_LIMIT_TZ).date().isoformat()


def get_route_daily_counts(state, route_id):
    route_state = get_route_state(state, route_id)
    counts = route_state.get("daily_publish_counts")
    if isinstance(counts, dict):
        return counts

    counts = {}
    route_state["daily_publish_counts"] = counts
    return counts


def get_route_daily_count(state, route_id, chat_id):
    counts = get_route_daily_counts(state, route_id)
    value = counts.get(str(chat_id), 0)
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return 0


def increment_route_daily_count(state, route_id, chat_id):
    counts = get_route_daily_counts(state, route_id)
    key = str(chat_id)
    counts[key] = get_route_daily_count(state, route_id, chat_id) + 1


def route_target_limit_reached(state, route_id, chat_id):
    limit = route_daily_post_limit(route_id)
    if limit <= 0:
        return True
    return get_route_daily_count(state, route_id, chat_id) >= limit


def route_all_targets_limit_reached(state, route_id, target_channels):
    targets = [chat_id for chat_id in (target_channels or []) if str(chat_id).strip()]
    if not targets:
        return False
    return all(route_target_limit_reached(state, route_id, chat_id) for chat_id in targets)


async def sync_route_daily_window(client, route, state, entity, current_source_signature):
    route_id = route["id"]
    route_state = get_route_state(state, route_id)
    current_day_key = get_current_day_key()
    previous_day_key = route_state.get("daily_limit_day")
    if previous_day_key == current_day_key:
        return False

    route_state["daily_limit_day"] = current_day_key
    route_state["daily_publish_counts"] = {}

    if previous_day_key:
        latest_post_key = await get_latest_post_key(client, entity)
        latest_source_message_id = await get_latest_source_message_id(client, entity)
        if latest_post_key and latest_source_message_id:
            route_state["last_post_key"] = latest_post_key
            route_state["source_signature"] = current_source_signature
            set_route_min_source_message_id(state, route_id, latest_source_message_id)
            save_state(state)
            print(f"[{route_id}] Daily limit reset: backlog skipped at:", safe_console_text(latest_post_key))
            return True

    save_state(state)
    return False


def migrate_legacy_state(state):
    if state.get("routes"):
        return state

    if not ROUTES:
        return state

    if state.get("last_post_key") or state.get("source_signature") or state.get("post_progress"):
        default_route_state = get_route_state(state, ROUTES[0]["id"])
        if state.get("last_post_key") and not default_route_state.get("last_post_key"):
            default_route_state["last_post_key"] = state.get("last_post_key")
        if state.get("source_signature") and not default_route_state.get("source_signature"):
            default_route_state["source_signature"] = state.get("source_signature")
        if state.get("post_progress") and not default_route_state.get("post_progress"):
            default_route_state["post_progress"] = state.get("post_progress")

    state.pop("last_post_key", None)
    state.pop("source_signature", None)
    state.pop("post_progress", None)
    return state


def get_post_progress(state, route_id):
    route_state = get_route_state(state, route_id)
    progress = route_state.get("post_progress")
    if isinstance(progress, dict):
        return progress

    progress = {}
    route_state["post_progress"] = progress
    return progress


def get_sent_targets_for_post(state, route_id, post_key):
    progress = get_post_progress(state, route_id)
    return {
        str(chat_id)
        for chat_id in progress.get(str(post_key), [])
        if str(chat_id).strip()
    }


def mark_target_sent(state, route_id, post_key, chat_id):
    progress = get_post_progress(state, route_id)
    key = str(post_key)
    sent_targets = get_sent_targets_for_post(state, route_id, post_key)
    sent_targets.add(str(chat_id))
    progress[key] = sorted(sent_targets)


def clear_post_progress(state, route_id, post_key):
    route_state = get_route_state(state, route_id)
    progress = get_post_progress(state, route_id)
    progress.pop(str(post_key), None)
    if not progress:
        route_state.pop("post_progress", None)


def get_message_map(state, route_id):
    route_state = get_route_state(state, route_id)
    message_map = route_state.get("message_map")
    if isinstance(message_map, dict):
        return message_map

    message_map = {}
    route_state["message_map"] = message_map
    return message_map


def get_target_message_id_for_source(state, route_id, chat_id, source_ref):
    if state is None or not source_ref:
        return None

    message_map = get_message_map(state, route_id)
    chat_map = message_map.get(str(chat_id))
    if not isinstance(chat_map, dict):
        return None

    target_message_id = chat_map.get(str(source_ref))
    if isinstance(target_message_id, int):
        return target_message_id

    if isinstance(target_message_id, str) and target_message_id.isdigit():
        return int(target_message_id)

    return None


def store_target_message_mapping(state, route_id, chat_id, source_refs, target_message_id):
    if state is None or not source_refs or not target_message_id:
        return

    message_map = get_message_map(state, route_id)
    chat_key = str(chat_id)
    chat_map = message_map.get(chat_key)
    if not isinstance(chat_map, dict):
        chat_map = {}
        message_map[chat_key] = chat_map

    for source_ref in source_refs:
        if source_ref:
            chat_map[str(source_ref)] = int(target_message_id)


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
    return perform_post_request(
        url,
        request_name=f"Telegram {method}",
        json=payload,
        timeout=60,
    )



def get_post_key(message):
    if message.grouped_id:
        return f"group_{message.grouped_id}"
    return f"msg_{message.id}"


def get_message_ref_by_id(message_id):
    if not message_id:
        return None
    return f"msg_{int(message_id)}"


def get_reply_to_source_ref(messages):
    for message in reversed(messages or []):
        reply_to = getattr(message, "reply_to", None)
        if not reply_to:
            continue

        reply_to_msg_id = getattr(reply_to, "reply_to_msg_id", None) or getattr(reply_to, "reply_to_top_id", None)
        if reply_to_msg_id:
            return get_message_ref_by_id(reply_to_msg_id)

    return None


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
    if is_unsupported_document_media(message):
        return False

    if getattr(message, "video", None):
        return True

    media = getattr(message, "media", None)
    document = getattr(media, "document", None)
    mime_type = getattr(document, "mime_type", "") if document else ""
    return mime_type.startswith("video/")


def has_downloadable_image(message):
    if is_unsupported_document_media(message):
        return False

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


def is_unsupported_document_media(message):
    if getattr(message, "sticker", None):
        return True

    media = getattr(message, "media", None)
    document = getattr(media, "document", None)
    if not document:
        return False

    attributes = getattr(document, "attributes", []) or []
    for attribute in attributes:
        attribute_name = attribute.__class__.__name__
        if attribute_name == "DocumentAttributeSticker":
            return True

        file_name = (getattr(attribute, "file_name", "") or "").strip().lower()
        if file_name.endswith(".webm") and "sticker" in file_name:
            return True

    mime_type = (getattr(document, "mime_type", "") or "").strip().lower()
    if mime_type == "video/webm":
        return True

    return False


def has_file_media(message):
    if is_unsupported_document_media(message):
        return True

    media = getattr(message, "media", None)
    document = getattr(media, "document", None)
    if not document:
        return False

    mime_type = getattr(document, "mime_type", "") or ""
    if mime_type.startswith("image/") or mime_type.startswith("video/"):
        return False
    return True


def has_reply_reference(message):
    reply_to = getattr(message, "reply_to", None)
    if not reply_to:
        return False

    if getattr(reply_to, "reply_to_msg_id", None):
        return True
    if getattr(reply_to, "reply_to_top_id", None):
        return True
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
    has_supported_media = count_supported_media(post_messages) > 0
    if has_text and not has_supported_media:
        print("Skip reason: text-only post")
        return True

    if not has_supported_media and not has_text:
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


async def get_latest_source_message_id(client, entity):
    messages = await client.get_messages(entity, limit=1)
    if not messages:
        return None
    return int(messages[0].id)


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


async def download_media_with_retries(client, message, file="data/"):
    for attempt in range(1, MEDIA_DOWNLOAD_RETRIES + 1):
        try:
            media_path = await client.download_media(message, file=file)
            if media_path and os.path.exists(media_path):
                return media_path

            print(
                f"Media download returned empty ({attempt}/{MEDIA_DOWNLOAD_RETRIES}) for message:",
                safe_console_text(getattr(message, "id", "unknown")),
            )
        except Exception as e:
            print(
                f"Media download error ({attempt}/{MEDIA_DOWNLOAD_RETRIES}) for message {safe_console_text(getattr(message, 'id', 'unknown'))}:",
                str(e),
            )

        if attempt < MEDIA_DOWNLOAD_RETRIES:
            await asyncio.sleep(RETRY_DELAY_SECONDS * attempt)

    return None


async def rebuild_post_media(client, entity, post_data):
    expected_media_count = int(post_data.get("media_count") or 0)
    media_items = post_data.get("media_items")
    if media_items is None:
        media_items = [
            {"type": "photo", "path": path}
            for path in (post_data.get("photo_paths") or [])
        ]

    if expected_media_count <= 0:
        return post_data

    if (
        media_items
        and len(media_items) >= expected_media_count
        and all(os.path.exists(item.get("path", "")) for item in media_items)
    ):
        return post_data

    message_id = post_data.get("source_message_id")
    if not message_id:
        raise RuntimeError(f"Cannot rebuild media for {post_data.get('key')}: missing source_message_id")

    source_message = await client.get_messages(entity, ids=message_id)
    if not source_message:
        raise RuntimeError(f"Cannot rebuild media for {post_data.get('key')}: source message not found")

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

        media_path = await download_media_with_retries(client, message, file="data/")
        if media_path:
            rebuilt_media_items.append({"type": media_type, "path": media_path})

    if len(rebuilt_media_items) < expected_media_count:
        cleanup_media_items(rebuilt_media_items)
        raise RuntimeError(
            f"Media rebuild incomplete for {post_data.get('key')}: expected {expected_media_count}, got {len(rebuilt_media_items)}"
        )

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
        "source_message_refs": list(dict.fromkeys(
            [get_post_key(last_msg)] + [get_message_ref_by_id(getattr(message, "id", None)) for message in post_messages]
        )),
        "source_reply_to_key": get_reply_to_source_ref(post_messages),
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
        "source_message_refs": list(dict.fromkeys(
            [get_post_key(last_msg)] + [get_message_ref_by_id(getattr(message, "id", None)) for message in post_messages]
        )),
        "source_reply_to_key": get_reply_to_source_ref(post_messages),
        "inline_partners": inline_partners,
        "primary_partner_only": primary_partner_only,
        "with_buttons": not inline_partners and not has_companies,
    }


async def get_new_posts_data(client, entity, last_post_key=None, limit=50, min_source_message_id=None):
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
        if post_data and (
            not min_source_message_id
            or int(post_data.get("source_message_id") or 0) > int(min_source_message_id)
        ):
            posts.append(post_data)

    posts.sort(key=lambda post: post.get("source_message_id", 0))
    return posts

def response_ok(response):
    try:
        data = response.json()
        return response.status_code == 200 and data.get("ok") is True
    except Exception:
        return response.status_code == 200


def get_response_message_ids(response):
    try:
        data = response.json()
    except Exception:
        return []

    if response.status_code != 200 or data.get("ok") is not True:
        return []

    result = data.get("result")
    if isinstance(result, dict):
        message_id = result.get("message_id")
        return [int(message_id)] if message_id else []

    if isinstance(result, list):
        message_ids = []
        for item in result:
            if not isinstance(item, dict):
                continue
            message_id = item.get("message_id")
            if message_id:
                message_ids.append(int(message_id))
        return message_ids

    return []

def publish_post_to_channel(post_data, chat_id, reply_to_message_id=None):
    text = post_data.get("processed_text", "")
    expected_media_count = int(post_data.get("media_count") or 0)
    media_items = post_data.get("media_items")
    if media_items is None:
        media_items = [
            {"type": "photo", "path": path}
            for path in (post_data.get("photo_paths") or [])
        ]

    with_buttons = bool(post_data.get("with_buttons")) and not post_contains_inline_partners(text, chat_id=chat_id)

    if expected_media_count and len(media_items) < expected_media_count:
        print(
            f"Media send blocked for {post_data.get('key')}: expected {expected_media_count}, got {len(media_items)}"
        )
        return None

    missing_files = [
        media_item.get("path")
        for media_item in media_items
        if not os.path.exists(media_item.get("path", ""))
    ]
    if missing_files:
        print("Media send blocked: missing files:", ", ".join(safe_console_text(path) for path in missing_files))
        return None

    if len(media_items) == 0:
        response = send_text(
            text,
            with_buttons=with_buttons,
            chat_id=chat_id,
            reply_to_message_id=reply_to_message_id,
        )
        print(f"Text sent to {safe_console_text(chat_id)}:", response.status_code)
        print(response.text)
        message_ids = get_response_message_ids(response)
        return message_ids[0] if response_ok(response) and message_ids else None

    elif len(media_items) == 1:
        media_item = media_items[0]
        if media_item.get("type") == "video":
            response = send_one_video(
                media_item["path"],
                text,
                with_buttons=with_buttons,
                chat_id=chat_id,
                reply_to_message_id=reply_to_message_id,
            )
            print(f"One video sent to {safe_console_text(chat_id)}:", response.status_code)
        else:
            response = send_one_photo(
                media_item["path"],
                text,
                with_buttons=with_buttons,
                chat_id=chat_id,
                reply_to_message_id=reply_to_message_id,
            )
            print(f"One photo sent to {safe_console_text(chat_id)}:", response.status_code)
        print(response.text)
        message_ids = get_response_message_ids(response)
        return message_ids[0] if response_ok(response) and message_ids else None

    else:
        response = send_media_group(media_items, text, chat_id=chat_id, reply_to_message_id=reply_to_message_id)
        print(f"Album sent to {safe_console_text(chat_id)} ({len(media_items)} media):", response.status_code)
        print(response.text)

        if not response_ok(response):
            return None

        message_ids = get_response_message_ids(response)
        target_message_id = message_ids[0] if message_ids else None

        if not with_buttons:
            return target_message_id

        buttons_response = send_text("ðŸ‘‡ Ð‘Ð¾Ð½ÑƒÑÐ½Ñ‹Ðµ ÑÑÑ‹Ð»ÐºÐ¸", with_buttons=True, chat_id=chat_id)
        print(f"Buttons sent to {safe_console_text(chat_id)}:", buttons_response.status_code)
        print(buttons_response.text)
        return target_message_id if response_ok(buttons_response) else None


def publish_post(post_data, use_ai=True, state=None):
    post_key = post_data.get("key")
    route_id = post_data.get("route_id", "route_1")
    target_channels = post_data.get("target_channels") or TARGET_CHANNELS
    source_reply_to_key = post_data.get("source_reply_to_key")
    source_message_refs = post_data.get("source_message_refs") or [post_key]

    if not target_channels:
        print("Error: TARGET_CHANNEL or TARGET_CHANNELS is missing")
        return False

    sent_targets = get_sent_targets_for_post(state, route_id, post_key) if state and post_key else set()

    for chat_id in target_channels:
        chat_key = str(chat_id)
        if chat_key in sent_targets:
            print("Skipping target already sent:", safe_console_text(chat_id))
            continue

        if state is not None and route_target_limit_reached(state, route_id, chat_id):
            print("Skipping target daily limit reached:", safe_console_text(chat_id))
            if post_key:
                mark_target_sent(state, route_id, post_key, chat_id)
                save_state(state)
            continue

        prepared_post = dict(post_data)
        prepared_post["processed_text"] = build_final_text(prepared_post, use_ai=use_ai, chat_id=chat_id)
        reply_to_message_id = None

        if source_reply_to_key:
            reply_to_message_id = get_target_message_id_for_source(state, route_id, chat_id, source_reply_to_key)
            if not reply_to_message_id:
                print(
                    "Skipping reply post for target: missing parent mapping",
                    safe_console_text(chat_id),
                    safe_console_text(source_reply_to_key),
                )
                if state is not None and post_key:
                    mark_target_sent(state, route_id, post_key, chat_id)
                    save_state(state)
                continue

        print("Publishing to target:", safe_console_text(chat_id))
        target_message_id = publish_post_to_channel(prepared_post, chat_id, reply_to_message_id=reply_to_message_id)
        if not target_message_id:
            return False

        if state is not None and post_key:
            store_target_message_mapping(state, route_id, chat_id, source_message_refs, target_message_id)
            mark_target_sent(state, route_id, post_key, chat_id)
            increment_route_daily_count(state, route_id, chat_id)
            save_state(state)

    if state is not None and post_key:
        clear_post_progress(state, route_id, post_key)
        save_state(state)

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
    prepared_post["route_id"] = post_data.get("route_id")
    prepared_post["source_channel"] = post_data.get("source_channel")
    prepared_post["target_channels"] = post_data.get("target_channels")

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
            source_channel = post_data.get("source_channel") or SOURCE_CHANNEL
            source_entity = await resolve_source_entity(client, parse_telegram_peer(source_channel))
            prepared_post = await rebuild_post_media(client, source_entity, post_data)
            success = publish_post(prepared_post, use_ai=False, state=state)
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


async def process_route(client, route, state):
    route_id = route["id"]
    route_state = get_route_state(state, route_id)
    target_channels = route.get("target_channels") or []
    entity = await resolve_source_entity(client, route["source_entity"])
    current_source_signature = get_source_signature(route["source_channel"], entity)

    if not route_state.get("initialized"):
        first_post_key = await get_latest_post_key(client, entity)

        if not first_post_key:
            print(f"[{route_id}] No messages in source channel")
            route_state["initialized"] = True
            save_state(state)
            return

        if route_state.get("source_signature") != current_source_signature:
            route_state["source_signature"] = current_source_signature
            route_state["last_post_key"] = first_post_key
            route_state["initialized"] = True
            save_state(state)
            print(f"[{route_id}] Source changed: current last post saved, waiting for new posts")
            return

        if not route_state.get("last_post_key"):
            route_state["last_post_key"] = first_post_key
            route_state["source_signature"] = current_source_signature
            route_state["initialized"] = True
            save_state(state)
            print(f"[{route_id}] First start: current last post saved, waiting for new posts")
            return

        route_state["initialized"] = True
        save_state(state)

    startup_min_source_message_id = get_route_min_source_message_id(state, route_id)
    if await sync_route_daily_window(client, route, state, entity, current_source_signature):
        return

    if route_startup_skip_backlog_enabled(route_id) and route_state.get("startup_guard_id") != PROCESS_BOOT_ID:
        latest_post_key = await get_latest_post_key(client, entity)
        latest_source_message_id = await get_latest_source_message_id(client, entity)
        if latest_post_key and latest_source_message_id:
            if startup_min_source_message_id:
                latest_source_message_id = max(int(startup_min_source_message_id), int(latest_source_message_id))
            route_state["last_post_key"] = latest_post_key
            route_state["source_signature"] = current_source_signature
            route_state["startup_guard_id"] = PROCESS_BOOT_ID
            set_route_min_source_message_id(state, route_id, latest_source_message_id)
            save_state(state)
            print(f"[{route_id}] Startup backlog skipped at:", safe_console_text(latest_post_key))
            return

    if route_skip_to_latest_once_enabled(route_id) and not route_state.get("skip_to_latest_once_completed"):
        latest_post_key = await get_latest_post_key(client, entity)
        route_state["last_post_key"] = latest_post_key
        route_state["source_signature"] = current_source_signature
        latest_source_message_id = await get_latest_source_message_id(client, entity)
        if latest_source_message_id:
            set_route_min_source_message_id(state, route_id, latest_source_message_id)
        route_state["skip_to_latest_once_completed"] = True
        save_state(state)
        print(f"[{route_id}] Skip-to-latest completed at:", safe_console_text(latest_post_key))
        return

    if route_backfill_latest_once_enabled(route_id) and not route_state.get("latest_backfill_once_completed"):
        latest_posts = await get_new_posts_data(client, entity, last_post_key=None, limit=1)
        if latest_posts:
            latest_post = latest_posts[-1]
            print(f"[{route_id}] Backfill latest once: {latest_post['key']}")
            prepared_post = dict(latest_post)
            prepared_post["route_id"] = route_id
            prepared_post["source_channel"] = route["source_channel"]
            prepared_post["target_channels"] = route["target_channels"]

            if REVIEW_MODE:
                print(f"[{route_id}] Backfill route: review channel")
                prepared_post = await rebuild_post_media(client, entity, prepared_post)
                success = queue_post_for_review(prepared_post)
            else:
                print(f"[{route_id}] Backfill route: target channels")
                prepared_post = await rebuild_post_media(client, entity, prepared_post)
                success = publish_post(prepared_post, state=state)
                cleanup_media_items(prepared_post.get("media_items") or [])

            if success:
                route_state["last_post_key"] = latest_post["key"]
                route_state["latest_backfill_once_completed"] = True
                save_state(state)
                print(f"[{route_id}] Backfill latest once completed")
            else:
                print(f"[{route_id}] Backfill latest once failed")
                return

    if route_all_targets_limit_reached(state, route_id, target_channels):
        latest_post_key = await get_latest_post_key(client, entity)
        latest_source_message_id = await get_latest_source_message_id(client, entity)
        if latest_post_key and latest_source_message_id:
            route_state["last_post_key"] = latest_post_key
            route_state["source_signature"] = current_source_signature
            set_route_min_source_message_id(state, route_id, latest_source_message_id)
            save_state(state)
            print(f"[{route_id}] Daily post limit reached for all targets; waiting for next day after:", safe_console_text(latest_post_key))
        return

    print(f"[{route_id}] SOURCE_CHANNEL:", safe_console_text(route["source_channel"]))
    print(f"[{route_id}] Source found:", safe_console_text(getattr(entity, "title", "no title")))
    print(
        f"[{route_id}] Target channels:",
        ", ".join(safe_console_text(chat_id) for chat_id in route["target_channels"]),
    )

    new_posts = await get_new_posts_data(
        client,
        entity,
        route_state.get("last_post_key"),
        limit=NEW_POST_SCAN_LIMIT,
        min_source_message_id=get_route_min_source_message_id(state, route_id),
    )
    print(f"[{route_id}] New posts found:", len(new_posts))
    print(f"[{route_id}] State key:", route_state.get("last_post_key"))

    if not new_posts:
        print(f"[{route_id}] No new posts")
        return

    for post_data in new_posts:
        if route_all_targets_limit_reached(state, route_id, target_channels):
            latest_post_key = await get_latest_post_key(client, entity)
            latest_source_message_id = await get_latest_source_message_id(client, entity)
            if latest_post_key and latest_source_message_id:
                route_state["last_post_key"] = latest_post_key
                route_state["source_signature"] = current_source_signature
                set_route_min_source_message_id(state, route_id, latest_source_message_id)
                save_state(state)
                print(f"[{route_id}] Daily post limit reached mid-batch; backlog skipped at:", safe_console_text(latest_post_key))
            return

        print(f"[{route_id}] Processing post: {post_data['key']}")
        prepared_post = dict(post_data)
        prepared_post["route_id"] = route_id
        prepared_post["source_channel"] = route["source_channel"]
        prepared_post["target_channels"] = target_channels

        if REVIEW_MODE:
            print(f"[{route_id}] Route: review channel")
            prepared_post = await rebuild_post_media(client, entity, prepared_post)
            success = queue_post_for_review(prepared_post)
        else:
            print(f"[{route_id}] Route: target channels")
            prepared_post = await rebuild_post_media(client, entity, prepared_post)
            success = publish_post(prepared_post, state=state)
            cleanup_media_items(prepared_post.get("media_items") or [])

        if success:
            route_state["last_post_key"] = post_data["key"]
            save_state(state)
            print(f"[{route_id}] Post sent and state updated")
        else:
            print(f"[{route_id}] Send error: state.json not updated")
            break


async def main():
    if not API_ID:
        print("Error: TG_API_ID is missing")
        return

    if not API_HASH:
        print("Error: TG_API_HASH is missing")
        return

    if not ROUTES:
        print("Error: at least one SOURCE_CHANNEL/TARGET_CHANNELS route is required")
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
    print("Routes configured:", len(ROUTES))
    state = migrate_legacy_state(load_state())
    save_state(state)

    try:
        while True:
            try:
                if not await ensure_client_connected(client):
                    await asyncio.sleep(CHECK_INTERVAL)
                    continue

                if REVIEW_MODE:
                    await handle_moderation_updates(client, None, state)

                for route in ROUTES:
                    await process_route(client, route, state)

            except Exception as e:
                print("Loop error:", str(e))

            await asyncio.sleep(CHECK_INTERVAL)

    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
