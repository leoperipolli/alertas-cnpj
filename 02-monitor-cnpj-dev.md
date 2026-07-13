# Alertas de CNPJ — Documento de Desenvolvimento

Documento de engenharia do produto principal descrito em [tres-ideias.md](tres-ideias.md): assinatura de baixa fricção que entrega, no WhatsApp ou e-mail do assinante, listas de empresas recém-registradas que batem com filtros configurados por ele mesmo. Freemium com paywall no **volume entregue** (grátis / R$ 29 / R$ 59 + overage), meta de 80–100 pagantes em 10–18 meses.

Dois princípios de calibração atravessam tudo aqui:

1. **Uma pessoa opera isso — com 100 assinantes de R$ 29.** Ticket baixo em volume significa que qualquer coisa que gere ticket de suporte por assinante mata o produto. Autoatendimento e transparência não são features: são requisitos de sobrevivência.
2. **A recusa deliberada de virar plataforma é o produto.** Toda decisão técnica abaixo protege essa recusa: o sistema faz uma coisa (filtrar empresas novas e entregar) e resiste a crescer para os lados.

---

## 1. Visão e escopo

### O que é

Três partes acopladas pelo mesmo dado:

1. **Pipeline de dados (o trabalho sujo):** ETL que baixa a atualização mensal dos Dados Abertos CNPJ da Receita Federal (~5 GB compactado, ~20 GB solto, CSV Latin-1, `;`, sem header), filtra empresas ativas recém-abertas e materializa a fatia entregável.
2. **Produto pago (uma tela de configuração):** conta com e-mail e senha → configura alertas (CNAE + região + capital + porte + natureza) → vê a **prévia** do que o filtro teria retornado → escolhe canal e recebe na cadência do plano. Metering de volume, cotas e overage.
3. **Bot público (a aquisição):** posts diários no X com agregados do mesmo dado. O post é a demo grátis; a bio aponta para a landing.

### O que NÃO é (non-goals — a lista mais importante do documento)

- **Não é CRM, não tem funil, não tem IA, não tem enriquecimento de contato, não tem dashboard de analytics.** Pedidos nessa direção são recusados por padrão.
- **Não é "tempo real" nem diário.** O dado é mensal na origem; a entrega é semanal (pagos) ou mensal (free). Toda mensagem cita a data de extração da Receita. Chamar de diário seria mentir — e a honestidade de cadência é posicionamento.
- **Não é plataforma vertical.** O produto não escolhe nicho; cada assinante configura o seu.
- **Não tem app mobile, não tem API pública** (no início; API pode virar tier futuro se pagantes pedirem).
- **Não tem suporte por WhatsApp/chat.** Suporte é e-mail com SLA de 48h — decisão de escopo, não de preguiça (§12).

### Critérios de sucesso

| Critério | Meta |
|---|---|
| Corretude da entrega | O que a prévia promete é o que o envio entrega; nunca acima da cota do plano |
| LGPD | Zero campos de pessoa física em qualquer saída, desde o dia 1 |
| Custo | < R$ 100/mês de operação até ~100 assinantes |
| Suporte | Resolvível por e-mail 48h; taxa de tickets < 5% dos assinantes/mês (autoatendimento cobre o resto) |
| Negócio | 80–100 pagantes (mix R$ 29/R$ 59) em 10–18 meses; free tier 5–10× isso |

---

## 2. Requisitos

### Funcionais — pipeline

- **RF-1** — Baixar automaticamente a atualização mensal dos Dados Abertos CNPJ (dados.gov.br): Empresas, Estabelecimentos, Simples e tabelas auxiliares (CNAE, município, natureza jurídica). **Os arquivos de Sócios não são baixados** (LGPD por construção, §6). Download resumível com verificação de integridade.
- **RF-2** — Filtrar `situacao_cadastral = 02` (ativa), `data_inicio_atividade` recente, `data_situacao_cadastral` recente; join com CNAE e município; materializar só a fatia entregável (janela rolante, §5) com os campos da allowlist.
- **RF-3** — Registrar cada extração da Receita com a data de referência — essa data aparece em **toda** mensagem enviada ("extração de DD/MM/AAAA").
- **RF-4** — Reprocessamento idempotente: rodar a mesma extração duas vezes não duplica empresas nem reenvia entregas.
- **RF-5** — Gerar os agregados semanais (UF × município × CNAE) que alimentam o bot público e as mensagens de semana zero.

### Funcionais — produto

