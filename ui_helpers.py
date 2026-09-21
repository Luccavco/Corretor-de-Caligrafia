"""Funcoes utilitarias de UI compartilhadas entre as abas do modo
Praticar. Centralizam padroes que antes estavam copiados varias vezes:
limpeza recursiva de layouts e o cabecalho padronizado das abas."""

from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel, QLayout, QSizePolicy
from PyQt5.QtCore import Qt, QRect, QPoint, QSize

from ui_theme import C_TEXT, C_MUTED


def limpar_layout(lay):
    """Remove e destroi recursivamente todos os itens de um layout
    (widgets e sub-layouts). Usado para reconstruir uma aba do zero."""
    while lay.count():
        item = lay.takeAt(0)
        w = item.widget()
        if w is not None:
            w.setParent(None)
            w.deleteLater()
        else:
            sub = item.layout()
            if sub is not None:
                limpar_layout(sub)


def cabecalho_aba(titulo, subtitulo, acao=None):
    """Monta o cabecalho padrao das abas: titulo grande + subtitulo
    cinza ao lado e, opcionalmente, um widget de acao a direita (botao).
    O subtitulo pode encolher em janelas estreitas, para nunca forcar a
    largura minima da tela. Devolve o QWidget pronto para o layout."""
    header = QHBoxLayout()
    header.setContentsMargins(0, 0, 0, 0)

    lbl_titulo = QLabel(titulo)
    lbl_titulo.setStyleSheet(
        f"color: {C_TEXT}; font-size: 28px; font-weight: 800;"
    )
    lbl_sub = QLabel(subtitulo)
    lbl_sub.setStyleSheet(f"color: {C_MUTED}; font-size: 17px;")
    lbl_sub.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)

    header.addWidget(lbl_titulo, alignment=Qt.AlignVCenter)
    header.addSpacing(14)
    header.addWidget(lbl_sub, 1, alignment=Qt.AlignVCenter)
    if acao is not None:
        header.addSpacing(12)
        header.addWidget(acao, alignment=Qt.AlignVCenter)

    wrap = QWidget()
    wrap.setMinimumHeight(52)
    wrap.setLayout(header)
    return wrap


class FlowLayout(QLayout):
    """Layout que dispoe os itens em linha e quebra para a linha seguinte
    quando falta largura, como texto num paragrafo. Cada linha e centralizada.

    Substitui as grades com numero fixo de colunas: os cartoes de letras,
    fases, quiz e conquistas passam a ocupar a largura disponivel, sem
    forcar um tamanho minimo de janela nem deixar metade da tela vazia."""

    def __init__(self, parent=None, espacamento=12, centralizar=True):
        super().__init__(parent)
        self._itens = []
        self._esp = espacamento
        self._centralizar = centralizar
        self.setContentsMargins(0, 0, 0, 0)

    # -- API obrigatoria do QLayout --------------------------------------
    def addItem(self, item):
        self._itens.append(item)

    def count(self):
        return len(self._itens)

    def itemAt(self, i):
        return self._itens[i] if 0 <= i < len(self._itens) else None

    def takeAt(self, i):
        return self._itens.pop(i) if 0 <= i < len(self._itens) else None

    def expandingDirections(self):
        return Qt.Orientations(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, largura):
        return self._dispor(QRect(0, 0, largura, 0), apenas_medir=True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._dispor(rect, apenas_medir=False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        # A largura minima e a do maior item: o layout nunca exige mais
        # que isso, e a altura vem de heightForWidth.
        tam = QSize()
        for item in self._itens:
            tam = tam.expandedTo(item.minimumSize())
        m = self.contentsMargins()
        return tam + QSize(m.left() + m.right(), m.top() + m.bottom())

    # -- Posicionamento --------------------------------------------------
    def _dispor(self, rect, apenas_medir):
        m = self.contentsMargins()
        area = rect.adjusted(m.left(), m.top(), -m.right(), -m.bottom())
        x = area.x()
        y = area.y()
        altura_linha = 0
        linha = []          # itens da linha atual, para centralizar

        def fechar_linha():
            if not linha or apenas_medir or not self._centralizar:
                return
            largura_usada = sum(it.sizeHint().width() for it in linha)
            largura_usada += self._esp * (len(linha) - 1)
            desloc = max(0, (area.width() - largura_usada) // 2)
            cx = area.x() + desloc
            for it in linha:
                it.setGeometry(QRect(QPoint(cx, y), it.sizeHint()))
                cx += it.sizeHint().width() + self._esp

        for item in self._itens:
            w = item.sizeHint().width()
            h = item.sizeHint().height()
            if linha and x + w > area.right() + 1:
                fechar_linha()
                x = area.x()
                y += altura_linha + self._esp
                altura_linha = 0
                linha = []
            if not apenas_medir and not self._centralizar:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))
            linha.append(item)
            x += w + self._esp
            altura_linha = max(altura_linha, h)
        fechar_linha()
        return y + altura_linha - rect.y() + m.bottom()
