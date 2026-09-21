"""Cartoes e barras reutilizados pelas abas do modo Praticar: barra segmentada
de progresso, cartao de letra, de fase, de quiz e de conquista."""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
from PyQt5.QtGui import QCursor, QPainter, QColor
from PyQt5.QtCore import Qt, pyqtSignal
from calligraphos.ui.ui_theme import C_CARD, C_PANEL, C_TEXT, C_MUTED, C_BORDER, C_ACCENT, C_GOOD, C_OK


class BarraSegmentada(QWidget):
    """Barra de progresso dividida em segmentos visiveis (tequinhos).
    Cada segmento e preenchido individualmente. Fica verde apenas
    quando todos os segmentos estao preenchidos (nivel maximo)."""

    def __init__(self, total, valor, altura=14):
        super().__init__()
        self.total = max(1, total)
        self.valor = valor
        self.setFixedHeight(altura)
        self.setMinimumWidth(60)

    def set_valor(self, valor):
        self.valor = valor
        self.update()

    def _cor(self):
        if self.valor >= self.total:
            return QColor(C_GOOD)
        elif self.valor >= self.total * 0.6:
            return QColor(C_ACCENT)
        elif self.valor >= 1:
            return QColor(C_OK)
        return QColor(C_BORDER)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w = self.width()
        h = self.height()
        gap = 3
        n = self.total
        seg_w = (w - gap * (n - 1)) / n
        cor_on = self._cor()
        cor_off = QColor(C_CARD)
        borda = QColor(C_BORDER)
        for i in range(n):
            x = i * (seg_w + gap)
            p.setPen(borda)
            cor = cor_on if i < self.valor else cor_off
            p.setBrush(cor)
            p.drawRoundedRect(int(x), 0, int(seg_w), h - 1, 3, 3)
        p.end()

class LetraCard(QFrame):
    clicked = pyqtSignal(str)

    def __init__(self, letra, nivel, fonte):
        super().__init__()
        self.letra = letra
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setFixedSize(140, 165)
        self._apply_style(nivel)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 12, 8, 12)
        layout.setSpacing(8)

        lbl_letra = QLabel(letra)
        lbl_letra.setAlignment(Qt.AlignCenter)
        lbl_letra.setStyleSheet(
            f"color: {C_TEXT}; font-size: 56px; font-weight: 800;"
            f" border: none; background: transparent;"
            f" font-family: {fonte};"
        )
        layout.addWidget(lbl_letra, 1)

        self.barra = BarraSegmentada(5, nivel, altura=12)
        layout.addWidget(self.barra)

    def _apply_style(self, nivel):
        borda = C_GOOD if nivel >= 5 else C_BORDER
        self.setStyleSheet(
            f"QFrame {{ background-color: {C_PANEL};"
            f" border: 1px solid {borda}; border-radius: 12px; }}"
            f"QFrame:hover {{ border: 1px solid {C_ACCENT}; }}"
        )

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.letra)

class FaseCard(QFrame):
    clicked = pyqtSignal(int)

    def __init__(self, indice, nome, descricao, n_palavras,
                 desbloqueada, completa, custom=False):
        super().__init__()
        self.indice = indice
        self.desbloqueada = desbloqueada
        self.setFixedSize(250, 250)
        if custom:
            cor_borda = C_ACCENT
        else:
            cor_borda = C_GOOD if completa else (C_ACCENT if desbloqueada else C_BORDER)
        hover_rule = f"QFrame:hover {{ border: 1px solid {C_ACCENT}; }}" if desbloqueada else ""
        self.setStyleSheet(
            f"QFrame {{ background-color: {C_PANEL};"
            f" border: 1px solid {cor_borda}; border-radius: 16px; }}"
            + hover_rule
        )
        if desbloqueada:
            self.setCursor(QCursor(Qt.PointingHandCursor))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        topo = QHBoxLayout()
        num = QLabel("Personalizada" if custom else f"Fase {indice + 1}")
        num.setStyleSheet(
            f"color: {C_MUTED}; font-size: 13px; font-weight: 700;"
            f" letter-spacing: 1.5px; border: none;"
        )
        topo.addWidget(num)
        topo.addStretch()
        if custom:
            status_txt, cor_st = ("Disponível", C_ACCENT) if desbloqueada else ("Vazia", C_MUTED)
        elif completa:
            status_txt, cor_st = "Concluída", C_GOOD
        elif desbloqueada:
            status_txt, cor_st = "Disponível", C_ACCENT
        else:
            status_txt, cor_st = "Bloqueada", C_MUTED
        status = QLabel(status_txt)
        status.setStyleSheet(
            f"color: {cor_st}; font-size: 13px; font-weight: 700; border: none;"
        )
        topo.addWidget(status)
        layout.addLayout(topo)

        lbl_nome = QLabel(nome)
        lbl_nome.setWordWrap(True)
        lbl_nome.setStyleSheet(
            f"color: {C_TEXT}; font-size: 22px; font-weight: 800; border: none;"
        )
        layout.addWidget(lbl_nome)

        desc = QLabel(descricao)
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {C_MUTED}; font-size: 13px; border: none;")
        desc.setAlignment(Qt.AlignTop)
        layout.addWidget(desc, 1)

        info = QLabel(f"{n_palavras} palavra(s)")
        info.setStyleSheet(
            f"color: {C_ACCENT if desbloqueada else C_MUTED};"
            f" font-size: 14px; font-weight: 600; border: none;"
        )
        layout.addWidget(info)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.desbloqueada:
            self.clicked.emit(self.indice)

