from __future__ import annotations

"""
Utility script to validate translation key coverage across languages.

Usage:
    python tools/check_translation_keys.py

The script uses English (en) as the baseline and reports any missing or extra
keys in Japanese (ja) or Portuguese (pt). It exits with a non-zero status code
if mismatches are found.
"""

import sys

from bot.texts import en, pt
from bot.texts.i18n import _collect_ja_texts


def collect_language_keys() -> dict[str, set[str]]:
    return {
        "en": set(en.TEXTS.keys()),
        "ja": set(_collect_ja_texts().keys()),
        "pt": set(pt.TEXTS.keys()),
    }


def main() -> int:
    keys = collect_language_keys()
    baseline = keys["en"]
    status = 0

    for lang in ("ja", "pt"):
        missing = sorted(baseline - keys[lang])
        extra = sorted(keys[lang] - baseline)

        print(f"[{lang}] missing: {missing or 'none'}")
        print(f"[{lang}] extra:   {extra or 'none'}")
        if missing or extra:
            status = 1

    return status


if __name__ == "__main__":
    sys.exit(main())
