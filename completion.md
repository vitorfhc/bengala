# Especificação Técnica — Bot Discord "Bengala"

## Visão Geral

**Bengala** é um bot para Discord desenvolvido em **Python**, com tipagem estrita (`mypy` strict mode) e desenvolvido seguindo a metodologia **TDD (Test-Driven Development)**. Toda comunicação do bot com usuários deve ser exclusivamente em **Português Brasileiro (pt-BR)**. A biblioteca recomendada é `discord.py` (versão com suporte a `app_commands` para slash commands).

---

## Configuração via Variáveis de Ambiente

O bot depende das seguintes variáveis de ambiente obrigatórias. A ausência de qualquer uma delas deve impedir a inicialização do bot e gerar um erro claro no log:

| Variável | Tipo | Descrição |
|---|---|---|
| `DISCORD_TOKEN` | `str` | Token de autenticação do bot no Discord |
| `WATCHED_CHANNEL_ID` | `int` | ID do canal onde o jogo acontece |
| `MUTE_ROLE_ID` | `int` | ID do cargo atribuído a jogadores silenciados |
| `ADMIN_ROLE_ID` | `int` | ID do cargo com acesso aos comandos `/secret` e `/restart` |

---

## Ciclo Diário do Jogo

### 1. Início da Rodada — 06h00 UTC

Todos os dias às **06h00 UTC**, na seguinte ordem:

#### 1.1 Envio do resumo do dia anterior (se houver rodada anterior)
Antes de selecionar a nova palavra, o bot deve calcular e enviar o placar da rodada que acabou de encerrar (ver seção **Placar Final**). Esse passo só ocorre se já houver uma rodada anterior registrada (ou seja, não acontece na primeira vez que o bot roda).

#### 1.2 Remoção do cargo de silenciamento
O cargo de silenciamento (`MUTE_ROLE_ID`) deve ser removido de **todos** os membros que o possuírem no momento, sem exceção.

#### 1.3 Seleção da palavra proibida do dia
O bot deve executar o seguinte pipeline para selecionar a palavra do dia:

1. **Buscar mensagens:** Coletar todas as mensagens enviadas no canal `WATCHED_CHANNEL_ID` nos **últimos 7 dias** (contando a partir do exato momento da execução às 06h00 UTC). Mensagens do próprio bot devem ser ignoradas.
2. **Tokenizar:** Extrair todas as palavras individuais de cada mensagem. Pontuação, emojis, menções (`@usuario`), links e caracteres especiais devem ser removidos antes da tokenização. Toda a comparação e processamento de palavras deve ser feito em **letras minúsculas**.
3. **Remover stop words:** Filtrar todas as palavras que constam na lista de stop words do **Português Brasileiro**. Usar a biblioteca `nltk` com o corpus `stopwords` para pt-BR.
4. **Remover palavras curtas:** Descartar todas as palavras com **menos de 4 caracteres** (ou seja, manter apenas palavras com 4 ou mais caracteres).
5. **Deduplicar:** Eliminar palavras duplicadas, resultando em um conjunto (`set`) de palavras únicas.
6. **Selecionar aleatoriamente:** Escolher **uma palavra aleatória** do conjunto resultante usando `random.choice`.
7. **Fallback:** Se o conjunto resultante estiver vazio (sem mensagens nos últimos 7 dias ou todas as palavras foram filtradas), o bot deve selecionar uma palavra aleatória em Português Brasileiro de uma lista embutida no código (hardcoded, com pelo menos 200 palavras comuns do pt-BR com 4+ caracteres).

A palavra selecionada é **secreta** — o bot **não a anuncia publicamente**. Os jogadores só descobrirão qual era a palavra quando o placar for revelado na manhã seguinte, ou via `/secret` por quem tiver a role `ADMIN_ROLE_ID`.

#### 1.4 Iniciar nova rodada
Registrar internamente o início da nova rodada com:
- A palavra proibida do dia
- O timestamp exato de início (06h00 UTC)
- Uma estrutura vazia de jogadores e mensagens para a nova rodada

---

## Monitoramento de Mensagens

O bot deve escutar **todas as mensagens** enviadas no canal `WATCHED_CHANNEL_ID` em tempo real.

### Registro de jogadores e mensagens
Qualquer usuário (exceto o próprio bot) que envie uma mensagem no canal durante uma rodada ativa (entre o início às 06h00 UTC e o próximo início às 06h00 UTC) é automaticamente considerado um **jogador da rodada**. Cada mensagem enviada por um jogador deve ser armazenada internamente para posterior contagem de pontos.

### Detecção da palavra proibida

Para cada mensagem recebida:

