# Avaliador híbrido de caligrafia — plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Substituir o avaliador atual (que não mede qualidade) por uma nota 0–100 por letra combinando legibilidade (CNN de 26 letras, calibrada) e formação geométrica contra moldes de letra de forma.

**Architecture:** Um módulo novo `letra_prep.py` concentra a normalização de máscaras de letra (usada igual no treino e na inferência). `train_cnn.py` passa a treinar MobileNetV2 nas 26 classes do EMNIST-letters com augmentation de espessura e salva temperatura de calibração. `handwriting_evaluator.py` mantém a interface `avaliar_texto()` e devolve `nota`, `legibilidade`, `formacao` e `medidas`; as telas passam a enviar a letra-alvo e a usar a nota.

**Tech Stack:** Python 3.11, PyTorch/torchvision (MobileNetV2, EMNIST), OpenCV, NumPy, Pillow (render de moldes), PyQt5 (telas).

**Spec:** `docs/superpowers/specs/2026-09-21-avaliador-hibrido-design.md`

## Global Constraints

- Interface pública `avaliar_texto(characters, alvos=None, batch_size=32)`; retorno mantém as chaves `indice, posicao, classe, categoria, confianca` e os agregados `pontuacao_geral, total, boas, aceitaveis, ruins`.
- Tamanho de entrada da CNN: **96×96**, 3 canais; máscara com tinta = 255, fundo = 0; margem de 10 % no enquadramento.
- Pesos: `nota = 100·(0,6·legibilidade + 0,4·formacao)`; `formacao = 0,45·iou + 0,20·proporcao + 0,15·inclinacao + 0,20·espessura`.
- Faixas: Boa ≥ 75, Aceitável 50–74, Ruim < 50. Exercício de letra passa com `nota ≥ 60`; palavra passa com média ≥ 60 e nenhuma letra < 40.
- Fontes dos moldes (nesta ordem): DejaVu Sans, Liberation Sans, Noto Sans, Noto Serif — localizadas por `fc-match`, com fallback por glob em `/usr/share/fonts`.
- Nada de novas dependências em `requirements.txt`.
- Comandos rodam com `venv/bin/python` na raiz do projeto. Testes são scripts executáveis (`python test_x.py`), sem pytest.
- `modelo_caligrafia.pth` está no `.gitignore` (não commitar).
- Comentários e strings em português; strings visíveis com acento, chaves de dicionário sem.

---

## Mapa de arquivos

| Arquivo | Responsabilidade |
|---|---|
| `letra_prep.py` (novo) | máscara a partir do recorte do pipeline / do EMNIST / de glifo de fonte; enquadramento 96×96; tensor para a CNN; localização de fontes |
| `test_letra_prep.py` (novo) | testes do enquadramento e das máscaras |
| `formacao.py` (novo) | moldes por letra (cache), 4 medidas geométricas, `avaliar_formacao(mascara, letra)` |
| `test_formacao.py` (novo) | testes das medidas com letras sintéticas |
| `train_cnn.py` (reescrito) | dataset EMNIST-letters com augmentation, treino, calibração de temperatura, salvamento |
| `handwriting_evaluator.py` (reescrito) | carrega modelo, legibilidade calibrada, combina com formação, agregados, relatório |
| `test_avaliador.py` (novo) | testes ponta a ponta com letras sintéticas (precisa do modelo treinado) |
| `analise_widget.py`, `praticar_widget.py` | passam `alvos`; `_validar` usa a nota e explica a pior medida |
| `detalhe_letra_dialog.py` | mostra nota, parcelas e medidas |
| `diagnostico_variancia.py` | removido |
| `Readme.md` | seções de avaliação/limitações atualizadas |

---

### Task 1: `letra_prep.py` — normalização compartilhada

**Files:**
- Create: `letra_prep.py`
- Test: `test_letra_prep.py`

**Interfaces:**
- Produces:
  - `TAMANHO = 96`, `MARGEM = 0.10`
  - `mascara_de_recorte(crop: np.ndarray) -> np.ndarray` — recorte do pipeline (fundo 255, tinta 0, ou BGR) → máscara uint8 0/255 com tinta = 255
  - `mascara_de_emnist(img_pil) -> np.ndarray` — imagem PIL 28×28 do torchvision (vem transposta) → máscara 0/255 orientada corretamente
  - `mascara_de_glifo(letra: str, caminho_fonte: str, tamanho_fonte: int = 160) -> np.ndarray` — glifo renderizado → máscara 0/255
  - `caixa_tinta(mascara) -> tuple[int,int,int,int] | None` — (x, y, w, h) da tinta
  - `normalizar_mascara(mascara) -> np.ndarray` — recorta na caixa, enquadra em quadrado com margem, redimensiona para TAMANHO×TAMANHO, rebinariza. Máscara vazia → zeros
  - `tensor_de_mascara(mascara_norm) -> torch.Tensor` — float (3, 96, 96), normalizado com média/desvio ImageNet
  - `localizar_fonte(nome: str) -> str | None` — caminho .ttf via `fc-match`, fallback glob
  - `FONTES_MOLDE = ["DejaVu Sans", "Liberation Sans", "Noto Sans", "Noto Serif"]`

- [x] **Step 1: Escrever o teste que falha**

```python
# test_letra_prep.py
"""Testes da normalizacao de letras (roda com: venv/bin/python test_letra_prep.py)."""
import numpy as np
import letra_prep as lp


def _quadrado(ink_val, bg_val, x0=20, y0=30, w=40, h=60, tam=(120, 100)):
    img = np.full(tam, bg_val, dtype=np.uint8)
    img[y0:y0 + h, x0:x0 + w] = ink_val
    return img


def test_mascara_de_recorte_inverte_fundo_branco():
    crop = _quadrado(ink_val=0, bg_val=255)
    m = lp.mascara_de_recorte(crop)
    assert m.dtype == np.uint8 and set(np.unique(m)) <= {0, 255}
    assert m[50, 40] == 255 and m[5, 5] == 0


def test_caixa_tinta():
    m = _quadrado(ink_val=255, bg_val=0)
    assert lp.caixa_tinta(m) == (20, 30, 40, 60)
    assert lp.caixa_tinta(np.zeros((10, 10), np.uint8)) is None


def test_normalizar_enquadra_com_margem():
    m = _quadrado(ink_val=255, bg_val=0)
    n = lp.normalizar_mascara(m)
    assert n.shape == (lp.TAMANHO, lp.TAMANHO)
    x, y, w, h = lp.caixa_tinta(n)
    # o lado maior (altura 60) ocupa ~80% do quadro; a largura mantem a proporcao 40/60
    assert abs(h - lp.TAMANHO * (1 - 2 * lp.MARGEM)) <= 2
    assert abs(w / h - 40 / 60) < 0.08
    # centralizado
    assert abs((x + w / 2) - lp.TAMANHO / 2) <= 2 and abs((y + h / 2) - lp.TAMANHO / 2) <= 2


def test_normalizar_vazia():
    assert lp.normalizar_mascara(np.zeros((30, 30), np.uint8)).sum() == 0


def test_tensor():
    t = lp.tensor_de_mascara(lp.normalizar_mascara(_quadrado(255, 0)))
    assert tuple(t.shape) == (3, lp.TAMANHO, lp.TAMANHO)
    assert t.dtype.is_floating_point


def test_glifo_e_fonte():
    caminho = lp.localizar_fonte("DejaVu Sans")
    assert caminho and caminho.endswith(".ttf")
    m = lp.mascara_de_glifo("A", caminho)
    assert m.max() == 255 and lp.caixa_tinta(m) is not None


if __name__ == "__main__":
    import sys
    falhas = 0
    for nome, fn in list(globals().items()):
        if nome.startswith("test_") and callable(fn):
            try:
                fn(); print(f"ok    {nome}")
            except Exception as e:
                falhas += 1; print(f"FALHA {nome}: {e!r}")
    sys.exit(1 if falhas else 0)
```

