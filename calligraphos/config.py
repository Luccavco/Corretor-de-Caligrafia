"""Configuracao do Calligraphos lida de config.json (na pasta do projeto).

Os valores abaixo sao os padroes; o config.json sobrescreve o que definir.
Assim os limiares da nota, os pesos das medidas e o motor de HTR padrao
podem ser ajustados sem mexer no codigo (ex.: deixar o exercicio mais
tolerante para criancas em alfabetizacao)."""

import copy
import json
import logging
import os

log = logging.getLogger(__name__)
from calligraphos.caminhos import CONFIG as CAMINHO_CONFIG

PADRAO = {
    "motor_htr_padrao": "google",
    "avaliador": {
        "nota_boa": 75,
        "nota_aceitavel": 50,
        "expoente_legibilidade": 0.5,
        "expoente_formacao": 1.25,
        "penalidade_segunda_opcao": 0.5,
    },
    "exercicio": {
        "nota_minima_letra": 65,
        "nota_minima_pior_letra_palavra": 40,
    },
    "formacao": {
        "pesos": {"iou": 0.40, "tracos": 0.20, "proporcao": 0.15, "inclinacao": 0.10, "espessura": 0.15},
        "semelhanca_zero": 0.45, "semelhanca_boa": 0.85,
        "tracos_zero": 0.35, "tracos_bom": 0.90,
        "proporcao_tolerancia": 0.20, "proporcao_zero": 1.00,
        "inclinacao_tolerancia_graus": 4.0, "inclinacao_zero_graus": 20.0,
        "espessura_tolerancia": 0.25, "espessura_zero": 0.70,
    },
}


def _mesclar(base, extra):
    for k, v in extra.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _mesclar(base[k], v)
        else:
            base[k] = v
    return base


def carregar():
    cfg = copy.deepcopy(PADRAO)
    try:
        with open(CAMINHO_CONFIG, encoding="utf-8") as f:
            _mesclar(cfg, json.load(f))
    except FileNotFoundError:
        pass
    except (OSError, ValueError) as e:
        log.warning("config.json ignorado (%s); usando os padrões", e)
    return cfg


CONFIG = carregar()
