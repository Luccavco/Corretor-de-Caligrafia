"""Anel de progresso circular desenhado com QPainter. A cor varia com
o desempenho: vermelho (baixo) -> ambar (medio) -> verde (alto)."""

from PyQt5.QtWidgets import QWidget, QSizePolicy
from PyQt5.QtGui import QPainter, QColor, QPen, QFont
from PyQt5.QtCore import Qt, QRectF

from calligraphos.ui.ui_theme import C_CARD, C_TEXT, C_MUTED, C_GOOD, C_OK, C_BAD


class AnelProgresso(QWidget):
    def __init__(self, percentual=0, tamanho=220, parent=None):
        super().__init__(parent)
        self.percentual = max(0, min(100, percentual))
        self.tamanho = tamanho
        self.setFixedSize(tamanho, tamanho)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

    def set_percentual(self, valor):
        self.percentual = max(0, min(100, valor))
        self.update()

    def _cor(self):
        if self.percentual >= 75:
            return QColor(C_GOOD)
        elif self.percentual >= 40:
            return QColor(C_OK)
        return QColor(C_BAD)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        margem = 16
        espessura = 18
        rect = QRectF(
            margem, margem,
            self.tamanho - 2 * margem, self.tamanho - 2 * margem
        )

        # Trilho de fundo
        pen_fundo = QPen(QColor(C_CARD), espessura, Qt.SolidLine, Qt.RoundCap)
        p.setPen(pen_fundo)
        p.drawArc(rect, 0, 360 * 16)

        # Arco de progresso (comeca no topo, sentido horario)
        cor = self._cor()
        pen_prog = QPen(cor, espessura, Qt.SolidLine, Qt.RoundCap)
        p.setPen(pen_prog)
        angulo_inicio = 90 * 16
        angulo_span = -int(360 * 16 * self.percentual / 100)
        p.drawArc(rect, angulo_inicio, angulo_span)

        # Texto central: percentual grande
        p.setPen(QColor(C_TEXT))
        fonte_num = QFont("Segoe UI", 40, QFont.Bold)
        p.setFont(fonte_num)
        p.drawText(
            rect, Qt.AlignCenter, f"{self.percentual}%"
        )

        # Rotulo abaixo do numero
        p.setPen(QColor(C_MUTED))
        fonte_rot = QFont("Segoe UI", 11)
        p.setFont(fonte_rot)
        rect_rot = QRectF(
            margem, self.tamanho / 2 + 26,
            self.tamanho - 2 * margem, 24
        )
        p.drawText(rect_rot, Qt.AlignHCenter | Qt.AlignTop, "concluido")

        p.end()