- [x] **Step 2: Rodar e confirmar que falha**

Run: `venv/bin/python test_letra_prep.py`
Expected: `ModuleNotFoundError: No module named 'letra_prep'`

- [x] **Step 3: Implementar `letra_prep.py`**

```python
"""Normalizacao de letras compartilhada entre treino e inferencia.

Toda letra (recorte do pipeline, imagem do EMNIST ou glifo de fonte) vira
uma MASCARA uint8 com tinta = 255 e fundo = 0, e depois e enquadrada num
quadrado de TAMANHO x TAMANHO com margem. Treino e inferencia passam pelo
mesmo caminho, entao a CNN ve exatamente o mesmo tipo de imagem nos dois."""

import glob
import os
import subprocess

import cv2
import numpy as np
import torch
from PIL import Image, ImageDraw, ImageFont

TAMANHO = 96
MARGEM = 0.10

FONTES_MOLDE = ["DejaVu Sans", "Liberation Sans", "Noto Sans", "Noto Serif"]
_ARQUIVOS_FONTE = {
    "DejaVu Sans": "DejaVuSans.ttf",
    "Liberation Sans": "LiberationSans-Regular.ttf",
    "Noto Sans": "NotoSans-Regular.ttf",
    "Noto Serif": "NotoSerif-Regular.ttf",
}

_MEDIA = torch.tensor([0.485, 0.456, 0.406]).view(3, 1, 1)
_DESVIO = torch.tensor([0.229, 0.224, 0.225]).view(3, 1, 1)


def mascara_de_recorte(crop):
    """Recorte do image_pipeline (fundo claro, tinta escura) -> mascara."""
    if crop.ndim == 3:
        crop = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    return np.where(crop < 128, 255, 0).astype(np.uint8)


def mascara_de_emnist(img_pil):
    """Imagem PIL do torchvision EMNIST (28x28, guardada transposta)."""
    arr = np.array(img_pil, dtype=np.uint8).T
    return np.where(arr > 127, 255, 0).astype(np.uint8)


def mascara_de_glifo(letra, caminho_fonte, tamanho_fonte=160):
    """Renderiza a letra numa fonte e devolve a mascara (tinta = 255)."""
    fonte = ImageFont.truetype(caminho_fonte, tamanho_fonte)
    img = Image.new("L", (tamanho_fonte * 2, tamanho_fonte * 2), 0)
    ImageDraw.Draw(img).text((tamanho_fonte // 2, tamanho_fonte // 4), letra,
                             fill=255, font=fonte)
    return np.where(np.array(img) > 127, 255, 0).astype(np.uint8)


def caixa_tinta(mascara):
    ys, xs = np.where(mascara > 0)
    if len(xs) == 0:
        return None
    return int(xs.min()), int(ys.min()), int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1)


def normalizar_mascara(mascara):
    """Recorta na caixa da tinta, enquadra num quadrado com margem e
    redimensiona para TAMANHO x TAMANHO. Mascara vazia -> zeros."""
    caixa = caixa_tinta(mascara)
    if caixa is None:
        return np.zeros((TAMANHO, TAMANHO), np.uint8)
    x, y, w, h = caixa
    recorte = mascara[y:y + h, x:x + w]
    lado = max(w, h)
    quadro = np.zeros((lado, lado), np.uint8)
    quadro[(lado - h) // 2:(lado - h) // 2 + h, (lado - w) // 2:(lado - w) // 2 + w] = recorte
    util = int(round(TAMANHO * (1 - 2 * MARGEM)))
    interp = cv2.INTER_AREA if lado > util else cv2.INTER_LINEAR
    miolo = cv2.resize(quadro, (util, util), interpolation=interp)
    saida = np.zeros((TAMANHO, TAMANHO), np.uint8)
    off = (TAMANHO - util) // 2
    saida[off:off + util, off:off + util] = miolo
    return np.where(saida > 127, 255, 0).astype(np.uint8)


def tensor_de_mascara(mascara_norm):
    t = torch.from_numpy(mascara_norm.astype(np.float32) / 255.0)
    t = t.unsqueeze(0).repeat(3, 1, 1)
    return (t - _MEDIA) / _DESVIO


def localizar_fonte(nome):
    """Caminho do .ttf de uma fonte: fc-match primeiro, glob como reserva."""
    try:
        saida = subprocess.run(["fc-match", "-f", "%{file}", nome],
                               capture_output=True, text=True, timeout=5).stdout.strip()
        # fc-match sempre devolve alguma fonte; so aceita se for a pedida
        if saida and os.path.basename(saida) == _ARQUIVOS_FONTE.get(nome, os.path.basename(saida)):
            return saida
    except (OSError, subprocess.SubprocessError):
        pass
    arquivo = _ARQUIVOS_FONTE.get(nome)
    if arquivo:
        achados = glob.glob(f"/usr/share/fonts/**/{arquivo}", recursive=True)
        if achados:
            return achados[0]
    return None
```

- [x] **Step 4: Rodar e confirmar que passa**

Run: `venv/bin/python test_letra_prep.py`
Expected: 6 linhas `ok`, exit 0.

- [x] **Step 5: Commit**

```bash
git add letra_prep.py test_letra_prep.py
git commit -m "Adiciona letra_prep: normalizacao de letras compartilhada entre treino e inferencia"
```

---

### Task 2: `formacao.py` — moldes e medidas geométricas

**Files:**
- Create: `formacao.py`
- Test: `test_formacao.py`

**Interfaces:**
- Consumes: `letra_prep.normalizar_mascara`, `mascara_de_glifo`, `localizar_fonte`, `caixa_tinta`, `FONTES_MOLDE`, `TAMANHO`
- Produces:
  - `moldes_da_letra(letra: str) -> list[np.ndarray]` — máscaras normalizadas, cache em memória
  - `medir_iou(mascara, molde) -> float` — melhor IoU com tolerância, sobre escalas/deslocamentos
  - `medir_proporcao(mascara, molde) -> float` (0–1)
  - `medir_inclinacao(mascara, molde) -> float` (0–1)
  - `medir_espessura(mascara) -> float` (0–1)
  - `avaliar_formacao(mascara_norm, letra) -> dict` com `formacao` (0–1) e `medidas` = `{"iou", "proporcao", "inclinacao", "espessura"}` (cada 0–1) e `pior` (nome da pior medida)
  - Constantes: `PESOS = {"iou": 0.45, "proporcao": 0.20, "inclinacao": 0.15, "espessura": 0.20}`, `IOU_BOM = 0.70`, `TOL_PIXELS = 3`

- [x] **Step 1: Escrever o teste que falha**

