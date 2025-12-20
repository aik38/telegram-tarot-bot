import os

os.environ.setdefault("TELEGRAM_BOT_TOKEN", "123456:TESTTOKEN")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")

from bot.texts import en, pt
from bot.texts.i18n import _collect_ja_texts


EN_BASELINE_KEYS = set(en.TEXTS.keys())


def test_en_text_keys_exist_in_all_languages():
    en_keys = EN_BASELINE_KEYS
    ja_keys = set(_collect_ja_texts().keys())
    pt_keys = set(pt.TEXTS.keys())

    missing_ja = sorted(en_keys - ja_keys)
    missing_pt = sorted(en_keys - pt_keys)

    assert not missing_ja, f"Japanese texts missing keys: {missing_ja}"
    assert not missing_pt, f"Portuguese texts missing keys: {missing_pt}"


def test_text_keys_have_no_extras():
    en_keys = EN_BASELINE_KEYS
    ja_keys = set(_collect_ja_texts().keys())
    pt_keys = set(pt.TEXTS.keys())

    extra_ja = sorted(ja_keys - en_keys)
    extra_pt = sorted(pt_keys - en_keys)

    assert not extra_ja, f"Japanese texts have unexpected keys: {extra_ja}"
    assert not extra_pt, f"Portuguese texts have unexpected keys: {extra_pt}"