- **RF-6** — Conta com e-mail e senha; confirmação de e-mail obrigatória antes do primeiro envio; reset de senha por e-mail. Sem onboarding, sem chamada, sem demo.
- **RF-7** — CRUD de alertas. Cada alerta: CNAE(s) com busca por código **ou descrição amigável** ("padaria"), região (UF, município ou lista de municípios), faixa de capital social (opcional), porte (opcional), natureza jurídica (opcional).
- **RF-8 (não-negociável nº 1)** — **Prévia antes de salvar:** a tela mostra quantas empresas o filtro teria retornado em cada uma das últimas 4 semanas ("12, 8, 15 e 3"). A prévia usa **a mesma função de match** do envio real (§5) — o que ela promete é o que o assinante recebe.
- **RF-9** — Canais por plano: free = e-mail; pagos = WhatsApp + e-mail (assinante escolhe um ou ambos). Cadência: free = mensal (dispara logo após cada extração); pagos = semanal (4 disparos espaçados com o diff acumulado até o momento).
- **RF-10** — Conteúdo da entrega: CNPJ, razão social, CNAE amigável, município, capital social, data de abertura. CSV anexo no e-mail nos planos pagos; no R$ 59, CSV com colunas extras (data da situação cadastral, natureza jurídica traduzida, link para o cartão CNPJ).
- **RF-11 (não-negociável nº 2)** — **Semana zero:** quando o alerta retorna zero no período, a mensagem vai mesmo assim: "nenhuma empresa bateu seu filtro essa semana — isso é normal em nichos pequenos e você não paga a mais por isso. Agregado do seu setor no estado: …". Zero em silêncio = assinante acha que quebrou.
- **RF-12** — **Metering por volume entregue:** contagem de CNPJs entregues por conta/ciclo. Limites: free 5/mês, R$ 29 → 50/mês, R$ 59 → 300/mês (somando todos os alertas da conta). Limite de alertas: 1 / 3 / 10.
- **RF-13** — **Corte por cota com transparência:** se o diff excede a cota restante, entrega até o limite (mais recentes primeiro) e informa: "mais 34 empresas bateram seu filtro e ficaram fora do limite do plano". O excedente fica em fila e sai nos ciclos seguintes conforme a cota liberar (enquanto estiver dentro da janela de dados).
- **RF-14** — **Overage:** ao estourar, o assinante pode comprar "+100 CNPJs por R$ 15 neste ciclo" (cobrança avulsa via Asaas) — libera imediatamente a fila represada.
- **RF-15** — Billing recorrente via Asaas (Pix/boleto/cartão), upgrade/downgrade self-service, bloqueio automático por inadimplência com grace de 7 dias (vira free tier, não apaga nada).
- **RF-16** — Página de autoatendimento por conta: histórico de despachos (o que foi enviado, quando, quantos, por qual canal, de qual extração), consumo da cota no ciclo, status dos canais. É a resposta pronta para 80% dos tickets ("por que não recebi?").

### Funcionais — bot público

- **RF-17** — 3–8 posts/dia no X a partir dos agregados: resumo por UF/cidade, top CNAEs da semana em regiões, curiosidades, comparações regionais. Reutiliza `render/` e `publish/` do bot de futebol.
- **RF-18** — 1 em cada ~10 posts com CTA leve para a landing; bio com link.

### Não-funcionais

- **RNF-1 (corretude do metering)** — Nunca entregar acima da cota; nunca contar duas vezes a mesma empresa para o mesmo alerta; overage credita exatamente o comprado. Bug aqui é bug de cobrança.
- **RNF-2 (consistência prévia↔entrega)** — Prévia e despacho compartilham a mesma implementação de match. Divergência entre os dois é o defeito que mais gera churn e ticket.
- **RNF-3 (honestidade de cadência)** — Data de extração da Receita visível em toda entrega e na landing.
- **RNF-4 (LGPD por construção)** — Dado de pessoa física nunca entra no banco da aplicação (§6).
- **RNF-5 (custo)** — < R$ 100/mês até ~100 assinantes; ETL roda em ~2 GB de RAM (DuckDB lendo CSV do disco).
- **RNF-6 (desempenho)** — Prévia em < 3 s (é a tela de conversão); dispatch semanal completo (todos os alertas) em < 30 min.
- **RNF-7 (disponibilidade)** — App: melhor esforço (~99%). O que não pode falhar é o ciclo mensal ingestão→despacho. Sem SLA contratual.
- **RNF-8 (resiliência a quebra de layout)** — O layout da Receita mudou em janeiro/2026; planejar **pelo menos uma quebra por ano** como evento normal de operação, não como surpresa (§7).

---

## 3. Arquitetura e system design

### Visão geral

```
   Receita Federal — Dados Abertos CNPJ (mensal, ~5GB zip)
                        │ download resumível + checksum
                        ▼
┌────────────────── VPS (Hetzner/Contabo) ──────────────────────┐
│                                                               │
│  ETL (Python + DuckDB, 1×/mês)                                │
│   baixa → valida layout → staging DuckDB → filtra ativas      │
│   recentes → allowlist LGPD → carga na janela rolante         │
│   → recalcula agregados semanais                              │
│                     │                                         │
│                     ▼                                         │
│   Postgres ── empresas_novas (janela ~90d) │ agregados        │
│            ── contas │ alertas │ despachos │ entregas         │
│            ── creditos_overage │ cargas │ eventos_billing     │
│                     ▲                                         │
│                     │                                         │
│  App web (Next.js: landing + conta + alertas + prévia)        │
│                     │                                         │
│  Dispatcher (job: semanal pagos / mensal free)                │
│     ├──▶ e-mail (Resend) — lista completa + CSV               │
│     └──▶ WhatsApp Cloud API oficial — resumo + link           │
│                                                               │
│  Bot público ──▶ X (GitHub Actions, módulos do bot futebol)   │
└───────────────────────────────────────────────────────────────┘
          ▲                                   ▲
          │ webhooks (assinatura, overage,    │ HTTPS (Caddy)
          │ status de mensagem WhatsApp)      │
        Asaas / Meta                     assinantes
```

### Decisões de design (mini-ADRs)

**ADR-1: ETL em batch mensal com DuckDB em staging local; Postgres recebe só a fatia entregável.**
- *Alternativa rejeitada:* carregar o dump no Postgres.
- *Porquê:* dezenas de milhões de linhas das quais só interessam as aberturas recentes. DuckDB lê os CSVs direto do disco com ~2 GB de RAM e cospe a fatia em minutos. Os repositórios públicos citados na fonte (`aphonsoar/Receita_Federal_do_Brasil_-_Dados_Publicos_CNPJ`, `libercapital/dados_publicos_cnpj_receita_federal`, `rictom/cnpj-sqlite`) servem de **referência de parsing e armadilhas** — não entram em produção, mas pouparam semanas de descoberta de esquisitice de layout.