```python
# test_formacao.py
"""Testes das medidas geometricas (roda com: venv/bin/python test_formacao.py)."""
import numpy as np
import cv2
import letra_prep as lp
import formacao as fm


def _glifo(letra, fonte="DejaVu Sans"):
    return lp.normalizar_mascara(lp.mascara_de_glifo(letra, lp.localizar_fonte(fonte)))


def _cisalhar(mascara, graus):
    h, w = mascara.shape
    t = np.tan(np.radians(graus))
    M = np.float32([[1, t, -t * h / 2], [0, 1, 0]])
    return lp.normalizar_mascara(cv2.warpAffine(mascara, M, (w, h)))


def _rabisco():
    rng = np.random.default_rng(3)
    img = np.zeros((300, 300), np.uint8)
    pts = rng.integers(40, 260, size=(14, 2)).astype(np.int32)
    cv2.polylines(img, [pts], False, 255, 12)
    return lp.normalizar_mascara(img)


def test_moldes_existem():
    moldes = fm.moldes_da_letra("A")
    assert 1 <= len(moldes) <= 4 and all(m.shape == (lp.TAMANHO, lp.TAMANHO) for m in moldes)


def test_iou_mesma_fonte_alta_e_rabisco_baixa():
    a = _glifo("A")
    assert fm.medir_iou(a, a) > 0.95
    assert fm.medir_iou(_rabisco(), a) < 0.45


def test_inclinacao_penaliza_cisalhamento():
    a = _glifo("A")
    assert fm.medir_inclinacao(a, a) > 0.9
    assert fm.medir_inclinacao(_cisalhar(a, 25), a) < 0.5


def test_espessura_regular_vs_irregular():
    regular = np.zeros((200, 200), np.uint8)
    cv2.line(regular, (30, 170), (100, 30), 255, 14); cv2.line(regular, (100, 30), (170, 170), 255, 14)
    irregular = regular.copy()
    cv2.line(irregular, (60, 110), (140, 110), 255, 40)   # barra muito mais grossa
    cv2.line(irregular, (40, 150), (160, 150), 255, 3)    # e um fio fino
    assert fm.medir_espessura(lp.normalizar_mascara(regular)) > 0.8
    assert fm.medir_espessura(lp.normalizar_mascara(irregular)) < 0.6


def test_avaliar_formacao_ordena_casos():
    limpo = _glifo("A", "Noto Sans")           # fonte que tambem e molde: deve ficar alto
    torto = _cisalhar(_glifo("A"), 25)
    rab = _rabisco()
    n_limpo = fm.avaliar_formacao(limpo, "A")["formacao"]
    n_torto = fm.avaliar_formacao(torto, "A")["formacao"]
    n_rab = fm.avaliar_formacao(rab, "A")["formacao"]
    assert n_limpo > 0.85 > n_torto > n_rab
    r = fm.avaliar_formacao(torto, "A")
    assert set(r["medidas"]) == {"iou", "proporcao", "inclinacao", "espessura"}
    assert r["pior"] in ("iou", "inclinacao")


if __name__ == "__main__":
    import sys
    falhas = 0
    for nome, fn in list(globals().items()):
        if nome.startswith("test_") and callable(fn):
            try:
                fn(); print(f"ok    {nome}")
            except Exception as e:
                falhas += 1; print(f"FALHA {nome}: {e!r}")
    sys.exit(1 if falhas else 0)
```

- [x] **Step 2: Rodar e confirmar que falha**

Run: `venv/bin/python test_formacao.py`
Expected: `ModuleNotFoundError: No module named 'formacao'`

- [x] **Step 3: Implementar `formacao.py`**

```python
"""Parcela geometrica da nota: compara a letra desenhada com moldes de
letra de forma renderizados de fontes do sistema.

Quatro medidas, cada uma mapeada para 0..1 (1 = dentro do esperado):
  iou         sobreposicao com o melhor molde (com tolerancia de TOL_PIXELS)
  proporcao   razao altura/largura vs. a do molde
  inclinacao  angulo do eixo principal vs. o do molde
  espessura   regularidade da largura do traco (nao depende do molde)
"""

import math

import cv2
import numpy as np

import letra_prep as lp

PESOS = {"iou": 0.45, "proporcao": 0.20, "inclinacao": 0.15, "espessura": 0.20}
IOU_BOM = 0.70          # iou >= isso vale 1.0
TOL_PIXELS = 3          # tolerancia de alinhamento (dilatacao) em pixels
PROP_TOL, PROP_ZERO = 0.10, 0.50     # desvio relativo: <= TOL vale 1, >= ZERO vale 0
INCL_TOL, INCL_ZERO = 4.0, 20.0      # graus
ESP_TOL, ESP_ZERO = 0.25, 0.70       # coeficiente de variacao da espessura
ESCALAS = (0.9, 1.0, 1.1)
DESLOCS = (-4, 0, 4)

_cache_moldes = {}
_KERNEL_TOL = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * TOL_PIXELS + 1,) * 2)


def moldes_da_letra(letra):
    """Mascaras normalizadas da letra nas fontes disponiveis (cache)."""
    letra = letra.upper()
    if letra not in _cache_moldes:
        moldes = []
        for nome in lp.FONTES_MOLDE:
            caminho = lp.localizar_fonte(nome)
            if caminho:
                m = lp.normalizar_mascara(lp.mascara_de_glifo(letra, caminho))
                if m.any():
                    moldes.append(m)
        _cache_moldes[letra] = moldes
    return _cache_moldes[letra]


def _rampa(valor, bom, zero):
    """1.0 ate `bom`, cai linearmente ate 0.0 em `zero`."""
    if valor <= bom:
        return 1.0
    if valor >= zero:
        return 0.0
    return 1.0 - (valor - bom) / (zero - bom)


def _variantes(mascara):
    """Pequenos ajustes de escala/deslocamento para alinhar antes do IoU."""
    h, w = mascara.shape
    for esc in ESCALAS:
        M = cv2.getRotationMatrix2D((w / 2, h / 2), 0, esc)
        base = cv2.warpAffine(mascara, M, (w, h), flags=cv2.INTER_NEAREST)
        for dx in DESLOCS:
            for dy in DESLOCS:
                yield np.roll(np.roll(base, dy, axis=0), dx, axis=1)


def medir_iou(mascara, molde):
    molde_d = cv2.dilate(molde, _KERNEL_TOL)
    melhor = 0.0
    for v in _variantes(mascara):
        v_d = cv2.dilate(v, _KERNEL_TOL)
        inter = np.logical_and(v_d > 0, molde_d > 0).sum()
        uniao = np.logical_or(v_d > 0, molde_d > 0).sum()
        if uniao:
            melhor = max(melhor, inter / uniao)
    return float(melhor)


def _razao_hw(mascara):
    caixa = lp.caixa_tinta(mascara)
    if caixa is None:
        return None
    _, _, w, h = caixa
    return h / max(w, 1)


def medir_proporcao(mascara, molde):
    r_letra, r_molde = _razao_hw(mascara), _razao_hw(molde)
    if r_letra is None or r_molde is None:
        return 0.0
    return _rampa(abs(r_letra - r_molde) / r_molde, PROP_TOL, PROP_ZERO)


def _angulo_eixo(mascara):
    """Angulo (graus) do eixo principal da tinta e sua anisotropia (0..1)."""
    m = cv2.moments(mascara, binaryImage=True)
    if m["m00"] == 0:
        return 0.0, 0.0
    mu20, mu02, mu11 = m["mu20"] / m["m00"], m["mu02"] / m["m00"], m["mu11"] / m["m00"]
    ang = 0.5 * math.degrees(math.atan2(2 * mu11, mu20 - mu02))
    aniso = ((mu20 - mu02) ** 2 + 4 * mu11 ** 2) / max((mu20 + mu02) ** 2, 1e-9)
    return ang, aniso


def medir_inclinacao(mascara, molde):
    a_letra, aniso_letra = _angulo_eixo(mascara)
    a_molde, aniso_molde = _angulo_eixo(molde)
    if aniso_molde < 0.05:
        # letra quase isotropica no molde (O, X...): eixo nao e confiavel
        return 1.0
    desvio = abs(a_letra - a_molde)
    desvio = min(desvio, 180 - desvio)
    return _rampa(desvio, INCL_TOL, INCL_ZERO)


def medir_espessura(mascara):
    """Coeficiente de variacao da largura do traco ao longo da crista."""
    if not mascara.any():
        return 0.0
    dist = cv2.distanceTransform(mascara, cv2.DIST_L2, 5)
    crista = (dist > 0) & (dist >= cv2.dilate(dist, np.ones((3, 3), np.uint8)) - 1e-6)
    larguras = 2 * dist[crista]
    if larguras.size < 10:
        return 0.0
    cv = float(larguras.std() / max(larguras.mean(), 1e-6))
    return _rampa(cv, ESP_TOL, ESP_ZERO)


def avaliar_formacao(mascara_norm, letra):
    moldes = moldes_da_letra(letra)
    if not moldes or not mascara_norm.any():
        esp = medir_espessura(mascara_norm)
        return {"formacao": esp, "medidas": {"iou": 0.0, "proporcao": 0.0,
                                             "inclinacao": 0.0, "espessura": esp},
                "pior": "iou"}
    ious = [medir_iou(mascara_norm, m) for m in moldes]
    melhor = int(np.argmax(ious))
    molde = moldes[melhor]
    medidas = {
        "iou": min(1.0, ious[melhor] / IOU_BOM),
        "proporcao": medir_proporcao(mascara_norm, molde),
        "inclinacao": medir_inclinacao(mascara_norm, molde),
        "espessura": medir_espessura(mascara_norm),
    }
    formacao = sum(PESOS[k] * medidas[k] for k in PESOS)
    pior = min(medidas, key=lambda k: medidas[k])
    return {"formacao": float(formacao), "medidas": {k: float(v) for k, v in medidas.items()},
            "pior": pior}
```

