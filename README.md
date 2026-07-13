# Alertas de CNPJ — etapas 1 a 3

Pipeline que transforma o dump mensal dos Dados Abertos CNPJ da Receita Federal em
agregados confiáveis, e um bot que gera um post por dia a partir deles.

Produto completo especificado em [02-monitor-cnpj-dev.md](02-monitor-cnpj-dev.md).
Estas três etapas existem antes do produto pago porque **o bot é o relógio mais lento**
(audiência acumula em tempo de calendário, código não) e porque **o bot constrói o ETL**
que o produto pago vai usar.

## Onde as coisas moram

| O quê | Onde | Por quê |
|---|---|---|
| Código | este repo (OneDrive) | pequeno, versionado |
| Zips + CSVs (~26 GB) | `C:\cnpj-data` (env `CNPJ_DATA_DIR`) | **fora do OneDrive**, senão ele sincroniza 26 GB para a nuvem |
| `data/agregados.parquet` | commitado no git | é a única coisa que o bot lê — por isso ele não precisa de banco nem de VPS |

## Rodar

```bash
# 1x/mês, no PC (a Receita publica lá pelo dia 13)
python -m etl.download   --extracao 2026-06     # ~6,4 GB, resumível; Sócios NUNCA é baixado
python -m etl.agregados  --extracao 2026-06     # extrai, filtra, agrega -> data/agregados.parquet
python -m etl.sanity     --extracao 2026-06     # OBRIGATÓRIO: ver abaixo
git add data/agregados.parquet && git commit -m "extracao 2026-06"

# o bot (roda sozinho no GitHub Actions, 1x/dia)
python -m bot.run --dry-run    # mostra o corte do dia sem publicar nem gastá-lo
python -m bot.run --todos      # gera o catálogo inteiro em out/ para você revisar
```

## Os sanity checks não são opcionais

O risco destas etapas não é o código quebrar — é **o código funcionar e estar errado**,
e você postar número errado por 60 dias antes de alguém reparar. `etl/sanity.py` existe
para tornar isso improvável. Os dois que mais importam:

- **Ordem de grandeza.** O Brasil abre ~300–400 mil empresas/mês. Se o filtro devolver
  3 milhões ou 3 mil, o parse está errado. Este check sozinho pega a maioria dos erros.
- **Armadilha da reativação.** Uma empresa suspensa que voltou à ativa tem
  `data_situacao_cadastral` recente e `data_inicio_atividade` antiga — **ela não é nova**.
  O filtro ancora em `data_inicio_atividade` por isso. Um contador que receber empresa de
  2019 numa lista de "abriram essa semana" cancela na hora.

Na primeira carga de cada mês, faça também o **spot-check**: o check imprime 5 CNPJs;
confira num site público de CNPJ que existem, estão ativos e abriram na data indicada.
É o único teste que valida o pipeline inteiro ponta a ponta.

## Decisões que valem saber

- **A API do X é paga desde fev/2026** (pay-per-use, créditos pré-pagos — o free tier
  acabou). Então a v1 publica no seu **Telegram** e você copia e cola no X.
  `bot/publish.py` tem a interface `Publisher`; trocar por `XPublisher` depois é um
  arquivo, não uma refatoração.
- **O dado é mensal, o post é diário.** Logo o bot não é um feed de novidades: é um
  catálogo de cortes parametrizados sobre a mesma extração. 6 cortes × (UF, CNAE,
  cidade) = **34 posts** sem repetir.
- **Nome amigável de CNAE é mapa curado, não busca por texto** (`bot/setores.py`).
  Não existe CNAE "barbearia" nem "pizzaria" — existe "Cabeleireiros, manicure e
  pedicure". Buscar por texto falha justamente nas palavras que fazem o post ser
  compartilhado.
- **Sócios nunca é baixado** (`etl/layout/`, allowlist explícita). Não dá para vazar o
  que nunca se teve. `etl/sanity.py` falha se um arquivo de Sócios aparecer em disco.
- **Semana parcial nunca vai para o post.** A semana em que a Receita cortou a extração
  está incompleta; postar "as aberturas caíram 60%" quando faltam 4 dias de dado é o
  jeito mais rápido de destruir a credibilidade que o bot existe para construir.
