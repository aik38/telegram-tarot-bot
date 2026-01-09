TEXTS = {
    "MAX_QUESTION_CHARS": 500,
    "EMPTY_QUESTION_TEXT": (
        "Parece que a mensagem veio vazia. Envie uma frase com sua pergunta.\n"
        "Ex.: “Vamos dar certo daqui para frente?”"
    ),
    "LONG_QUESTION_TEXT": (
        "Parece um pouco longo. Resuma em até 500 caracteres, em uma frase.\n"
        "Dica: inclua a situação, o que quer saber e quando."
    ),
    "NON_TEXT_MESSAGE_TEXT": (
        "Envie em texto, por favor. Apenas emojis ou figurinhas não funcionam—uma frase basta."
    ),
    "THROTTLE_TEXT": "Por favor, espere um pouco antes de tentar de novo.",
    "RETRY_READING_TEXT": (
        "A resposta está demorando um pouco. Tente novamente depois de aguardar um pouco."
    ),
    "START_TEXT": (
        "Olá, sou o tarot_cat para leituras de tarot e conversa. 🐈‍⬛\n"
        "Você pode tirar uma carta grátis até 2 vezes por dia (/read1).\n"
        "\n"
        "Para leituras mais profundas ou conversa liberada, há passes de 7 e 30 dias.\n"
        "\n"
        "Use os botões abaixo para escolher “🎩 Tarot” ou “💬 Conversa”.\n"
        "Veja /help para as instruções.\n"
    ),
    "ARISA_START_TEXT": (
        "Oi, eu sou a Arisa. 💕\n"
        "Podemos falar de amor com frio na barriga ou de um papo mais adulto—sempre com segurança.\n"
        "Tem um sentimento secreto? Pode desabafar por aqui. 🥰\n"
        "※ NG: menores / descrições sexuais explícitas / atividades ilegais\n"
        "Me conta como você está se sentindo agora."
    ),
    "ARISA_MENU_LOVE_LABEL": "💖 Amor",
    "ARISA_MENU_SEXY_LABEL": "🔥 Sexy",
    "ARISA_LOVE_PROMPT": (
        "Vamos ligar o modo amor. 💖 Tem alguém na sua cabeça? Conta a situação em uma linha."
    ),
    "ARISA_SEXY_PROMPT": (
        "Um segredo só nosso… 🔥 Compartilhe apenas o que for confortável — que tipo de clima você quer?"
    ),
    "ARISA_LOVE_PROMPTS": [
        "Vamos ligar o modo amor. 💖 Tem alguém na sua cabeça? Conta a situação em uma linha.",
        "Você está radiante ou mais melancólica(o)? 💗 Deixa eu ouvir esse sentimento de perto.",
        "Hoje é dia de avançar no amor? 💞 A distância entre vocês está em quantos por cento?",
    ],
    "ARISA_SEXY_PROMPTS": [
        "Um segredo só nosso… 🔥 Compartilhe apenas o que for confortável — que tipo de clima você quer?",
        "Que tal um clima mais adulto? 🥀 Você quer carinho, um frio na barriga ou mais calma?",
        "Você curte essa aproximação pelas palavras? ✨ Se estiver com vergonha, pode falar de forma indireta.",
    ],
    "ARISA_CHARGE_BLOCKED_TEXT": "Recargas não estão disponíveis neste modo. Aqui é só conversa.",
    "ARISA_STATUS_BLOCKED_TEXT": "Status não está disponível neste modo.",
    "ARISA_BLOCK_NOTICE": "Tarô e pagamentos estão desativados neste bot. Só conversa.",
    "STORE_INTRO_TEXT": (
        "Depois da compra, você pode voltar para “🎩 Tarot” ou “💬 Conversa”.\n"
        "As Stars ficam na sua conta e o saldo continua disponível.\n"
    ),
    "ARISA_STORE_INTRO_TEXT": (
        "Após a compra, você volta direto para o papo de amor ou conversa casual.\n"
        "As Stars ficam na sua conta e o saldo restante pode ser usado depois.\n"
    ),
    "HELP_TEXT_TEMPLATE": (
        "❓ Como usar\n"
        "\n"
        "1. Toque em “🎩 Tarot” e escolha um tema (amor/casamento/trabalho/vida).\n"
        "2. Envie sua pergunta em uma frase.\n"
        "   Ex.: “Como vai ser meu trabalho este mês?”\n"
        "3. Você recebe uma leitura de 1 carta.\n"
        "   Para mais detalhes, use “3 cartas (pago)” ou /buy.\n"
        "\n"
        "💬 Modo conversa\n"
        "\n"
        "Organize seus sentimentos e encontre o próximo pequeno passo.\n"
        "Desabafos e bate-papo casual também são bem-vindos.\n"
        "\n"
        "🎯 Exemplos por tema\n"
        "\n"
        "{theme_examples}\n"
        "\n"
        "🛒 Créditos\n"
        "Compre via /buy ou “🛒 Loja”.\n"
        "Útil para leituras mais longas ou para conversar sempre que quiser.\n"
        "\n"
        "🚫 Aviso\n"
        "Questões de saúde, legais, investimentos ou autolesão devem ser tratadas por profissionais.\n"
        "Este bot ajuda apenas na reflexão e em pequenos passos práticos.\n"
        "\n"
        "📜 Termos: veja /terms quando quiser."
    ),
    "TERMS_TEXT": (
        "Termos (resumo)\n"
        "- Use por sua própria conta se tiver 18 anos ou mais.\n"
        "- Para temas médicos/jurídicos/investimentos/autolesão, procure profissionais.\n"
        "- Uso indevido ou ilegal é proibido.\n"
        "- Produtos digitais normalmente não são reembolsados; problemas serão analisados e reembolsados se necessário.\n"
        "- Contato: {support_email}\n\n"
        "Concorde antes de comprar."
    ),
    "SUPPORT_TEXT": (
        "Canal de contato.\n"
        "・Suporte a clientes: {support_email}\n"
        "・Perguntas gerais: Telegram @akolasia_support\n"
        "※ O Telegram geral não trata pagamentos. Para isso, use /paysupport."
    ),
    "PAY_SUPPORT_TEXT": (
        "Atendimento para problemas de pagamento. Copie e envie o modelo:\n"
        "Data/hora da compra:\n"
        "Produto/SKU:\n"
        "charge_id: (se aparecer)\n"
        "Forma de pagamento: Stars / Outro\n"
        "Captura de tela: sim/não\n"
        "Vamos verificar e reembolsar ou conceder o produto se necessário.\n"
        "Contato: {support_email}"
    ),
    "TERMS_PROMPT_BEFORE_BUY": "Confira /terms e aceite antes de comprar.",
    "TERMS_PROMPT_FOLLOWUP": "Confira /terms e aceite antes de continuar a compra.",
    "STATUS_TITLE": "📊 Seu uso atual.",
    "STATUS_TITLE_ADMIN": "📊 Uso (modo admin).",
    "STATUS_ADMIN_LABEL": "admin",
    "STATUS_ADMIN_FLAG": "• Privilégios de administrador: ativos (compras não são limitadas).",
    "STATUS_TRIAL_LINE": "• Dia de teste: dia {trial_day}",
    "STATUS_PASS_LABEL": "• Validade do passe: {pass_label}",
    "STATUS_PASS_NONE": "nenhum",
    "STATUS_PASS_REMAINING": "(faltam {remaining_days} dias)",
    "STATUS_ONE_ORACLE": "• Tiragens grátis de 1 carta: {limit} por dia (restam {remaining} hoje)",
    "STATUS_GENERAL": "• Conversa: {text}",
    "STATUS_GENERAL_PASS": "Passe ativo: conversa ilimitada.",
    "STATUS_GENERAL_TRIAL": (
        "O teste termina em {trial_days_left} dia(s) (restam {remaining} mensagens hoje).\n"
        "• A partir do 6º dia é preciso passe."
    ),
    "STATUS_GENERAL_LOCKED": "A conversa não está disponível sem passe. Considere /buy.",
    "STATUS_TICKET_3": "• Ingressos de 3 cartas: {count}",
    "STATUS_TICKET_7": "• Ingressos de 7 cartas: {count}",
    "STATUS_TICKET_10": "• Ingressos de 10 cartas: {count}",
    "STATUS_IMAGES": "• Opção de imagem: {state}",
    "STATUS_IMAGES_ON": "ativada",
    "STATUS_IMAGES_OFF": "desativada",
    "STATUS_RESET": "• Próximo reset dos limites gratuitos: {reset_time}",
    "STATUS_LATEST_PURCHASE": "• Compra recente: {label} / SKU: {sku} (crédito: {purchased_at})",
    "ARISA_PRODUCT_PASS_7D_TITLE": "Passe de 7 dias (Amor)",
    "ARISA_PRODUCT_PASS_7D_DESCRIPTION": "Passe de 7 dias para manter conversas de amor e papo adulto com leveza.",
    "ARISA_PRODUCT_PASS_30D_TITLE": "Passe de 30 dias (Papo profundo)",
    "ARISA_PRODUCT_PASS_30D_DESCRIPTION": "Passe de 30 dias para conversas contínuas e sem pressa.",
    "ARISA_PRODUCT_TICKET_3_TITLE": "Ticket de mergulho leve",
    "ARISA_PRODUCT_TICKET_3_DESCRIPTION": "Um ticket para aprofundar o assunto de forma rápida e suave.",
    "ARISA_PRODUCT_TICKET_7_TITLE": "Ticket de mergulho focado",
    "ARISA_PRODUCT_TICKET_7_DESCRIPTION": "Um ticket para organizar melhor a situação e conversar com calma.",
    "ARISA_PRODUCT_TICKET_10_TITLE": "Ticket de conversa lenta",
    "ARISA_PRODUCT_TICKET_10_DESCRIPTION": "Um ticket especial para conversar no seu ritmo.",
    "ARISA_PRODUCT_ADDON_IMAGES_TITLE": "Adicional de imagens",
    "ARISA_PRODUCT_ADDON_IMAGES_DESCRIPTION": "Ativa um toque visual que combina com o clima da conversa.",
    "NON_CONSULT_OUT_OF_QUOTA_MESSAGE": (
        "Este bot é para leituras de tarô e conversa. Use /read1 para leituras ou /love1 para temas de amor. "
        "Recarregue via /buy."
    ),
    "STALE_CALLBACK_MESSAGE": "O botão expirou. Abra /buy novamente, por favor.",
    "TAROT_THEME_PROMPT": "🎩 Modo tarô. Escolha um tema abaixo (Amor/Casamento/Trabalho/Vida).",
    "TAROT_THEME_SELECT_PROMPT": "Escolha um tema 👇",
    "TAROT_QUESTION_PROMPT": (
        "✅ Tema: {theme_label}. Envie uma pergunta que queira fazer.\n"
        "Exemplo: “{example_text}”"
    ),
    "TAROT_THEME_SET_CONFIRMATION": "Tema definido.",
    "TAROT_THEME_BUTTON_LOVE": "❤️ Amor",
    "TAROT_THEME_BUTTON_MARRIAGE": "💍 Casamento",
    "TAROT_THEME_BUTTON_WORK": "💼 Trabalho",
    "TAROT_THEME_BUTTON_LIFE": "🌉 Vida",
    "UPGRADE_BUTTON_TEXT": "Aprofundar em 3 cartas (pago)",
    "CONSULT_MODE_PROMPT": "💬 Modo conversa. Conte comigo para ouvir o que quiser!",
    "CHARGE_MODE_PROMPT": (
        "🛒 Menu de créditos\n"
        "Escolha um ticket ou passe (pagamento com Telegram Stars)."
    ),
    "STATUS_MODE_PROMPT": "📊 Seu uso atual.",
    "INACTIVE_RESET_NOTICE": (
        "A sessão foi reiniciada após inatividade. Comece novamente com /start ou /help."
    ),
    "MENU_HOME_TEXT": "🏠 Voltar ao menu",
    "MENU_TAROT_LABEL": "🎩 Tarot",
    "MENU_CHAT_LABEL": "💬 Conversa",
    "MENU_STORE_LABEL": "🛒 Loja",
    "MENU_STATUS_LABEL": "📊 Status",
    "MENU_LANGUAGE_LABEL": "🌐 Idioma",
    "GO_TO_STORE_BUTTON": "🛒 Ir para a loja",
    "VIEW_STATUS_BUTTON": "📊 Ver status",
    "ASK_FOR_MORE_DETAIL": "Conte um pouco mais sobre o que está pensando, por favor.",
    "DEFAULT_TAROT_QUERY_FALLBACK": "Faça uma leitura sobre o que estou pensando agora.",
    "BUSY_TAROT_MESSAGE": "Uma leitura já está em andamento—aguarde um instante.",
    "BUSY_CHAT_MESSAGE": "Estou respondendo agora—aguarde um instante.",
    "READING_IN_PROGRESS_NOTICE": "🔮 Leitura em andamento… aguarde, por favor.",
    "APOLOGY_RETRY_NOTE": "Desculpe o transtorno. Tente novamente depois de esperar um pouco.",
    "USER_INFO_MISSING": "Não conseguimos confirmar suas informações de usuário.",
    "USER_INFO_DM_REQUIRED": "Não conseguimos confirmar suas informações. Tente a partir de um chat direto, por favor.",
    "LANGUAGE_SELECT_PROMPT": "Escolha o idioma.",
    "LANGUAGE_OPTION_JA": "🇯🇵 Japonês",
    "LANGUAGE_OPTION_EN": "🇺🇸 Inglês",
    "LANGUAGE_OPTION_PT": "🇧🇷 Português",
    "LANGUAGE_SET_CONFIRMATION": "Idioma salvo ({language}).",
    "LANGUAGE_SET_FAILED": "Não foi possível atualizar o idioma.",
    "MENU_RETURNED_TEXT": "Voltamos ao menu. Use os botões abaixo.",
    "POSTPROCESS_TRUNCATION_NOTE": (
        "A mensagem estava muito longa, então enviei a primeira parte. "
        "Se quiser o restante, é só pedir novamente."
    ),
    "OPENAI_FATAL_ERROR": "Ocorreu um problema do nosso lado. Tente novamente em instantes.",
    "OPENAI_PROCESSING_ERROR": "Houve um problema ao processar a leitura. Tente novamente em breve.",
    "OPENAI_COMMUNICATION_ERROR": "A conexão falhou. Tente novamente depois de esperar um pouco.",
    "SENSITIVE_TOPIC_LABEL_INVESTMENT": "Investimentos/Finanças",
    "SENSITIVE_TOPIC_LABEL_LEGAL": "Legal/Contratos/Disputas",
    "SENSITIVE_TOPIC_LABEL_MEDICAL": "Saúde",
    "SENSITIVE_TOPIC_LABEL_SELF_HARM": "Autolesão/Angústia intensa",
    "SENSITIVE_TOPIC_LABEL_VIOLENCE": "Violência/Dano a outros",
    "SENSITIVE_TOPIC_NOTICE_HEADER": (
        "🚫 Esses temas exigem apoio profissional, então não podemos dar leituras definitivas: {topics}."
    ),
    "SENSITIVE_TOPIC_NOTICE_PRO_HELP": (
        "• Para sintomas ou problemas, consulte profissionais médicos, jurídicos ou órgãos públicos."
    ),
    "SENSITIVE_TOPIC_GUIDANCE_MEDICAL": (
        "Não fazemos diagnóstico ou tratamento. Procure profissionais de saúde rapidamente se houver preocupação."
    ),
    "SENSITIVE_TOPIC_GUIDANCE_LEGAL": (
        "Decisões legais e contratos devem ser analisados por um advogado."
    ),
    "SENSITIVE_TOPIC_GUIDANCE_INVESTMENT": (
        "Não damos conselhos de investimento nem garantimos retornos. Planeje com profissionais financeiros."
    ),
    "SENSITIVE_TOPIC_GUIDANCE_SELF_HARM": (
        "Se sentir perigo, contate emergências ou um canal de apoio imediatamente. Não enfrente isso sozinho."
    ),
    "SENSITIVE_TOPIC_GUIDANCE_VIOLENCE": (
        "Se houver risco, vá para um lugar seguro e contate a polícia ou autoridades."
    ),
    "SENSITIVE_TOPIC_NOTICE_FOCUS": (
        "Na leitura, focamos em organizar sentimentos e em próximos passos ou autocuidado prático."
    ),
    "SENSITIVE_TOPIC_NOTICE_LIST_REMINDER": "Veja /help ou /terms para a lista de temas restritos.",
    "PRODUCT_PASS_7D_TITLE": "Passe de 7 dias",
    "PRODUCT_PASS_7D_DESCRIPTION": "Passe de 7 dias que libera a conversa para você usar leituras ou bate-papo todos os dias.",
    "PRODUCT_PASS_30D_TITLE": "Passe de 30 dias",
    "PRODUCT_PASS_30D_DESCRIPTION": "Passe de 30 dias para acompanhar conversas por mais tempo, com tranquilidade.",
    "PRODUCT_TICKET_3_TITLE": "Leitura de 3 cartas",
    "PRODUCT_TICKET_3_DESCRIPTION": "Uma leitura de 3 cartas para organizar a situação—ideal para revisar o presente de forma simples.",
    "PRODUCT_TICKET_7_TITLE": "Hexagrama (7 cartas)",
    "PRODUCT_TICKET_7_DESCRIPTION": "Um hexagrama de 7 cartas para aprofundar—ótimo para acompanhar causas e fluxo.",
    "PRODUCT_TICKET_10_TITLE": "Cruz Celta (10 cartas)",
    "PRODUCT_TICKET_10_DESCRIPTION": "Uma Cruz Celta de 10 cartas para uma visão completa de vários ângulos.",
    "PRODUCT_ADDON_IMAGES_TITLE": "Complemento de imagem",
    "PRODUCT_ADDON_IMAGES_DESCRIPTION": "Ative a opção de anexar imagens às leituras.",
    "PASS_EXTENDED_TEXT": "Validade atualizada.",
    "UNLOCK_TICKET_ADDED": "Adicionado {product}. Saldo restante: {balance}.",
    "UNLOCK_PASS_GRANTED": "Passe concedido: {duration}.\nValidade: {until_text}{remaining_hint}",
    "UNLOCK_IMAGES_ENABLED": "Complemento de imagem ativado. Suas próximas leituras terão um toque visual.",
    "PURCHASE_GENERIC_THANKS": "Obrigado pela compra. Fale com o suporte se precisar de algo.",
    "TERMS_PROMPT_REMINDER": (
        "Revise /terms e concorde antes de comprar.\n"
        "Use /terms para registrar seu aceite."
    ),
    "TERMS_BUTTON_AGREE": "Concordar",
    "TERMS_BUTTON_VIEW": "Ver termos",
    "TERMS_BUTTON_AGREE_AND_BUY": "Concordar e seguir para a compra",
    "ADDON_PENDING_LABEL": "Complemento de imagem (em breve)",
    "TERMS_AGREED_RECORDED": "Seu aceite dos termos foi registrado. Você pode seguir com /buy.",
    "TERMS_NEXT_STEP_REMINDER": "Após concordar, continue com /buy para comprar.",
    "RETURN_TO_TAROT_BUTTON": "🎩 Voltar ao Tarot",
    "ADDON_PENDING_ALERT": "O complemento de imagem está chegando em breve. Aguarde mais um pouco.",
    "PASS_ALREADY_ACTIVE_ALERT": "Um passe está ativo, então a leitura de 3 cartas já está liberada.",
    "PASS_ALREADY_ACTIVE_MESSAGE": "O passe está ativo—não é preciso comprar outro ticket de 3 cartas. Experimente o spread de 3 cartas em 🎩 Tarot.",
    "PURCHASE_DEDUP_ALERT": "Uma tela de checkout já está aberta. Verifique a janela de pagamento.",
    "PURCHASE_DEDUP_MESSAGE": "Uma confirmação para o mesmo produto está em andamento. Verifique a tela de pagamento aberta.",
    "INVOICE_DISPLAY_FAILED": "Falha ao mostrar a tela de checkout. Tente /buy novamente.",
    "OPENING_PAYMENT_SCREEN": "Abrindo a tela de pagamento—siga no seu tempo.",
    "PURCHASE_THANK_YOU": "Obrigado por comprar {product}!",
    "PURCHASE_STATUS_REMINDER": "Você também pode ver os detalhes da concessão em /status.",
    "PURCHASE_NAVIGATION_HINT": "Use os botões abaixo para voltar ao Tarot ou ver seu status.",
    "PAYMENT_ALREADY_PROCESSED": "Este pagamento já foi processado. Consulte /status para detalhes.",
    "PAYMENT_INFO_MISMATCH": (
        "Não foi possível confirmar os dados do pagamento. Fale com o suporte, por favor.\n"
        "Se a cobrança foi concluída, resolveremos para você."
    ),
    "PAYMENT_VERIFICATION_DELAY": (
        "Pagamento concluído, mas a confirmação da compra está demorando um pouco.\n"
        "Entre em contato com o suporte se precisar."
    ),
    "FEEDBACK_DM_REQUIRED": "Envie o feedback a partir de um chat direto, por favor.",
    "FEEDBACK_PROMPT": (
        "📝 Conte sua opinião\n"
        "\n"
        "• O que funcionou bem\n"
        "• O que ficou confuso\n"
        "• Funcionalidades que gostaria de ver\n"
        "• Impressões sobre as leituras e linguagem\n"
        "\n"
        "Mensagens curtas são bem-vindas. Seu retorno nos ajuda a melhorar."
    ),
    "FEEDBACK_SAVE_ERROR": "Não foi possível salvar o feedback. Tente novamente mais tarde.",
    "FEEDBACK_THANKS": "Obrigado pelo feedback—vamos usá-lo para melhorar o serviço.",
    "UNKNOWN_THEME": "Não conseguimos reconhecer o tema.",
    "PRODUCT_INFO_MISSING": "Não foi possível confirmar as informações do produto. Comece novamente, por favor.",
    "PURCHASER_INFO_MISSING": "Não foi possível confirmar os dados do comprador. Tente outra vez.",
}