**ADR-2: Janela rolante de ~90 dias de detalhe + agregados semanais permanentes.**
- *Alternativa rejeitada:* histórico completo no Postgres.
- *Porquê do 90:* a fonte manda materializar ~60 dias; 90 dá folga para (a) a prévia de 4 semanas sempre cair dentro da janela, (b) excedente de cota em fila ser entregue em ciclos seguintes sem sumir, (c) atraso da Receita não esvaziar a janela. Purge mensal do que passa de 90 dias.
- *Matemática de tamanho (a restrição real):* o Brasil abre ~300–400 mil empresas/mês; 90 dias ≈ ~1M de linhas ≈ 400–700 MB com índices. Isso **estoura o free tier do Supabase (500 MB)** em cenário cheio. Decisão: `empresas_novas` e `agregados` vivem num **Postgres na própria VPS** (dado 100% regenerável a partir do dump — não precisa de backup), e os dados preciosos e pequenos (contas, alertas, entregas, billing) vivem no **Supabase free** (gerenciado, com backup). O dispatcher roda na VPS e fala com os dois; não há join SQL entre eles (a junção é em código, por alerta). Se preferir simplicidade de um banco só no início: tudo no Supabase até doer, com este split como gatilho de migração já desenhado.

**ADR-3: `entregas` por item como fonte única de verdade do metering e do diff.**
- *Alternativa rejeitada:* watermark simples por carga (última extração entregue).
- *Porquê:* o corte por cota gera **entrega parcial** de uma extração — um watermark por carga não representa "entreguei 50 das 84". Registrando cada (alerta, empresa) entregue, o diff do próximo despacho é "empresas na janela que batem o filtro e ainda não estão em `entregas`" — isso implementa de graça: anti-duplicata (constraint UNIQUE), metering (COUNT no ciclo), fila de excedente (o que bateu e não foi entregue) e a expiração natural do excedente (sai da janela de 90 dias, sai da fila). Volume: ≤ ~30 mil linhas/mês com 100 assinantes no teto — trivial.

**ADR-4: Prévia e despacho usam a mesma função de match (RNF-2).**
- *Implementação:* uma única query parametrizada (`match_empresas(filtro, periodo)`) usada pelos dois caminhos; a prévia agrupa por semana e conta, o despacho seleciona linhas. Teste automatizado garante que os dois nunca divergem (§11). É a materialização técnica do requisito não-negociável nº 1.

**ADR-5: WhatsApp via Cloud API oficial; a mensagem é resumo + link, não a lista.**
- *Alternativa rejeitada (proibida pela fonte):* Baileys/biblioteca não-oficial — o número que envia é o **do produto**; ban derruba o canal de todos os assinantes de uma vez.
- *Restrição técnica que vira design:* template `utility` tem texto fixo com variáveis posicionais, e variáveis não aceitam quebra de linha — listas longas não cabem. Então: **WhatsApp é o sino, não o carteiro** — "Sua lista dessa semana: {{1}} empresas novas no seu filtro {{2}} (extração de {{3}}). Veja e baixe: {{4}}", onde {{4}} é link autenticado por token para a página da entrega. A lista completa vive no e-mail (com CSV) e na página. Isso também reduz custo por mensagem e risco de bloqueio por spam-report.

**ADR-6: Auth e-mail + senha (Argon2id), sessão em cookie httpOnly.**
- *Porquê:* é o que a fonte especifica ("cria conta com e-mail e senha, sem onboarding"). Custos aceitos: fluxo de reset de senha e rate limit de login (§6). Confirmação de e-mail obrigatória protege a reputação de envio (Resend) e garante canal válido antes do primeiro despacho.

**ADR-7: Ciclo de cota = mês calendário.**
- *Alternativa rejeitada:* ciclo por data de assinatura (billing cycle).
- *Porquê:* cota atrelada ao mês calendário é trivial de explicar ("seu limite renova dia 1º"), trivial de mostrar na página de autoatendimento e independe de sincronizar com o Asaas. O descasamento com a data de cobrança é irrelevante para o assinante e elimina uma classe inteira de bugs de borda.

**ADR-8: Sem fila/mensageria; o dispatcher é um job idempotente.**
- *Porquê:* cadência semanal, centenas de alertas no teto — um processo sequencial com estado em `despachos`/`entregas` resolve. Re-rodar o job só processa o que não foi despachado (§5). Mensageria aqui seria complexidade sem carga que a justifique.

---

## 4. APIs e interfaces

### API da aplicação (Next.js API routes — consumida pelo próprio frontend)

```
POST /api/auth/signup                # e-mail + senha; dispara confirmação
POST /api/auth/login                 # rate limited
POST /api/auth/reset                 # fluxo de reset por e-mail
GET  /api/me                         # plano, cota consumida/restante no ciclo, canais

GET    /api/alertas
POST   /api/alertas                  # valida limite de alertas do plano
PUT    /api/alertas/:id
DELETE /api/alertas/:id
POST   /api/alertas/previa           # filtro (sem salvar) → contagem das últimas 4 semanas
                                     # rate limited por conta; usa match_empresas (ADR-4)

GET  /api/despachos                  # histórico da conta (autoatendimento, RF-16)
GET  /api/despachos/:id              # página da entrega: lista completa + CSV
GET  /api/despachos/:id?token=...    # mesma página via link do WhatsApp (token assinado, expira)

POST /api/overage                    # cria cobrança avulsa Asaas de +100/R$15
POST /api/canais/whatsapp            # cadastra número + envia mensagem de confirmação (opt-in)

POST /api/webhooks/asaas             # assinatura criada/paga/vencida/cancelada + overage pago
POST /api/webhooks/whatsapp          # status de mensagem (sent/delivered/failed) + qualidade
GET  /api/health
```

