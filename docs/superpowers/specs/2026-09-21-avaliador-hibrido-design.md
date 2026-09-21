# Avaliador híbrido de caligrafia — design

Data: 2026-09-21 · Status: aprovado em conversa, aguardando revisão do spec

## Problema

O avaliador atual (`handwriting_evaluator.py` + `train_cnn.py`) não mede qualidade.
Os rótulos ruim/aceitável/boa usados no treino foram gerados pela **variância de
pixels** de imagens do EMNIST, então a CNN aprendeu a estimar quantidade de tinta.
Letras reais (foto ou quadro) têm traço mais grosso que o EMNIST e caem todas em
"boa" — inclusive rabiscos aleatórios (testado: rabisco → Boa, confiança 1,0,
pontuação 100). Efeitos visíveis:

- no exercício, basta o Google Vision reconhecer a letra para "acertar";
- na Análise, a pontuação geral é quase sempre 100.

## Objetivo

Nota contínua de 0 a 100 por letra que caia quando a letra (a) não se parece com a
letra-alvo e (b) foge do molde de letra de forma (proporção, inclinação, traço
irregular, formas arredondadas onde deveriam ser retas). Critério escolhido pelo
autor: **"boa" = parecida com o molde de letra de forma**, não apenas legível.

## Visão geral

```
letra recortada (binária) ──┬─► CNN MobileNetV2 (26 classes EMNIST) ─► legibilidade (0–1)
                            │        P(alvo) calibrada por temperatura, penalizada pela margem
                            │
                            └─► medidas geométricas vs. molde ─────────► formação (0–1)
                                     IoU, proporção, inclinação, espessura

nota = 100 · (0,6 · legibilidade + 0,4 · formação)
categoria: Boa ≥ 75 · Aceitável 50–74 · Ruim < 50
```

## Componentes

### 1. `train_cnn.py` (reescrito)

- Dataset: `torchvision.datasets.EMNIST(split="letters")` — 26 classes (a–z,
  maiúsculas e minúsculas fundidas), 124.800 treino / 20.800 teste, rótulos reais.
- Pré-processamento idêntico ao de inferência: binarização Otsu, recorte na caixa da
  letra, enquadramento em quadrado com margem de 10 %, redimensionamento para
  **96×96**, 3 canais.
- Augmentation para fechar a lacuna EMNIST → letra real: dilatação/erosão aleatória
  (traço grosso/fino), rotação ±12°, escala 0,85–1,15, cisalhamento ±8°, pequena
  translação.
- Modelo: MobileNetV2 com pesos ImageNet, classificador final com 26 saídas.
  6 épocas, Adam 1e-3 com decaimento, batch 128.
- Calibração: após o treino, ajusta uma **temperatura** `T` no conjunto de validação
  (minimiza NLL) e salva `{"state_dict", "temperatura", "classes", "acuracia_val",
  "tamanho"}` em `modelo_caligrafia.pth`.
- Saída no terminal: acurácia por época e final (número para o artigo).

### 2. `handwriting_evaluator.py` (reescrito, mesma interface pública)

```python
avaliar_texto(characters, alvos=None, batch_size=32) -> dict | None
```

- `characters`: lista `(x, y, w, h, img_binaria)` como hoje.
- `alvos`: lista opcional de letras esperadas (`"A"`–`"Z"`, ou `None` por posição).
  Sem alvo, o alvo é a classe prevista pela CNN (legibilidade = confiança calibrada).
- Retorno por letra (mantém as chaves atuais para a UI não quebrar):

  | chave | conteúdo |
  |---|---|
  | `indice`, `posicao` | como hoje |
  | `nota` | 0–100 (novo) |
  | `classe` / `categoria` | 0/1/2 — Ruim/Aceitável/Boa, derivados da nota |
  | `confianca` | legibilidade calibrada (0–1), continua existindo |
  | `letra_prevista` | letra com maior probabilidade na CNN |
  | `legibilidade`, `formacao` | parcelas 0–1 (novo) |
  | `medidas` | dict com `iou`, `proporcao`, `inclinacao`, `espessura` (novo) |

- Agregados: `pontuacao_geral = média das notas` (acaba o 100 automático);
  `boas/aceitaveis/ruins` contam pelas categorias.

**Legibilidade.** `p = softmax(logits / T)`; `legibilidade = p[alvo] · (1 − 0,5 · p[segunda])`
— a penalidade pela segunda opção pune letras ambíguas (A que parece O).

