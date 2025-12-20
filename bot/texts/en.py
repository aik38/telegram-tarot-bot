TEXTS = {
    "START_TEXT": (
        "Hello, I'm tarot_cat for tarot readings and consultations. 🐈‍⬛\n"
        "You can draw a one-card reading for free up to twice a day (/read1).\n"
        "\n"
        "If you want deeper readings or unlimited chat/consultation, 7-day and 30-day passes are available.\n"
        "\n"
        "Use the buttons below to choose “🎩 Tarot” or “💬 Chat”.\n"
        "Check /help for details.\n"
    ),
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
}
