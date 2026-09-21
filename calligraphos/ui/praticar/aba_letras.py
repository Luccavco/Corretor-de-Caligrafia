"""Aba Letras: grade das 26 letras com progresso por nivel e tela de boas-vindas."""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QScrollArea
from PyQt5.QtCore import Qt, pyqtSignal
from calligraphos.ui.ui_helpers import limpar_layout, cabecalho_aba, FlowLayout, rotulo
from calligraphos.ui.ui_theme import C_TEXT, C_MUTED, C_ACCENT
from calligraphos.nuvem import progresso as prog
from calligraphos.ui.praticar.cartoes import BarraSegmentada, LetraCard
from calligraphos.ui.praticar.constantes import FONTE_FORMA, LETRAS


class AbaLetras(QWidget):
    letra_selecionada = pyqtSignal(str)

    def __init__(self, uid, estado):
        super().__init__()
        self.uid = uid
        self.estado = estado
        self._layout_raiz = QVBoxLayout(self)
        self._layout_raiz.setContentsMargins(20, 20, 20, 20)
        self._layout_raiz.setSpacing(14)
        self.cards = {}
        self._construir()

    def _limpar(self):
        limpar_layout(self._layout_raiz)
        self.cards.clear()

    def _construir(self):
        if not self.estado.get("iniciou_letras", False):
            self._construir_boas_vindas()
        else:
            self._construir_grid()

    def _construir_boas_vindas(self):
        self._layout_raiz.addStretch(1)
        titulo = QLabel("Aprender caligrafia")
        titulo.setAlignment(Qt.AlignCenter)
        titulo.setStyleSheet(
            f"color: {C_TEXT}; font-size: 28px; font-weight: 800;"
            f" font-family: 'Cambria', 'Georgia', serif;"
        )
        self._layout_raiz.addWidget(titulo)

        desc = QLabel(
            "Você vai treinar as 26 letras do alfabeto uma por uma.\n"
            "Cada letra tem uma barra de progresso de 0 a 5.\n"
            "A cada acerto, a barra sobe. Quando chegar em 5, a letra está dominada."
        )
        desc.setAlignment(Qt.AlignCenter)
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {C_MUTED}; font-size: 14px;")
        self._layout_raiz.addWidget(desc)
        self._layout_raiz.addStretch(1)

        btn_wrap = QHBoxLayout()
        btn_wrap.addStretch()
        btn = QPushButton("Começar a aprender caligrafia!")
        btn.setMinimumHeight(48)
        btn.setStyleSheet(
            f"QPushButton {{ background-color: {C_ACCENT}; color: #fff;"
            f" border: none; border-radius: 10px; padding: 12px 32px;"
            f" font-size: 15px; font-weight: 700; }}"
            f"QPushButton:hover {{ background-color: #62adff; }}"
        )
        btn.clicked.connect(self._on_iniciar)
        btn_wrap.addWidget(btn)
        btn_wrap.addStretch()
        self._layout_raiz.addLayout(btn_wrap)
        self._layout_raiz.addStretch(2)

    def _construir_grid(self):
        letras_estado = self.estado.get("letras", {})
        dominadas = sum(1 for n in letras_estado.values() if n >= 5)
        fonte = FONTE_FORMA

        # Cabecalho padronizado (mesma estrutura da aba Palavras):
        # linha 1 = titulo + subtitulo + acao a direita (altura fixa)
        # linha 2 = barra de progresso geral (altura fixa)
        self._layout_raiz.addWidget(
            cabecalho_aba("Progresso das Letras", "clique em uma letra para praticar")
        )

        # Barra de progresso geral (linha propria, altura fixa)
        prog_row = QHBoxLayout()
        prog_row.setContentsMargins(0, 0, 0, 0)
        lbl_prog = rotulo(f"Progresso geral: {dominadas}/26 dominadas", C_MUTED, 14)
        lbl_prog.setFixedWidth(260)
        barra_geral = BarraSegmentada(len(LETRAS), dominadas, altura=10)
        prog_row.addWidget(lbl_prog)
        prog_row.addSpacing(10)
        prog_row.addWidget(barra_geral, 1)
        prog_wrap = QWidget()
        prog_wrap.setMinimumHeight(40)
        prog_wrap.setLayout(prog_row)
        self._layout_raiz.addWidget(prog_wrap)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        container.setObjectName("transparente")
        # Grade fluida: o numero de colunas depende da largura da janela
        grid = FlowLayout(container, espacamento=12)

        for letra in LETRAS:
            nivel = letras_estado.get(letra, 0)
            card = LetraCard(letra, nivel, fonte)
            card.clicked.connect(self.letra_selecionada.emit)
            self.cards[letra] = card
            grid.addWidget(card)

        scroll.setWidget(container)
        self._layout_raiz.addWidget(scroll, 1)

    def _on_iniciar(self):
        prog.marcar_iniciou_letras(self.uid, self.estado)
        self.reconstruir()

    def reconstruir(self):
        self._limpar()
        self._construir()