1. **Pré-processar a mensagem:** Remover pontuação, emojis e caracteres especiais, converter tudo para minúsculas e tokenizar em palavras individuais.
2. **Verificar ocorrência:** Checar se a palavra proibida do dia aparece como **palavra inteira** na lista de tokens. A comparação deve ser **case-insensitive** e deve usar **correspondência exata de token** — ou seja, a palavra `"gato"` **não** dispara se a mensagem contiver `"gatoca"` ou `"mingato"`, mas **dispara** se contiver `"gato"`, `"Gato"` ou `"GATO"`.

#### Caso: Jogador não silenciado diz a palavra proibida
1. Atribuir imediatamente o cargo `MUTE_ROLE_ID` ao usuário. Esse cargo deve estar configurado no servidor de forma a **impedir o usuário de enviar mensagens** no canal.
2. Registrar internamente que esse jogador foi silenciado durante essa rodada, marcando o **timestamp exato do silenciamento** (usado para calcular os pontos apenas com as mensagens anteriores a esse momento).
3. Enviar uma **mensagem efêmera** (visível somente para o usuário que foi silenciado). A mensagem deve:
   - Informar que ele disse a palavra proibida e foi silenciado.
   - Deixar claro que **somente ele está vendo essa mensagem**, tornando mais difícil para os outros jogadores deduzirem qual é a palavra proibida.
   - Exemplo de formato (em pt-BR):
     > 🔇 Você disse a palavra proibida e foi silenciado! Só você está vendo esta mensagem — os outros jogadores não sabem o que aconteceu. Boa sorte na próxima rodada!

#### Caso: Jogador já silenciado diz a palavra proibida
O usuário silenciado não deveria conseguir enviar mensagens (pois o cargo restringe isso). Porém, caso isso aconteça por alguma falha de permissão, o bot deve enviar uma **mensagem efêmera de deboche**, visível apenas para esse usuário, sem aplicar nenhuma punição adicional. Exemplo:
   > 😂 Você tentou dizer a palavra proibida de novo... mas já está silenciado! Só você está vendo esta mensagem.

---

## Placar Final (enviado às 06h00 UTC antes da nova rodada)

Ao final de cada rodada, o bot calcula e envia o placar no canal `WATCHED_CHANNEL_ID`. O placar é **público** e deve **revelar a palavra proibida do dia que acabou de encerrar**.

### Cálculo de Pontos por Jogador

O mesmo algoritmo de cálculo é usado tanto para o placar final quanto para o comando `/placar`:

Para cada jogador da rodada:

- **Se o jogador foi silenciado em algum momento durante a rodada:**
  1. Coletar apenas as mensagens enviadas pelo jogador **antes do timestamp de silenciamento**.
  2. Aplicar o pipeline: tokenizar → remover stop words → remover palavras curtas (< 4 caracteres) → deduplicar.
  3. **Pontuação = número de palavras únicas restantes.** Jogadores silenciados pontuam normalmente com base no que enviaram até serem silenciados.

- **Se o jogador não foi silenciado:**
  1. Coletar todas as mensagens enviadas pelo jogador durante a rodada.
  2. Aplicar o mesmo pipeline de tokenização, remoção de stop words, remoção de palavras curtas e deduplicação.
  3. **Pontuação = número de palavras únicas restantes.**

### Formato da Mensagem do Placar Final

O bot envia uma única mensagem pública em pt-BR, revelando a palavra do dia e listando todos os jogadores em ordem decrescente de pontuação. Jogadores silenciados são identificados com ícone e nota, pois a rodada já encerrou e a palavra é revelada de qualquer forma. Exemplo:

```
🏆 Fim da rodada! Placar do dia:
🤫 A palavra proibida era: "abacaxi"

🥇 1º — @alice — 42 pontos
🥈 2º — @bob — 31 pontos
🥉 3º — @carlos — 28 pontos
🔇 4º — @diana — 5 pontos (silenciada)
🔇 5º — @edu — 2 pontos (silenciado)

Boa sorte na próxima rodada! 🎮
```

Se não houver jogadores na rodada, o bot envia uma mensagem informando que não houve participantes, mas ainda assim revela a palavra do dia encerrado.

---

## Comandos

### `/rules`
Resposta **pública** no canal onde o comando foi usado, com as regras e funcionamento do jogo em pt-BR. Deve cobrir:
- O que é o jogo Bengala
- Como a palavra proibida é escolhida (sem revelar a palavra em si)
- O que acontece quando alguém diz a palavra proibida (e que a notificação é silenciosa/efêmera)
- Como os pontos são calculados (inclusive para silenciados)
- Quando o placar é divulgado e a rodada é reiniciada