class QuizCard(QFrame):
    """Card de selecao do tipo de quiz (Letras ou Minhas Palavras)."""
    clicked = pyqtSignal(str)   # "letras" ou "palavras"

    def __init__(self, tipo, icone, titulo, descricao, quantidade, disponivel):
        super().__init__()
        self.tipo = tipo
        self.disponivel = disponivel
        self.setFixedSize(440, 400)
        cor_borda = C_ACCENT if disponivel else C_BORDER
        hover = f"QFrame:hover {{ border: 1px solid {C_ACCENT}; }}" if disponivel else ""
        self.setStyleSheet(
            f"QFrame {{ background-color: {C_PANEL};"
            f" border: 1px solid {cor_borda}; border-radius: 18px; }}"
            + hover
        )
        if disponivel:
            self.setCursor(QCursor(Qt.PointingHandCursor))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 32, 30, 32)
        layout.setSpacing(18)
        layout.setAlignment(Qt.AlignTop)

        lbl_icone = QLabel(icone)
        lbl_icone.setAlignment(Qt.AlignCenter)
        lbl_icone.setFixedSize(132, 132)
        # Fonte do icone menor quando e texto (ABC) do que quando e um simbolo
        tam_icone = 44 if len(icone) > 1 else 58
        lbl_icone.setStyleSheet(
            f"background-color: {C_CARD}; color: {C_ACCENT};"
            f" border: 3px solid {C_ACCENT}; border-radius: 66px;"
            f" font-size: {tam_icone}px; font-weight: 800;"
        )
        layout.addWidget(lbl_icone, alignment=Qt.AlignHCenter)

        lbl_titulo = QLabel(titulo)
        lbl_titulo.setAlignment(Qt.AlignCenter)
        lbl_titulo.setStyleSheet(
            f"color: {C_TEXT}; font-size: 30px; font-weight: 800; border: none;"
        )
        layout.addWidget(lbl_titulo)

        lbl_desc = QLabel(descricao)
        lbl_desc.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        lbl_desc.setWordWrap(True)
        lbl_desc.setMinimumHeight(66)
        lbl_desc.setStyleSheet(
            f"color: {C_MUTED}; font-size: 17px; border: none;"
        )
        layout.addWidget(lbl_desc)

        info = QLabel(
            f"{quantidade} itens disponiveis" if disponivel
            else "Indisponível"
        )
        info.setAlignment(Qt.AlignCenter)
        info.setStyleSheet(
            f"color: {C_ACCENT if disponivel else C_MUTED};"
            f" font-size: 16px; font-weight: 600; border: none;"
        )
        layout.addWidget(info)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.disponivel:
            self.clicked.emit(self.tipo)

class ConquistaCard(QFrame):
    """Card de uma conquista/medalha (desbloqueada ou bloqueada)."""

    def __init__(self, conquista):
        super().__init__()
        desbloqueada = conquista["desbloqueada"]
        self.setFixedSize(250, 104)
        cor_borda = C_GOOD if desbloqueada else C_BORDER
        self.setStyleSheet(
            f"QFrame {{ background-color: {C_PANEL};"
            f" border: 1px solid {cor_borda}; border-radius: 12px; }}"
        )
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(12)

        # Medalha (circulo)
        medalha = QLabel("*" if desbloqueada else "-")
        medalha.setAlignment(Qt.AlignCenter)
        medalha.setFixedSize(48, 48)
        cor_med = C_GOOD if desbloqueada else C_CARD
        cor_txt = "#ffffff" if desbloqueada else C_MUTED
        medalha.setStyleSheet(
            f"background-color: {cor_med}; color: {cor_txt};"
            f" border-radius: 24px; font-size: 22px; font-weight: 800;"
        )
        lay.addWidget(medalha)

        texto = QVBoxLayout()
        texto.setSpacing(2)
        titulo = QLabel(conquista["titulo"])
        cor_titulo = C_TEXT if desbloqueada else C_MUTED
        titulo.setStyleSheet(
            f"color: {cor_titulo}; font-size: 14px; font-weight: 700;"
            f" border: none; background: transparent;"
        )
        texto.addWidget(titulo)
        desc = QLabel(conquista["descricao"])
        desc.setWordWrap(True)
        desc.setStyleSheet(
            f"color: {C_MUTED}; font-size: 12px; border: none;"
            f" background: transparent;"
        )
        texto.addWidget(desc)
        lay.addLayout(texto, 1)