Regras: validação zod na borda; todo recurso checado contra a conta da sessão (IDOR é o bug mais provável — teste dedicado, §11); webhooks idempotentes por id de evento com resposta 200 rápida.

### Contratos internos

- **`match_empresas(filtro, periodo)`** — a função central (ADR-4). Único lugar do sistema que traduz um alerta em SQL sobre `empresas_novas`.
- **ETL → dispatcher:** o ETL finaliza gravando a linha da extração em `cargas` (status `concluida`, `data_extracao`). O dispatcher só considera cargas `concluida`.
- **Dispatcher → canais:** interface `Canal.enviar(despacho) -> resultado`, implementações `email` e `whatsapp`. Falha no WhatsApp com e-mail configurado → fallback automático para e-mail, registrado no despacho.

### Template WhatsApp (submetido à aprovação da Meta, categoria `utility`)

```
Nome: lista_semanal_v1
"Sua lista dessa semana: {{1}} empresas novas bateram seu alerta "{{2}}".
Dados da extração oficial da Receita de {{3}}. Ver lista e baixar CSV: {{4}}"
```

Versionar templates (`_v2`, `_v3`...) — template aprovado é imutável; mudanças exigem novo template e período de convivência.

### CLI operacional

```
python -m etl run [--extracao 2026-06]     # pipeline completo (detecta a mais nova por padrão)
python -m etl status                       # última carga, contagens, tamanho da janela
python -m dispatch run [--dry-run]         # despacha o que estiver pendente (idempotente)
python -m dispatch resend --despacho ID    # reenvio pontual (suporte)
python -m dispatch preview --alerta ID     # o que o próximo despacho entregaria
```

---

## 5. Dados, estado e comunicação

### Modelo de dados

**Postgres da VPS (regenerável, sem backup):**

```sql
CREATE TABLE cargas (
    id BIGSERIAL PRIMARY KEY,
    data_extracao DATE NOT NULL UNIQUE,     -- a data que aparece nas mensagens (RF-3)
    status TEXT NOT NULL,                   -- baixando | validando | carregada | concluida | quarentena
    linhas_lidas BIGINT,
    empresas_novas INT,
    detalhe JSONB                           -- checksums, contagens por UF, avisos
);

CREATE TABLE empresas_novas (               -- janela rolante ~90 dias (ADR-2)
    id BIGSERIAL PRIMARY KEY,
    carga_id BIGINT NOT NULL REFERENCES cargas(id),
    cnpj TEXT NOT NULL,
    razao_social TEXT NOT NULL,
    nome_fantasia TEXT,
    cnae_principal TEXT NOT NULL,
    cnae_descricao TEXT NOT NULL,
    cnaes_secundarios TEXT[],
    data_abertura DATE NOT NULL,
    data_situacao DATE,
    natureza_juridica TEXT NOT NULL,
    porte TEXT,                             -- MEI | ME | EPP | demais
    capital_social NUMERIC(15,2),
    municipio_codigo TEXT NOT NULL,
    municipio TEXT NOT NULL,
    uf CHAR(2) NOT NULL,
    endereco TEXT,                          -- NULL quando MEI (§6)
    eh_mei BOOLEAN NOT NULL,
    UNIQUE (cnpj, carga_id)                 -- reprocesso da mesma carga não duplica (RF-4)
);
CREATE INDEX ON empresas_novas (uf, municipio_codigo, cnae_principal, data_abertura);
CREATE INDEX ON empresas_novas (cnae_principal, data_abertura);

CREATE TABLE agregados_semanais (           -- permanente, pequeno; alimenta bot e semana zero
    semana DATE NOT NULL,                   -- segunda-feira da semana de data_abertura
    uf CHAR(2) NOT NULL,
    municipio_codigo TEXT NOT NULL,
    cnae_principal TEXT NOT NULL,
    contagem INT NOT NULL,
    PRIMARY KEY (semana, uf, municipio_codigo, cnae_principal)
);
```

**Supabase (precioso, com backup):**

