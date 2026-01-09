TEXTS = {
    "MAX_QUESTION_CHARS": 500,
    "EMPTY_QUESTION_TEXT": (
        "It looks like your message was empty. Please send one sentence about what you'd like to ask.\n"
        "Example: “Will things go well with them?”"
    ),
    "LONG_QUESTION_TEXT": (
        "It seems a bit long. Please keep it within 500 characters and summarize in one sentence.\n"
        "Tip: briefly include the situation, what you want to know, and when."
    ),
    "NON_TEXT_MESSAGE_TEXT": (
        "Please send text. Emojis or stickers alone aren't enough—just one sentence is fine."
    ),
    "THROTTLE_TEXT": "Please wait a moment before trying again.",
    "RETRY_READING_TEXT": "Generating the result is taking a little longer. Please try again after a short wait.",
    "START_TEXT": (
        "Hello, I'm tarot_cat for tarot readings and consultations. 🐈‍⬛\n"
        "You can draw a one-card reading for free up to twice a day (/read1).\n"
        "\n"
        "If you want deeper readings or unlimited chat/consultation, 7-day and 30-day passes are available.\n"
        "\n"
        "Use the buttons below to choose “🎩 Tarot” or “💬 Chat”.\n"
        "Check /help for details.\n"
    ),
    "ARISA_START_TEXT": (
        "Hi, I'm Arisa.\n"
        "Feel free to talk about love, sexy topics, or casual chat.\n"
        "NG: minors, explicit sexual descriptions, or illegal activity.\n"
        "Tell me how you're feeling."
    ),
    "ARISA_MENU_LOVE_LABEL": "💖 Love",
    "ARISA_MENU_SEXY_LABEL": "🔥 Sexy",
    "ARISA_LOVE_PROMPT": "Let's talk about love. Tell me about the person or situation on your mind.",
    "ARISA_SEXY_PROMPT": "Sexy topic noted. Share only what you're comfortable with.",
    "ARISA_CHARGE_BLOCKED_TEXT": "Top-ups aren't available in this mode. We only chat here.",
    "ARISA_STATUS_BLOCKED_TEXT": "Status is not available in this mode.",
    "ARISA_BLOCK_NOTICE": "Tarot and payments are disabled in this bot. Chat only.",
    "STORE_INTRO_TEXT": (
        "After purchase, you can return to “🎩 Tarot” or “💬 Chat”.\n"
        "Stars stay on your account and any unused balance carries over.\n"
    ),
    "HELP_TEXT_TEMPLATE": (
        "❓ How to use\n"
        "\n"
        "1. Tap “🎩 Tarot” below, then choose a theme (Love/Marriage/Work/Life).\n"
        "2. Send your question in one sentence.\n"
        '   Example: “How will my work go this month?”\n'
        "3. You'll receive a one-card reading.\n"
        '   Want more? Try “3-card deep dive (paid)” or /buy.\n'
        "\n"
        "💬 Chat mode\n"
        "\n"
        "Organize how you feel and find your next small step together.\n"
        "Casual talk and venting are welcome too—share freely.\n"
        "\n"
        "🎯 Sample questions by theme\n"
        "\n"
        "{theme_examples}\n"
        "\n"
        "🛒 Top up\n"
        "Purchase via /buy or “🛒 Store”.\n"
        "Use it when you want deeper readings or a chat partner anytime.\n"
        "\n"
        "🚫 Warnings\n"
        "Medical, legal, investment, self-harm, or crisis matters belong to professionals.\n"
        "This bot helps with reflection and planning small actions.\n"
        "\n"
        "📜 Terms: Check /terms anytime."
    ),
    "TERMS_TEXT": (
        "Terms (excerpt)\n"
        "- Use at your own responsibility if you are 18 or older.\n"
        "- For medical/legal/investment/self-harm topics, please consult professionals.\n"
        "- Misuse or illegal use is prohibited.\n"
        "- Digital goods are generally non-refundable; issues will be investigated and refunded if needed.\n"
        "- Contact: {support_email}\n\n"
        "Please agree before purchasing."
    ),
    "SUPPORT_TEXT": (
        "Support desk.\n"
        "・Customer support: {support_email}\n"
        "・General inquiries: Telegram @akolasia_support\n"
        "※ The Telegram general desk cannot handle payment issues. Use /paysupport if needed."
    ),
    "PAY_SUPPORT_TEXT": (
        "Payment support. Copy and send the template below:\n"
        "Purchase date/time:\n"
        "Product/SKU:\n"
        "charge_id: (if shown)\n"
        "Payment method: Stars / Other\n"
        "Screenshot: yes/no\n"
        "We will review and refund or grant as needed.\n"
        "Contact: {support_email}"
    ),
    "TERMS_PROMPT_BEFORE_BUY": "Please review /terms and agree before purchasing.",
    "TERMS_PROMPT_FOLLOWUP": "Please review /terms and agree before continuing.",
    "STATUS_TITLE": "📊 Your current usage.",
    "STATUS_TITLE_ADMIN": "📊 Usage (admin mode).",
    "STATUS_ADMIN_LABEL": "admin",
    "STATUS_ADMIN_FLAG": "• Admin privileges: enabled (purchases are not limited).",
    "STATUS_TRIAL_LINE": "• Trial day: Day {trial_day}",
    "STATUS_PASS_LABEL": "• Pass expiry: {pass_label}",
    "STATUS_PASS_NONE": "none",
    "STATUS_PASS_REMAINING": "(in {remaining_days} days)",
    "STATUS_ONE_ORACLE": "• One-oracle free draws: {limit} per day (remaining today: {remaining})",
    "STATUS_GENERAL": "• Chat: {text}",
    "STATUS_GENERAL_PASS": "Pass active: Chat is unlimited.",
    "STATUS_GENERAL_TRIAL": (
        "Trial ends in {trial_days_left} day(s) (remaining {remaining} messages today).\n"
        "• From day 6 a pass is required."
    ),
    "STATUS_GENERAL_LOCKED": "Chat is unavailable without a pass. Please consider /buy.",
    "STATUS_TICKET_3": "• 3-card tickets: {count}",
    "STATUS_TICKET_7": "• 7-card tickets: {count}",
    "STATUS_TICKET_10": "• 10-card tickets: {count}",
    "STATUS_IMAGES": "• Image option: {state}",
    "STATUS_IMAGES_ON": "enabled",
    "STATUS_IMAGES_OFF": "disabled",
    "STATUS_RESET": "• Next reset for free limits: {reset_time}",
    "STATUS_LATEST_PURCHASE": "• Latest purchase: {label} / SKU: {sku} (granted: {purchased_at})",
    "NON_CONSULT_OUT_OF_QUOTA_MESSAGE": (
        "This bot is for tarot readings and chat. Use /read1 for readings or /love1 for love topics. "
        "Top up via /buy."
    ),
    "STALE_CALLBACK_MESSAGE": "The button has expired. Please open /buy again.",
    "TAROT_THEME_PROMPT": "🎩 Tarot mode. Choose a theme below (Love/Marriage/Work/Life).",
    "TAROT_THEME_SELECT_PROMPT": "Please choose a theme 👇",
    "TAROT_QUESTION_PROMPT": (
        "✅ Theme: {theme_label}. Send one question you want to ask.\n"
        "Example: “{example_text}”"
    ),
    "TAROT_THEME_SET_CONFIRMATION": "Theme set.",
    "TAROT_THEME_BUTTON_LOVE": "❤️ Love",
    "TAROT_THEME_BUTTON_MARRIAGE": "💍 Marriage",
    "TAROT_THEME_BUTTON_WORK": "💼 Work",
    "TAROT_THEME_BUTTON_LIFE": "🌉 Life",
    "UPGRADE_BUTTON_TEXT": "3-card deep dive (paid)",
    "CONSULT_MODE_PROMPT": "💬 Chat mode. I'm here to listen—tell me anything!",
    "CHARGE_MODE_PROMPT": (
        "🛒 Store menu\n"
        "Choose a ticket or pass (paid with Telegram Stars)."
    ),
    "STATUS_MODE_PROMPT": "📊 Your current usage.",
    "INACTIVE_RESET_NOTICE": (
        "The session was reset after inactivity. Please start again with /start or /help."
    ),
    "MENU_HOME_TEXT": "🏠 Back to menu",
    "MENU_TAROT_LABEL": "🎩 Tarot",
    "MENU_CHAT_LABEL": "💬 Chat",
    "MENU_STORE_LABEL": "🛒 Store",
    "MENU_STATUS_LABEL": "📊 Status",
    "MENU_LANGUAGE_LABEL": "🌐 Language",
    "GO_TO_STORE_BUTTON": "🛒 Go to Store",
    "VIEW_STATUS_BUTTON": "📊 View status",
    "ASK_FOR_MORE_DETAIL": "Could you share a bit more about what's on your mind?",
    "DEFAULT_TAROT_QUERY_FALLBACK": "Please read about what's on my mind right now.",
    "BUSY_TAROT_MESSAGE": "A reading is already in progress—please wait a moment.",
    "BUSY_CHAT_MESSAGE": "I'm replying now—please wait a moment.",
    "READING_IN_PROGRESS_NOTICE": "🔮 Reading in progress… please wait.",
    "APOLOGY_RETRY_NOTE": "Sorry for the trouble. Please try again after a short wait.",
    "USER_INFO_MISSING": "We couldn't confirm your user information.",
    "USER_INFO_DM_REQUIRED": "We couldn't confirm your user info. Please try from a direct chat.",
    "LANGUAGE_SELECT_PROMPT": "Please choose your language.",
    "LANGUAGE_OPTION_JA": "🇯🇵 Japanese",
    "LANGUAGE_OPTION_EN": "🇺🇸 English",
    "LANGUAGE_OPTION_PT": "🇧🇷 Português",
    "LANGUAGE_SET_CONFIRMATION": "Language saved ({language}).",
    "LANGUAGE_SET_FAILED": "Couldn't update the language.",
    "MENU_RETURNED_TEXT": "Returned to the menu. Use the buttons below.",
    "POSTPROCESS_TRUNCATION_NOTE": (
        "The message was very long, so I sent the first part. "
        "If you'd like the rest, please ask again."
    ),
    "OPENAI_FATAL_ERROR": "There was an issue on our side. Please try again in a moment.",
    "OPENAI_PROCESSING_ERROR": "We hit a snag processing the reading. Please try again shortly.",
    "OPENAI_COMMUNICATION_ERROR": "It seems the connection failed. Please try again after a short wait.",
    "SENSITIVE_TOPIC_LABEL_INVESTMENT": "Investment/Finance",
    "SENSITIVE_TOPIC_LABEL_LEGAL": "Legal/Contracts/Disputes",
    "SENSITIVE_TOPIC_LABEL_MEDICAL": "Medical/Health",
    "SENSITIVE_TOPIC_LABEL_SELF_HARM": "Self-harm/Intense distress",
    "SENSITIVE_TOPIC_LABEL_VIOLENCE": "Violence/Harm to others",
    "SENSITIVE_TOPIC_NOTICE_HEADER": (
        "🚫 These topics require professional help, so we cannot give definitive readings: {topics}."
    ),
    "SENSITIVE_TOPIC_NOTICE_PRO_HELP": (
        "• For symptoms or troubles, please consult medical, legal, or public professionals."
    ),
    "SENSITIVE_TOPIC_GUIDANCE_MEDICAL": (
        "We cannot diagnose or treat. Please consult medical professionals promptly if you feel unwell."
    ),
    "SENSITIVE_TOPIC_GUIDANCE_LEGAL": "Legal decisions and contracts should be reviewed by an attorney.",
    "SENSITIVE_TOPIC_GUIDANCE_INVESTMENT": (
        "We do not give investment advice or promised returns. Confirm plans with financial professionals."
    ),
    "SENSITIVE_TOPIC_GUIDANCE_SELF_HARM": (
        "If you feel in danger, contact emergency services or a trusted hotline immediately. Please don't stay alone with it."
    ),
    "SENSITIVE_TOPIC_GUIDANCE_VIOLENCE": (
        "If you're in danger, move to a safe place and contact the police or public authorities."
    ),
    "SENSITIVE_TOPIC_NOTICE_FOCUS": (
        "As a reading, we focus on organizing feelings and practical self-care or next steps."
    ),
    "SENSITIVE_TOPIC_NOTICE_LIST_REMINDER": "See /help or /terms for the list of restricted topics.",
    "PRODUCT_PASS_7D_TITLE": "7-day Pass",
    "PRODUCT_PASS_7D_DESCRIPTION": "A 7-day pass that unlocks chat so you can enjoy readings or conversation every day.",
    "PRODUCT_PASS_30D_TITLE": "30-day Pass",
    "PRODUCT_PASS_30D_DESCRIPTION": "A 30-day pass for longer consultations so you can use the service with peace of mind.",
    "PRODUCT_TICKET_3_TITLE": "3-card Spread",
    "PRODUCT_TICKET_3_DESCRIPTION": "One 3-card spread to organize the situation—perfect for a simple check-in on the present.",
    "PRODUCT_TICKET_7_TITLE": "Hexagram (7 cards)",
    "PRODUCT_TICKET_7_DESCRIPTION": "One 7-card hexagram for deeper exploration—great for tracing causes and flow.",
    "PRODUCT_TICKET_10_TITLE": "Celtic Cross (10 cards)",
    "PRODUCT_TICKET_10_DESCRIPTION": "One 10-card Celtic Cross for a thorough look from multiple perspectives.",
    "PRODUCT_ADDON_IMAGES_TITLE": "Image add-on",
    "PRODUCT_ADDON_IMAGES_DESCRIPTION": "Enable an option to attach images to your readings.",
    "PASS_EXTENDED_TEXT": "Expiration updated.",
    "UNLOCK_TICKET_ADDED": "Added {product}. Remaining balance: {balance}.",
    "UNLOCK_PASS_GRANTED": "Granted {duration}.\nExpiration: {until_text}{remaining_hint}",
    "UNLOCK_IMAGES_ENABLED": "Image add-on enabled. Your future readings will include a visual touch.",
    "PURCHASE_GENERIC_THANKS": "Thank you for your purchase. Contact support if you need anything.",
    "TERMS_PROMPT_REMINDER": (
        "Please review /terms and agree before purchasing.\n"
        "Use /terms to record your agreement."
    ),
    "TERMS_BUTTON_AGREE": "Agree",
    "TERMS_BUTTON_VIEW": "View terms",
    "TERMS_BUTTON_AGREE_AND_BUY": "Agree and proceed to purchase",
    "ADDON_PENDING_LABEL": "Image add-on (coming soon)",
    "TERMS_AGREED_RECORDED": "Your agreement to the terms has been recorded. You can proceed with /buy.",
    "TERMS_NEXT_STEP_REMINDER": "After agreeing, continue with /buy to purchase.",
    "RETURN_TO_TAROT_BUTTON": "🎩 Back to Tarot",
    "ADDON_PENDING_ALERT": "The image add-on is coming soon. Please wait a little longer.",
    "PASS_ALREADY_ACTIVE_ALERT": "A pass is active, so the 3-card spread is available without extra purchase.",
    "PASS_ALREADY_ACTIVE_MESSAGE": "Your pass is active—no need to buy another 3-card ticket. Try the 3-card spread from 🎩 Tarot.",
    "PURCHASE_DEDUP_ALERT": "A checkout screen is already open. Please check the payment window.",
    "PURCHASE_DEDUP_MESSAGE": "A confirmation for the same product is in progress. Please check the open checkout screen.",
    "INVOICE_DISPLAY_FAILED": "Failed to show the checkout screen. Please try /buy again.",
    "OPENING_PAYMENT_SCREEN": "Opening the payment screen—take your time.",
    "PURCHASE_THANK_YOU": "Thank you for purchasing {product}!",
    "PURCHASE_STATUS_REMINDER": "You can also check the grant details via /status.",
    "PURCHASE_NAVIGATION_HINT": "Use the buttons below to return to Tarot or view your status.",
    "PAYMENT_ALREADY_PROCESSED": "This payment has already been processed. Check /status for details.",
    "PAYMENT_INFO_MISMATCH": (
        "We couldn't confirm the payment details. Please contact support.\n"
        "If the charge went through, we'll take care of it."
    ),
    "PAYMENT_VERIFICATION_DELAY": (
        "Payment completed, but confirming the purchase is taking a moment.\n"
        "Please contact support if needed."
    ),
    "FEEDBACK_DM_REQUIRED": "Please send feedback from a direct chat.",
    "FEEDBACK_PROMPT": (
        "📝 Please share your feedback\n"
        "\n"
        "• What worked well\n"
        "• What was confusing\n"
        "• Features you'd like to see\n"
        "• Impressions of the readings/wording\n"
        "\n"
        "Short notes are welcome. Your input helps us improve."
    ),
    "FEEDBACK_SAVE_ERROR": "We couldn't save your feedback. Please try again later.",
    "FEEDBACK_THANKS": "Thank you for your feedback—we'll use it to improve operations.",
    "UNKNOWN_THEME": "We couldn't recognize the theme.",
    "PRODUCT_INFO_MISSING": "We couldn't confirm the product information. Please start over.",
    "PURCHASER_INFO_MISSING": "We couldn't confirm the purchaser information. Please try again.",
}
