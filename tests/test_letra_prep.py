"""Testes da normalizacao de letras (roda com: venv/bin/python tests/test_letra_prep.py)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from calligraphos.nucleo import letra_prep as lp
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


def test_dataset_emnist_augmentado():
    import os
    if os.environ.get("CI") and not os.path.isdir(os.path.join("data", "EMNIST")):
        print("      (pulado: EMNIST não está disponível no CI)")
        return
    from calligraphos.nucleo import train_cnn as tc
    ds = tc.DatasetLetras(treino=True, limite=64)
    x, y = ds[0]
    assert tuple(x.shape) == (3, lp.TAMANHO, lp.TAMANHO)
    assert 0 <= int(y) < 26
    assert len(ds) == 64


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
