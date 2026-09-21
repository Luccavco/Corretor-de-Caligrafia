"""Dialogo para adicionar/remover palavras da lista pessoal (Minhas Palavras)."""

from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QDialog, QLineEdit, QListWidget, QListWidgetItem
from PyQt5.QtGui import QRegExpValidator
from PyQt5.QtCore import QRegExp
from calligraphos.ui.ui_theme import C_BG, C_CARD, C_PANEL, C_TEXT, C_MUTED, C_BORDER, C_ACCENT, com_alpha
from calligraphos.ui.ui_helpers import rotulo
from calligraphos.nuvem import progresso as prog


class GerenciarPalavrasDialog(QDialog):
    def __init__(self, uid, estado, parent=None):
        super().__init__(parent)
        self.uid = uid
        self.estado = estado
        self.setWindowTitle("Minhas Palavras")
        self.setFixedSize(420, 520)
        self.setStyleSheet(f"QDialog {{ background-color: {C_BG}; }}")
        self.setup_ui()

    def setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(12)

        titulo = rotulo("Gerenciar minhas palavras", C_TEXT, 18, peso=800)
        root.addWidget(titulo)

        dica = QLabel(
            "Adicione palavras que você quer treinar (apenas letras A-Z, "
            "sem espaços ou acentos)."
        )
        dica.setWordWrap(True)
        dica.setStyleSheet(f"color: {C_MUTED}; font-size: 12px;")
        root.addWidget(dica)

        linha_add = QHBoxLayout()
        self.input_palavra = QLineEdit()
        self.input_palavra.setPlaceholderText("NOVA PALAVRA")
        self.input_palavra.setMaxLength(15)
        self.input_palavra.setValidator(QRegExpValidator(QRegExp("[A-Za-z]+")))
        self.input_palavra.setStyleSheet(
            f"QLineEdit {{ background-color: {C_CARD}; color: {C_TEXT};"
            f" border: 1px solid {C_BORDER}; border-radius: 8px;"
            f" padding: 10px 12px; font-size: 14px; font-weight: 600; }}"
            f"QLineEdit:focus {{ border: 1px solid {C_ACCENT}; }}"
        )
        self.input_palavra.returnPressed.connect(self._adicionar)
        linha_add.addWidget(self.input_palavra, 1)

        btn_add = QPushButton("Adicionar")
        btn_add.setObjectName("primary")
        btn_add.clicked.connect(self._adicionar)
        linha_add.addWidget(btn_add)
        root.addLayout(linha_add)

        self.lista = QListWidget()
        self.lista.setStyleSheet(
            f"QListWidget {{ background-color: {C_PANEL}; color: {C_TEXT};"
            f" border: 1px solid {C_BORDER}; border-radius: 10px;"
            f" padding: 6px; font-size: 14px; }}"
            f"QListWidget::item {{ padding: 8px; border-radius: 6px; }}"
            f"QListWidget::item:selected {{ background-color: {com_alpha(C_ACCENT, 0x33)}; }}"
        )
        root.addWidget(self.lista, 1)

        linha_botoes = QHBoxLayout()
        btn_remover = QPushButton("Remover selecionada")
        btn_remover.clicked.connect(self._remover)
        linha_botoes.addWidget(btn_remover)
        linha_botoes.addStretch()
        btn_fechar = QPushButton("Fechar")
        btn_fechar.setObjectName("ghost")
        btn_fechar.clicked.connect(self.accept)
        linha_botoes.addWidget(btn_fechar)
        root.addLayout(linha_botoes)

        self._recarregar_lista()

    def _recarregar_lista(self):
        self.lista.clear()
        for p in self.estado.get("palavras_customizadas", []):
            self.lista.addItem(QListWidgetItem(p))

    def _adicionar(self):
        palavra = (self.input_palavra.text() or "").strip().upper()
        if len(palavra) < 2:
            return
        ok = prog.adicionar_palavra_customizada(self.uid, self.estado, palavra)
        if ok:
            self.input_palavra.clear()
            self._recarregar_lista()

    def _remover(self):
        item = self.lista.currentItem()
        if item is None:
            return
        prog.remover_palavra_customizada(self.uid, self.estado, item.text())
        self._recarregar_lista()
