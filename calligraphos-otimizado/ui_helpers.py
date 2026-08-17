"""Funcoes utilitarias de UI compartilhadas entre as abas do modo
Praticar. Centralizam padroes que antes estavam copiados varias vezes:
limpeza recursiva de layouts e o cabecalho padronizado das abas."""

from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel
from PyQt5.QtCore import Qt

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


def cabecalho_aba(titulo, subtitulo):
    """Monta o cabecalho padrao das abas: titulo grande + subtitulo
    cinza ao lado, dentro de um wrap de altura minima (nunca corta
    descendentes como 'g'/'p'). Devolve o QWidget pronto para adicionar
    ao layout da aba."""
    header = QHBoxLayout()
    header.setContentsMargins(0, 0, 0, 0)

    lbl_titulo = QLabel(titulo)
    lbl_titulo.setStyleSheet(
        f"color: {C_TEXT}; font-size: 31px; font-weight: 800;"
    )
    lbl_sub = QLabel(subtitulo)
    lbl_sub.setStyleSheet(f"color: {C_MUTED}; font-size: 22px;")

    header.addWidget(lbl_titulo, alignment=Qt.AlignVCenter)
    header.addSpacing(16)
    header.addWidget(lbl_sub, alignment=Qt.AlignVCenter)
    header.addStretch()

    wrap = QWidget()
    wrap.setMinimumHeight(58)
    wrap.setLayout(header)
    return wrap