```sql
CREATE TABLE contas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT NOT NULL UNIQUE,
    email_confirmado BOOLEAN NOT NULL DEFAULT false,
    senha_hash TEXT NOT NULL,               -- Argon2id
    plano TEXT NOT NULL DEFAULT 'free',     -- free | p29 | p59
    status TEXT NOT NULL DEFAULT 'ativo',   -- ativo | inadimplente | cancelado (cancelado ⇒ free)
    whatsapp_numero TEXT,                   -- E.164; NULL = só e-mail
    whatsapp_confirmado BOOLEAN NOT NULL DEFAULT false,
    asaas_customer_id TEXT UNIQUE,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE alertas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conta_id UUID NOT NULL REFERENCES contas(id),
    nome TEXT NOT NULL,
    cnaes TEXT[] NOT NULL,
    ufs TEXT[] NOT NULL DEFAULT '{}',
    municipios TEXT[] NOT NULL DEFAULT '{}',
    capital_min NUMERIC(15,2),
    capital_max NUMERIC(15,2),
    portes TEXT[] NOT NULL DEFAULT '{}',
    naturezas TEXT[] NOT NULL DEFAULT '{}',
    canais TEXT[] NOT NULL DEFAULT '{email}',
    ativo BOOLEAN NOT NULL DEFAULT true,
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE despachos (                    -- um por alerta × execução, INCLUSIVE semana zero
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alerta_id UUID NOT NULL REFERENCES alertas(id),
    ciclo TEXT NOT NULL,                    -- 'AAAA-MM' (ADR-7)
    janela_ref DATE NOT NULL,               -- semana/mês de referência do disparo
    data_extracao DATE NOT NULL,            -- rastreabilidade (RF-3)
    contagem_entregue INT NOT NULL,         -- 0 = semana zero (RF-11)
    contagem_represada INT NOT NULL,        -- quantos ficaram fora por cota (RF-13)
    canal_resultado JSONB NOT NULL,         -- {email: ok, whatsapp: failed→fallback}
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (alerta_id, janela_ref)          -- idempotência do dispatcher (ADR-8)
);

CREATE TABLE entregas (                     -- metering item a item (ADR-3)
    id BIGSERIAL PRIMARY KEY,
    despacho_id UUID NOT NULL REFERENCES despachos(id),
    alerta_id UUID NOT NULL,
    conta_id UUID NOT NULL,
    ciclo TEXT NOT NULL,
    cnpj TEXT NOT NULL,
    UNIQUE (alerta_id, cnpj)                -- a mesma empresa nunca é entregue 2× no mesmo alerta
);
CREATE INDEX ON entregas (conta_id, ciclo); -- COUNT da cota

CREATE TABLE creditos_overage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conta_id UUID NOT NULL REFERENCES contas(id),
    ciclo TEXT NOT NULL,
    quantidade INT NOT NULL DEFAULT 100,
    asaas_pagamento_id TEXT UNIQUE,         -- credita 1× por pagamento (RNF-1)
    criado_em TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE eventos_billing (
    evento_id TEXT PRIMARY KEY,             -- idempotência de webhook
    tipo TEXT NOT NULL,
    payload JSONB NOT NULL,
    processado_em TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### O algoritmo do despacho (o coração do produto)

Para cada alerta ativo de conta com canal confirmado, na cadência do plano:

1. `cota_restante = limite_plano + créditos_overage_do_ciclo − COUNT(entregas no ciclo da conta)`
2. `candidatas = match_empresas(filtro, janela) − entregas já feitas ao alerta` (ADR-3/4)
3. `entregar = candidatas ORDER BY data_abertura DESC LIMIT cota_restante_da_conta` (mais recentes primeiro; o resto fica represado e é reportado)
4. Transação: INSERT `despachos` (com a UNIQUE por `alerta_id, janela_ref` garantindo idempotência) + INSERT `entregas`.
5. Envio pelos canais (fora da transação): e-mail com lista + CSV; WhatsApp com resumo + link. Falha de canal **não** desfaz as entregas — marca no `canal_resultado` e o reenvio é operação de suporte (`dispatch resend`), nunca re-contagem de cota.
6. `contagem = 0` → caminho da semana zero: mesma mensagem estrutural, com o agregado do setor no estado (via `agregados_semanais`) no lugar da lista.

**Cadência com dado mensal, dito honestamente:** quando a extração nova carrega, o primeiro disparo semanal dos pagos leva o grosso; as semanas seguintes tendem a semana zero ou ao escoamento do represado por cota. É exatamente o comportamento que a comunicação do produto descreve — o sistema não finge cadência que a fonte não tem.

---

## 6. Segurança e LGPD

### LGPD — regra de produto implementada como mecanismo

1. **Allowlist explícita no ETL.** O SELECT final nomeia coluna por coluna (as do schema acima, todas da lista "entrega sem problema" da fonte). Nunca `SELECT *`. Campo novo do layout é invisível até ser adicionado deliberadamente, com a pergunta de auditoria da fonte: *"essa coluna identifica pessoa? Corta."*
2. **Sócios nem entram na máquina** (RF-1): os arquivos do quadro societário não são baixados. Não dá para vazar o que nunca se teve.
3. **MEI tratado como pessoa física:** a linha entra (a empresa existe e o filtro por porte MEI é caso de uso legítimo do contador), mas `endereco = NULL` e nenhum dado derivado do titular. A UI e o FAQ explicam o porquê — a limitação é o posicionamento.
4. **Teste de regressão de privacidade (CI, bloqueante):** (a) schema de `empresas_novas` ⊆ allowlist; (b) nenhum artefato de saída (e-mail renderizado, CSV, página de entrega, post do bot) contém padrão de CPF válido; (c) linhas MEI saem sem endereço. Falhou → não deploya.
5. **Página pública "Como tratamos os dados":** curta, clara, na landing — o que entrega, o que não entrega e por quê. A fonte é explícita: vale mais que uma feature nova.

### Segurança da aplicação

- **Senhas:** Argon2id com parâmetros atuais; rate limit de login (5 tentativas/15 min por conta+IP); reset por token de uso único (30 min); sem pergunta secreta, sem SMS.
- **Sessão:** cookie httpOnly/secure/SameSite=Lax; logout invalida.
- **Links de entrega no WhatsApp:** token assinado (HMAC) com expiração de 30 dias e escopo de um despacho — o link vaza? Expõe uma lista que o assinante pagou para ver, não a conta.
- **Autorização:** toda query de alerta/despacho/entrega filtrada por `conta_id` da sessão; teste de IDOR no CI.
- **Webhooks:** Asaas validado por token de cabeçalho; WhatsApp (Meta) por assinatura `X-Hub-Signature-256`; ambos idempotentes.
- **CSV injection:** células iniciando com `=`, `+`, `-`, `@` são escapadas — o público-alvo abre exatamente esses CSVs no Excel.
- **Segredos:** `.env` na VPS (600) + GitHub Secrets no CI; chaves: dois Postgres, Asaas, Resend, Meta (token permanente do WABA), X. Rotação documentada no runbook.
- **VPS:** só 80/443 (Caddy) + SSH por chave; fail2ban; atualizações de segurança automáticas.
- **O que nunca logar:** filtros junto de identidade (o CNAE que um contador monitora é informação comercial dele), senhas/hashes, payloads de billing, número de WhatsApp em log de aplicação. Logar IDs.

---

## 7. Confiabilidade

### O evento crítico continua sendo a carga mensal — agora com quebra anual esperada

| Falha | Detecção | Resposta |
|---|---|---|
| **Layout da Receita muda** (aconteceu jan/2026; assumir ≥1×/ano) | Validação estrutural pré-staging: nº de colunas por arquivo, tipos por amostragem, contagens dentro de faixa histórica (±40%) | **Quarentena:** `cargas.status = quarentena`, nada chega ao Postgres, alerta imediato. Correção é trabalho manual planejado (o pipeline é versionado e testado com fixtures para isso ser horas, não dias). **Fallback documentado:** CNPJ.ws Premium (endpoint de pesquisa por CNAE, pago por consulta) como paliativo **manual e temporário** para não furar a entrega dos pagantes — decisão humana, nunca automática, porque custa por consulta |
| Receita atrasa a publicação | Job diário verifica novidade no endpoint | Nada quebra: pagos recebem semana zero honesta ("Receita ainda não publicou a extração de junho"); aviso na página de autoatendimento |
| Download corrompido | Checksum + tamanho | Retry diário; 3 falhas → alerta |
| Carga parcial | Transação por carga | Rollback; rerun idempotente (UNIQUE `cnpj, carga_id`) |
| Dispatcher morre no meio | UNIQUE `(alerta_id, janela_ref)` em `despachos` | Rerun processa só os alertas sem despacho na janela; entregas já commitadas não se repetem (UNIQUE `alerta_id, cnpj`) |
| E-mail falha (Resend fora, bounce) | `canal_resultado` + taxa de falha | Reenvio via `dispatch resend`; bounce duro marca o e-mail e pausa envios até o assinante corrigir (protege reputação do domínio) |
| **WhatsApp: template pausado / qualidade do número degradada** | Webhook de status + painel Meta; taxa `failed` no `canal_resultado` | Fallback automático por despacho para e-mail (ADR-5); se a qualidade do número cair (spam reports), pausar o canal globalmente e investigar — número banido some da noite para o dia, e-mail segura o produto enquanto isso |
| VPS morre | UptimeRobot em `/api/health` | VPS recriável por script (<1h); dado precioso está no Supabase; `empresas_novas` se regenera do dump |
| Supabase indisponível | Health check | App fora do ar — aceitável (RNF-7); dispatcher simplesmente re-roda depois |

### Backup e restore

- **Supabase (contas, alertas, entregas, billing):** backup do provedor + `pg_dump` semanal para bucket (B2/R2, centavos). **Teste de restore trimestral no runbook** — é o único dado que não se regenera.
- **Postgres da VPS:** sem backup — regenerável do dump da Receita por construção (ADR-2).
- **Dump bruto:** guardar o último na VPS por conveniência de reprocesso; a Receita é o backup.

### Runbook (`RUNBOOK.md` no repo, vivo)

1. Carga em quarentena → ler `detalhe`, comparar layout, ajustar parser/validação com fixture nova, rerun; se a entrega dos pagos ficar em risco > 1 semana, avaliar o paliativo CNPJ.ws.
2. "Não recebi minha lista" → página de autoatendimento primeiro; depois `SELECT * FROM despachos WHERE alerta_id=...` → `dispatch resend`.
3. WhatsApp com falhas → checar qualidade do número e status do template no painel Meta; fallback já cobriu os assinantes; decidir pausa global.
4. Overage pago e não creditado → conferir `eventos_billing` e `creditos_overage.asaas_pagamento_id`.
5. Restore do Supabase → passos do `pg_restore` (testados no trimestre).
6. Recriar VPS → script de provisionamento + `.env` do gerenciador de senhas + `docker compose up -d` + `etl run`.

---

## 8. Observabilidade

### Pipeline
- `cargas` é a métrica primária (linhas, empresas novas por UF, duração, status) — uma query responde "a carga de junho foi normal?".
- Logs estruturados por etapa com rotação na VPS.

### Produto (as métricas que dirigem o negócio saem das tabelas do §5, via SQL salvo)
- Despachos por status/canal; taxa de fallback WhatsApp→e-mail; semana zero por alerta (alerta com N semanas zero seguidas = candidato a churn — sinal para o e-mail de semana zero caprichado).
- Cota: distribuição de consumo por plano (quantos batem no teto = demanda de overage/upgrade); overage comprado.
- Funil: prévias executadas → alertas salvos → contas confirmadas → pagantes (a prévia é a tela de conversão; medir é barato, é um COUNT).
- Uso do autoatendimento vs tickets de e-mail (mede se o RF-16 está funcionando).

### Alertas acionáveis (6, e só)
1. Carga não `concluida` até D+3 da publicação da Receita.
2. Carga em `quarentena` (imediato).
3. Dispatcher não rodou na janela esperada (dead man's switch).
4. Taxa de falha de canal > 10% num despacho em massa.
5. Webhook (Asaas ou Meta) retornando 5xx.
6. Bot público sem post há 24h (mesmo mecanismo do bot de futebol).

Sem Grafana/Prometheus até doer. Uptime externo: UptimeRobot free. Analytics de landing: Plausible/Umami se quiser funil — cookie-less, coerente com o posicionamento de privacidade.

---

## 9. Infraestrutura e deploy

- **Ambientes:** local (compose com os dois Postgres + fixture pequena do dump) e produção. O `--dry-run` do dispatcher + fixtures fazem papel de staging.
- **VPS:** provisionamento por script idempotente versionado (Docker, Caddy, fail2ban, firewall). Terraform é overkill para 1 VPS.
- **Deploy:** GitHub Actions → build → GHCR → SSH `docker compose pull && up -d`. Rollback = tag anterior. ETL/dispatcher: mesma imagem, disparados por systemd timers versionados no repo.
- **Bot público:** GitHub Actions (padrão do bot de futebol).
- **Migrações:** versionadas (dbmate/Prisma Migrate) nos **dois** bancos; aditiva primeiro, destrutiva depois de estável.
- **DNS/TLS:** Cloudflare na frente do Caddy.
- **Setup Meta/WhatsApp (é infraestrutura, e das mais burocráticas — começar cedo, no mês 3):** criar WABA, verificar o negócio (exige CNPJ próprio — o MEI do operador), registrar número dedicado (chip/virtual barato que você controla), submeter template `utility` à aprovação, configurar webhook de status. Prazo real: dias a semanas — por isso o roadmap entrega e-mail primeiro.

---

## 10. Custos

| Fase | Custo mensal | Composição |
|---|---|---|
| Validação (semana 1) | **R$ 0** | DuckDB no PC pessoal, posts manuais |
| Bot no ar (semanas 2–4) | **R$ 0–10** | GitHub Actions free, X API free; domínio amortizado |
| MVP pago (mês 2–3) | **~R$ 40–70** | VPS R$ 30–50; Supabase free; Resend free (3k e-mails); Cloudflare free |
| WhatsApp + escala (mês 3+) | **~R$ 60–100** | + número dedicado (chip ~R$ 20/mês ou virtual); + mensagens `utility` ≈ US$ 0,008/msg → **~R$ 0,20/assinante/mês** na cadência semanal (confirmar preço vigente da Meta na implementação); + Asaas por transação (só existe com receita) |
| 100 assinantes | **< R$ 100 fixo** | Mesma infra; custos variáveis (WhatsApp ~R$ 20, gateway) escalam com a receita, não antes dela |

**Conta de chegada (da fonte):** bruto ~R$ 3.400 para R$ 3k líquido (gateway, infra, MEI). Mix plausível: 60 × R$ 29 + 25 × R$ 59 = R$ 3.215. Com custo fixo < R$ 100, a margem estrutural é > 90%.

**Gatilhos de gasto (não pagar antes):** Supabase Pro só se o free limitar os dados preciosos (improvável — são pequenos); e-mail pago só acima de 3k envios/mês (= dezenas de pagantes); CNPJ.ws só como paliativo de quarentena; segundo número de WhatsApp só se a qualidade do primeiro degradar com volume.

---

## 11. Manutenibilidade e testes

### Organização (monorepo)

```
alertas-cnpj/
├── etl/
│   ├── allowlist.py        # a lista LGPD, um arquivo, comentário por campo
│   ├── layout/             # spec do layout da Receita POR VERSÃO (jan-2026, ...) — a quebra
│   │                       #   anual vira "adicionar um arquivo", não "arqueologia no parser"
│   └── ...
├── dispatch/
│   ├── match.py            # match_empresas — usado por prévia E despacho (ADR-4)
│   ├── canais/             # email.py, whatsapp.py (interface Canal)
│   └── ...
├── app/                    # Next.js: landing, conta, alertas, prévia, autoatendimento
├── bot/                    # posts públicos (importa render/publish do bot de futebol)
├── db/migrations/{vps,supabase}/
├── infra/
├── RUNBOOK.md
└── tests/fixtures/         # amostras reais pequenas do dump, POR VERSÃO de layout
```

### Estratégia de testes — prioridade por dano

1. **Privacidade (CI, bloqueante):** o teste do §6. Dano: existencial.
2. **Metering/cota (RNF-1):** cota nunca ultrapassada somando alertas; empresa nunca 2× no mesmo alerta; overage credita exatamente 100 e uma única vez por pagamento; represado escoa nos ciclos seguintes; represado que sai da janela expira. Dano: bug de cobrança.
3. **Prévia ≡ entrega (RNF-2):** para um conjunto de fixtures e filtros, a contagem da prévia por semana bate com o que o despacho entregaria nas mesmas janelas. Dano: churn por promessa quebrada.
4. **Diff/idempotência do dispatcher:** rodar 2× a mesma janela → zero novas entregas; morrer no meio e re-rodar → completa sem duplicar.
5. **Semana zero:** filtro sem match → despacho registrado com contagem 0 e mensagem com agregado, nunca silêncio.
6. **Corretude do filtro:** casos maldosos — empresa reativada (não é nova), MEI sem endereço, capital na borda da faixa, CNAE secundário vs principal, município homônimo em UFs diferentes.
7. **Schema drift:** fixture com layout adulterado → quarentena, nunca carga.
8. **Webhooks:** evento duplicado não duplica efeito (assinatura e overage); IDOR nas rotas de dados.

**Não vale o custo agora:** e2e de browser além de um smoke (signup → alerta → prévia); teste de carga; snapshot de UI.

### Dependências
Lock em tudo; atualização mensal em bloco. A dependência mais frágil não é pacote — é o **layout da Receita**: o diretório `etl/layout/` por versão + fixtures por versão é a resposta estrutural (RNF-8).

---

## 12. Riscos técnicos e mitigações

| Risco | Impacto | Mitigação |
|---|---|---|
| Frustração com cadência (cliente esperava diário) | Alto — churn | Prévia com histórico real antes de assinar (quem vê "0,1,0,2" não assina — e é bom que não assine); data de extração em toda mensagem; semana zero comunicada; landing explícita. A honestidade é o mecanismo anti-churn |
| **Suporte em escala** (100 × R$ 29 > barulho que 20 × R$ 197) | Alto — mata o operador solo | Autoatendimento como feature de 1ª classe (RF-16); FAQ agressiva; suporte só e-mail SLA 48h, sem canal WhatsApp de suporte; futura ferramenta "por que a empresa X não veio no meu alerta?" (cola o CNPJ → o sistema explica: fora do filtro / fora da janela / cota / MEI sem endereço) — deflexão do ticket mais comum |
| Layout da Receita quebra (≥1×/ano) | Alto — pipeline para | Quarentena + layouts versionados + fixtures por versão (§7, §11); paliativo CNPJ.ws manual; janela de 90 dias segura a entrega por semanas durante o conserto |
| Copycat low-cost (é fácil copiar) | Médio–alto | Fosso de execução: bot com audiência acumulada, reputação de entrega consistente, LGPD limpa. Chegar primeiro e não parar. Nenhuma mitigação técnica — é disciplina |
| Ban/limite da conta do bot no X | Alto — canal de aquisição | Práticas de automação do X (conta rotulada, cadência humana); **lista de e-mail própria desde o dia 1** (opt-in na landing) — canal que sobrevive à plataforma |
| Template WhatsApp reprovado/pausado pela Meta; qualidade do número cai | Médio | Canal como interface com fallback automático para e-mail (ADR-5); templates versionados; número dedicado monitorado; e-mail é sempre o canal de segurança |
| Free tier vira custo (400–1000 usuários grátis) | Baixo | Free é mensal e só e-mail: ~1 e-mail/usuário/mês cabe no Resend free até ~3k; empresas entregues ≤ 5 → cota de metering minúscula |
| LGPD: reclamação de MEI ou incidente | Existencial p/ marca | §6 inteiro: allowlist por construção, sócios nunca baixados, teste bloqueante, página pública, auditoria por release |
| Bus factor 1 | Médio | RUNBOOK vivo, provisionamento scriptado, backups testados; pipeline mensal permite férias planejadas |

---

## 13. Roadmap de desenvolvimento

Critérios de "pronto" verificáveis; não avançar sem cumprir. Espelha o roadmap da fonte.

**Semana 1 — Validação de dado (custo zero, sem código de produto)**
Baixar o dump, rodar DuckDB no PC, gerar agregado por UF, publicar (ou rascunhar) um post manual por 7 dias seguidos.
*Pronto quando:* confirmado que o dado existe na granularidade certa, que você aguenta a rotina, e que o formato causa reação. Se falhar aqui, o resto não importa.

**Semanas 2–4 — Bot no ar**
Automatizar o manual: Actions + X API + matplotlib, reutilizando os módulos do bot de futebol. Publicar todo dia por ≥ 60 dias antes de monetizar. Captura de e-mail na landing mínima desde já (o backup anti-ban).
*Pronto quando:* 60 dias de posts sem intervenção; alvo de 500–2.000 seguidores orgânicos no período.

**Mês 2–3 — MVP pago (só e-mail)**
ETL de produção (validação, quarentena, allowlist, janela rolante, agregados), landing, cadastro e-mail+senha, tela de alerta com **prévia**, dispatcher com metering/cota/semana zero, entrega por e-mail, Asaas. **Sem WhatsApp, sem CSV, sem dashboard.** Em paralelo: iniciar verificação do negócio na Meta (a burocracia demora — §9).
*Pronto quando:* primeiro assinante pago recebendo; testes de prioridade 1–5 verdes no CI; duas extrações processadas com um reprocesso idempotente comprovado.

**Mês 3–5 — Canal WhatsApp e refinos**
Cloud API oficial com template aprovado, resumo+link, fallback para e-mail, CSV anexo nos pagos, autoatendimento (RF-16), segundo/terceiro alerta por conta.
*Pronto quando:* 10–20 pagantes; despacho semanal completo rodando nas duas vias com taxa de falha < 5%.

**Mês 5–10 — Escala orgânica**
Overage self-service, tier R$ 59 (colunas extras no CSV), refinamento guiado por feedback de pagante, e-mail de semana zero caprichado com agregados.
*Pronto quando:* ~50 pagantes; tickets < 5% dos assinantes/mês (o autoatendimento está funcionando).

**Mês 10–18 — Travar em R$ 3k**
Ajuste fino de conversão (funil prévia→pagante medido), filtros pedidos por assinantes (sem virar plataforma — cada pedido passa pelo crivo dos non-goals), considerar segundo bot regional para ampliar alcance.
*Pronto quando:* 80–100 pagantes estáveis com churn compensado pelo funil do bot.

**Checkpoint honesto (da fonte):** se em 6 meses o bot estiver < 1.000 seguidores **e** zero pagantes — reavaliar formato, canal ou produto. Nunca só "persistir mais".

---

## Relação com os outros produtos

Herda do bot de futebol os módulos de render/publicação e os padrões operacionais (cron gratuito, dead man's switch, golden tests). Exporta para a automação de WhatsApp ([03-automacao-whatsapp-dev.md](03-automacao-whatsapp-dev.md)) o billing Asaas com webhooks idempotentes, a VPS, o padrão de backup/runbook e — principalmente — o público e o upsell: o assinante recebe leads aqui e contrata lá o meio de contatá-los. Nota de fronteira importante: **este produto usa a Cloud API oficial (o número é seu, o risco é seu); o produto 3 usa Baileys local (o número é do cliente, na máquina do cliente)** — as duas escolhas são opostas e ambas corretas, porque a posição de quem opera o número é oposta.
