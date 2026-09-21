"""Pecas visuais da Analise Individual: chip de letra e imagem clicavel
(arrastar/soltar, clique em letra)."""

from PyQt5.QtWidgets import QLabel
from PyQt5.QtGui import QPixmap, QCursor
from PyQt5.QtCore import Qt, pyqtSignal
from calligraphos.ui.ui_theme import com_alpha


class LetraChip(QLabel):
    clicado = pyqtSignal(int)

    def __init__(self, indice, letra_reconhecida, cor, texto_visivel):
        super().__init__(texto_visivel)
        self.indice = indice
        self.letra_reconhecida = letra_reconhecida
        self.setAlignment(Qt.AlignCenter)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setStyleSheet(
            f"background-color: {com_alpha(cor, 0x18)}; color: {cor};"
            f" border: 1px solid {com_alpha(cor, 0x45)}; border-radius: 6px;"
            f" padding: 6px 4px; font-size: 11px; font-weight: 600;"
        )
        if letra_reconhecida and letra_reconhecida != "?":
            self.setToolTip(f"Letra: {letra_reconhecida}  (clique para ver detalhes)")
        else:
            self.setToolTip("Letra não identificada  (clique para ver detalhes)")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicado.emit(self.indice)

class ImagemClicavel(QLabel):
    clicou_para_adicionar = pyqtSignal(int, int)
    clicou_selecao = pyqtSignal(int, int)   # clique normal (selecionar caixa)

    def __init__(self):
        super().__init__()
        self.modo_adicionar = False
        self.pixmap_original = None
        self.escala_atual = 1.0
        self.offset_x = 0
        self.offset_y = 0

    def setImagemOriginal(self, qimg):
        self.pixmap_original = QPixmap.fromImage(qimg)
        self._reexibir()

    def setModoAdicionar(self, ativo):
        self.modo_adicionar = ativo
        self.setCursor(QCursor(Qt.CrossCursor if ativo else Qt.ArrowCursor))

    def _reexibir(self):
        if self.pixmap_original is None:
            return
        w_disp = max(1, self.width() - 12)
        h_disp = max(1, self.height() - 12)
        escalado = self.pixmap_original.scaled(
            w_disp, h_disp, Qt.KeepAspectRatio, Qt.SmoothTransformation,
        )
        self.escala_atual = escalado.width() / self.pixmap_original.width()
        self.offset_x = (self.width() - escalado.width()) // 2
        self.offset_y = (self.height() - escalado.height()) // 2
        self.setPixmap(escalado)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reexibir()

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton or self.pixmap_original is None:
            return
        x_widget = event.x() - self.offset_x
        y_widget = event.y() - self.offset_y
        esc_w = self.pixmap_original.width() * self.escala_atual
        esc_h = self.pixmap_original.height() * self.escala_atual
        if not (0 <= x_widget <= esc_w and 0 <= y_widget <= esc_h):
            return
        x_orig = int(x_widget / self.escala_atual)
        y_orig = int(y_widget / self.escala_atual)
        if self.modo_adicionar:
            self.clicou_para_adicionar.emit(x_orig, y_orig)
        else:
            self.clicou_selecao.emit(x_orig, y_orig)
