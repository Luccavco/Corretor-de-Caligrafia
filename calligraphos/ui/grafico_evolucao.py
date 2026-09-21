"""Grafico de linha da evolucao da nota (media diaria) desenhado com
QPainter, no estilo do app. Sem dependencia de bibliotecas de grafico."""

from datetime import date, timedelta

from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import QPainter, QPen, QColor, QBrush, QFont, QPainterPath
from PyQt5.QtCore import Qt, QPointF, QRectF

from calligraphos.ui.ui_theme import C_CARD, C_BORDER, C_TEXT, C_MUTED, C_ACCENT, C_GOOD, C_OK, C_BAD, com_alpha
from calligraphos.nucleo.handwriting_evaluator import NOTA_BOA, NOTA_ACEITAVEL


class GraficoEvolucao(QWidget):
    """Recebe [(data_iso, media, n)] e desenha a linha dos ultimos `dias`."""

    def __init__(self, pontos, dias=30, parent=None):
        super().__init__(parent)
        self.pontos = pontos
        self.dias = dias
        self.setMinimumHeight(190)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        p.fillRect(0, 0, w, h, QColor(C_CARD))

        # Area util do grafico
        esq, dir_, topo, base = 40, 14, 14, 30
        gw, gh = w - esq - dir_, h - topo - base

        def y_de(nota):
            return topo + gh * (1 - nota / 100.0)

        # Faixas Boa / Aceitavel / Ruim (fundo sutil)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(com_alpha(C_GOOD, 0x12))))
        p.drawRect(QRectF(esq, topo, gw, y_de(NOTA_BOA) - topo))
        p.setBrush(QBrush(QColor(com_alpha(C_OK, 0x12))))
        p.drawRect(QRectF(esq, y_de(NOTA_BOA), gw, y_de(NOTA_ACEITAVEL) - y_de(NOTA_BOA)))
        p.setBrush(QBrush(QColor(com_alpha(C_BAD, 0x12))))
        p.drawRect(QRectF(esq, y_de(NOTA_ACEITAVEL), gw, y_de(0) - y_de(NOTA_ACEITAVEL)))

        # Eixo Y: 0, 50, 75, 100
        fonte = QFont(); fonte.setPointSize(8); p.setFont(fonte)
        for nota in (0, NOTA_ACEITAVEL, NOTA_BOA, 100):
            y = y_de(nota)
            p.setPen(QPen(QColor(C_BORDER), 1, Qt.DashLine))
            p.drawLine(QPointF(esq, y), QPointF(esq + gw, y))
            p.setPen(QColor(C_MUTED))
            p.drawText(QRectF(0, y - 8, esq - 6, 16), Qt.AlignRight | Qt.AlignVCenter, str(nota))

        # Eixo X: dias (hoje a direita)
        hoje = date.today()
        inicio = hoje - timedelta(days=self.dias - 1)

        def x_de(d):
            return esq + gw * ((d - inicio).days / max(self.dias - 1, 1))

        p.setPen(QColor(C_MUTED))
        for i in range(0, self.dias, max(1, self.dias // 5)):
            d = inicio + timedelta(days=i)
            p.drawText(QRectF(x_de(d) - 24, topo + gh + 6, 48, 16), Qt.AlignCenter, d.strftime("%d/%m"))

        if not self.pontos:
            p.setPen(QColor(C_MUTED))
            p.drawText(QRectF(esq, topo, gw, gh), Qt.AlignCenter,
                       "Ainda não há tentativas neste período.\nPratique uma letra para começar o gráfico.")
            return

        # Linha + pontos
        coords = []
        for d_iso, media, _n in self.pontos:
            d = date.fromisoformat(d_iso)
            if d < inicio:
                continue
            coords.append(QPointF(x_de(d), y_de(media)))
        if len(coords) >= 2:
            caminho = QPainterPath(coords[0])
            for c in coords[1:]:
                caminho.lineTo(c)
            p.setPen(QPen(QColor(C_ACCENT), 2.2))
            p.setBrush(Qt.NoBrush)
            p.drawPath(caminho)
        p.setPen(QPen(QColor(C_CARD), 2))
        p.setBrush(QBrush(QColor(C_ACCENT)))
        for c in coords:
            p.drawEllipse(c, 4, 4)
        # Valor do ultimo ponto
        if coords:
            ult = coords[-1]
            p.setPen(QColor(C_TEXT))
            fonte.setBold(True); p.setFont(fonte)
            p.drawText(QRectF(ult.x() - 30, ult.y() - 24, 60, 16), Qt.AlignCenter,
                       f"{self.pontos[-1][1]:.0f}")
