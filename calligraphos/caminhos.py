"""Caminhos dos arquivos que ficam na RAIZ do projeto (fora do pacote):
modelo treinado, config.json, credenciais, sessao, log, icone e dados.
Centralizados aqui para nenhum modulo depender da propria localizacao."""

import os

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MODELO = os.path.join(RAIZ, "modelo_caligrafia.pth")
CONFIG = os.path.join(RAIZ, "config.json")
LOG = os.path.join(RAIZ, "calligraphos.log")
SESSAO = os.path.join(RAIZ, "sessao.json")
CREDENCIAIS_GOOGLE = os.path.join(RAIZ, "google_credentials.json")
CREDENCIAIS_FIREBASE = os.path.join(RAIZ, "firebase_credentials.json")
ICONE = os.path.join(RAIZ, "calligraphos.png")
DADOS = os.path.join(RAIZ, "data")
