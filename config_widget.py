"""Tela de configuracoes: alterar email, alterar senha, resetar progresso
e sair da conta. Requer confirmacao para acoes destrutivas."""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QMessageBox, QComboBox, QScrollArea,
)
from PyQt5.QtCore import Qt, pyqtSignal

from ui_theme import (
    C_PANEL, C_CARD, C_TEXT, C_MUTED, C_BORDER, C_ACCENT,
    C_GOOD, C_BAD, com_alpha,
)
from auth_service import alterar_email, alterar_senha, ErroAuth
import progresso as prog


class ConfigWidget(QWidget):
    voltar_solicitado = pyqtSignal()
    logout_solicitado = pyqtSignal()

    def __init__(self, sessao, estado):
        super().__init__()
        self.sessao = sessao
        self.estado = estado
        self.setup_ui()

    def setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 14, 18, 16)
        root.setSpacing(12)

        # Cabecalho
        header = QHBoxLayout()
        btn_voltar = QPushButton("Voltar")
        btn_voltar.setObjectName("ghost")
        btn_voltar.setFixedWidth(90)
        btn_voltar.clicked.connect(self.voltar_solicitado.emit)
        header.addWidget(btn_voltar)
        header.addSpacing(10)
        titulo = QLabel("Configuracoes")
        titulo.setStyleSheet(f"font-size: 20px; font-weight: 800; color: {C_TEXT};")
        header.addWidget(titulo)
        header.addStretch()
        root.addLayout(header)

        # Corpo: coluna centralizada de largura limitada, com rolagem
        # (assim a tela cabe em qualquer altura de janela)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        conteudo = QWidget()
        conteudo.setObjectName("transparente")
        centro = QHBoxLayout(conteudo)
        centro.setContentsMargins(0, 4, 0, 4)
        centro.addStretch()
        coluna = QWidget()
        coluna.setObjectName("transparente")
        coluna.setMaximumWidth(640)
        col = QVBoxLayout(coluna)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(16)
        col.setAlignment(Qt.AlignTop)
        centro.addWidget(coluna, 1)
        centro.addStretch()
        scroll.setWidget(conteudo)
        root.addWidget(scroll, 1)

        # Card: conta
        col.addWidget(self._card_conta())

        # Card: mudar email
        col.addWidget(self._card_mudar_email())

        # Card: mudar senha
        col.addWidget(self._card_mudar_senha())

        # Card: meta diaria
        col.addWidget(self._card_meta_diaria())

        # Card: zona de perigo
        col.addWidget(self._card_zona_perigo())

    # ── Cards ──────────────────────────────────────────────────────

    def _make_card(self, titulo):
        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background-color: {C_PANEL};"
            f" border: 1px solid {C_BORDER}; border-radius: 12px; }}"
        )
        lay = QVBoxLayout(card)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(10)
        lbl = QLabel(titulo)
        lbl.setStyleSheet(
            f"color: {C_MUTED}; font-size: 11px; font-weight: 700;"
            f" letter-spacing: 1.2px; border: none;"
        )
        lay.addWidget(lbl)
        return card, lay

    def _estilo_input(self):
        return (
            f"QLineEdit {{ background-color: {C_CARD}; color: {C_TEXT};"
            f" border: 1px solid {C_BORDER}; border-radius: 8px;"
            f" padding: 9px 12px; font-size: 13px; }}"
            f"QLineEdit:focus {{ border: 1px solid {C_ACCENT}; }}"
        )

    def _card_conta(self):
        card, lay = self._make_card("CONTA")
        info = QLabel(f"Voce esta logado como:")
        info.setStyleSheet(f"color: {C_MUTED}; font-size: 12px; border: none;")
        lay.addWidget(info)

        self.lbl_email_atual = QLabel(self.sessao.get("email", "?"))
        self.lbl_email_atual.setStyleSheet(
            f"color: {C_TEXT}; font-size: 15px; font-weight: 600; border: none;"
        )
        lay.addWidget(self.lbl_email_atual)

        btn_sair = QPushButton("Sair da conta")
        btn_sair.clicked.connect(self._sair)
        lay.addWidget(btn_sair, alignment=Qt.AlignLeft)
        return card

    def _card_meta_diaria(self):
        card, lay = self._make_card("META DIARIA")
        info = QLabel(
            "Quantos exercicios voce quer fazer por dia. A meta aparece na "
            "tela inicial e ajuda a manter sua sequencia."
        )
        info.setWordWrap(True)
        info.setStyleSheet(f"color: {C_MUTED}; font-size: 12px; border: none;")
        lay.addWidget(info)

        linha = QHBoxLayout()
        lbl = QLabel("Exercicios por dia:")
        lbl.setStyleSheet(f"color: {C_TEXT}; font-size: 13px; border: none;")
        linha.addWidget(lbl)

        self.combo_meta = QComboBox()
        for v in (3, 5, 10, 15, 20, 30):
            self.combo_meta.addItem(str(v), v)
        atual = self.estado.get("meta_diaria", 5) if self.estado else 5
        idx = self.combo_meta.findData(atual)
        if idx >= 0:
            self.combo_meta.setCurrentIndex(idx)
        self.combo_meta.currentIndexChanged.connect(self._salvar_meta)
        linha.addWidget(self.combo_meta)
        linha.addStretch()
        lay.addLayout(linha)
        return card

    def _salvar_meta(self, _idx):
        if not self.estado:
            return
        meta = self.combo_meta.currentData()
        prog.definir_meta_diaria(self.sessao["uid"], self.estado, meta)

    def _card_mudar_email(self):
        card, lay = self._make_card("ALTERAR EMAIL")
        self.input_novo_email = QLineEdit()
        self.input_novo_email.setPlaceholderText("Novo email")
        self.input_novo_email.setStyleSheet(self._estilo_input())
        lay.addWidget(self.input_novo_email)

        self.msg_email = QLabel("")
        self.msg_email.setWordWrap(True)
        self.msg_email.setStyleSheet(
            f"color: {C_MUTED}; font-size: 12px; border: none;"
        )
        lay.addWidget(self.msg_email)

        btn = QPushButton("Alterar email")
        btn.setObjectName("primary")
        btn.clicked.connect(self._alterar_email)
        lay.addWidget(btn, alignment=Qt.AlignLeft)
        return card

    def _card_mudar_senha(self):
        card, lay = self._make_card("ALTERAR SENHA")
        self.input_nova_senha = QLineEdit()
        self.input_nova_senha.setEchoMode(QLineEdit.Password)
        self.input_nova_senha.setPlaceholderText("Nova senha (minimo 6 caracteres)")
        self.input_nova_senha.setStyleSheet(self._estilo_input())
        lay.addWidget(self.input_nova_senha)

        self.msg_senha = QLabel("")
        self.msg_senha.setWordWrap(True)
        self.msg_senha.setStyleSheet(
            f"color: {C_MUTED}; font-size: 12px; border: none;"
        )
        lay.addWidget(self.msg_senha)

        btn = QPushButton("Alterar senha")
        btn.setObjectName("primary")
        btn.clicked.connect(self._alterar_senha)
        lay.addWidget(btn, alignment=Qt.AlignLeft)
        return card

    def _card_zona_perigo(self):
        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background-color: {C_PANEL};"
            f" border: 1px solid {com_alpha(C_BAD, 0x55)}; border-radius: 12px; }}"
        )
        lay = QVBoxLayout(card)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(10)

        lbl = QLabel("ZONA DE PERIGO")
        lbl.setStyleSheet(
            f"color: {C_BAD}; font-size: 11px; font-weight: 700;"
            f" letter-spacing: 1.2px; border: none;"
        )
        lay.addWidget(lbl)

        aviso = QLabel(
            "Apagar seu progresso ira reiniciar todas as suas letras dominadas "
            "e fases completas. Essa acao nao pode ser desfeita."
        )
        aviso.setWordWrap(True)
        aviso.setStyleSheet(f"color: {C_MUTED}; font-size: 12px; border: none;")
        lay.addWidget(aviso)

        btn = QPushButton("Resetar progresso")
        btn.setStyleSheet(
            f"QPushButton {{ background-color: {C_BAD}; color: #fff;"
            f" border: none; border-radius: 8px; padding: 10px 16px;"
            f" font-size: 13px; font-weight: 600; }}"
            f"QPushButton:hover {{ background-color: #e87070; }}"
        )
        btn.clicked.connect(self._resetar_progresso)
        lay.addWidget(btn, alignment=Qt.AlignLeft)
        return card

    # ── Acoes ──────────────────────────────────────────────────────

    def _alterar_email(self):
        novo = self.input_novo_email.text().strip()
        try:
            alterar_email(self.sessao["idToken"], novo)
            self.sessao["email"] = novo
            self.lbl_email_atual.setText(novo)
            self.input_novo_email.clear()
            self.msg_email.setText("Email alterado com sucesso.")
            self.msg_email.setStyleSheet(
                f"color: {C_GOOD}; font-size: 12px; border: none;"
            )
        except ErroAuth as e:
            self.msg_email.setText(str(e))
            self.msg_email.setStyleSheet(
                f"color: {C_BAD}; font-size: 12px; border: none;"
            )

    def _alterar_senha(self):
        nova = self.input_nova_senha.text()
        try:
            alterar_senha(self.sessao["idToken"], nova)
            self.input_nova_senha.clear()
            self.msg_senha.setText("Senha alterada com sucesso.")
            self.msg_senha.setStyleSheet(
                f"color: {C_GOOD}; font-size: 12px; border: none;"
            )
        except ErroAuth as e:
            self.msg_senha.setText(str(e))
            self.msg_senha.setStyleSheet(
                f"color: {C_BAD}; font-size: 12px; border: none;"
            )

    def _resetar_progresso(self):
        resposta = QMessageBox.question(
            self,
            "Resetar progresso",
            "Tem certeza que deseja resetar todo o seu progresso?\n\n"
            "Todas as letras dominadas e fases completas serao perdidas.\n"
            "Essa acao nao pode ser desfeita.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if resposta == QMessageBox.Yes:
            uid = self.sessao["uid"]
            prog.resetar(uid, self.estado)
            QMessageBox.information(
                self, "Pronto",
                "Seu progresso foi resetado."
            )

    def _sair(self):
        resposta = QMessageBox.question(
            self,
            "Sair da conta",
            "Deseja mesmo sair da sua conta?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if resposta == QMessageBox.Yes:
            self.logout_solicitado.emit()
