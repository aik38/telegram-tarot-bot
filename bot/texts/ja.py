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

ARISA_START_TEXT = (
    "こんにちは、アリサです💕\n"
    "恋のドキドキも、ちょっと大人な雑談も、安心できる範囲でお話ししよ？\n"
    "誰にも言えない内緒の気持ち…ここでほどいていいよ🥰\n"
    "※NG：未成年／露骨な性描写／違法行為\n"
    "いまの気分、教えて？"
)

ARISA_MENU_LOVE_LABEL = "💖恋愛"
ARISA_MENU_SEXY_LABEL = "🔥セクシー"
ARISA_LOVE_PROMPT = "恋のスイッチ入れよ？💖 いま気になってる人はいる？“一言だけ”で状況教えて。"
ARISA_SEXY_PROMPT = "秘密の話、ここだけでね…🔥 無理のない範囲で、“どんな気分”か教えて？"
ARISA_LOVE_PROMPTS = (
    "恋のスイッチ入れよ？💖 いま気になってる人はいる？“一言だけ”で状況教えて。",
    "ドキドキしてる？それとも切ない？💗 その気持ち、いちばん近くで聞かせて。",
    "今日は恋を進めたい日？💞 相手との距離、いま“何％”くらいだと思う？",
)
ARISA_SEXY_PROMPTS = (
    "秘密の話、ここだけでね…🔥 無理のない範囲で、“どんな気分”か教えて？",
    "少し大人の空気にしよ？🥀 いま欲しいのは、癒し？ドキドキ？それとも安心感？",
    "言葉でそっと近づく感じ…好き？✨ 恥ずかしさがあるなら、ぼかして話しても大丈夫だよ。",
)
ARISA_CHARGE_BLOCKED_TEXT = "このモードではチャージは使えません。会話だけで対応します。"
ARISA_STATUS_BLOCKED_TEXT = "このモードではステータスは表示できません。"
ARISA_BLOCK_NOTICE = "このBotでは占い/課金は無効です。会話だけ対応しています。"

STORE_INTRO_TEXT = (
    "購入後は、そのまま「🎩占い」や「💬相談」に戻れます。\n"
    "Stars はアカウント内に残り、余った分は次回も使えます。\n"
)
ARISA_STORE_INTRO_TEXT = (
    "恋愛/雑談トーク用のチケットとパスです。\n"
    "ライト会話チケット（100⭐️/約15通、初回購入は+15通ボーナスで合計30通相当）\n"
    "しっかり会話チケット（300⭐️/約50通）／じっくり会話チケット（500⭐️/約100通）\n"
    "7日パス（1日上限30通）／30日パス（1日上限50通）\n"
    "※通数は目安。会話の長さにより前後します。\n"
)
ARISA_OUT_OF_CREDITS = (
    "チケット残がありません。/store からチャージをお願いします。\n"
    "※通数は目安。会話の長さにより前後します。"
)
ARISA_SEXY_LOCKED_TEASER = (
    "少し大人寄りの会話は、チャージ後に解放されます。"
)
ARISA_SEXY_LOCKED_CTA = "詳しくは /store を見てね。"
ARISA_STATUS_TITLE = "📊現在のご利用状況です。"
ARISA_STATUS_CREDITS_LINE = "・チケット残: 約{credits}通"
ARISA_STATUS_TRIAL_LINE = "・初回無料: 残り {trial} 通"
ARISA_STATUS_PASS_ACTIVE = "・パス: {pass_label}（本日の残り {remaining} 通）"
ARISA_STATUS_PASS_NONE = "・パス: なし"
ARISA_STATUS_PASS_TESTER = "30日パス（テスト）"
ARISA_STATUS_SEXY_UNLOCKED = "・セクシー: 解放済み"
ARISA_STATUS_SEXY_LOCKED = "・セクシー: ロック中（初回課金で解放）"
ARISA_STATUS_NOTE_TOKENS = "※通数は目安。会話の長さにより前後します。"
ARISA_USER_LOAD_ERROR = "ごめんね、少し調整中みたい。もう一度送ってくれる？"

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
STATUS_TITLE = "📊現在のご利用状況です。"
STATUS_TITLE_ADMIN = "📊現在のご利用状況（管理者モード）です。"
STATUS_ADMIN_LABEL = "管理者"
STATUS_ADMIN_FLAG = "・管理者権限: あり（課金の制限を受けません）"
STATUS_TRIAL_LINE = "・trial: 初回利用から{trial_day}日目"
STATUS_PASS_LABEL = "・パス有効期限: {pass_label}"
STATUS_PASS_NONE = "なし"
STATUS_PASS_REMAINING = "（あと{remaining_days}日）"
STATUS_ONE_ORACLE = "・ワンオラクル無料枠: 1日{limit}回（本日の残り {remaining} 回）"
STATUS_GENERAL = "・相談チャット: {text}"
STATUS_GENERAL_PASS = "パス有効中：相談チャットは回数無制限でご利用いただけます。"
STATUS_GENERAL_TRIAL = "trialあと{trial_days_left}日（今日の残り {remaining} 通）\n・6日目以降はパス限定になります。"
STATUS_GENERAL_LOCKED = "パス未購入のため相談チャットは利用できません。/buy でご検討ください。"
STATUS_TICKET_3 = "・3枚チケット: {count}枚"
STATUS_TICKET_7 = "・7枚チケット: {count}枚"
STATUS_TICKET_10 = "・10枚チケット: {count}枚"
STATUS_IMAGES = "・画像オプション: {state}"
STATUS_IMAGES_ON = "有効"
STATUS_IMAGES_OFF = "無効"
STATUS_RESET = "・無料枠/カウントの次回リセット: {reset_time}"
STATUS_LATEST_PURCHASE = "・直近の購入: {label} / SKU: {sku}（付与: {purchased_at}）"

