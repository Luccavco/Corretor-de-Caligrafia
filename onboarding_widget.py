"""Onboarding: 3 telas de boas-vindas com setinhas de navegacao.
So aparece na primeira vez que o usuario abre o app apos criar conta."""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QStackedWidget, QFrame, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal

from ui_theme import (
    C_BG, C_PANEL, C_CARD, C_TEXT, C_MUTED, C_BORDER, C_ACCENT,
)


TELAS = [
    {
        "icone": "OI",
        "titulo": "Seja bem-vindo ao Calligraphos!",
        "texto": "Um sistema que reconhece texto manuscrito e avalia a qualidade da sua caligrafia usando visao computacional e redes neurais.",
    },
    {
        "icone": "?",
        "titulo": "Como usar",
        "texto": "Voce tem dois modos: 'Praticar Caligrafia' para treinar letras e palavras com feedback automatico, e 'Analise Individual' para transcrever e avaliar qualquer texto manuscrito.",
    },
    {
        "icone": "*",
        "titulo": "Seu progresso, salvo em qualquer lugar",
        "texto": "Ao criar uma conta, seu progresso e salvo online. Isso permite que voce continue de onde parou em qualquer computador.",
    },
]


class Bolinha(QLabel):
    """Bolinha do indicador de pagina (embaixo da tela)."""
    def __init__(self, ativa):
        super().__init__()
        self.setFixedSize(10, 10)
        cor = C_ACCENT if ativa else C_BORDER
        self.setStyleSheet(
            f"background-color: {cor}; border-radius: 5px;"
        )


class TelaOnboarding(QWidget):
    def __init__(self, dados):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(60, 40, 60, 40)
        layout.setSpacing(24)
        layout.setAlignment(Qt.AlignCenter)

        layout.addStretch(1)

        # Icone circular
        icone = QLabel(dados["icone"])
        icone.setAlignment(Qt.AlignCenter)
        icone.setFixedSize(120, 120)
        icone.setStyleSheet(
            f"background-color: {C_PANEL}; color: {C_ACCENT};"
            f" border: 2px solid {C_ACCENT}; border-radius: 60px;"
            f" font-size: 44px; font-weight: 800;"
        )
        wrap_icone = QHBoxLayout()
        wrap_icone.addStretch()
        wrap_icone.addWidget(icone)
        wrap_icone.addStretch()
        layout.addLayout(wrap_icone)

        # Titulo
        titulo = QLabel(dados["titulo"])
        titulo.setAlignment(Qt.AlignCenter)
        titulo.setWordWrap(True)
        titulo.setStyleSheet(
            f"color: {C_TEXT}; font-size: 26px; font-weight: 800;"
            f" font-family: 'Cambria', 'Georgia', serif;"
        )
        layout.addWidget(titulo)

        # Texto
        texto = QLabel(dados["texto"])
        texto.setAlignment(Qt.AlignCenter)
        texto.setWordWrap(True)
        texto.setStyleSheet(
            f"color: {C_MUTED}; font-size: 15px;"
        )
        texto.setMaximumWidth(560)
        wrap_texto = QHBoxLayout()
        wrap_texto.addStretch()
        wrap_texto.addWidget(texto)
        wrap_texto.addStretch()
        layout.addLayout(wrap_texto)

        layout.addStretch(2)


class OnboardingWidget(QWidget):
    concluido = pyqtSignal()
    pular = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.indice = 0
        self.setup_ui()

    def setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 20, 0, 30)
        root.setSpacing(20)

        # Topo: botao pular no canto direito
        topo = QHBoxLayout()
        topo.setContentsMargins(30, 0, 30, 0)
        topo.addStretch()
        btn_pular = QPushButton("Pular")
        btn_pular.setObjectName("ghost")
        btn_pular.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {C_MUTED};"
            f" border: none; font-size: 13px; padding: 6px 12px; }}"
            f"QPushButton:hover {{ color: {C_TEXT}; }}"
        )
        btn_pular.clicked.connect(self.pular.emit)
        topo.addWidget(btn_pular)
        root.addLayout(topo)

        # Stack de telas
        self.stack = QStackedWidget()
        for dados in TELAS:
            self.stack.addWidget(TelaOnboarding(dados))
        root.addWidget(self.stack, 1)

        # Indicador de pagina
        self.dots_layout = QHBoxLayout()
        self.dots_layout.setSpacing(8)
        self.dots_wrap = QHBoxLayout()
        self.dots_wrap.addStretch()
        self.dots_wrap.addLayout(self.dots_layout)
        self.dots_wrap.addStretch()
        self._atualizar_bolinhas()
        root.addLayout(self.dots_wrap)

        # Botoes de navegacao
        botoes = QHBoxLayout()
        botoes.setContentsMargins(60, 0, 60, 0)
        self.btn_voltar = QPushButton("< Voltar")
        self.btn_voltar.setObjectName("ghost")
        self.btn_voltar.setMinimumWidth(120)
        self.btn_voltar.clicked.connect(self._anterior)
        botoes.addWidget(self.btn_voltar)

        botoes.addStretch()

        self.btn_avancar = QPushButton("Proximo >")
        self.btn_avancar.setObjectName("primary")
        self.btn_avancar.setMinimumWidth(160)
        self.btn_avancar.setMinimumHeight(42)
        self.btn_avancar.clicked.connect(self._proximo)
        botoes.addWidget(self.btn_avancar)
        root.addLayout(botoes)

        self._atualizar_botoes()

    def _atualizar_bolinhas(self):
        while self.dots_layout.count():
            item = self.dots_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for i in range(len(TELAS)):
            self.dots_layout.addWidget(Bolinha(i == self.indice))

    def _atualizar_botoes(self):
        self.btn_voltar.setVisible(self.indice > 0)
        if self.indice == len(TELAS) - 1:
            self.btn_avancar.setText("Comecar")
        else:
            self.btn_avancar.setText("Proximo >")

    def _proximo(self):
        if self.indice == len(TELAS) - 1:
            self.concluido.emit()
            return
        self.indice += 1
        self.stack.setCurrentIndex(self.indice)
        self._atualizar_bolinhas()
        self._atualizar_botoes()

    def _anterior(self):
        if self.indice == 0:
            return
        self.indice -= 1
        self.stack.setCurrentIndex(self.indice)
        self._atualizar_bolinhas()
        self._atualizar_botoes()
