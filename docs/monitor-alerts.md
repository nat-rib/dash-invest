# Monitor — alertas e backtest

## Alertas

O job `jobs.monitor_daily` roda todo dia às 07:30 (America/Sao_Paulo), grava um
snapshot do ranking e envia alertas dos candidatos acima do score mínimo. O
mesmo ativo não é alertado de novo dentro do cooldown.

### Canais

Configure no `.env` da VPS (ou local):

```bash
ALERT_CHANNELS=console,telegram     # console sempre útil para log
ALERT_MIN_SCORE=80
ALERT_COOLDOWN_DAYS=3
ALERT_MAX_PER_RUN=5
```

Sem canais externos, o alerta só aparece no `journalctl` (console).

### Telegram (bot)

1. No Telegram, abra **@BotFather** e envie `/newbot`.
2. Escolha nome e usuário; guarde o **token** (`123456:ABC...`).
3. Envie uma mensagem qualquer para o seu bot (ou adicione-o a um grupo).
4. Descubra o `chat_id`:

```bash
curl "https://api.telegram.org/bot<TOKEN>/getUpdates"
# procure result[].message.chat.id (grupos têm id negativo)
```

5. No `.env`:

```bash
TELEGRAM_BOT_TOKEN=123456:ABC...
TELEGRAM_CHAT_ID=123456789
ALERT_CHANNELS=console,telegram
```

6. Recrie o container e teste:

```bash
docker compose up -d --force-recreate
docker exec dash-invest python -m jobs.monitor_daily --test
```

O token do bot pode ser revogado a qualquer momento no BotFather. Nunca o
versione.

### E-mail (SMTP)

```bash
ALERT_CHANNELS=console,email
SMTP_HOST=smtp.seuprovedor.com
SMTP_PORT=587
SMTP_USER=voce@exemplo.com
SMTP_PASSWORD=sua-senha-ou-app-password
ALERT_EMAIL_FROM=voce@exemplo.com
ALERT_EMAIL_TO=voce@exemplo.com
```

Porta 465 usa SSL; 587 usa STARTTLS. Para Gmail, use uma **senha de app**.

### Regras

- Só alerta candidatos com `score >= ALERT_MIN_SCORE`.
- Cooldown por ativo (`ALERT_COOLDOWN_DAYS`) evita repetição.
- No máximo `ALERT_MAX_PER_RUN` alertas por execução.
- Falha de um canal não impede os outros; erros aparecem no log.
- O alerta é uma **triagem**, não recomendação.

## Backtest do ranking

Todo dia o snapshot registra, para cada candidato:

- score, confiança e componentes;
- preço de referência (fechamento mais recente até a data) e qual série foi usada.

Depois de 30 ou 90 dias, a página **Monitor** calcula o retorno futuro:

```
retorno = preço_no_horizonte / preço_de_referência - 1
```

O preço do horizonte é o último fechamento até a data-alvo (tolerância de 7
dias). Sem preço de referência ou sem preço maduro, o snapshot não entra.

### Como ler

- **Avaliados**: snapshots com retorno calculado.
- **Faixas de score**: retorno médio e taxa de acerto (retorno > 0) por faixa.
- **Spread topo-base**: retorno médio da faixa 80–100 menos a faixa 0–20.
- **Correlação de postos (Spearman)**: se positiva, scores maiores tenderam a
  vir antes de retornos maiores.

Amostra mínima padrão: 5 avaliações. Antes disso, a página mostra o motivo.

### Limitações

- Só ativos com série de preço entram (renda fixa fica fora).
- O horizonte depende da disponibilidade de fechamentos; feriados e falhas do
  provedor podem encurtar a janela.
- Correlação não é causalidade; amostras curtas são ruidosas.
- O backtest avalia o **ranking**, não recomenda compra/venda.
