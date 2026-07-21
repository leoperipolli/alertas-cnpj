# Textos dos 15 posts — extração 2026-07 (referência junho/2026)

> **Números reais de junho/2026**, extração oficial da Receita de **11/07/2026** (carga 2026-07, validada pelo `etl.sanity`: 439.247 aberturas/mês, SP em 30,1%). Junho é mês completo; a semana de 06/07 é parcial e não entra em nenhum post.
>
> **Antes de publicar qualquer post per capita:**
> - Citar a fonte da população: **Censo IBGE 2022**. Sem isso, um "por 100 mil habitantes" queima credibilidade.
> - Filtrar a pseudo-UF **`EX`** (exterior) — valores absurdos que contaminam ranking. (Já filtrada nos números abaixo.)
> - Ignorar setor com poucas aberturas no mês: com N baixo o "líder per capita" muda por acaso (ex.: Amapá lidera restaurante per capita, mas com só 39 no mês — por isso não é o herói do post 3).
>
> A linha de fonte de cada post deve levar a data exata da extração: **11/07/2026**.

As mecânicas estão agrupadas porque cada grupo é um **molde reutilizável todo mês**, não um post único. **Atenção:** vários "heróis" mudaram de maio para junho (o líder de bar/academia virou Mato Grosso, o de restaurante deixou de ser Rondônia). Recalcule sempre — não confie no ranking do mês anterior.

---

## Mecânica A — Per capita (SP despenca quando se conta gente)

### 1. O estado mais empreendedor não é São Paulo

```
Todo mundo sabe que São Paulo é o estado que mais abre empresa no Brasil.

Mas quando você divide por população, ele cai para o 3º lugar.

Quem mais abre empresa por habitante é Santa Catarina: 382 empresas
novas por 100 mil habitantes. Depois o Distrito Federal (351). SP: 349,
colado no DF mas atrás.

Fonte: Dados abertos da Receita Federal, extração de 11/07/2026 +
população (Censo IBGE 2022).
```
- **Gráfico:** barras horizontais, aberturas por 100 mil hab, top 10 UFs. SC destacado; SP marcado em 3º para o contraste bater.
- **Alt:** Ranking de aberturas de empresa por 100 mil habitantes em junho de 2026. Santa Catarina 382, DF 351, São Paulo 349 (3º).

### 2. A capital do boteco é o Espírito Santo

```
A capital do boteco não é São Paulo. Nem o Rio.

É o Espírito Santo.

Por habitante, o ES abriu mais bar do que qualquer estado em junho:
3,0 bares novos por 100 mil habitantes. São Paulo, o gigante,
ficou só em 10º.

Fonte: Receita Federal (extração de 11/07/2026) + Censo IBGE 2022.
```
- **Gráfico:** bares por 100 mil hab, top 8. ES destacado; SP marcado em 10º.
- **Alt:** Aberturas de bares por 100 mil habitantes, junho de 2026. Espírito Santo 3,0; Minas 2,5; São Paulo 1,6 (10º).

### 3. No ranking de restaurante, São Paulo é só o 6º

```
O estado que mais abre restaurante por habitante no Brasil não é
São Paulo. Ele aparece só em 6º.

Na frente dele, estados que ninguém associa a gastronomia: Distrito
Federal (5,0 por 100 mil hab) e Goiás (4,7) abrem mais restaurante
por habitante que SP (4,1).

Fonte: Receita Federal (extração de 11/07/2026) + Censo IBGE 2022.
```
- **Gráfico:** restaurantes por 100 mil hab, top 8 (com base mínima de aberturas para não subir Amapá por acaso). SP marcado em 6º.
- **Alt:** Aberturas de restaurantes por 100 mil habitantes, junho de 2026. DF 5,0; Goiás 4,7; São Paulo 4,1 (6º).

### 4. A capital da vaidade: Rio e Brasília empatados

```
São Paulo não é a capital da vaidade do Brasil. É só o 4º.

Quem mais abre salão de beleza por habitante são Rio e Brasília,
empatados no topo (15,7 por 100 mil hab cada). Santa Catarina vem
logo atrás. SP fica em 4º.

Fonte: Receita Federal (extração de 11/07/2026) + Censo IBGE 2022.
```
- **Gráfico:** salões por 100 mil hab, top 8. RJ e DF empatados destacados.
- **Alt:** Aberturas de salão de beleza por 100 mil habitantes, junho de 2026. Rio e DF 15,7; SC 14,8; São Paulo 14,8 (4º).

### 5. O estado mais fitness fica no Nordeste