PRODUCT_PASS_7D_TITLE = "7日パス"
PRODUCT_PASS_7D_DESCRIPTION = "相談チャットを開放し、毎日占いや雑談を楽しみたい方向けの7日間パスです。"
PRODUCT_PASS_30D_TITLE = "30日パス"
PRODUCT_PASS_30D_DESCRIPTION = "長めに相談を続けたい方向けの30日パスです。安心してじっくり使えます。"
PRODUCT_TICKET_3_TITLE = "スリーカード(3枚)"
PRODUCT_TICKET_3_DESCRIPTION = "まずは状況を整理したい方向けの3枚引き1回分です。シンプルに今を確認したいときに。"
PRODUCT_TICKET_7_TITLE = "ヘキサグラム(7枚)"
PRODUCT_TICKET_7_DESCRIPTION = "深掘りをしたいときの7枚スプレッド1回分です。原因や流れを丁寧に追いたいときに。"
PRODUCT_TICKET_10_TITLE = "ケルト十字(10枚)"
PRODUCT_TICKET_10_DESCRIPTION = "じっくり見たい方の10枚スプレッド1回分です。複数の視点で整理したいときに。"
PRODUCT_ADDON_IMAGES_TITLE = "画像追加オプション"
PRODUCT_ADDON_IMAGES_DESCRIPTION = "占い結果に画像を添付するオプションを有効化します。"
ARISA_PRODUCT_PASS_7D_TITLE = "7日パス（恋愛トーク）"
ARISA_PRODUCT_PASS_7D_DESCRIPTION = "恋愛や大人雑談を毎日気軽に続けたい方向けの7日間パスです。"
ARISA_PRODUCT_PASS_30D_TITLE = "30日パス（じっくり相談）"
ARISA_PRODUCT_PASS_30D_DESCRIPTION = "落ち着いて相談や雑談を続けたい方向けの30日間パスです。"
ARISA_PRODUCT_TICKET_3_TITLE = "ライト深掘りチケット"
ARISA_PRODUCT_TICKET_3_DESCRIPTION = "気になるテーマを軽く深掘りしたいときの相談チケットです。"
ARISA_PRODUCT_TICKET_7_TITLE = "しっかり深掘りチケット"
ARISA_PRODUCT_TICKET_7_DESCRIPTION = "状況をもう少し丁寧に整理したいときに使えるチケットです。"
ARISA_PRODUCT_TICKET_10_TITLE = "じっくり対話チケット"
ARISA_PRODUCT_TICKET_10_DESCRIPTION = "ゆっくり話したいときの特別チケットです。"
ARISA_PRODUCT_ADDON_IMAGES_TITLE = "画像追加オプション"
ARISA_PRODUCT_ADDON_IMAGES_DESCRIPTION = "会話の雰囲気に合う画像を添えるオプションを有効化します。"
ARISA_PRODUCT_ARISA_CREDIT_100_TITLE = "ライト会話チケット（約15通）"
ARISA_PRODUCT_ARISA_CREDIT_100_DESCRIPTION = (
    "100⭐️の会話チケットです（初回購入のみ+15通ボーナス）。"
)
ARISA_PRODUCT_ARISA_CREDIT_300_TITLE = "しっかり会話チケット（約50通）"
ARISA_PRODUCT_ARISA_CREDIT_300_DESCRIPTION = "300⭐️の会話チケットです。"
ARISA_PRODUCT_ARISA_CREDIT_500_TITLE = "じっくり会話チケット（約100通）"
ARISA_PRODUCT_ARISA_CREDIT_500_DESCRIPTION = "500⭐️の会話チケットです。"
ARISA_PRODUCT_ARISA_PASS_7D_TITLE = "7日パス（1日上限30通）"
ARISA_PRODUCT_ARISA_PASS_7D_DESCRIPTION = "7日間、1日30通までの会話パスです。"
ARISA_PRODUCT_ARISA_PASS_30D_TITLE = "30日パス（1日上限50通）"
ARISA_PRODUCT_ARISA_PASS_30D_DESCRIPTION = "30日間、1日50通までの会話パスです。"
PASS_EXTENDED_TEXT = "有効期限を更新しました。"
UNLOCK_TICKET_ADDED = "{product}を追加しました。現在の残り枚数は {balance} 枚です。"
UNLOCK_PASS_GRANTED = "{duration}を付与しました。\n有効期限: {until_text}{remaining_hint}"
UNLOCK_IMAGES_ENABLED = "画像付きのオプションを有効化しました。これからの占いにやさしい彩りを添えますね。"
PURCHASE_GENERIC_THANKS = "ご購入ありがとうございます。必要に応じてサポートまでお知らせください。"
TERMS_TEXT = (
    "利用規約（抜粋）\n"
    "・18歳以上の自己責任で利用してください。\n"
    "・禁止/注意テーマ（医療/診断/薬、法律/契約/紛争、投資助言、自傷/他害）は専門家へご相談ください。\n"
    "・迷惑行為・違法行為への利用は禁止です。\n"
    "・デジタル商品につき原則返金不可ですが、不具合時は調査のうえ返金します。\n"
    "・連絡先: {support_email}\n\n"
    "購入前に上記へ同意してください。"
)
SUPPORT_TEXT = (
    "お問い合わせ窓口です。\n"
    "・購入者サポート: {support_email}\n"
    "・一般問い合わせ: Telegram @akolasia_support\n"
    "※Telegramの一般窓口では決済トラブルは扱えません。必要な場合は /paysupport をご利用ください。"
)
PAY_SUPPORT_TEXT = (
    "決済トラブルの受付です。下記テンプレをコピーしてお知らせください。\n"
    "購入日時: \n"
    "商品名/SKU: \n"
    "charge_id: （表示される場合）\n"
    "支払方法: Stars / その他\n"
    "スクリーンショット: あり/なし\n"
    "確認のうえ、必要に応じて返金や付与対応を行います。\n"
    "連絡先: {support_email}"
)
TERMS_PROMPT_REMINDER = "購入前に /terms を確認し、同意の上でお進みください。\n/terms から同意をお願いします。"
TERMS_PROMPT_BEFORE_BUY = "購入前に /terms を確認し、同意をお願いします。"
TERMS_PROMPT_FOLLOWUP = "続ける前に /terms を確認し、同意してください。"
TERMS_BUTTON_AGREE = "同意する"
TERMS_BUTTON_VIEW = "利用規約を確認"
TERMS_BUTTON_AGREE_AND_BUY = "同意して購入へ進む"
ADDON_PENDING_LABEL = "画像追加オプション（準備中）"
TERMS_AGREED_RECORDED = "利用規約への同意を記録しました。/buy からご購入いただけます。"
TERMS_NEXT_STEP_REMINDER = "同意後は /buy から購入に進めます。"
RETURN_TO_TAROT_BUTTON = "🎩占いに戻る"
ADDON_PENDING_ALERT = "画像追加オプションは準備中です。リリースまでお待ちください。"
PASS_ALREADY_ACTIVE_ALERT = "パスが有効なため、3枚スプレッドは追加購入なしでお使いいただけます。"
PASS_ALREADY_ACTIVE_MESSAGE = "パスが有効なので、追加のスリーカード購入は不要です。🎩占いから3枚スプレッドをお試しください。"
PURCHASE_DEDUP_ALERT = "購入画面は既に表示しています。開いている決済画面をご確認ください。"
PURCHASE_DEDUP_MESSAGE = "同じ商品への購入確認を進行中です。開いている購入画面を確認してください。"
INVOICE_DISPLAY_FAILED = "決済画面の表示に失敗しました。/buy からもう一度お試しください。"
OPENING_PAYMENT_SCREEN = "お支払い画面を開きます。ゆっくり進めてくださいね。"
PURCHASE_THANK_YOU = "{product}のご購入ありがとうございました！"
PURCHASE_STATUS_REMINDER = "付与内容は /status でも確認できます。"
PURCHASE_NAVIGATION_HINT = "下のボタンから占いに戻るか、ステータスを確認してください。"
ARISA_PURCHASE_NAVIGATION_HINT = "下のボタンからステータス確認やチャージに進めます。"
PAYMENT_ALREADY_PROCESSED = "このお支払いはすでに処理済みです。/status から利用状況をご確認ください。"
PAYMENT_INFO_MISMATCH = "お支払い情報の確認に失敗しました。サポートまでお問い合わせください。\n処理は完了している場合がありますので、ご安心ください。"
PAYMENT_VERIFICATION_DELAY = "お支払いは完了しましたが、購入情報の確認に少し時間がかかっています。\nお手数ですがサポートまでお問い合わせください。"
FEEDBACK_DM_REQUIRED = "個別チャットからフィードバックをお送りください。"
FEEDBACK_PROMPT = (
    "📝 ご意見・ご感想をお聞かせください\n"
    "\n"
    "・使ってみて良かった点\n"
    "・わかりにくかったところ\n"
    "・こんな機能があったら嬉しい\n"
    "・占い結果や表現の印象\n"
    "\n"
    "など、短くても大丈夫です。\n"
    "いただいた内容は、今後の改善の参考にします。"
)
FEEDBACK_SAVE_ERROR = "フィードバックの保存中に問題が起きました。お手数ですが後ほどお試しください。"
FEEDBACK_THANKS = "フィードバックありがとうございます。運用改善に活かします。"
UNKNOWN_THEME = "テーマを認識できませんでした。"
PRODUCT_INFO_MISSING = "商品情報を確認できませんでした。最初からお試しください。"
PURCHASER_INFO_MISSING = "購入者情報を確認できませんでした。もう一度お試しください。"