- [x] **Step 4: Rodar e confirmar que passa**

Run: `venv/bin/python test_formacao.py`
Expected: 5 linhas `ok`. Se `test_espessura_regular_vs_irregular` ou `test_avaliar_formacao_ordena_casos` falhar por margem pequena, ajustar apenas as constantes `*_TOL/*_ZERO` (não a lógica) e anotar o valor final no commit.

- [x] **Step 5: Commit**

```bash
git add formacao.py test_formacao.py
git commit -m "Adiciona formacao.py: medidas geometricas contra moldes de letra de forma"
```

---

### Task 3: `train_cnn.py` — classificador de 26 letras com calibração

**Files:**
- Modify: `train_cnn.py` (reescrever inteiro)
- Delete: `diagnostico_variancia.py`

**Interfaces:**
- Consumes: `letra_prep.mascara_de_emnist`, `normalizar_mascara`, `tensor_de_mascara`, `TAMANHO`
- Produces: arquivo `modelo_caligrafia.pth` = `torch.save({"state_dict", "temperatura": float, "classes": "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "tamanho": 96, "acuracia_val": float})`
- Função `construir_modelo() -> nn.Module` (MobileNetV2 com 26 saídas) — reutilizada pelo avaliador

- [x] **Step 1: Escrever o teste de fumaça (dataset + augmentation) que falha**

Adicionar ao final de `test_letra_prep.py`, antes do `if __name__`:

```python
def test_dataset_emnist_augmentado():
    import train_cnn as tc
    ds = tc.DatasetLetras(treino=True, limite=64)
    x, y = ds[0]
    assert tuple(x.shape) == (3, lp.TAMANHO, lp.TAMANHO)
    assert 0 <= int(y) < 26
    assert len(ds) == 64
```

- [x] **Step 2: Rodar e confirmar que falha**

Run: `venv/bin/python test_letra_prep.py`
Expected: `FALHA test_dataset_emnist_augmentado: AttributeError ... 'DatasetLetras'` (ou ImportError)

- [x] **Step 3: Reescrever `train_cnn.py`**

```python
"""Treina a CNN de LEGIBILIDADE: MobileNetV2 (transfer learning) que
reconhece qual das 26 letras esta na imagem, usando o EMNIST-letters com
rotulos reais.

A qualidade da caligrafia NAO e rotulada aqui (o EMNIST nao tem isso). O
que a rede entrega ao avaliador e a probabilidade calibrada de a imagem ser
a letra-alvo; a parte de "formacao" fica em formacao.py, sem treino.

Augmentation fecha a diferenca entre o EMNIST (traco fino, 28x28) e as
letras reais (foto/quadro, traco grosso): dilatacao/erosao, rotacao,
escala, cisalhamento e translacao aleatorios.

Ao final ajusta uma temperatura no conjunto de validacao (calibracao) e
salva tudo em modelo_caligrafia.pth. Uso: venv/bin/python train_cnn.py
"""

import os
import random

import cv2
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset
from torchvision import datasets, models

import letra_prep as lp

_AQUI = os.path.dirname(os.path.abspath(__file__))
PASTA_DADOS = os.path.join(_AQUI, "data")
MODELO_PATH = os.path.join(_AQUI, "modelo_caligrafia.pth")
CLASSES = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
EPOCAS = 6
BATCH = 128


def augmentar(mascara, rng):
    """Deforma a mascara 28x28 do EMNIST para parecer uma letra real."""
    m = mascara
    # espessura: dilata (traco grosso, como caneta/quadro) ou afina
    k = rng.choice([0, 1, 1, 2, 3])
    if k:
        kernel = np.ones((k + 1, k + 1), np.uint8)
        m = cv2.dilate(m, kernel) if rng.random() < 0.8 else cv2.erode(m, kernel)
    # afim: rotacao, escala, cisalhamento, translacao
    h, w = m.shape
    ang = rng.uniform(-12, 12)
    esc = rng.uniform(0.85, 1.15)
    cis = np.tan(np.radians(rng.uniform(-8, 8)))
    M = cv2.getRotationMatrix2D((w / 2, h / 2), ang, esc)
    M[0, 1] += cis
    M[0, 2] += rng.uniform(-2, 2)
    M[1, 2] += rng.uniform(-2, 2)
    m = cv2.warpAffine(m, M, (w, h), flags=cv2.INTER_NEAREST, borderValue=0)
    return m


class DatasetLetras(Dataset):
    """EMNIST-letters -> mascara normalizada (96x96) + rotulo 0..25."""

    def __init__(self, treino, limite=None, semente=0):
        self.base = datasets.EMNIST(PASTA_DADOS, split="letters", train=treino, download=True)
        self.treino = treino
        self.indices = list(range(len(self.base)))
        if limite:
            random.Random(semente).shuffle(self.indices)
            self.indices = self.indices[:limite]
        self.rng = np.random.default_rng(semente)

    def __len__(self):
        return len(self.indices)

    def __getitem__(self, i):
        img, rotulo = self.base[self.indices[i]]
        m = lp.mascara_de_emnist(img)
        if self.treino:
            m = augmentar(m, self.rng)
        return lp.tensor_de_mascara(lp.normalizar_mascara(m)), int(rotulo) - 1


def construir_modelo(pretreinado=True):
    pesos = models.MobileNet_V2_Weights.DEFAULT if pretreinado else None
    modelo = models.mobilenet_v2(weights=pesos)
    modelo.classifier[1] = nn.Linear(modelo.last_channel, len(CLASSES))
    return modelo


def _avaliar(modelo, loader, device):
    modelo.eval()
    logits_todos, rotulos_todos = [], []
    with torch.no_grad():
        for x, y in loader:
            logits_todos.append(modelo(x.to(device)).cpu())
            rotulos_todos.append(y)
    logits = torch.cat(logits_todos)
    rotulos = torch.cat(rotulos_todos)
    acuracia = (logits.argmax(1) == rotulos).float().mean().item() * 100
    return logits, rotulos, acuracia


def calibrar_temperatura(logits, rotulos):
    """Escala os logits por 1/T minimizando a NLL (Guo et al., 2017)."""
    log_t = torch.zeros(1, requires_grad=True)
    otim = optim.LBFGS([log_t], lr=0.1, max_iter=100)
    criterio = nn.CrossEntropyLoss()

    def passo():
        otim.zero_grad()
        perda = criterio(logits / log_t.exp(), rotulos)
        perda.backward()
        return perda

    otim.step(passo)
    return float(log_t.exp().item())


def treinar():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Usando: {device}")
    ds_treino = DatasetLetras(treino=True)
    ds_val = DatasetLetras(treino=False)
    ld_treino = DataLoader(ds_treino, batch_size=BATCH, shuffle=True, num_workers=4, pin_memory=True)
    ld_val = DataLoader(ds_val, batch_size=256, num_workers=4)
    print(f"Treino: {len(ds_treino)} imagens | Validação: {len(ds_val)}")

    modelo = construir_modelo().to(device)
    criterio = nn.CrossEntropyLoss(label_smoothing=0.05)
    otim = optim.Adam([
        {"params": modelo.features.parameters(), "lr": 1e-4},
        {"params": modelo.classifier.parameters(), "lr": 1e-3},
    ])
    agenda = optim.lr_scheduler.CosineAnnealingLR(otim, T_max=EPOCAS)

    for epoca in range(EPOCAS):
        modelo.train()
        perda_total = 0.0
        for x, y in ld_treino:
            x, y = x.to(device, non_blocking=True), y.to(device, non_blocking=True)
            otim.zero_grad()
            perda = criterio(modelo(x), y)
            perda.backward()
            otim.step()
            perda_total += perda.item()
        agenda.step()
        _, _, acc = _avaliar(modelo, ld_val, device)
        print(f"Época {epoca + 1}/{EPOCAS} — perda {perda_total / len(ld_treino):.4f} — acurácia val {acc:.2f}%")

    logits, rotulos, acc = _avaliar(modelo, ld_val, device)
    temperatura = calibrar_temperatura(logits, rotulos)
    print(f"Acurácia final (EMNIST letters, validação): {acc:.2f}%")
    print(f"Temperatura de calibração: {temperatura:.3f}")
    torch.save({
        "state_dict": modelo.state_dict(),
        "temperatura": temperatura,
        "classes": CLASSES,
        "tamanho": lp.TAMANHO,
        "acuracia_val": acc,
    }, MODELO_PATH)
    print(f"Modelo salvo em {MODELO_PATH}")


if __name__ == "__main__":
    treinar()
```