```
O estado mais fitness do Brasil fica no Nordeste.

A Paraíba foi quem mais abriu academia por habitante em junho.
São Paulo ficou em 6º.

(Sim, de novo: em número absoluto SP lidera tudo. Por habitante,
quase nunca.)

Fonte: Receita Federal (extração de 11/07/2026) + Censo IBGE 2022.
```
- **Gráfico:** academias por 100 mil hab, top 8. PB destacado.
- **Alt:** Aberturas de academia por 100 mil habitantes, junho de 2026. Paraíba 0,98; São Paulo 0,64 (6º).

---

## Mecânica B — Razão entre dois setores (índice com nome engraçado)

### 6. Índice bar ÷ academia

```
Índice bar ÷ academia: quantos bares novos abrem para cada
academia nova.

Campeão em junho: Mato Grosso, com mais de 8 bares para cada
academia. Goiás vem em 2º (6 para 1).

O Centro-Oeste escolhe o happy hour.

Fonte: Receita Federal, extração de 11/07/2026.
```
- **Gráfico:** razão bar/academia por UF, top 8. Só entra UF com base mínima de academias para a razão não estourar.
- **Alt:** Razão entre bares e academias abertos por estado, junho de 2026. Mato Grosso 8,4; Goiás 6,0.

### 7. O mineiro resolve no boteco, não no divã

```
Para cada consultório de psicologia que abre em Minas Gerais,
abrem quase 6 bares e restaurantes.

O mineiro, ao que parece, resolve as coisas no boteco — não no divã.

(Em São Paulo a conta é 3 para 1.)

Fonte: Receita Federal, extração de 11/07/2026.
```
- **Gráfico:** razão (bar+restaurante) / psicologia por UF, top 8. MG destacado; SP marcado.
- **Alt:** Razão entre bares/restaurantes e consultórios de psicologia por estado, junho de 2026. Minas Gerais 5,8; São Paulo 3,4.

### 8. O pet está alcançando a padaria

```
No Rio de Janeiro, ainda abrem 4 padarias para cada petshop.

Mas essa distância está encolhendo no Brasil inteiro — em vários
estados o pet já chega perto da padaria.

O país está trocando o pão pela ração? (Não. Mas o gráfico é bom.)

Fonte: Receita Federal, extração de 11/07/2026.
```
- **Gráfico:** razão padaria/petshop por UF, ordenado; linha de referência em 1,0 para mostrar quem está perto do empate.
- **Alt:** Razão entre padarias e petshops abertos por estado, junho de 2026. Rio de Janeiro 4,0.

---

## Mecânica C — Correlação ≠ causa (o formato pedido)

### 9. Vaidade e ansiedade no mesmo CEP

```
Coincidência do mês:

O Distrito Federal está no topo do país ao mesmo tempo em salão de
beleza E em consultório de psicologia por habitante.

Vaidade e ansiedade, no mesmo CEP.

(Antes que perguntem: correlação não é causa. Um salão de beleza
não deixa ninguém ansioso.)

Fonte: Receita Federal (extração de 11/07/2026) + Censo IBGE 2022.
```
- **Gráfico:** duas barras para o DF (salão per capita, psicologia per capita), ambas no topo do país; miniatura do ranking nacional ao lado. (DF é o nº1 em psicologia e empata em 1º em salão.)
- **Alt:** Distrito Federal no topo do Brasil tanto em salões quanto em consultórios de psicologia por habitante, junho de 2026.

### 10. O gráfico espúrio do mês (formato recorrente)

```
📈 O gráfico espúrio do mês.

Estes dois setores abriram quase no mesmo ritmo em todos os estados.
A linha é quase perfeita.

Eles não têm absolutamente nada a ver um com o outro.

Lembrete carinhoso: correlação não é causa.

Fonte: Receita Federal, extração de 11/07/2026.
```
- **Como montar:** escolher dois CNAEs sem relação nenhuma cujas aberturas por estado andem juntas (alta correlação entre UFs). A piada é justamente o disclaimer. Vira uma coluna fixa — cada mês um par novo e absurdo.
- **Gráfico:** dispersão UF a UF (eixo X = setor A, eixo Y = setor B) com a reta de tendência; ou duas linhas sobrepostas.
- **Alt:** Dispersão mostrando correlação alta e sem sentido entre dois setores não relacionados, por estado, junho de 2026.

---

## Mecânica D — SP não lidera nem no número absoluto (raro, logo forte)

### 11. O maior polo de roupa não é São Paulo

```
O maior polo de roupa que abre CNPJ no Brasil não é São Paulo.

Em junho, Santa Catarina abriu mais empresas de facção de vestuário
que SP: 158 contra 139 — em número absoluto, não por habitante.

Fonte: Receita Federal, extração de 11/07/2026.
```
- **Gráfico:** facção de vestuário (CNAE 1412603), aberturas absolutas, top 8. SC à frente de SP — a diferença apertada é a história.
- **Alt:** Aberturas de empresas de facção de vestuário por estado, junho de 2026. Santa Catarina 158, São Paulo 139.

