"""Testes do servico HTTP (roda com: venv/bin/python tests/test_api.py).
Usa o TestClient do FastAPI (sem subir servidor); precisa do modelo treinado."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2
import numpy as np
from fastapi.testclient import TestClient

from calligraphos.nucleo import letra_prep as lp
from calligraphos.nucleo import handwriting_evaluator as he
from calligraphos.api import app

cliente = TestClient(app)


def _png_de_mascara(m):
    ok, buf = cv2.imencode(".png", np.where(m > 0, 0, 255).astype(np.uint8))
    return buf.tobytes()


def _glifo(letra):
    return lp.mascara_de_glifo(letra, lp.localizar_fonte("Liberation Sans"))


def test_saude():
    r = cliente.get("/saude")
    assert r.status_code == 200 and r.json()["ok"] and r.json()["modelo_presente"]


def test_avaliar_letra_limpa():
    r = cliente.post("/avaliar", files={"imagem": ("a.png", _png_de_mascara(_glifo("A")), "image/png")},
                     data={"alvo": "A", "incluir_imagens": "true"})
    assert r.status_code == 200, r.text
    j = r.json()
    assert len(j["letras"]) == 1 and j["letras"][0]["nota"] >= 75 and j["letras"][0]["prevista"] == "A"
    assert j["mapa_diferencas_png"] and j["imagem_anotada_png"]
    assert j["motor"] in ("google", "cnn", "trocr")


def test_sem_imagens():
    r = cliente.post("/avaliar", files={"imagem": ("a.png", _png_de_mascara(_glifo("B")), "image/png")},
                     data={"alvo": "B", "incluir_imagens": "false"})
    assert r.status_code == 200 and "mapa_diferencas_png" not in r.json()


def test_imagem_vazia():
    r = cliente.post("/avaliar", files={"imagem": ("x.png", b"", "image/png")})
    assert r.status_code == 400


def test_imagem_invalida():
    r = cliente.post("/avaliar", files={"imagem": ("x.png", b"isso nao e png", "image/png")})
    assert r.status_code == 400


if __name__ == "__main__":
    if not os.path.exists(he.MODELO_PATH):
        print("modelo_caligrafia.pth nao existe: rode train_cnn primeiro"); sys.exit(2)
    falhas = 0
    for nome, fn in list(globals().items()):
        if nome.startswith("test_") and callable(fn):
            try:
                fn(); print(f"ok    {nome}")
            except Exception as e:
                falhas += 1; print(f"FALHA {nome}: {e!r}")
    sys.exit(1 if falhas else 0)
