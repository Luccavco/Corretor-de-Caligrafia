"""Configuracao unica de logging do Calligraphos.

Grava em calligraphos.log (rotativo, na pasta do projeto) e no terminal.
Cada modulo usa `log = logging.getLogger(__name__)`; erros que antes eram
silenciados (Firestore fora do ar, sessao ilegivel) ficam registrados aqui
para diagnostico sem poluir a interface."""

import logging
import os
from logging.handlers import RotatingFileHandler

from calligraphos.caminhos import LOG as CAMINHO_LOG
_configurado = False


def configurar(nivel=logging.INFO):
    global _configurado
    if _configurado:
        return
    _configurado = True
    raiz = logging.getLogger()
    raiz.setLevel(nivel)
    formato = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s", "%Y-%m-%d %H:%M:%S")
    try:
        arquivo = RotatingFileHandler(CAMINHO_LOG, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
        arquivo.setFormatter(formato)
        raiz.addHandler(arquivo)
    except OSError:
        pass
    terminal = logging.StreamHandler()
    terminal.setFormatter(formato)
    terminal.setLevel(logging.WARNING)
    raiz.addHandler(terminal)
    # Bibliotecas tagarelas
    for nome in ("urllib3", "google", "firebase_admin", "PIL", "transformers", "torch"):
        logging.getLogger(nome).setLevel(logging.WARNING)