- [x] **Step 4: Rodar o teste de fumaça**

Run: `venv/bin/python test_letra_prep.py`
Expected: todas `ok` (inclusive `test_dataset_emnist_augmentado`).

- [x] **Step 5: Treinar (GPU, ~20–40 min) em segundo plano e acompanhar**

Run: `venv/bin/python train_cnn.py 2>&1 | tee /tmp/treino.log`
Expected: acurácia de validação subindo por época; final ≥ 90 % (EMNIST letters costuma dar 93–95 %). Temperatura tipicamente entre 0,8 e 2,0. Se a GPU estourar memória (4 GB), reduzir `BATCH` para 64.

- [x] **Step 6: Remover o diagnóstico antigo e commitar**

```bash
git rm diagnostico_variancia.py
git add train_cnn.py test_letra_prep.py
git commit -m "train_cnn: classificador de 26 letras (EMNIST) com augmentation e calibracao de temperatura"
```

---

### Task 4: `handwriting_evaluator.py` — nota híbrida

**Files:**
- Modify: `handwriting_evaluator.py` (reescrever inteiro)
- Test: `test_avaliador.py`

**Interfaces:**
- Consumes: `letra_prep.mascara_de_recorte`, `normalizar_mascara`, `tensor_de_mascara`; `formacao.avaliar_formacao`; `train_cnn.construir_modelo`, `CLASSES`
- Produces:
  - `avaliar_texto(characters, alvos=None, batch_size=32) -> dict | None` (contrato na seção Global Constraints + chaves novas `nota`, `letra_prevista`, `legibilidade`, `formacao`, `medidas`, `pior_medida`)
  - `explicar_letra(r: dict) -> str` — frase curta: "está parecendo 'O'", "muito inclinada", "traço irregular", "proporção fora do molde", "pouco parecida com o molde"
  - `load_modelo()`, `formatar_feedback(av)`, `gerar_relatorio(texto, av)` (mantidos)
  - Constantes: `PESO_LEGIBILIDADE = 0.6`, `PESO_FORMACAO = 0.4`, `NOTA_BOA = 75`, `NOTA_ACEITAVEL = 50`

- [ ] **Step 1: Escrever o teste que falha**

