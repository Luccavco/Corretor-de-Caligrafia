"""Aba Palavras: fases progressivas e o cartao Minhas Palavras."""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QScrollArea
from PyQt5.QtCore import pyqtSignal
from calligraphos.ui.ui_helpers import limpar_layout, cabecalho_aba, FlowLayout, rotulo
from calligraphos.ui.ui_theme import C_CARD, C_TEXT, C_MUTED, C_BORDER, C_ACCENT
from calligraphos.ui.praticar.cartoes import BarraSegmentada, FaseCard
from calligraphos.ui.praticar.constantes import FASES


class AbaPalavras(QWidget):
    fase_selecionada = pyqtSignal(int)
    fase_custom_selecionada = pyqtSignal()
    gerenciar_solicitado = pyqtSignal()

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
        completas = self.estado["fases_completas"]

        # Cabecalho padronizado (mesma estrutura da aba Letras):
        # linha 1 = titulo + subtitulo + acao a direita (altura fixa)
        # linha 2 = barra de progresso geral (altura fixa)
        btn_gerenciar = QPushButton("Adicionar palavras")
        btn_gerenciar.setFixedHeight(32)
        btn_gerenciar.setStyleSheet(
            f"QPushButton {{ background-color: {C_CARD}; color: {C_TEXT};"
            f" border: 1px solid {C_BORDER}; border-radius: 8px;"
            f" padding: 0px 16px; font-size: 13px; }}"
            f"QPushButton:hover {{ border: 1px solid {C_ACCENT}; }}"
        )
        btn_gerenciar.clicked.connect(self.gerenciar_solicitado.emit)
        self._layout_raiz.addWidget(
            cabecalho_aba(
                "Fases de Palavras",
                "complete uma fase para desbloquear a próxima",
                acao=btn_gerenciar,
            )
        )

        # Barra de progresso geral (linha propria, altura fixa)
        prog_row = QHBoxLayout()
        prog_row.setContentsMargins(0, 0, 0, 0)
        lbl_prog = rotulo(f"Progresso das fases: {completas}/{len(FASES)}", C_MUTED, 14)
        lbl_prog.setFixedWidth(260)
        barra_geral = BarraSegmentada(len(FASES), completas, altura=10)
        prog_row.addWidget(lbl_prog)
        prog_row.addSpacing(10)
        prog_row.addWidget(barra_geral, 1)
        prog_wrap = QWidget()
        prog_wrap.setMinimumHeight(40)
        prog_wrap.setLayout(prog_row)
        self._layout_raiz.addWidget(prog_wrap)

        # Cartoes de fase em grade fluida: 4 lado a lado quando cabe,
        # 2x2 em janelas menores
        cards_container = QWidget()
        cards_container.setObjectName("transparente")
        cards_wrap = FlowLayout(cards_container, espacamento=18)
        cards_wrap.setContentsMargins(0, 12, 0, 12)
        for i, fase in enumerate(FASES):
            desbloqueada = i <= self.estado["fases_completas"]
            completa = i < self.estado["fases_completas"]
            card = FaseCard(
                i, fase["nome"], fase["descricao"], len(fase["palavras"]),
                desbloqueada, completa,
            )
            card.clicked.connect(self.fase_selecionada.emit)
            cards_wrap.addWidget(card)

        minhas = self.estado.get("palavras_customizadas", [])
        card_custom = FaseCard(
            99, "Minhas Palavras",
            "Treine as palavras que você mesmo adicionou."
            if minhas else
            "Adicione palavras pelo botão acima para liberar este treino.",
            len(minhas),
            desbloqueada=len(minhas) > 0,
            completa=False,
            custom=True,
        )
        card_custom.clicked.connect(lambda _i: self.fase_custom_selecionada.emit())
        cards_wrap.addWidget(card_custom)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(cards_container)
        self._layout_raiz.addWidget(scroll, 1)

    def reconstruir(self):
        self._limpar()
        self._construir()
