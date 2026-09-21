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
    assert fm.medir_iou(_rabisco(), a) < 0.65


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
    # a forma sozinha nao distingue bem "A torto" de rabisco (isso e papel
    # da legibilidade); o que ela precisa garantir e que ambos fiquem longe
    # do A limpo
    assert n_limpo > 0.85, n_limpo
    assert n_torto < 0.65 and n_rab < 0.65, (n_torto, n_rab)
    r = fm.avaliar_formacao(torto, "A")
    assert set(r["medidas"]) == {"iou", "proporcao", "inclinacao", "espessura"}
    assert r["pior"] in ("iou", "inclinacao"), r


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
