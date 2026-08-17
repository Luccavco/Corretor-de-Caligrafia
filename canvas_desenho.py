"""Quadro de desenho reutilizavel. A pessoa escreve com o mouse (ou
touchscreen) sobre um fundo branco com traco preto - o formato ideal
para o OCR e para a avaliacao de caligrafia.

Suporta uma "letra-guia" transparente: quando ha um alvo especifico
(letra ou palavra do exercicio), o contorno aparece bem claro atras do
traco, para a pessoa desenhar por cima (tracing). A guia e PURAMENTE
visual - fica numa camada separada da tinta e NUNCA entra na imagem
salva para analise, para nao interferir no reconhecimento.

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
from PyQt5.QtGui import QPainter, QPen, QImage, QColor, QFont, QFontMetrics
from PyQt5.QtCore import Qt, QPoint, pyqtSignal

from ui_theme import C_TEXT, C_BORDER, C_ACCENT, C_CARD, C_PANEL

COR_GUIA = QColor(0, 0, 0, 45)   # preto bem transparente = efeito "letra fantasma"


class AreaDesenho(QWidget):
    """A superficie branca onde o traco preto e desenhado.

    Estrutura em camadas (de baixo para cima, desenhadas no paintEvent):
    1. fundo branco (papel)
    2. letra-guia cinza claro (opcional, so exibicao)
    3. tinta da pessoa (self.imagem: transparente, so opaco onde ha traco)

    Apenas as camadas 1 e 3 vao para o PNG salvo - a guia nunca e
    exportada, entao nao interfere no OCR nem na avaliacao.
    """
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
        self.guia_texto = ""
        self._garantir_imagem()

    def _garantir_imagem(self):
        """Cria a camada de tinta (transparente) do tamanho do widget."""
        if self.imagem is None or self.imagem.size() != self.size():
            nova = QImage(self.size(), QImage.Format_ARGB32_Premultiplied)
            nova.fill(Qt.transparent)
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
        painter.setRenderHint(QPainter.Antialiasing)
        # 1. fundo branco (papel)
        painter.fillRect(self.rect(), QColor("white"))
        # 2. letra-guia (se houver). O tamanho da fonte e calculado AQUI,
        # a cada desenho, usando as dimensoes REAIS e atuais do widget -
        # nao em cache no momento de definir_guia(), que pode ser chamado
        # antes do widget ter seu tamanho final na tela (fazendo a guia
        # nao aparecer ou aparecer minuscula).
        if self.guia_texto:
            fonte = self._fonte_para_guia()
            if fonte:
                painter.setPen(COR_GUIA)
                painter.setFont(fonte)
                painter.drawText(self.rect(), Qt.AlignCenter, self.guia_texto)
        # 3. traco da pessoa (camada transparente, so a tinta e opaca)
        painter.drawImage(0, 0, self.imagem)
        painter.end()

    def _fonte_para_guia(self):
        """Calcula o maior tamanho de fonte que cabe confortavelmente na
        area de desenho, usando as dimensoes atuais (nao cacheadas)."""
        largura = self.width()
        altura = self.height()
        if largura <= 10 or altura <= 10 or not self.guia_texto:
            return None
        largura_max = int(largura * 0.82)
        altura_max = int(altura * 0.82)
        tamanho = 10
        fonte = QFont("Georgia", tamanho, QFont.Light)
        while tamanho < 500:
            fonte.setPointSize(tamanho + 4)
            metrics = QFontMetrics(fonte)
            rect = metrics.boundingRect(self.guia_texto)
            if rect.width() > largura_max or rect.height() > altura_max:
                break
            tamanho += 4
        fonte.setPointSize(max(10, tamanho))
        return fonte

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
        painter.setRenderHint(QPainter.Antialiasing)
        if self.modo_borracha:
            # Apaga de volta para transparente (nao pinta de branco por
            # cima, senao criaria uma mancha branca sobre a letra-guia)
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
            pen = QPen(
                QColor(0, 0, 0, 255), self.ESPESSURA_BORRACHA,
                Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin
            )
        else:
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
            pen = QPen(
                QColor("black"), self.ESPESSURA_CANETA,
                Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin
            )
        painter.setPen(pen)
        painter.drawLine(self.ultimo_ponto, ponto)
        painter.end()
        self.ultimo_ponto = ponto
        if not self.tem_conteudo and not self.modo_borracha:
            self.tem_conteudo = True
            self.desenhou.emit()
        self.update()

    def limpar(self):
        self.imagem.fill(Qt.transparent)
        self.tem_conteudo = False
        self.update()

    def set_borracha(self, ativo):
        self.modo_borracha = ativo
        self.setCursor(Qt.PointingHandCursor if ativo else Qt.CrossCursor)

    def esta_vazio(self):
        return not self.tem_conteudo

    def definir_guia(self, texto):
        """Define a letra ou palavra-guia exibida atras do traco, para
        a pessoa desenhar por cima (tracing). O tamanho da fonte e
        calculado dinamicamente no proximo paintEvent, entao funciona
        mesmo se chamado antes do widget ter seu tamanho final."""
        self.guia_texto = (texto or "").strip()
        self.update()

    def limpar_guia(self):
        self.guia_texto = ""
        self.update()

    def salvar_png(self):
        """Salva SOMENTE o traco (fundo branco + tinta) em um PNG
        temporario - a letra-guia nunca entra aqui, entao nao interfere
        na transcricao nem na avaliacao. Devolve o caminho do arquivo."""
        composta = QImage(self.imagem.size(), QImage.Format_RGB888)
        composta.fill(QColor("white"))
        painter = QPainter(composta)
        painter.drawImage(0, 0, self.imagem)
        painter.end()
        fd, caminho = tempfile.mkstemp(suffix=".png", prefix="desenho_")
        os.close(fd)
        composta.save(caminho, "PNG")
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

    def definir_guia(self, texto):
        self.area.definir_guia(texto)

    def limpar_guia(self):
        self.area.limpar_guia()

    def salvar_png(self):
        return self.area.salvar_png()