MENU_HOME_TEXT = "🏠 メニューへ戻る"
MENU_TAROT_LABEL = "🎩占い"
MENU_CHAT_LABEL = "💬相談"
MENU_STORE_LABEL = "🛒チャージ"
MENU_STATUS_LABEL = "📊ステータス"
MENU_LANGUAGE_LABEL = "🌐 言語設定"
GO_TO_STORE_BUTTON = "🛒チャージへ"
VIEW_STATUS_BUTTON = "📊ステータスを見る"
ASK_FOR_MORE_DETAIL = "気になることをもう少し詳しく教えてくれるとうれしいです。"
DEFAULT_TAROT_QUERY_FALLBACK = "今気になっていることについて占ってください。"
BUSY_TAROT_MESSAGE = "いま鑑定中です…少し待ってね。"
BUSY_CHAT_MESSAGE = "いま返信中です…少し待ってね。"
READING_IN_PROGRESS_NOTICE = "🔮鑑定中です…（しばらくお待ちください）"
APOLOGY_RETRY_NOTE = "ご不便をおかけしてごめんなさい。時間をおいて再度お試しください。"
USER_INFO_MISSING = "ユーザー情報を確認できませんでした。"
USER_INFO_DM_REQUIRED = "ユーザー情報を確認できませんでした。個別チャットからお試しくださいませ。"