### 12. Maranhão, capital do representante comercial

```
O estado que mais abriu representante comercial (de mercadorias em
geral) no Brasil em junho foi o Maranhão.

Não São Paulo, não o Rio. Maranhão: 234 contra 169 de SP — em número
absoluto.

Fonte: Receita Federal, extração de 11/07/2026.
```
- **Gráfico:** representantes comerciais de mercadorias em geral, aberturas absolutas, top 8. MA no topo, SP em 2º.
- **Alt:** Aberturas de representantes comerciais por estado, junho de 2026. Maranhão 234, São Paulo 169.

---

## Mecânica E — O setor-assinatura de cada estado ("me representa")

### 13. Mapa: o que cada estado abre muito acima da média

```
O que cada estado abre MUITO acima da média do Brasil:

📇 Maranhão — representante comercial (14x a média nacional)
🏥 Bahia — hospital (8x)
⚡ Paraná — geração de energia elétrica (7x)
🚜 Mato Grosso — máquina agrícola (6x)
🚕 Sergipe — táxi (6x)
🧵 Santa Catarina — confecção de roupa (5x)
👟 Ceará — calçados (5x)
💹 Rio de Janeiro — fundo de investimento (4x)

Cada estado tem uma cara. Achou a do seu?

Fonte: Receita Federal, extração de 11/07/2026.
```
- **Como montar:** location quotient = (peso do setor no estado) ÷ (peso do setor no Brasil). LQ alto = o estado abre esse setor muito acima do esperado. Exigir base mínima de aberturas por setor (n≥40). Filtrar `EX`.
- **Gráfico:** mapa do Brasil com um ícone/rótulo por estado, ou carrossel com um card por estado.
- **Alt:** Setor que cada estado abre proporcionalmente mais que a média nacional, junho de 2026.

### 14. Sergipe, o estado do táxi

```
Curiosidade do mês:

O estado que proporcionalmente mais abre empresa de táxi no Brasil
é Sergipe — 6 vezes acima da média nacional.

Ninguém sabe direito por quê. Mas o dado está lá.

Fonte: Receita Federal, extração de 11/07/2026.
```
- **Gráfico:** location quotient de "serviço de táxi" por UF, top 8. SE isolado no topo.
- **Alt:** Índice de especialização em serviços de táxi por estado, junho de 2026. Sergipe 6x a média nacional.

---

## Mecânica F — Temporal (o que mudou de um mês para o outro)

### 15. O setor que mais acelerou no mês

```
O setor que mais acelerou de maio para junho no Brasil?

Corretores e agentes de seguros: saltaram de 474 para 1.059 aberturas
em um mês (+123%).

Fonte: Receita Federal, extração de 11/07/2026.
```
- **⚠️ Cuidado (obrigatório antes de publicar):** o maior salto bruto de junho foi "comércio varejista de laticínios e frios", de 436 para 2.166 (+397%). Um pulo de ~5x num único mês quase nunca é tendência econômica — é reclassificação de CNAE ou lote de cadastros. **Confira o vencedor no dado bruto antes de postar.** Por isso a copy acima usa corretores de seguros (+123%), mais defensável — mas mesmo esse merece um olhar humano. Regra: salto de 3x+ = suspeitar primeiro, postar depois.
- **Gráfico:** top setores por variação percentual mês contra mês (o corte `anomalia` já faz isso), com piso de volume.
- **Alt:** Setores com maior crescimento de aberturas entre maio e junho de 2026.

---

## Resumo das mecânicas (o que precisa entrar no código)

| Mecânica | Posts | O que falta no pipeline |
|---|---|---|
| A — per capita | 1–5 | tabela estática de população IBGE 2022 por UF em `etl/` |
| B — razão entre setores | 6–8 | corte novo em `bot/cortes.py`; piso de base para não estourar a razão |
| C — correlação ≠ causa | 9–10 | corte novo; seleção de pares (item 10 é semiautomático/curado) |
| D — SP fora do topo absoluto | 11–12 | consulta "CNAE onde líder ≠ SP" (recalcular todo mês: os exemplos mudam) |
| E — location quotient | 13–14 | corte novo de LQ; filtrar `EX`; piso de base |
| F — temporal | 15 | já existe (`anomalia`); adicionar guarda contra saltos de 3x+ (reclassificação) |

**Fila sugerida de implementação:** A e E primeiro (maior alcance, dependem só da tabela de população e de um cálculo de LQ), depois B, D, F, e por fim C (o item 10 pede curadoria manual do par).
```
