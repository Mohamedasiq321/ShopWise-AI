
"""Rule-based product intent detection for ShopWise AI."""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class QueryIntent:
    product_type: str | None
    required_terms: tuple[str, ...] = ()
    excluded_terms: tuple[str, ...] = ()
    message: str = ""


INTENT_RULES = [
    {
        "name": "wireless_keyboard_combo",
        "patterns": [
            r"\bwireless\s+keyboard\s+(?:and|&|\+)\s+mouse\b",
            r"\bkeyboard\s+(?:and|&|\+)\s+mouse\s+(?:combo|set)\b",
            r"\bkeyboard\s+mouse\s+combo\b",
            r"\bkeyboard\s+and\s+mouse\s+set\b",
            r"\bwireless\s+keyboard\s+(?:combo|set)\b",
        ],
        "required": ("keyboard", "mouse"),
        "excluded": ("keyboard cover", "keyboard case", "keycap"),
        "message": "Prioritizing wireless keyboard-and-mouse combo products.",
    },
    {
        "name": "wireless_keyboard",
        "patterns": [
            r"\bwireless\s+keyboards?\b",
            r"\bkeyboards?\s+wireless\b",
        ],
        "required": ("keyboard",),
        "excluded": (
            "keyboard cover",
            "keyboard case",
            "keycap",
            "keyboard and mouse",
            "keyboard & mouse",
            "keyboard combo",
            "keyboard set",
        ),
        "message": (
            "Prioritizing standalone wireless keyboards; "
            "use an explicit combo query for keyboard-and-mouse sets."
        ),
    },
    {
        "name": "gaming_mouse",
        "patterns": [r"\bgaming\s+mouse\b", r"\bgaming\s+mice\b"],
        "required": ("mouse",),
        "excluded": ("mousepad", "mouse pad", "mouse mat"),
        "message": "Showing gaming-mouse candidates; mousepads are excluded.",
    },
    {
        "name": "usb_c_cable",
        "patterns": [
            r"\busb[\s-]*c\s+cables?\b",
            r"\btype[\s-]*c\s+cables?\b",
            r"\busb[\s-]*c\b",
            r"\btype[\s-]*c\b",
        ],
        "required": ("cable",),
        "excluded": (),
        "message": "Prioritizing cable listings with USB-C/Type-C evidence.",
    },
    {
        "name": "webcam",
        "patterns": [r"\bwebcams?\b", r"\bweb\s+cameras?\b"],
        "required": ("webcam",),
        "excluded": ("cover", "privacy", "protector", "blocker"),
        "message": "Prioritizing actual webcam listings over privacy covers.",
    },
    {
        "name": "wireless_earbuds",
        "patterns": [
            r"\bwireless\s+earbuds?\b",
            r"\bbluetooth\s+earbuds?\b",
            r"\b(?:tws|true\s+wireless)\s+earbuds?\b",
        ],
        "required": ("earbud",),
        "excluded": ("earbud case", "earbud cover"),
        "message": "Showing wireless earbud candidates only.",
    },
    {
        "name": "soundbar",
        "patterns": [
            r"\bsound\s*bars?\b",
            r"\bsoundbars?\b",
        ],
        "required": ("soundbar",),
        "excluded": ("cover", "wall mount", "remote control"),
        "message": "Prioritizing soundbar listings.",
    },
    {
        "name": "bluetooth_speaker",
        "patterns": [r"\bbluetooth\s+speakers?\b"],
        "required": ("speaker",),
        "excluded": ("adapter", "dongle"),
        "message": "Showing speaker candidates, excluding Bluetooth adapters.",
    },
    {
        "name": "external_hard_drive",
        "patterns": [
            r"\bexternal\s+hard\s+drives?\b",
            r"\bexternal\s+hdds?\b",
            r"\bportable\s+hard\s+drives?\b",
        ],
        "required": ("hard drive", "external hdd", "portable hdd"),
        "excluded": ("cable", "case", "caddy", "cover", "adapter"),
        "message": "Prioritizing external storage products over accessories.",
    },
]


def detect_query_intent(query: str) -> QueryIntent:
    """Return a known product intent, or a neutral intent for other queries."""
    normalized = re.sub(r"\s+", " ", str(query or "").lower()).strip()

    for rule in INTENT_RULES:
        if any(re.search(pattern, normalized) for pattern in rule["patterns"]):
            return QueryIntent(
                product_type=rule["name"],
                required_terms=rule["required"],
                excluded_terms=rule["excluded"],
                message=rule["message"],
            )

    return QueryIntent(
        product_type=None,
        message="No specific product-type rule matched this query.",
    )
