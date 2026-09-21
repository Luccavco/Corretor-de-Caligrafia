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
    r = _nota(_rabisco(), "A")
    assert r["nota"] < 40, r


def test_a_limpo_e_bom():
    # DejaVu Sans Mono nao e molde: evita comparar a letra com ela mesma
    fonte = "DejaVu Sans Mono" if lp.localizar_fonte("DejaVu Sans Mono") else "Liberation Sans"
    r = _nota(_glifo("A", fonte), "A")
    assert r["nota"] >= 75 and r["categoria"] == "Boa", r


def test_a_arredondado_cai():
    # abaixo da nota minima do exercicio (65): reconhecido como A, mas
    # com topo em arco e pernas abertas
    r = _nota(_a_arredondado(), "A")
    assert r["nota"] < 65, r
    assert r["pior_medida"] in ("iou", "tracos", "inclinacao", "proporcao"), r


def test_a_inclinado():
    r = _nota(_cisalhar(_glifo("A", "Liberation Sans"), 25), "A")
    assert r["medidas"]["inclinacao"] < 0.5, r


def test_o_no_lugar_de_a():
    r = _nota(_glifo("O", "Liberation Sans"), "A")
    assert r["legibilidade"] < 0.4 and r["letra_prevista"] == "O", r


def test_ordenacao():
    limpo = _nota(_glifo("A", "Liberation Sans"), "A")["nota"]
    arred = _nota(_a_arredondado(), "A")["nota"]
    rab = _nota(_rabisco(), "A")["nota"]
    assert limpo > arred > rab, (limpo, arred, rab)


def test_interface_compativel():
    av = he.avaliar_texto([_char(_glifo("A", "Liberation Sans")), _char(_rabisco())], alvos=["A", None])
    for k in ("pontuacao_geral", "total", "boas", "aceitaveis", "ruins"):
        assert k in av
    r = av["caracteres"][0]
    for k in ("indice", "posicao", "classe", "categoria", "confianca", "nota"):
        assert k in r
    assert av["pontuacao_geral"] == round(float(np.mean([c["nota"] for c in av["caracteres"]])), 1)
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
