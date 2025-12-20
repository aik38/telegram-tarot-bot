MAX_QUESTION_CHARS = 500

HELP_TEXT_TEMPLATE = (
    "❓ ご利用方法\n"
    "\n"
    "1. 下の「🎩占い」→ テーマ（恋愛／結婚／仕事／人生）を選びます\n"
    "2. 気になっていることを1文で送ってください\n"
    "　例：『今月の仕事運は？』\n"
    "3. ワンオラクル（1枚引き）の結果が届きます\n"
    "　もっと知りたいときは「3枚で深掘り（有料）」から /buy へどうぞ\n"
    "\n"
    "💬 相談モード\n"
    "\n"
    "今の気持ちを整理し、\n"
    "次に試せそうな小さな行動を一緒に考えます。\n"
    "雑談でも、愚痴でも大丈夫です。安心して話してください。\n"
    "\n"
    "🎯 テーマ別の質問例\n"
    "\n"
    "{theme_examples}\n"
    "\n"
    "🛒 チャージ\n"
    "/buy または「🛒チャージ」から購入できます。\n"
    "本格的な占いを続けたいとき、\n"
    "いつでも話せる相談相手が欲しいときにご利用ください。\n"
    "\n"
    "🚫 禁止／注意\n"
    "医療・法律・投資・自傷や危機対応は専門家の領域です。\n"
    "このボットでは、気持ちや行動の整理までをお手伝いします。\n"
    "\n"
    "📜 規約：/terms でいつでも確認できます。"
)

EMPTY_QUESTION_TEXT = (
    "ご相談内容が空のようです。1文で大丈夫なので、気になっていることを教えてくださいね。\n"
    "例：『あの人とこの先うまくいく？』"
)

LONG_QUESTION_TEXT = (
    f"少し長めのようです。{MAX_QUESTION_CHARS}文字以内で要点を1文にまとめてもらえると助かります。\n"
    "テンプレ例：『現状』『知りたいこと』『いつ頃』を短く教えてください。"
)

NON_TEXT_MESSAGE_TEXT = (
    "テキストで送ってくださいませ。絵文字やスタンプだけでは占えないので、1文で教えてくださいね。"
)

THROTTLE_TEXT = "恐れ入ります、少し間をあけてからもう一度お試しくださいませ。"

RETRY_READING_TEXT = "ただいま生成に少し時間がかかっています。少しおいてから、もう一度お試しいただけると助かります。"

START_TEXT = (
    "こんにちは、タロット占い＆お悩み相談 tarot_cat です🐈‍⬛\n"
    "ワンオラクルは1日2回まで無料でカードを引けます（/read1）。\n"
    "\n"
    "もっとじっくり占いたい方や、\n"
    "トークや相談を自由に使いたい方には7日／30日パスも用意しています。\n"
    "\n"
    "下のボタンから\n"
    "「🎩占い」または「💬相談」を選んでください。\n"
    "使い方は /help で確認できます。\n"
)

STORE_INTRO_TEXT = (
    "購入後は、そのまま「🎩占い」や「💬相談」に戻れます。\n"
    "Stars はアカウント内に残り、余った分は次回も使えます。\n"
)

NON_CONSULT_OUT_OF_QUOTA_MESSAGE = (
    "このボットはタロット占い・相談用です。占いは /read1、恋愛は /love1 などをご利用"
    "ください。チャージは /buy です。"
)

STALE_CALLBACK_MESSAGE = "ボタンの有効期限が切れました。/buy からもう一度お願いします。"

TAROT_THEME_PROMPT = "🎩占いモードです。まずテーマを選んでください👇（恋愛/結婚/仕事/人生）"
TAROT_THEME_SELECT_PROMPT = "テーマを選んでください👇"
TAROT_QUESTION_PROMPT = (
    "✅テーマ：{theme_label}。占いたいことを1つ送ってください。\n"
    "例：『{example_text}』"
)
TAROT_THEME_SET_CONFIRMATION = "テーマを設定しました。"

TAROT_THEME_BUTTON_LOVE = "❤️恋愛"
TAROT_THEME_BUTTON_MARRIAGE = "💍結婚"
TAROT_THEME_BUTTON_WORK = "💼仕事"
TAROT_THEME_BUTTON_LIFE = "🌉人生"
UPGRADE_BUTTON_TEXT = "3枚で深掘り（有料）"

CONSULT_MODE_PROMPT = "💬相談モードです。なんでも相談してね。お話し聞くよ！"
CHARGE_MODE_PROMPT = "🛒 チャージメニュー\nチケット／パスを選んでください（Telegram Stars 決済）。"
STATUS_MODE_PROMPT = "📊現在のご利用状況です。"

INACTIVE_RESET_NOTICE = "しばらく操作がなかったため状態をリセットしました。/start か /help からやり直してください。"
