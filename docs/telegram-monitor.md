# Monitor via Telegram — passo a passo (para implementar depois)

Este documento descreve como integrar canais do Telegram ao monitor de ativos
sem violar termos de uso nem expor sua conta. **A integração ainda não está
implementada**; a V1 usa apenas RSS.

## O que é possível (e o que não é)

| Cenário | Viabilidade | Observação |
|---|---|---|
| Canal público (broadcast) que você segue | Alta | Leitura via Telethon com sua conta ou bot, se o canal permitir |
| Grupo privado do qual você participa | Média/baixa | Exige sua sessão e consentimento; não raspe em massa, respeite o grupo |
| Grupo privado do qual você não participa | Não | Sem acesso legítimo |
| Canal seu | Alta | Crie um bot administrador e use a Bot API |

Regra prática: **só leia o que você já tem acesso legítimo**, armazene apenas
trecho + link, e nunca republique conteúdo de terceiros.

## 1. Use uma conta dedicada

Sua conta pessoal dá acesso a conversas privadas. Para reduzir risco:

1. Crie uma conta secundária no Telegram (número virtual ou chip dedicado).
2. Entre apenas nos canais/grupos que deseja monitorar.
3. Não use essa conta para conversas pessoais.
4. Se algo der errado, revogue a sessão (Dispositivos conectados) ou exclua a conta.

## 2. Obtenha API ID e API Hash

1. Acesse <https://my.telegram.org> com a conta dedicada.
2. Vá em **API development tools**.
3. Crie um aplicativo (nome e plataforma podem ser genéricos).
4. Anote `api_id` e `api_hash`. Eles identificam o aplicativo, não a conta.

## 3. Instale o Telethon

Fora da imagem principal (para não aumentar o container sem necessidade):

```bash
python3 -m venv .venv-telegram
source .venv-telegram/bin/activate
pip install telethon
```

## 4. Gere uma sessão (StringSession)

Crie um script local, por exemplo `telegram_login.py`:

```python
from telethon.sync import TelegramClient
from telethon.sessions import StringSession

api_id = int(input("api_id: "))
api_hash = input("api_hash: ")

with TelegramClient(StringSession(), api_id, api_hash) as client:
    print(client.session.save())
    for dialog in client.iter_dialogs():
        if dialog.is_channel:
            print(dialog.id, dialog.name, getattr(dialog.entity, "username", None))
```

O comando pedirá seu telefone e o código recebido no Telegram. A string impressa
é a **sessão completa** — quem tiver essa string controla a conta.

## 5. Guarde os segredos no `.env` da VPS

```bash
TELEGRAM_API_ID=123456
TELEGRAM_API_HASH=...
TELEGRAM_SESSION=1BVtsOK...
```

Nunca versione esses valores. O `deploy/compose.yaml` precisará passá-los ao
container **apenas se o coletor rodar dentro dele**; a alternativa mais segura é
rodar o coletor em um processo separado no host, com acesso somente leitura à
mesma pasta de dados.

## 6. Descubra os canais

No script acima, `iter_dialogs()` lista canais e grupos. Prefira:

- canais públicos (`username` definido) — link estável `https://t.me/<username>`;
- grupos em que você é membro e cujo conteúdo é público.

Evite grupos privados com dados pessoais. Se for inevitável, obtenha
consentimento e armazene apenas o mínimo.

## 7. Colete mensagens com limites

```python
from datetime import datetime, timedelta, timezone
from telethon.sync import TelegramClient
from telethon.sessions import StringSession

with TelegramClient(StringSession(session), api_id, api_hash) as client:
    since = datetime.now(timezone.utc) - timedelta(days=1)
    for message in client.iter_messages("@canal", offset_date=None, limit=200):
        if message.date < since:
            break
        print(message.id, message.date, (message.message or "")[:500])
```

Regras:

- máximo de mensagens por execução (ex.: 200);
- uma passada por canal por hora, no máximo;
- trate `FloodWaitError` dormindo o tempo indicado;
- não baixe mídia nem membros;
- guarde só `id`, `date`, `texto` (trecho) e `https://t.me/<canal>/<id>`.

## 8. Converta para o mesmo `Signal` do RSS

O monitor já tem o contrato pronto (`src/domain/signals.py`):

```python
Signal(
    source="Telegram — <canal>",
    source_type="telegram",
    title=(message.message or "")[:200],
    url=f"https://t.me/{username}/{message.id}",
    summary=(message.message or "")[:2000],
    published_at=message.date,
    collected_at=datetime.now(timezone.utc),
    content_hash=sha256(texto.encode()).hexdigest(),
    assets=tuple(extract_assets(texto, issuers=issuers)),
)
```

A deduplicação é por `(source, url)`, então reexecuções não duplicam. A partir
daí, extração e ranking são os mesmos — não é preciso um motor separado.

## 9. Implementação sugerida (quando decidir)

1. `src/monitor/telegram.py` com uma função `fetch_channel(session, channel, since) -> list[FeedItem]`.
2. `jobs/collect_telegram.py` com `--channel @x` repetível e `--since-days 1`.
3. Timer systemd próprio (`dash-invest-telegram.timer`), horário diferente do RSS.
4. Rodar em um sidecar/venv do host, não no container principal, para isolar a sessão.
5. Testes com um `FakeTelegramClient` (sem rede).

## 10. Segurança e conformidade

- A sessão do Telegram é equivalente à senha da conta. Use conta dedicada,
  restrinja o acesso ao arquivo (modo `600`) e revogue se houver suspeita.
- Respeite os termos do Telegram e as regras de cada grupo.
- LGPD: não armazene nomes, telefones ou mensagens de terceiros além do
  necessário; prefira conteúdo público e links.
- Não use o monitor para spam, revenda de conteúdo ou recomendações a terceiros.
- Lembre-se: mensagens de grupos são opinião, não fato; o ranking continuará
  determinístico e mostrará a fonte e a data.