**Formação.** Compara a letra normalizada (mesmo enquadramento do treino, 96×96)
com moldes da letra-alvo renderizados de 4 fontes do sistema (DejaVu Sans,
Liberation Sans, Noto Sans, Noto Serif — a última é a da letra-guia do quadro).
Para cada molde testa pequenos ajustes (escala ±10 %, deslocamento ±4 px) e fica com o
melhor. Quatro medidas, cada uma mapeada para 0–1:

| medida | como | 1,0 quando |
|---|---|---|
| `iou` | interseção/união das máscaras dilatadas (tolerância de 3 px) | ≥ 0,70 |
| `proporcao` | \|razão h/w da letra − razão h/w do molde\| relativa | desvio ≤ 10 % |
| `inclinacao` | ângulo do eixo principal (momentos de imagem) vs. molde | desvio ≤ 4° |
| `espessura` | coef. de variação da largura do traço (transformada de distância) | ≤ 0,25 |

`formacao = 0,45·iou + 0,20·proporcao + 0,15·inclinacao + 0,20·espessura`.
Os moldes são renderizados uma vez por letra e guardados em cache em memória.
Se o alvo não existir (`None`) usa a letra prevista.

### 3. Chamadas existentes (mudanças mínimas)

- `analise_widget.AnaliseWorker` (modo Google): passa `alvos=[s["letra"] for s in simbolos]`.
  Modo TrOCR: passa as letras do texto previsto se o número bater com o de
  caracteres; senão `None`.
- `praticar_widget.VerificarWorker`: passa `alvos=list(alvo)` (letra ou palavra).
- `praticar_widget.PainelExercicio._validar`:
  - letra: passa se reconhecida **e** `nota ≥ 60`; mensagens distintas para
    "reconheci outra letra", "está parecendo X" (legibilidade baixa) e "formação
    fora do molde" (formação baixa, com a pior medida citada: "muito inclinada",
    "traço irregular", "muito larga/estreita").
  - palavra: passa se texto correto **e** média das notas ≥ 60 **e** nenhuma
    letra < 40.
- `detalhe_letra_dialog.py`: mostra a nota, as duas parcelas e as quatro medidas
  (barras simples), no lugar de só "categoria + confiança".
- `handwriting_evaluator.gerar_relatorio`: inclui a nota por letra.
- `Readme.md` e `diagnostico_variancia.py`: o diagnóstico de variância deixa de fazer
  sentido e é removido; o Readme descreve o avaliador novo e retira a limitação
  "baseada na variância".

### 4. Testes

`test_avaliador.py` (executável direto, sem framework), com imagens sintéticas
geradas por PIL — não depende de fotos:

1. **Rabisco aleatório** com alvo "A": nota < 40.
2. **A limpo de fonte** (renderizado de uma fonte não usada como molde): nota ≥ 75.
3. **A arredondado/exagerado**: nota < 60 e a pior medida é `iou` ou `inclinacao`.
4. **A muito inclinado** (cisalhado 25°): `inclinacao` < 0,5.
5. **O com alvo "A"**: `legibilidade` < 0,4.
6. Ordenação: nota(limpo) > nota(arredondado) > nota(rabisco).
7. Interface: retorno mantém `classe`, `categoria`, `confianca`, `pontuacao_geral`.

Os testes rodam contra o modelo treinado; enquanto ele não existir, o script avisa
e roda só os testes de geometria (1, 3, 4 com `formacao` isolada).

### 5. Fora do escopo

- Letras minúsculas como molde próprio (EMNIST letters funde caixas; o molde usa a
  caixa da letra reconhecida — maiúscula no exercício).
- Cursiva.
- Retreinar com amostras reais rotuladas (fica como trabalho futuro no artigo).

## Impacto no artigo

A subseção 3.4 (avaliação) e 3.4.1 (calibração de limiares) precisam ser
reescritas: a CNN passa a ser um classificador de letras com acurácia real
reportada, e a nota combina legibilidade e formação geométrica. Ganha-se uma
tabela de resultados honesta (acurácia no EMNIST + os testes sintéticos).

## Riscos

- Domínio EMNIST × letra real ainda existe; a augmentation de espessura mitiga, e a
  parcela geométrica não depende do treino.
- Moldes de fonte podem ser rígidos demais para algumas letras (G, Q, J variam entre
  fontes); usar 4 fontes e ficar com o melhor molde reduz isso. Os pesos e limiares
  ficam em constantes no topo do arquivo para ajuste rápido.