Pode ser usado por qualquer jogador, sem restrição de cargo.

---

### `/placar`
Resposta **pública** no canal onde o comando foi usado, exibindo o placar **parcial da rodada atual em andamento**.

**Regras de exibição:**
- Listar **todos os jogadores** da rodada atual, incluindo os silenciados, em ordem decrescente de pontuação.
- A pontuação exibida para cada jogador é calculada com o mesmo algoritmo do placar final: pontos acumulados até o momento (ou até o timestamp de silenciamento, no caso de silenciados).
- **Não deve indicar quem foi ou não foi silenciado** — o objetivo é não revelar pistas sobre a palavra proibida. Todos aparecem apenas com nome e pontuação.
- A palavra proibida **não deve ser revelada**.

Exemplo de formato:
```
📊 Placar parcial da rodada:

🥇 1º — @alice — 38 pontos
🥈 2º — @carlos — 25 pontos
🥉 3º — @diana — 5 pontos
4º — @bob — 3 pontos
5º — @edu — 1 ponto

A rodada continua! 🎮
```

Se ainda não houver jogadores na rodada atual, o bot envia uma mensagem informando que ninguém jogou ainda.

Pode ser usado por qualquer jogador, sem restrição de cargo.

---

### `/secret`
Revela a palavra proibida da rodada atual de forma **efêmera** (visível somente para quem usou o comando).

**Restrição de acesso:** Somente membros que possuam o cargo `ADMIN_ROLE_ID` podem usar este comando. Se um membro sem o cargo tentar usar, o bot responde com uma mensagem efêmera informando que ele não tem permissão.

**Comportamento:**
- Verificar se há uma rodada ativa com palavra definida.
- Se sim, responder de forma efêmera com a palavra atual. Exemplo:
  > 🤫 A palavra proibida de hoje é: **"abacaxi"**. Só você está vendo esta mensagem.
- Se não houver rodada ativa, responder de forma efêmera informando que nenhuma palavra foi selecionada ainda.

---

### `/restart`
Força o encerramento imediato da rodada atual e inicia uma nova rodada, como se fosse o ciclo normal das 06h00 UTC, **mas executado imediatamente**. Destinado a uso em debug e testes.

**Restrição de acesso:** Somente membros que possuam o cargo `ADMIN_ROLE_ID` podem usar este comando. Se um membro sem o cargo tentar usar, o bot responde com uma mensagem efêmera informando que ele não tem permissão.

**Comportamento, em ordem:**
1. Executar o placar final da rodada atual (mesmo formato do ciclo normal), se houver rodada ativa.
2. Remover o cargo `MUTE_ROLE_ID` de todos os membros que o possuírem.
3. Executar o pipeline de seleção da nova palavra proibida (idêntico ao ciclo das 06h00 UTC).
4. Iniciar nova rodada com a nova palavra e timestamp atual.
5. Responder de forma **efêmera** ao admin confirmando que o reinício foi executado. Exemplo:
   > ✅ Jogo reiniciado com sucesso! A próxima palavra foi selecionada. O próximo ciclo automático ocorre às 06h00 UTC.

**Importante:** O agendamento automático das 06h00 UTC **não é alterado** — o `/restart` não reseta nem atrasa o próximo ciclo automático. Ele apenas executa o fluxo de virada de rodada imediatamente, de forma independente.

---

## Evento: Bot Adicionado ao Servidor

Quando o bot for adicionado a um novo servidor Discord (`on_guild_join`), ele deve enviar automaticamente a mensagem de regras (mesmo conteúdo do `/rules`) no canal `WATCHED_CHANNEL_ID` configurado, se esse canal pertencer ao servidor em questão. Se o canal não pertencer ao servidor, o bot deve logar um aviso e não enviar mensagem.

---

## Persistência de Estado

O bot deve persistir seu estado entre reinicializações usando **SQLite local** via `aiosqlite`. Em caso de queda e restart, o bot deve ser capaz de retomar a rodada atual sem perder:

- A palavra proibida do dia
- Os jogadores registrados na rodada atual e suas mensagens
- Quais jogadores foram silenciados e o **timestamp exato do silenciamento**

O arquivo `.db` deve ser armazenado em um volume persistente (ver seção Docker). O schema deve ser fortemente tipado e acessado por uma camada de repositório isolada (facilitando os testes).

---

## Docker e Containerização

O projeto deve ser containerizado seguindo as melhores práticas de Docker para aplicações Python em produção.