```python
# test_avaliador.py
"""Testes ponta a ponta do avaliador com letras sinteticas.
Roda com: venv/bin/python test_avaliador.py  (precisa de modelo_caligrafia.pth)."""
import os
import sys
import numpy as np
import cv2
import letra_prep as lp
import handwriting_evaluator as he


def _recorte_de_mascara(m):
    """Mascara (tinta=255) -> recorte no formato do pipeline (fundo 255, tinta 0)."""
    return np.where(m > 0, 0, 255).astype(np.uint8)


def _char(mascara):
    h, w = mascara.shape
    return (0, 0, w, h, _recorte_de_mascara(mascara))


def _glifo(letra, fonte):
    return lp.mascara_de_glifo(letra, lp.localizar_fonte(fonte))


def _rabisco():
    rng = np.random.default_rng(3)
    img = np.zeros((300, 300), np.uint8)
    cv2.polylines(img, [rng.integers(40, 260, size=(14, 2)).astype(np.int32)], False, 255, 12)
    return img


def _a_arredondado():
    img = np.zeros((400, 400), np.uint8)
    cv2.ellipse(img, (200, 230), (120, 160), 0, 200, 340, 255, 18)
    cv2.line(img, (90, 330), (150, 60), 255, 16); cv2.line(img, (250, 60), (330, 340), 255, 16)
    cv2.line(img, (120, 260), (300, 240), 255, 14)
    return img


def _cisalhar(m, graus):
    h, w = m.shape
    t = np.tan(np.radians(graus))
    return cv2.warpAffine(m, np.float32([[1, t, -t * h / 2], [0, 1, 0]]), (w, h))


def _nota(mascara, alvo):
    return he.avaliar_texto([_char(mascara)], alvos=[alvo])["caracteres"][0]


def test_rabisco_e_ruim():
    assert _nota(_rabisco(), "A")["nota"] < 40


def test_a_limpo_e_bom():
    # DejaVu Sans Mono nao e molde: evita comparar a letra com ela mesma
    r = _nota(_glifo("A", "DejaVu Sans Mono") if lp.localizar_fonte("DejaVu Sans Mono") else _glifo("A", "Liberation Sans"), "A")
    assert r["nota"] >= 75 and r["categoria"] == "Boa"


def test_a_arredondado_cai():
    r = _nota(_a_arredondado(), "A")
    assert r["nota"] < 60
    assert r["pior_medida"] in ("iou", "inclinacao", "proporcao")


def test_a_inclinado():
    r = _nota(_cisalhar(_glifo("A", "Liberation Sans"), 25), "A")
    assert r["medidas"]["inclinacao"] < 0.5


def test_o_no_lugar_de_a():
    r = _nota(_glifo("O", "Liberation Sans"), "A")
    assert r["legibilidade"] < 0.4 and r["letra_prevista"] == "O"


def test_ordenacao():
    limpo = _nota(_glifo("A", "Liberation Sans"), "A")["nota"]
    arred = _nota(_a_arredondado(), "A")["nota"]
    rab = _nota(_rabisco(), "A")["nota"]
    assert limpo > arred > rab


def test_interface_compativel():
    av = he.avaliar_texto([_char(_glifo("A", "Liberation Sans")), _char(_rabisco())], alvos=["A", None])
    for k in ("pontuacao_geral", "total", "boas", "aceitaveis", "ruins"):
        assert k in av
    r = av["caracteres"][0]
    for k in ("indice", "posicao", "classe", "categoria", "confianca", "nota"):
        assert k in r
    assert av["pontuacao_geral"] == round(np.mean([c["nota"] for c in av["caracteres"]]), 1)
    assert he.avaliar_texto([]) is None


if __name__ == "__main__":
    if not os.path.exists(he.MODELO_PATH):
        print("modelo_caligrafia.pth nao existe: rode train_cnn.py primeiro"); sys.exit(2)
    falhas = 0
    for nome, fn in list(globals().items()):
        if nome.startswith("test_") and callable(fn):
            try:
                fn(); print(f"ok    {nome}")
            except Exception as e:
                falhas += 1; print(f"FALHA {nome}: {e!r}")
    sys.exit(1 if falhas else 0)
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `venv/bin/python test_avaliador.py`
Expected: falhas por `TypeError: avaliar_texto() got an unexpected keyword argument 'alvos'` / KeyError `nota`.

- [ ] **Step 3: Reescrever `handwriting_evaluator.py`**

```python
"""Avaliador hibrido de caligrafia.

Para cada letra recortada:
  legibilidade  = P(letra-alvo) da CNN (calibrada por temperatura),
                  penalizada pela probabilidade da segunda opcao
  formacao      = medidas geometricas contra moldes (formacao.py)
  nota          = 100 * (0.6 * legibilidade + 0.4 * formacao)
Categorias: Boa >= 75, Aceitavel >= 50, Ruim < 50.
"""

import os

import numpy as np
import torch

import letra_prep as lp
from formacao import avaliar_formacao
from train_cnn import construir_modelo, CLASSES

_AQUI = os.path.dirname(os.path.abspath(__file__))
MODELO_PATH = os.path.join(_AQUI, "modelo_caligrafia.pth")

PESO_LEGIBILIDADE = 0.6
PESO_FORMACAO = 0.4
NOTA_BOA = 75
NOTA_ACEITAVEL = 50
PENALIDADE_SEGUNDA = 0.5

CATEGORIAS = {0: "Ruim", 1: "Aceitável", 2: "Boa"}
_EXPLICACOES = {
    "iou": "pouco parecida com o molde",
    "proporcao": "proporção fora do molde (muito larga ou estreita)",
    "inclinacao": "muito inclinada",
    "espessura": "traço irregular",
}

modelo_cnn = None
temperatura = 1.0
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


def load_modelo():
    """Carrega a CNN de legibilidade e a temperatura de calibração."""
    global modelo_cnn, temperatura
    print("Carregando modelo de avaliação...")
    salvo = torch.load(MODELO_PATH, map_location=device)
    if not (isinstance(salvo, dict) and "state_dict" in salvo):
        raise RuntimeError(
            "modelo_caligrafia.pth está no formato antigo (3 classes). "
            "Rode 'python train_cnn.py' para treinar o avaliador novo."
        )
    modelo_cnn = construir_modelo(pretreinado=False)
    modelo_cnn.load_state_dict(salvo["state_dict"])
    modelo_cnn.to(device).eval()
    temperatura = float(salvo.get("temperatura", 1.0))
    print("Modelo de avaliação carregado!")


def _classe_para_nota(nota):
    if nota >= NOTA_BOA:
        return 2
    if nota >= NOTA_ACEITAVEL:
        return 1
    return 0


def _legibilidade(probs, alvo_idx):
    p_alvo = float(probs[alvo_idx])
    outros = probs.clone()
    outros[alvo_idx] = 0.0
    p_segunda = float(outros.max())
    return p_alvo * (1.0 - PENALIDADE_SEGUNDA * p_segunda)


def avaliar_texto(characters, alvos=None, batch_size=32):
    """Avalia as letras em lote. `alvos` e uma lista opcional de letras
    esperadas (A-Z ou None por posicao); sem alvo, usa a letra prevista."""
    if not characters:
        return None
    if modelo_cnn is None:
        load_modelo()
    if alvos is None:
        alvos = [None] * len(characters)

    mascaras = [lp.normalizar_mascara(lp.mascara_de_recorte(c[4])) for c in characters]
    tensores = torch.stack([lp.tensor_de_mascara(m) for m in mascaras])

    probs_todos = []
    with torch.no_grad():
        for i in range(0, len(tensores), batch_size):
            logits = modelo_cnn(tensores[i:i + batch_size].to(device))
            probs_todos.append(torch.softmax(logits / temperatura, dim=1).cpu())
    probs_todos = torch.cat(probs_todos)

    resultados = []
    for i, (x, y, w, h, _) in enumerate(characters):
        probs = probs_todos[i]
        prevista = CLASSES[int(probs.argmax())]
        alvo = (alvos[i] or "").upper()
        if alvo not in CLASSES:
            alvo = prevista
        legib = _legibilidade(probs, CLASSES.index(alvo))
        form = avaliar_formacao(mascaras[i], alvo)
        nota = 100.0 * (PESO_LEGIBILIDADE * legib + PESO_FORMACAO * form["formacao"])
        classe = _classe_para_nota(nota)
        resultados.append({
            "indice": i + 1,
            "posicao": (x, y, w, h),
            "nota": round(nota, 1),
            "classe": classe,
            "categoria": CATEGORIAS[classe],
            "confianca": round(legib, 3),
            "letra_alvo": alvo,
            "letra_prevista": prevista,
            "legibilidade": round(legib, 3),
            "formacao": round(form["formacao"], 3),
            "medidas": form["medidas"],
            "pior_medida": form["pior"],
        })

    return {
        "caracteres": resultados,
        "pontuacao_geral": round(float(np.mean([r["nota"] for r in resultados])), 1),
        "total": len(resultados),
        "boas": sum(1 for r in resultados if r["classe"] == 2),
        "aceitaveis": sum(1 for r in resultados if r["classe"] == 1),
        "ruins": sum(1 for r in resultados if r["classe"] == 0),
    }


def explicar_letra(r):
    """Frase curta dizendo o principal problema da letra."""
    if r["legibilidade"] < 0.4 and r["letra_prevista"] != r["letra_alvo"]:
        return f"está parecendo '{r['letra_prevista']}'"
    if r["legibilidade"] < 0.4:
        return "difícil de reconhecer"
    return _EXPLICACOES.get(r["pior_medida"], "formação irregular")


