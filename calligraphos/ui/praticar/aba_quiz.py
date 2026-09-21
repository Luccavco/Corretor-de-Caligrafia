"""Aba Quiz: escolha entre quiz de letras e quiz de palavras."""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea
from PyQt5.QtCore import pyqtSignal
from calligraphos.ui.ui_helpers import limpar_layout, cabecalho_aba
from calligraphos.ui.ui_theme import C_MUTED
from calligraphos.ui.praticar.cartoes import QuizCard
from calligraphos.ui.praticar.constantes import LETRAS


class AbaQuiz(QWidget):
    """Aba de quiz: a pessoa e questionada aleatoriamente sobre como se
    escreve uma letra do alfabeto ou uma das palavras que cadastrou."""
    quiz_selecionado = pyqtSignal(str)   # "letras" ou "palavras"

    def __init__(self, estado):
        super().__init__()
        self.estado = estado
        self._layout_raiz = QVBoxLayout(self)
        self._layout_raiz.setContentsMargins(20, 20, 20, 20)
        self._layout_raiz.setSpacing(14)
        self._construir()

    def _limpar(self):
        limpar_layout(self._layout_raiz)

    def _construir(self):
        # Cabecalho padronizado (mesma estrutura das outras abas)
        self._layout_raiz.addWidget(
            cabecalho_aba("Quiz de Caligrafia", "escolha um tipo e pratique com itens sorteados")
        )

        # Linha de instrucao (equivalente a barra de progresso das outras
        # abas), com texto bem visivel
        instrucao_row = QHBoxLayout()
        instrucao_row.setContentsMargins(0, 0, 0, 0)
        lbl_instrucao = QLabel(
            "Os itens sao sorteados aleatoriamente a cada quiz"
        )
        lbl_instrucao.setStyleSheet(f"color: {C_MUTED}; font-size: 17px;")
        instrucao_row.addWidget(lbl_instrucao)
        instrucao_row.addStretch()
        instrucao_wrap = QWidget()
        instrucao_wrap.setMinimumHeight(40)
        instrucao_wrap.setLayout(instrucao_row)
        self._layout_raiz.addWidget(instrucao_wrap)

        self._layout_raiz.addSpacing(16)

        # Conteudo com rolagem: garante que nada fica cortado, mesmo em
        # telas menores
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background: transparent;")
        container = QWidget()
        container.setObjectName("transparente")
        conteudo = QVBoxLayout(container)
        conteudo.setContentsMargins(0, 0, 8, 0)

        # Stretch antes E depois dos cards -> centralizados verticalmente
        # no espaco disponivel (nao mais colados ao topo)
        conteudo.addStretch(1)

        # Cards de escolha, centralizados e grandes
        cards_wrap = QHBoxLayout()
        cards_wrap.setSpacing(32)
        cards_wrap.addStretch()

        card_letras = QuizCard(
            "letras", "ABC", "Quiz de Letras",
            "Sorteia letras do alfabeto para você escrever.",
            len(LETRAS), disponivel=True,
        )
        card_letras.clicked.connect(self.quiz_selecionado.emit)
        cards_wrap.addWidget(card_letras)

        minhas = self.estado.get("palavras_customizadas", [])
        card_palavras = QuizCard(
            "palavras", "Aa", "Quiz de Palavras",
            "Sorteia palavras da sua lista 'Minhas Palavras'."
            if minhas else
            "Cadastre palavras em Palavras > Adicionar palavras para liberar.",
            len(minhas), disponivel=len(minhas) > 0,
        )
        card_palavras.clicked.connect(self.quiz_selecionado.emit)
        cards_wrap.addWidget(card_palavras)

        cards_wrap.addStretch()
        conteudo.addLayout(cards_wrap)
        conteudo.addStretch(1)

        scroll.setWidget(container)
        self._layout_raiz.addWidget(scroll, 1)

    def reconstruir(self):
        self._limpar()
        self._construir()
