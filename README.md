# Bengala — Bot Discord de Palavra Proibida

Bengala é um jogo diário para Discord onde uma palavra proibida secreta é escolhida automaticamente. Jogadores conversam normalmente no canal — quem disser a palavra proibida é silenciado até a próxima rodada. Ao final do dia, o placar é revelado com a contagem de palavras únicas de cada jogador.

## Sumário

- [Pré-requisitos](#pré-requisitos)
- [1. Criar o Bot no Discord](#1-criar-o-bot-no-discord)
- [2. Configurar Permissões e Intents](#2-configurar-permissões-e-intents)
- [3. Convidar o Bot para o Servidor](#3-convidar-o-bot-para-o-servidor)
- [4. Configurar o Servidor Discord](#4-configurar-o-servidor-discord)
- [5. Configurar Variáveis de Ambiente](#5-configurar-variáveis-de-ambiente)
- [6. Deploy com Docker (Recomendado)](#6-deploy-com-docker-recomendado)
- [7. Deploy Local (Desenvolvimento)](#7-deploy-local-desenvolvimento)
- [8. Verificar se Está Funcionando](#8-verificar-se-está-funcionando)
- [9. Comandos do Bot](#9-comandos-do-bot)
- [10. Como o Jogo Funciona](#10-como-o-jogo-funciona)
- [11. Manutenção e Operação](#11-manutenção-e-operação)
- [12. Solução de Problemas](#12-solução-de-problemas)

---

## Pré-requisitos

- Uma conta Discord com permissão para criar bots
- Docker e Docker Compose instalados (para deploy em produção)
- Python 3.12+ (apenas para desenvolvimento local)

---

## 1. Criar o Bot no Discord

### 1.1 Acessar o Portal de Desenvolvedores

1. Acesse o [Discord Developer Portal](https://discord.com/developers/applications)
2. Faça login com sua conta Discord

### 1.2 Criar uma Nova Aplicação

1. Clique em **"New Application"** no canto superior direito
2. Dê o nome **"Bengala"** (ou o nome que preferir)
3. Aceite os termos de serviço e clique em **"Create"**

### 1.3 Criar o Bot

1. No menu lateral esquerdo, clique em **"Bot"**
2. Você verá a seção de configuração do bot (ele é criado automaticamente com a aplicação)

### 1.4 Copiar o Token do Bot

1. Na seção **"Token"**, clique em **"Reset Token"**
2. Confirme a ação (pode pedir sua senha ou 2FA)
3. **Copie o token gerado e guarde em local seguro** — ele só é mostrado uma vez
4. Este token será usado na variável `DISCORD_TOKEN`

> **IMPORTANTE**: Nunca compartilhe ou commite o token do bot. Qualquer pessoa com o token tem controle total sobre o bot.

---

## 2. Configurar Permissões e Intents

### 2.1 Privileged Gateway Intents

Ainda na página **"Bot"** do Developer Portal:

1. Role até a seção **"Privileged Gateway Intents"**
2. Ative os seguintes intents:
   - **MESSAGE CONTENT INTENT** — necessário para ler o conteúdo das mensagens e detectar a palavra proibida
   - **SERVER MEMBERS INTENT** — necessário para gerenciar cargos dos membros (mute/unmute)
3. Clique em **"Save Changes"**

### 2.2 Permissões Necessárias

O bot precisa das seguintes permissões no servidor:

| Permissão | Motivo |
|---|---|
| **Send Messages** | Enviar o placar e regras no canal |
| **Read Message History** | Ler mensagens dos últimos 7 dias para selecionar a palavra |
| **Manage Roles** | Adicionar/remover o cargo de silenciamento dos membros |
| **Use Application Commands** | Registrar e responder aos slash commands |
| **View Channels** | Ver o canal monitorado |

---

## 3. Convidar o Bot para o Servidor

### 3.1 Gerar o Link de Convite

1. No Developer Portal, vá para **"OAuth2"** no menu lateral
2. Na seção **"OAuth2 URL Generator"**:
   - Em **"Scopes"**, marque:
     - `bot`
     - `applications.commands`
   - Em **"Bot Permissions"**, marque:
     - `Send Messages`
     - `Read Message History`
     - `Manage Roles`
     - `Use Application Commands`
     - `View Channels`
3. Copie a URL gerada na parte inferior da página

### 3.2 Adicionar ao Servidor

1. Abra a URL copiada no navegador
2. Selecione o servidor onde deseja adicionar o bot
3. Confirme as permissões e clique em **"Authorize"**
4. Complete o captcha se solicitado

---

## 4. Configurar o Servidor Discord

Antes de iniciar o bot, você precisa configurar três coisas no seu servidor Discord e anotar seus IDs.

### 4.1 Ativar o Modo de Desenvolvedor (para copiar IDs)

1. Abra as **Configurações do Discord** (ícone de engrenagem)
2. Vá em **"Avançado"** (ou "Advanced")
3. Ative **"Modo de Desenvolvedor"** (Developer Mode)

Com o modo de desenvolvedor ativo, você pode clicar com o botão direito em canais, cargos e usuários para copiar seus IDs.

### 4.2 Escolher o Canal do Jogo

1. Escolha (ou crie) o canal de texto onde o jogo acontecerá
2. Clique com o botão direito no canal e selecione **"Copiar ID do Canal"**
3. Este ID será usado na variável `WATCHED_CHANNEL_ID`

### 4.3 Criar o Cargo de Silenciamento (Mute)

1. Vá em **Configurações do Servidor > Cargos**
2. Crie um novo cargo chamado **"Silenciado"** (ou "Muted")
3. Nas permissões do cargo, **não conceda nenhuma permissão**
4. Clique com o botão direito no cargo e selecione **"Copiar ID do Cargo"**
5. Este ID será usado na variável `MUTE_ROLE_ID`

Agora configure o canal para impedir mensagens de quem tem este cargo:

1. Vá nas **configurações do canal do jogo** (clique na engrenagem ao lado do nome)
2. Vá em **"Permissões"**
3. Clique em **"Adicionar cargo"** e selecione o cargo **"Silenciado"**
4. **Negue** (marque com X vermelho) a permissão **"Enviar Mensagens"**
5. Salve as alterações

### 4.4 Criar o Cargo de Admin do Bot

1. Em **Configurações do Servidor > Cargos**, crie um novo cargo chamado **"Bengala Admin"**
2. Atribua este cargo aos membros que devem ter acesso aos comandos `/secret` e `/restart`
3. Clique com o botão direito no cargo e selecione **"Copiar ID do Cargo"**
4. Este ID será usado na variável `ADMIN_ROLE_ID`

### 4.5 Hierarquia de Cargos (Muito Importante)

O cargo do bot **deve estar acima** do cargo "Silenciado" na hierarquia de cargos do servidor. Caso contrário, o bot não conseguirá atribuir/remover o cargo de mute.

1. Em **Configurações do Servidor > Cargos**, arraste o cargo do bot (geralmente com o mesmo nome da aplicação, ex: "Bengala") para **acima** do cargo "Silenciado"

```
Hierarquia correta:
  ├── @Admin
  ├── Bengala (cargo do bot)    ← acima do Silenciado
  ├── Bengala Admin
  ├── Silenciado                ← abaixo do cargo do bot
  └── @everyone
```

---

## 5. Configurar Variáveis de Ambiente

### 5.1 Criar o Arquivo .env

Copie o arquivo de exemplo e preencha com os valores coletados:

```bash
cp .env.example .env
```

Edite o `.env` com os valores reais:

```env
DISCORD_TOKEN=MTIzNDU2Nzg5MDEy...seu_token_aqui
WATCHED_CHANNEL_ID=1234567890123456789
MUTE_ROLE_ID=1234567890123456789
ADMIN_ROLE_ID=1234567890123456789
```

| Variável | De onde vem |
|---|---|
| `DISCORD_TOKEN` | Token copiado no [passo 1.4](#14-copiar-o-token-do-bot) |
| `WATCHED_CHANNEL_ID` | ID do canal copiado no [passo 4.2](#42-escolher-o-canal-do-jogo) |
| `MUTE_ROLE_ID` | ID do cargo de mute copiado no [passo 4.3](#43-criar-o-cargo-de-silenciamento-mute) |
| `ADMIN_ROLE_ID` | ID do cargo admin copiado no [passo 4.4](#44-criar-o-cargo-de-admin-do-bot) |

> **IMPORTANTE**: O arquivo `.env` contém o token do bot e **nunca deve ser commitado** no repositório. Ele já está incluído no `.gitignore`.

---

## 6. Deploy com Docker (Recomendado)

### 6.1 Build e Iniciar

```bash
docker compose up -d --build
```

Isso vai:
- Construir a imagem Docker com multi-stage build
- Baixar os dados do NLTK (stop words) durante o build
- Iniciar o bot em background com restart automático
- Criar um volume persistente para o banco SQLite

### 6.2 Verificar Logs

```bash
docker compose logs -f bengala
```

Você deve ver algo como:

```
2025-01-01 06:00:00 [INFO] bengala: Bengala bot online como Bengala#1234
2025-01-01 06:00:00 [INFO] bengala: Slash commands synced.
2025-01-01 06:00:00 [INFO] bengala: Scheduler iniciado — ciclo diário às 06h00 UTC
```

### 6.3 Parar o Bot

```bash
docker compose down
```

### 6.4 Atualizar após Mudanças no Código

```bash
docker compose up -d --build
```

O banco de dados SQLite é persistido no volume `bengala_data`, então os dados da rodada atual sobrevivem a reinicializações.

---

## 7. Deploy Local (Desenvolvimento)

### 7.1 Criar Ambiente Virtual

```bash
python3 -m venv .venv
source .venv/bin/activate   # Linux/macOS
# .venv\Scripts\activate    # Windows
```

### 7.2 Instalar Dependências

```bash
pip install -r requirements.txt
```

Para desenvolvimento (inclui pytest, mypy):

```bash
pip install -r requirements-dev.txt
```

### 7.3 Baixar Dados do NLTK

```bash
python -c "import nltk; nltk.download('stopwords')"
```

### 7.4 Configurar Variáveis de Ambiente

Certifique-se de que o `.env` está criado (veja [passo 5](#5-configurar-variáveis-de-ambiente)), depois exporte as variáveis:

```bash
export $(cat .env | xargs)
```

Ou carregue-as diretamente no shell:

```bash
source .env   # funciona se o .env usar formato KEY=VALUE sem espaços
```

### 7.5 Iniciar o Bot

```bash
python -m bengala
```

### 7.6 Rodar os Testes

```bash
pytest tests/ -v
```

### 7.7 Verificar Tipagem

```bash
mypy --strict bengala/
```

---

## 8. Verificar se Está Funcionando

Após iniciar o bot, verifique os seguintes pontos:

### 8.1 Bot Online

No Discord, o bot deve aparecer como **online** (bolinha verde) na lista de membros do servidor.

### 8.2 Slash Commands Disponíveis

No canal do jogo, digite `/` e verifique se os comandos do Bengala aparecem:
- `/rules`
- `/placar`
- `/secret` (visível para todos, mas só funciona para admins)
- `/restart` (visível para todos, mas só funciona para admins)

> **Nota**: Os slash commands podem levar até 1 hora para aparecer globalmente no Discord. Se não aparecerem imediatamente, aguarde ou tente reiniciar o Discord.

### 8.3 Teste Rápido

1. Use `/rules` para ver as regras — deve responder com uma mensagem pública
2. Use `/secret` (com o cargo de admin) — deve mostrar a palavra proibida de forma efêmera
3. Use `/restart` (com o cargo de admin) — deve forçar uma nova rodada
4. Envie mensagens no canal e use `/placar` para ver os pontos sendo contados

---

## 9. Comandos do Bot

| Comando | Acesso | Visibilidade | Descrição |
|---|---|---|---|
| `/rules` | Todos | Pública | Exibe as regras do jogo |
| `/placar` | Todos | Pública | Mostra o placar parcial da rodada atual (sem revelar quem foi silenciado) |
| `/secret` | Apenas `ADMIN_ROLE_ID` | Efêmera (só você vê) | Revela a palavra proibida do dia |
| `/restart` | Apenas `ADMIN_ROLE_ID` | Efêmera (só você vê) | Força o encerramento da rodada atual e inicia uma nova |

---

## 10. Como o Jogo Funciona

### Ciclo Diário (06h00 UTC)

Todos os dias às 06h00 UTC, automaticamente:

1. O placar da rodada anterior é publicado no canal (revelando a palavra proibida)
2. Todos os jogadores silenciados são desbloqueados
3. Uma nova palavra proibida é selecionada a partir das mensagens dos últimos 7 dias
4. Uma nova rodada começa

### Seleção da Palavra

A palavra proibida é escolhida automaticamente:
- Coleta mensagens do canal dos últimos 7 dias
- Remove pontuação, emojis, menções e links
- Remove stop words do português e palavras com menos de 4 caracteres
- Escolhe uma palavra aleatória do conjunto restante
- Se não houver palavras válidas, usa uma lista de fallback com 200+ palavras em pt-BR

### Pontuação

- Cada palavra **única** (4+ caracteres, excluindo stop words) que um jogador envia conta como **1 ponto**
- Jogadores silenciados pontuam com base nas mensagens enviadas **antes** do silenciamento
- O placar parcial (`/placar`) não revela quem foi silenciado

### Silenciamento

- Quando um jogador diz a palavra proibida, ele recebe o cargo de mute via **DM privada** (ninguém mais fica sabendo)
- Jogadores silenciados não podem enviar mensagens no canal até a próxima rodada

---

## 11. Manutenção e Operação

### Persistência de Dados

O bot usa SQLite para persistir o estado entre reinicializações. O banco de dados armazena:
- A rodada ativa e sua palavra proibida
- Todos os jogadores e suas mensagens
- Timestamps de silenciamento

No deploy Docker, os dados ficam no volume `bengala_data` em `/app/data/bengala.db`.

### Backup do Banco de Dados

```bash
# Copiar o banco do container para o host
docker compose cp bengala:/app/data/bengala.db ./backup_bengala.db
```

### Ver Logs em Tempo Real

```bash
docker compose logs -f bengala
```

### Reiniciar o Bot

```bash
docker compose restart bengala
```

### Atualizar o Bot

```bash
git pull
docker compose up -d --build
```

---

## 12. Solução de Problemas

### Bot não aparece online

- Verifique se o `DISCORD_TOKEN` está correto no `.env`
- Verifique os logs: `docker compose logs bengala`
- Certifique-se de que o token não foi regenerado no Developer Portal sem atualizar o `.env`

### Slash commands não aparecem

- Aguarde até 1 hora — o Discord pode demorar para sincronizar globalmente
- Reinicie o bot: `docker compose restart bengala`
- Verifique se o bot tem a permissão `Use Application Commands` no servidor
- Verifique nos logs se aparece `"Slash commands synced."`

### Bot não consegue silenciar membros

- Verifique se o cargo do bot está **acima** do cargo "Silenciado" na hierarquia (veja [passo 4.5](#45-hierarquia-de-cargos-muito-importante))
- Verifique se o bot tem a permissão **Manage Roles** no servidor
- Verifique se o `MUTE_ROLE_ID` está correto no `.env`

### Silenciado mas ainda consegue enviar mensagens

- Verifique se o canal tem a permissão **"Enviar Mensagens"** negada para o cargo "Silenciado" (veja [passo 4.3](#43-criar-o-cargo-de-silenciamento-mute))

### Erro "Variáveis de ambiente ausentes"

- Certifique-se de que o `.env` existe e contém todas as 4 variáveis
- Verifique se não há espaços ao redor do `=` nos valores
- IDs devem ser apenas números (sem aspas)

### Bot não envia DM ao silenciar

- O jogador pode ter DMs desativadas para membros do servidor
- Isso não impede o silenciamento — apenas a notificação privada não é enviada
- O log registrará um aviso: `"Não foi possível enviar DM para ..."`

### Banco de dados corrompido

```bash
# Parar o bot
docker compose down

# Remover o volume (PERDA DE DADOS da rodada atual)
docker volume rm roleta_bengala_data

# Reiniciar — o bot cria um banco novo automaticamente
docker compose up -d --build
```

---

## Estrutura do Projeto

```
bengala/
├── __init__.py
├── __main__.py          # Entry point (python -m bengala)
├── bot.py               # Bot Discord, event handlers, slash commands
├── config.py            # Carregamento de variáveis de ambiente
├── db/
│   ├── __init__.py
│   ├── repository.py    # CRUD operations (aiosqlite)
│   └── schema.py        # Schema SQL e inicialização
├── fallback_words.py    # 200+ palavras pt-BR de fallback
├── messages.py          # Templates de mensagens em pt-BR
├── models.py            # Dataclasses (RoundData, PlayerData, etc.)
├── scheduler.py         # APScheduler para ciclo diário 06h UTC
├── scoring.py           # Cálculo de pontuação
└── word_pipeline.py     # Tokenização, filtragem, seleção de palavra
```