def formatar_feedback(avaliacao):
    """Feedback em texto simples para terminal e testes."""
    if avaliacao is None:
        return "Nenhum caractere detectado."
    linhas = [
        f"Pontuação geral: {avaliacao['pontuacao_geral']}/100",
        f"Caracteres analisados: {avaliacao['total']}",
        "-" * 32,
        f"Boa formação:     {avaliacao['boas']} letra(s)",
        f"Aceitável:        {avaliacao['aceitaveis']} letra(s)",
        f"Precisa melhorar: {avaliacao['ruins']} letra(s)",
    ]
    ruins = [r for r in avaliacao["caracteres"] if r["classe"] == 0]
    if ruins:
        linhas.append("-" * 32)
        linhas.append("Letras que precisam de atenção:")
        for r in ruins:
            linhas.append(f"  Letra {r['indice']} ({r['nota']:.0f}/100): {explicar_letra(r)}")
    return "\n".join(linhas)


def gerar_relatorio(texto, avaliacao):
    """Relatório completo em texto, pronto para salvar em arquivo."""
    linhas = ["=" * 48, "RELATÓRIO DE ANÁLISE DE CALIGRAFIA", "=" * 48, "",
              "TEXTO RECONHECIDO:", texto if texto else "(nenhum texto reconhecido)", "",
              formatar_feedback(avaliacao), ""]
    if avaliacao:
        linhas.append("DETALHE POR LETRA:")
        for r in avaliacao["caracteres"]:
            linhas.append(
                f"  Letra {r['indice']:>3}  {r['letra_alvo']}  {r['categoria']:<10}"
                f" nota {r['nota']:>5.1f}  legibilidade {r['legibilidade']:.0%}"
                f"  formação {r['formacao']:.0%}"
            )
    return "\n".join(linhas)
```

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `venv/bin/python test_avaliador.py`
Expected: 7 linhas `ok`. Se `test_a_arredondado_cai` ficar entre 60 e 65, é ajuste de constante em `formacao.py` (`IOU_BOM` ou pesos) — registrar o valor escolhido no commit. Se `test_o_no_lugar_de_a` falhar com legibilidade alta, o modelo está descalibrado: conferir a temperatura impressa no treino.

- [ ] **Step 5: Rodar também o experimento manual e a pré-carga**

Run: `venv/bin/python test_letra_prep.py && venv/bin/python test_formacao.py && venv/bin/python -c "import handwriting_evaluator"`
Expected: tudo `ok`; o import não pode falhar (a splash pré-carrega este módulo).

- [ ] **Step 6: Commit**

```bash
git add handwriting_evaluator.py test_avaliador.py
git commit -m "Avaliador hibrido: nota 0-100 = legibilidade (CNN calibrada) + formacao geometrica"
```

---

### Task 5: telas — alvos, validação do exercício e diálogo de detalhe

**Files:**
- Modify: `analise_widget.py:42-70` (AnaliseWorker.run)
- Modify: `praticar_widget.py:101-125` (VerificarWorker) e `praticar_widget.py:669-692` (`_validar`)
- Modify: `detalhe_letra_dialog.py:24-38` (construtor) e `detalhe_letra_dialog.py:113-131` (`_card_avaliacao`)
- Modify: `analise_widget.py:791-800` (criação do diálogo)

**Interfaces:**
- Consumes: `avaliar_texto(characters, alvos=...)`, `explicar_letra(r)`, chaves `nota`, `legibilidade`, `formacao`, `medidas`, `pior_medida`
- Produces: `DetalheLetraDialog(..., resultado=None)` — dict da letra (opcional) para exibir nota e medidas

- [ ] **Step 1: AnaliseWorker passa os alvos**

Em `analise_widget.py`, dentro de `AnaliseWorker.run`:

```python
            if self.motor == "google":
                from htr_google import predict_detailed
                texto, simbolos = predict_detailed(self.image_path)
                boxes = [(s["x"], s["y"], s["w"], s["h"]) for s in simbolos]
                characters = characters_from_boxes(self.image_path, boxes)
                avaliacao = avaliar_texto(characters, alvos=[s["letra"] for s in simbolos])
```

e no ramo TrOCR:

```python
                pil_word, characters = dados
                texto = predict(pil_word).strip().strip(".")
                letras_texto = [c for c in texto.upper() if "A" <= c <= "Z"]
                alvos = letras_texto if len(letras_texto) == len(characters) else None
                avaliacao = avaliar_texto(characters, alvos=alvos)
```

- [ ] **Step 2: VerificarWorker recebe e passa o alvo**

Em `praticar_widget.py`:

```python
class VerificarWorker(QThread):
    finished = pyqtSignal(str, object)
    error = pyqtSignal(str)

    def __init__(self, image_path, alvo="", apagar_ao_fim=False):
        super().__init__()
        self.image_path = image_path
        self.alvo = alvo
        # Quando a imagem e um PNG temporario do quadro, apaga apos usar
        # para nao acumular arquivos desenho_*.png em /tmp.
        self.apagar_ao_fim = apagar_ao_fim

    def run(self):
        try:
            from htr_google import predict_from_path
            texto = predict_from_path(self.image_path)
            _, characters, _ = process(self.image_path)
            alvos = list(self.alvo) if len(self.alvo) == len(characters) else None
            avaliacao = avaliar_texto(characters, alvos=alvos)
            self.finished.emit(texto, avaliacao)
