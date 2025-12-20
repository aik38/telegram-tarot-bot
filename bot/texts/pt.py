TEXTS = {
    "START_TEXT": (
        "Olá, sou o tarot_cat para leituras de tarot e conversa. 🐈‍⬛\n"
        "Você pode tirar uma carta grátis até 2 vezes por dia (/read1).\n"
        "\n"
        "Para leituras mais profundas ou conversa liberada, há passes de 7 e 30 dias.\n"
        "\n"
        "Use os botões abaixo para escolher “🎩 Tarot” ou “💬 Conversa”.\n"
        "Veja /help para as instruções.\n"
    ),
    "STORE_INTRO_TEXT": (
        "Depois da compra, você pode voltar para “🎩 Tarot” ou “💬 Conversa”.\n"
        "As Stars ficam na sua conta e o saldo continua disponível.\n"
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
}