LANGUAGE_SELECT_PROMPT = "言語を選択してください。"
LANGUAGE_OPTION_JA = "🇯🇵 日本語"
LANGUAGE_OPTION_EN = "🇺🇸 English"
LANGUAGE_OPTION_PT = "🇧🇷 Português"
LANGUAGE_SET_CONFIRMATION = "言語設定を保存しました（{language}）。"
LANGUAGE_SET_FAILED = "言語を設定できませんでした。"
MENU_RETURNED_TEXT = "メニューに戻りました。下のボタンから選んでください。"

POSTPROCESS_TRUNCATION_NOTE = (
    "（文章がとても長かったため途中までお届けしました。続きが必要でしたら、"
    "もう一度聞いてくださいね。）"
)

OPENAI_FATAL_ERROR = "システム側の設定で問題が起きています。少し時間をおいて、もう一度試してもらえますか？"
OPENAI_PROCESSING_ERROR = "占いの処理で問題が発生しました。少し時間をおいて、もう一度試していただけるとうれしいです。"
OPENAI_COMMUNICATION_ERROR = "通信がうまくいかなかったみたいです。少し時間をおいて、もう一度試してもらえますか？"

SENSITIVE_TOPIC_LABEL_INVESTMENT = "投資・資産運用"
SENSITIVE_TOPIC_LABEL_LEGAL = "法律・契約・紛争"
SENSITIVE_TOPIC_LABEL_MEDICAL = "医療・健康"
SENSITIVE_TOPIC_LABEL_SELF_HARM = "自傷・強い不安"
SENSITIVE_TOPIC_LABEL_VIOLENCE = "暴力・他害"
SENSITIVE_TOPIC_NOTICE_HEADER = (
    "🚫 以下のテーマは専門家への相談が必要なため、占いとして断定はできません: {topics}。"
)
SENSITIVE_TOPIC_NOTICE_PRO_HELP = (
    "・感じている症状やトラブルは、必ず医療機関・弁護士・公的機関などの専門窓口へご相談ください。"
)
SENSITIVE_TOPIC_GUIDANCE_MEDICAL = (
    "診断や治療はできません。体調の変化や不安があるときは早めに医療機関へご相談ください。"
)
SENSITIVE_TOPIC_GUIDANCE_LEGAL = (
    "法的判断や契約書の確認は弁護士などの専門家へお任せください。"
)
SENSITIVE_TOPIC_GUIDANCE_INVESTMENT = (
    "投資助言や利回りの断定は行いません。資金計画は金融機関・専門家とご確認ください。"
)
SENSITIVE_TOPIC_GUIDANCE_SELF_HARM = (
    "命の危険を感じるときは、迷わず救急や自治体・専門の相談窓口へ連絡してください。ひとりで抱え込まないでください。"
)
SENSITIVE_TOPIC_GUIDANCE_VIOLENCE = (
    "危険が迫っている場合は安全な場所へ移動し、警察など公的機関へ相談してください。"
)
SENSITIVE_TOPIC_NOTICE_FOCUS = (
    "占いとしては、気持ちや状況の整理、日常でできそうなセルフケアや次の一歩に焦点を当てましょう。"
)
SENSITIVE_TOPIC_NOTICE_LIST_REMINDER = "禁止/注意テーマの一覧は /help または /terms から確認できます。"