```

Localizar as chamadas `VerificarWorker(` em `PainelExercicio` (`grep -n "VerificarWorker(" praticar_widget.py`) e acrescentar `alvo=self.alvo_atual()` — onde `alvo_atual()` é o método/atributo que já dá a letra ou palavra corrente do painel (conferir nome real em `mostrar_alvo_atual`; se for atributo `self.alvo`, usar ele).

- [ ] **Step 3: `_validar` usa a nota**

Substituir o corpo de `_validar` em `PainelExercicio`:

```python
    def _validar(self, alvo, texto, avaliacao):
        from handwriting_evaluator import explicar_letra
        limpo = "".join(c for c in (texto or "").upper() if c.isalpha())
        if self.modo == "letra":
            if not limpo:
                return False, "Não consegui identificar nenhuma letra. Tente outra foto."
            if limpo[0] != alvo:
                return False, f"O sistema reconheceu '{limpo[0]}', mas o alvo era '{alvo}'."
            if not avaliacao or avaliacao["total"] == 0:
                return False, "Não consegui detectar o traço. Tente uma foto mais clara."
            r = avaliacao["caracteres"][0]
            if r["nota"] < NOTA_MINIMA_LETRA:
                return False, (f"Reconheci o '{alvo}', mas a letra está {explicar_letra(r)} "
                               f"(nota {r['nota']:.0f}/100). Tente de novo.")
            return True, ""
        else:
            if limpo != alvo:
                return False, f"Reconhecido: '{texto.strip() if texto else '(nada)'}'. Esperado: '{alvo}'."
            if not avaliacao or avaliacao["total"] == 0:
                return False, "Não consegui detectar as letras. Tente uma foto mais clara."
            notas = [c["nota"] for c in avaliacao["caracteres"]]
            if avaliacao["pontuacao_geral"] < NOTA_MINIMA_LETRA or min(notas) < NOTA_MINIMA_PIOR:
                pior = min(avaliacao["caracteres"], key=lambda c: c["nota"])
                return False, (f"Palavra correta, mas a letra '{pior['letra_alvo']}' está "
                               f"{explicar_letra(pior)} (nota {pior['nota']:.0f}/100).")
            return True, ""
```

e no topo do arquivo, junto das outras constantes (perto de `FONTE_FORMA`):

```python
NOTA_MINIMA_LETRA = 60   # nota minima para o exercicio contar como acerto
NOTA_MINIMA_PIOR = 40    # numa palavra, nenhuma letra pode ficar abaixo disto
```

- [ ] **Step 4: Diálogo de detalhe mostra nota e medidas**

Em `detalhe_letra_dialog.py`, construtor: acrescentar parâmetro `resultado=None` após `modo_adicao_manual=False` e guardar `self.resultado = resultado`. Substituir `_card_avaliacao`:

```python
    def _card_avaliacao(self):
        card, lay = self._make_card("AVALIAÇÃO DA CALIGRAFIA")
        cores = {0: C_BAD, 1: C_OK, 2: C_GOOD}
        cor = cores.get(self.classe, C_MUTED)
        linha = QHBoxLayout()
        lbl_categoria = QLabel(self.categoria or "-")
        lbl_categoria.setStyleSheet(
            f"color: {cor}; font-size: 20px; font-weight: 800;"
            f" border: none; background: transparent;"
        )
        linha.addWidget(lbl_categoria)
        linha.addStretch()
        r = self.resultado
        texto_dir = f"nota {r['nota']:.0f}/100" if r else f"{self.confianca:.0%} de confiança"
        lbl_conf = QLabel(texto_dir)
        lbl_conf.setStyleSheet(f"color: {C_MUTED}; font-size: 12px; border: none;")
        linha.addWidget(lbl_conf)
        lay.addLayout(linha)

        if r:
            from handwriting_evaluator import explicar_letra
            itens = [("Legibilidade", r["legibilidade"]), ("Formação", r["formacao"])]
            nomes = {"iou": "Semelhança com o molde", "proporcao": "Proporção",
                     "inclinacao": "Inclinação", "espessura": "Regularidade do traço"}
            itens += [(nomes[k], v) for k, v in r["medidas"].items()]
            for nome, valor in itens:
                lay.addWidget(self._barra_medida(nome, valor))
            if r["classe"] < 2:
                dica = QLabel(f"Principal ponto: {explicar_letra(r)}.")
                dica.setWordWrap(True)
                dica.setStyleSheet(f"color: {C_MUTED}; font-size: 12px; border: none;")
                lay.addWidget(dica)
        return card

    def _barra_medida(self, nome, valor):
        from PyQt5.QtWidgets import QProgressBar
        wrap = QWidget()
        wrap.setObjectName("transparente")
        lay = QHBoxLayout(wrap)
        lay.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel(nome)
        lbl.setFixedWidth(170)
        lbl.setStyleSheet(f"color: {C_TEXT}; font-size: 12px; border: none;")
        barra = QProgressBar()
        barra.setRange(0, 100)
        barra.setValue(int(round(valor * 100)))
        barra.setTextVisible(False)
        barra.setFixedHeight(8)
        cor = C_GOOD if valor >= 0.75 else C_OK if valor >= 0.5 else C_BAD
        barra.setStyleSheet(f"QProgressBar::chunk {{ background-color: {cor}; border-radius: 3px; }}")
        lay.addWidget(lbl)
        lay.addWidget(barra, 1)
        return wrap
```

(Conferir que `QWidget` está importado em `detalhe_letra_dialog.py`; se não, acrescentar ao import de `PyQt5.QtWidgets`.) O diálogo tem `setFixedSize(440, 620)`: subir para `(440, 760)` para caber as 6 barras.

Em `analise_widget.py`, na criação do diálogo de letra detectada (linha ~791), acrescentar `resultado=r,`.

- [ ] **Step 5: Verificar com o script de captura e o app real**

Run: `venv/bin/python -c "import analise_widget, praticar_widget, detalhe_letra_dialog; print('imports ok')"` (offscreen: `QT_QPA_PLATFORM=offscreen`)
Expected: `imports ok`.
Depois abrir o app (`scratchpad/abrir_app.sh`), desenhar um A bem feito e um A arredondado no exercício da letra A e observar: o bom passa, o arredondado recebe mensagem com a nota e o motivo. Na Análise, a pontuação geral deixa de ser 100.

- [ ] **Step 6: Commit**

```bash
git add analise_widget.py praticar_widget.py detalhe_letra_dialog.py
git commit -m "Telas usam a nota do avaliador: alvos por letra, criterio do exercicio e detalhe com medidas"
```

---

### Task 6: documentação

**Files:**
- Modify: `Readme.md` (seções "Recursos", "Como funciona a análise", "Retreinar o modelo", "Limitações conhecidas", "Estrutura do projeto")

- [ ] **Step 1: Atualizar o Readme**

Trocar, em "Recursos": `- Avaliação da qualidade de cada letra por uma rede neural (CNN MobileNetV2)` por
`- Avaliação de cada letra com nota 0–100: legibilidade (CNN MobileNetV2 treinada no EMNIST, calibrada) combinada com formação geométrica contra moldes de letra de forma (sobreposição, proporção, inclinação, regularidade do traço)`.

Em "Retreinar o modelo de avaliação": substituir o parágrafo por
```
Baixa o dataset EMNIST (split *letters*, 26 classes) e treina a CNN de legibilidade com augmentation de espessura/rotação/cisalhamento. Ao final calibra a confiança (temperatura) e imprime a acurácia de validação. O modelo é salvo em `modelo_caligrafia.pth`.
```
e remover o bloco de `diagnostico_variancia.py`.

Em "Limitações conhecidas": substituir o item da variância por
`- A parcela de formação compara com moldes de fontes de letra de forma; estilos pessoais válidos podem perder pontos. Os pesos e limiares ficam em constantes no topo de `formacao.py` e `handwriting_evaluator.py`.`

Em "Estrutura do projeto": acrescentar `letra_prep.py  # normalização de letras (treino e inferência)` e `formacao.py  # medidas geométricas contra moldes`, remover `diagnostico_variancia.py`, e acrescentar os três `test_*.py`.

- [ ] **Step 2: Commit**

```bash
git add Readme.md
git commit -m "Readme: descreve o avaliador hibrido e remove o diagnostico de variancia"
```

---

## Self-review

- **Cobertura do spec:** normalização (T1), moldes e 4 medidas com pesos (T2), CNN 26 classes + augmentation + temperatura + arquivo salvo (T3), legibilidade com penalidade da segunda opção, nota, categorias, agregados, chaves compatíveis, `explicar_letra` (T4), alvos em Análise (Google e TrOCR) e exercício, `_validar` com 60/40, diálogo com medidas, relatório com nota (T4/T5), remoção do diagnóstico e Readme (T3/T6), testes 1–7 do spec (T2/T4).
- **Consistência de nomes:** `avaliar_formacao` devolve `formacao/medidas/pior`; o avaliador expõe `pior_medida` e `medidas`; o diálogo e `_validar` leem exatamente essas chaves. `construir_modelo(pretreinado=...)` é usado no treino e no carregamento. `NOTA_MINIMA_LETRA/NOTA_MINIMA_PIOR` só existem em `praticar_widget.py`.
- **Ponto a conferir na execução:** o nome do atributo do alvo corrente em `PainelExercicio` (Task 5, passo 2) — o plano manda verificar com grep antes de editar.
