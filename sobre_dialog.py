"""Tela "Sobre": o que o sistema faz, como a nota e calculada, metricas do
modelo em uso e as tecnologias. As metricas vem do proprio arquivo do
modelo (acuracia de validacao e temperatura salvas pelo train_cnn.py)."""

import os

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QWidget,
)
from PyQt5.QtCore import Qt

from ui_theme import C_BG, C_TEXT, C_MUTED, C_ACCENT, make_card, stat_chip, C_GOOD, C_OK, C_BAD
from ui_helpers import FlowLayout
from config import CONFIG

VERSAO = "1.0"
GITHUB_URL = "https://github.com/Luccavco/Corretor-de-Caligrafia"


def _metricas_modelo():
    """Le acuracia/temperatura gravadas no modelo, sem carregar a rede na GPU."""
    try:
        import torch
        from handwriting_evaluator import MODELO_PATH
        salvo = torch.load(MODELO_PATH, map_location="cpu")
        if isinstance(salvo, dict) and "state_dict" in salvo:
            return {
                "acuracia": salvo.get("acuracia_val"),
                "temperatura": salvo.get("temperatura"),
                "classes": len(salvo.get("classes", "")),
                "tamanho": salvo.get("tamanho"),
                "arquivo": os.path.basename(MODELO_PATH),
            }
    except Exception:
        pass
    return None


def _versoes():
    itens = []
    for nome, modulo in (("PyQt5", "PyQt5.QtCore"), ("OpenCV", "cv2"), ("PyTorch", "torch"),
                         ("torchvision", "torchvision"), ("Transformers", "transformers")):
        try:
            m = __import__(modulo, fromlist=["x"])
            v = getattr(m, "__version__", None) or getattr(m, "QT_VERSION_STR", "?")
            itens.append(f"{nome} {v}")
        except Exception:
            continue
    return itens


class SobreDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sobre o Calligraphos")
        self.setMinimumSize(640, 560)
        self.resize(680, 640)
        self.setStyleSheet(f"QDialog {{ background-color: {C_BG}; }}")
        self._montar()

    def _texto(self, html, tamanho=13, cor=None):
        lbl = QLabel(html)
        lbl.setWordWrap(True)
        lbl.setOpenExternalLinks(True)
        lbl.setTextInteractionFlags(Qt.TextBrowserInteraction)
        lbl.setStyleSheet(f"color: {cor or C_TEXT}; font-size: {tamanho}px; border: none; line-height: 1.5;")
        return lbl

    def _montar(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 16)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.viewport().setStyleSheet("background: transparent;")
        conteudo = QWidget()
        conteudo.setObjectName("transparente")
        lay = QVBoxLayout(conteudo)
        lay.setContentsMargins(0, 0, 8, 0)
        lay.setSpacing(12)

        linha_titulo = QHBoxLayout()
        titulo = QLabel("Calligraphos")
        titulo.setStyleSheet(
            f"color: {C_TEXT}; font-size: 30px; font-weight: 800;"
            f" font-family: 'Cambria', 'Georgia', serif; border: none;"
        )
        titulo.setMinimumHeight(44)
        versao = QLabel(f"v{VERSAO}")
        versao.setStyleSheet(f"color: {C_MUTED}; font-size: 14px; border: none; padding-top: 12px;")
        linha_titulo.addWidget(titulo)
        linha_titulo.addSpacing(8)
        linha_titulo.addWidget(versao)
        linha_titulo.addStretch()
        lay.addLayout(linha_titulo)
        lay.addWidget(self._texto(
            "Sistema de reconhecimento e avaliação de caligrafia em letra de forma, "
            "desenvolvido como Trabalho de Conclusão de Curso. Transcreve o que foi "
            "escrito à mão e dá uma nota a cada letra, apontando o que melhorar.",
            cor=C_MUTED))

        # ── Como funciona ──
        card, cl = make_card(None, "COMO A NOTA É CALCULADA")
        cfg = CONFIG["avaliador"]
        cl.addWidget(self._texto(
            "Cada letra recortada passa por dois julgamentos independentes:<br>"
            "<b>Legibilidade</b> — uma rede neural (MobileNetV2, transfer learning) treinada "
            "para reconhecer as 26 letras diz o quanto a imagem parece a letra esperada; "
            "a confiança é calibrada por temperatura.<br>"
            "<b>Formação</b> — cinco medidas geométricas comparam a letra com moldes de "
            "letra de forma: semelhança de forma, direção dos traços, proporção, inclinação "
            "e regularidade da espessura.<br><br>"
            f"<code>nota = 100 · legibilidade<sup>{cfg['expoente_legibilidade']}</sup> · "
            f"formação<sup>{cfg['expoente_formacao']}</sup></code> — "
            f"Boa ≥ {cfg['nota_boa']} · Aceitável ≥ {cfg['nota_aceitavel']} · Ruim abaixo disso. "
            f"No exercício, a letra conta como acerto com nota ≥ {CONFIG['exercicio']['nota_minima_letra']}."
        ))
        lay.addWidget(card)

        # ── Metricas ──
        card, cl = make_card(None, "MODELO EM USO")
        m = _metricas_modelo()
        chips_wrap = QWidget()
        chips_wrap.setObjectName("transparente")
        chips = FlowLayout(chips_wrap, espacamento=8, centralizar=False)
        if m and m["acuracia"] is not None:
            chips.addWidget(stat_chip(C_GOOD, f"acurácia {m['acuracia']:.1f}% (EMNIST letters, validação)"))
            chips.addWidget(stat_chip(C_ACCENT, f"{m['classes']} classes · {m['tamanho']}×{m['tamanho']} px"))
            chips.addWidget(stat_chip(C_OK, f"temperatura {m['temperatura']:.2f}"))
        else:
            chips.addWidget(stat_chip(C_BAD, "modelo não encontrado — rode train_cnn.py"))
        cl.addWidget(chips_wrap)
        cl.addWidget(self._texto(
            "Treinado com 124.800 imagens do EMNIST (split <i>letters</i>) com augmentation de "
            "espessura, rotação, escala, cisalhamento e largura, para aproximar o dataset das "
            "letras reais de foto e do quadro. Validado em 20.800 imagens.",
            tamanho=12, cor=C_MUTED))
        lay.addWidget(card)

        # ── Pipeline ──
        card, cl = make_card(None, "PIPELINE")
        cl.addWidget(self._texto(
            "1. <b>Pré-processamento</b> (OpenCV): binarização adaptativa, remoção de linhas de "
            "pauta, correção de inclinação, detecção de linhas de texto e segmentação de letras "
            "(com fusão de fragmentos e separação de letras encostadas).<br>"
            "2. <b>Transcrição</b>: Google Cloud Vision (principal, online) ou TrOCR (offline, "
            "palavra única). Sem internet, o exercício usa a própria CNN.<br>"
            "3. <b>Avaliação</b>: legibilidade + formação → nota por letra e mapa de diferenças "
            "contra o molde.<br>"
            "4. <b>Progresso</b>: níveis por letra, histórico de notas e conquistas sincronizados "
            "no Firebase entre o aplicativo e o site."
        ))
        lay.addWidget(card)

        # ── Tecnologias ──
        card, cl = make_card(None, "TECNOLOGIAS")
        cl.addWidget(self._texto("Python 3.11 · " + " · ".join(_versoes()) + " · Firebase · React + Vite (site)",
                                 tamanho=12, cor=C_MUTED))
        cl.addWidget(self._texto(
            f"<b>Desenvolvido por:</b> Lucca Vasconcelos Costa &nbsp;·&nbsp; "
            f"<a href='{GITHUB_URL}' style='color:{C_ACCENT}'>código-fonte no GitHub</a>",
            tamanho=12))
        lay.addWidget(card)
        lay.addStretch()

        scroll.setWidget(conteudo)
        root.addWidget(scroll, 1)

        rodape = QHBoxLayout()
        rodape.addStretch()
        btn = QPushButton("Fechar")
        btn.setObjectName("primary")
        btn.clicked.connect(self.accept)
        rodape.addWidget(btn)
        root.addLayout(rodape)