### `Dockerfile`
- Usar imagem base oficial **`python:3.12-slim`**.
- Usar **multi-stage build**:
  - **Stage `builder`:** Instalar dependências via `pip` em um ambiente isolado.
  - **Stage final:** Copiar apenas os artefatos necessários do `builder`, sem ferramentas de build.
- **Não rodar como root:** Criar um usuário não-privilegiado (ex: `bengala`) e executar o processo com esse usuário.
- Definir `WORKDIR` explícito (ex: `/app`).
- Usar `COPY` seletivo — nunca copiar arquivos desnecessários.
- Usar `.dockerignore` para excluir: `.git`, `__pycache__`, `*.pyc`, `tests/`, `.env`, `*.db`, `*.md`.
- O `CMD` deve executar diretamente `python -m bengala`, sem shell desnecessário.

### `docker-compose.yml`
- Definir um único serviço `bengala`.
- Passar as variáveis de ambiente via arquivo `.env` (usando `env_file: .env`). O arquivo `.env` nunca deve ser commitado — incluir `.env.example` com as chaves e valores de exemplo.
- Montar um **volume nomeado** para o arquivo SQLite:
  ```yaml
  volumes:
    - bengala_data:/app/data
  ```
- Definir `restart: unless-stopped`.
- Definir `healthcheck` básico que verifica se o processo Python está rodando.

---

## Arquitetura e Boas Práticas

### Dependências
- Todas as dependencias devem ser instaladas usando a linha de comando para garantir a ultima versao

### Documentacao
- Em caso de problemas, procurar na web a documentacao mais recente

### Tipagem
- Todo o código deve passar em `mypy --strict` sem erros.
- Usar `dataclass` ou `pydantic.BaseModel` para modelar entidades como `Rodada`, `Jogador`, `Mensagem`, etc.

### TDD
- Cada módulo de lógica de negócio deve ter testes unitários escritos **antes** da implementação.
- Usar `pytest` como framework de testes.
- A lógica de negócio deve ser completamente desacoplada do Discord (funções puras), facilitando os testes.
- Usar `pytest-asyncio` para testes de código assíncrono.
- Usar `unittest.mock` ou `pytest-mock` para mockar chamadas à API do Discord e ao banco de dados.

---

## Resumo das Decisões de Design

| Decisão | Escolha |
|---|---|
| Idioma de todas as mensagens | Português Brasileiro (pt-BR) |
| Janela de busca de mensagens | Últimos 7 dias |
| Fallback sem palavras válidas | Palavra aleatória em pt-BR (lista embutida) |
| Palavra proibida anunciada no início? | Não — secreta durante toda a rodada |
| Palavra proibida revelada quando? | No placar final às 06h00 UTC do dia seguinte |
| Stop words | pt-BR (`nltk`) |
| Correspondência da palavra proibida | Case-insensitive, token exato (não substring) |
| Quem é jogador | Quem enviar mensagem entre 06h UTC e 06h UTC seguinte |
| Notificação de silenciamento | Efêmera (visível só para o silenciado) |
| Silenciado diz a palavra de novo | Mensagem efêmera de deboche, sem nova punição |
| Pontos de silenciados | Contam normalmente até o momento do silenciamento |
| Envio do placar final | Às 06h UTC, antes de selecionar a nova palavra |
| Remoção do cargo de mute | Às 06h UTC, antes de selecionar a nova palavra |
| `/rules` | Público, qualquer jogador |
| `/placar` | Público, mostra todos sem indicar silenciados |
| `/secret` | Efêmero, restrito ao cargo `ADMIN_ROLE_ID` |
| `/restart` | Efêmero para admin, reinicia imediatamente sem alterar o agendamento das 06h UTC |
| Regras enviadas automaticamente | Ao entrar no servidor e via `/rules` |
| Linguagem | Python, `mypy --strict`, TDD com `pytest` |
| Persistência | SQLite local via `aiosqlite`, volume Docker nomeado |
| Containerização | Docker com multi-stage build, usuário não-root, `docker-compose.yml` |

---

CRITÉRIOS DE CONCLUSÃO:
- Todo o código Python passa em mypy --strict sem erros
- Todos os testes pytest passam (incluindo pytest-asyncio)
- O Dockerfile faz build sem erros
- O docker-compose.yml está válido
- O arquivo .env.example contém todas as variáveis necessárias
- O schema SQLite está criado e documentado
- Os comandos /rules, /placar, /secret e /restart estão implementados
- O ciclo diário das 06h00 UTC está implementado com APScheduler ou equivalente
- A lista de fallback de palavras em pt-BR tem pelo menos 200 palavras

Quando todos os critérios acima forem atendidos e verificados, escreva exatamente: BENGALA_CONCLUIDO"