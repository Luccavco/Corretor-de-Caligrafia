"""Quadro de desenho reutilizavel. A pessoa escreve com o mouse (ou
touchscreen) sobre um fundo branco com traco preto - o formato ideal
para o OCR e para a avaliacao de caligrafia.

O desenho pode ser salvo como PNG temporario, alimentando exatamente o
mesmo pipeline de uma imagem carregada de arquivo.

Ferramentas: desenhar, borracha e limpar tudo.
"""

import os
import tempfile

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSizePolicy,
    QFrame
)
from PyQt5.QtGui import QPainter, QPen, QImage, QColor
from PyQt5.QtCore import Qt, QPoint, pyqtSignal

from ui_theme import C_TEXT, C_MUTED, C_BORDER, C_ACCENT, C_CARD, C_PANEL


class AreaDesenho(QWidget):
    """A superficie branca onde o traco preto e desenhado."""
    desenhou = pyqtSignal()   # emitido no primeiro traco (habilita analisar)

    ESPESSURA_CANETA = 8
    ESPESSURA_BORRACHA = 28

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(480, 360)
        self.setCursor(Qt.CrossCursor)
        self.imagem = None
        self.desenhando = False
        self.ultimo_ponto = QPoint()
        self.modo_borracha = False
        self.tem_conteudo = False
        self._garantir_imagem()

    def _garantir_imagem(self):
        """Cria a imagem interna (fundo branco) do tamanho do widget."""
        if self.imagem is None or self.imagem.size() != self.size():
            nova = QImage(self.size(), QImage.Format_RGB888)
            nova.fill(QColor("white"))
            if self.imagem is not None:
                # Preserva o desenho existente ao redimensionar
                painter = QPainter(nova)
                painter.drawImage(0, 0, self.imagem)
                painter.end()
            self.imagem = nova

    def resizeEvent(self, event):
        self._garantir_imagem()
        super().resizeEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawImage(0, 0, self.imagem)
        painter.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.desenhando = True
            self.ultimo_ponto = event.pos()
            # Um clique simples ja marca um ponto
            self._desenhar_ate(event.pos())

    def mouseMoveEvent(self, event):
        if self.desenhando and (event.buttons() & Qt.LeftButton):
            self._desenhar_ate(event.pos())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.desenhando = False

    def _desenhar_ate(self, ponto):
        self._garantir_imagem()
        painter = QPainter(self.imagem)
        if self.modo_borracha:
            cor = QColor("white")
            espessura = self.ESPESSURA_BORRACHA
        else:
            cor = QColor("black")
            espessura = self.ESPESSURA_CANETA
        pen = QPen(cor, espessura, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(pen)
        painter.drawLine(self.ultimo_ponto, ponto)
        painter.end()
        self.ultimo_ponto = ponto
        if not self.tem_conteudo and not self.modo_borracha:
            self.tem_conteudo = True
            self.desenhou.emit()
        self.update()

    def limpar(self):
        self.imagem.fill(QColor("white"))
        self.tem_conteudo = False
        self.update()

    def set_borracha(self, ativo):
        self.modo_borracha = ativo
        self.setCursor(Qt.PointingHandCursor if ativo else Qt.CrossCursor)

    def esta_vazio(self):
        return not self.tem_conteudo

    def salvar_png(self):
        """Salva o desenho em um PNG temporario e devolve o caminho."""
        fd, caminho = tempfile.mkstemp(suffix=".png", prefix="desenho_")
        os.close(fd)
        self.imagem.save(caminho, "PNG")
        return caminho


class CanvasDesenho(QWidget):
    """Quadro completo: area de desenho + barra de ferramentas."""
    desenhou = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.area = AreaDesenho()
        self.area.desenhou.connect(self.desenhou.emit)
        self.area.setStyleSheet(
            f"border: 1px solid {C_BORDER}; border-radius: 10px;"
            f" background-color: white;"
        )
        # A area absorve TODO o espaco vertical extra, colando a barra
        # de ferramentas na base (sem sobrar vazio embaixo)
        self.area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.area, 1)

        # Barra de ferramentas dentro de um painel proprio, com altura fixa
        painel = QFrame()
        painel.setFixedHeight(52)
        painel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        painel.setStyleSheet(
            f"QFrame {{ background-color: {C_PANEL};"
            f" border: 1px solid {C_BORDER}; border-radius: 10px; }}"
        )
        barra = QHBoxLayout(painel)
        barra.setContentsMargins(14, 0, 14, 0)
        barra.setSpacing(10)

        dica = QLabel("Escreva no quadro")
        dica.setStyleSheet(
            f"color: {C_TEXT}; font-size: 14px; font-weight: 600;"
            f" border: none; background: transparent;"
        )
        barra.addWidget(dica)
        barra.addStretch()

        self.btn_caneta = QPushButton("Caneta")
        self.btn_caneta.setCheckable(True)
        self.btn_caneta.setChecked(True)
        self.btn_caneta.clicked.connect(self._usar_caneta)
        barra.addWidget(self.btn_caneta)

        self.btn_borracha = QPushButton("Borracha")
        self.btn_borracha.setCheckable(True)
        self.btn_borracha.clicked.connect(self._usar_borracha)
        barra.addWidget(self.btn_borracha)

        self.btn_limpar = QPushButton("Limpar")
        self.btn_limpar.clicked.connect(self.area.limpar)
        barra.addWidget(self.btn_limpar)

        layout.addWidget(painel)
        self._atualizar_estilo_ferramentas()

    def _usar_caneta(self):
        self.area.set_borracha(False)
        self.btn_caneta.setChecked(True)
        self.btn_borracha.setChecked(False)
        self._atualizar_estilo_ferramentas()

    def _usar_borracha(self):
        self.area.set_borracha(True)
        self.btn_borracha.setChecked(True)
        self.btn_caneta.setChecked(False)
        self._atualizar_estilo_ferramentas()

    def _atualizar_estilo_ferramentas(self):
        ativo = (
            f"QPushButton {{ background-color: {C_ACCENT}22; color: {C_ACCENT};"
            f" border: 1px solid {C_ACCENT}; border-radius: 8px;"
            f" padding: 6px 14px; font-weight: 600; }}"
        )
        inativo = (
            f"QPushButton {{ background-color: {C_CARD}; color: {C_TEXT};"
            f" border: 1px solid {C_BORDER}; border-radius: 8px;"
            f" padding: 6px 14px; }}"
        )
        self.btn_caneta.setStyleSheet(ativo if self.btn_caneta.isChecked() else inativo)
        self.btn_borracha.setStyleSheet(ativo if self.btn_borracha.isChecked() else inativo)

    def esta_vazio(self):
        return self.area.esta_vazio()

    def limpar(self):
        self.area.limpar()

    def salvar_png(self):
        return self.area.salvar_png()
