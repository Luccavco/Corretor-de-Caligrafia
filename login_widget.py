"""Tela de login e registro. Emite `logado(user)` quando o usuario
faz login ou cria conta com sucesso."""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame
)
from PyQt5.QtCore import Qt, pyqtSignal, QThread

from ui_theme import (
    C_PANEL, C_CARD, C_TEXT, C_MUTED, C_BORDER, C_ACCENT,
    C_BAD,
)
from auth_service import login, registrar, ErroAuth


class AuthWorker(QThread):
    ok = pyqtSignal(object)
    erro = pyqtSignal(str)

    def __init__(self, acao, email, senha):
        super().__init__()
        self.acao = acao   # "login" ou "registrar"
        self.email = email
        self.senha = senha

    def run(self):
        try:
            if self.acao == "login":
                user = login(self.email, self.senha)
            else:
                user = registrar(self.email, self.senha)
            self.ok.emit(user)
        except ErroAuth as e:
            self.erro.emit(str(e))
        except Exception as e:
            self.erro.emit(f"Erro inesperado: {e}")


class LoginWidget(QWidget):
    logado = pyqtSignal(object)
    pular_solicitado = pyqtSignal()   # continuar sem conta (fluxo local antigo)

    def __init__(self, permitir_pular=True):
        super().__init__()
        self.modo = "login"   # ou "registrar"
        self.permitir_pular = permitir_pular
        self.worker = None
        self.setup_ui()

    def setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(40, 40, 40, 40)
        root.setSpacing(20)
        root.setAlignment(Qt.AlignCenter)

        root.addStretch(1)

        # Titulo do app
        titulo = QLabel("Calligraphos")
        titulo.setAlignment(Qt.AlignCenter)
        titulo.setStyleSheet(
            f"color: {C_TEXT}; font-size: 40px; font-weight: 800;"
            f" font-family: 'Cambria', 'Georgia', serif;"
        )
        root.addWidget(titulo)

        sub = QLabel("Entre na sua conta para continuar")
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet(f"color: {C_MUTED}; font-size: 14px;")
        root.addWidget(sub)

        # Card do formulario
        card = QFrame()
        card.setFixedWidth(400)
        card.setStyleSheet(
            f"QFrame {{ background-color: {C_PANEL};"
            f" border: 1px solid {C_BORDER}; border-radius: 14px; }}"
        )
        form_layout = QVBoxLayout(card)
        form_layout.setContentsMargins(28, 24, 28, 24)
        form_layout.setSpacing(12)

        self.lbl_titulo_form = QLabel("Entrar")
        self.lbl_titulo_form.setStyleSheet(
            f"color: {C_TEXT}; font-size: 18px; font-weight: 700; border: none;"
        )
        form_layout.addWidget(self.lbl_titulo_form)

        self.input_email = QLineEdit()
        self.input_email.setPlaceholderText("Email")
        self.input_email.setStyleSheet(self._estilo_input())
        form_layout.addWidget(self.input_email)

        self.input_senha = QLineEdit()
        self.input_senha.setPlaceholderText("Senha (mínimo 6 caracteres)")
        self.input_senha.setEchoMode(QLineEdit.Password)
        self.input_senha.setStyleSheet(self._estilo_input())
        self.input_senha.returnPressed.connect(self._acao_principal)
        form_layout.addWidget(self.input_senha)

        self.lbl_erro = QLabel("")
        self.lbl_erro.setWordWrap(True)
        self.lbl_erro.setStyleSheet(
            f"color: {C_BAD}; font-size: 12px; border: none;"
            f" background: transparent;"
        )
        form_layout.addWidget(self.lbl_erro)

        self.btn_principal = QPushButton("Entrar")
        self.btn_principal.setObjectName("primary")
        self.btn_principal.setMinimumHeight(42)
        self.btn_principal.clicked.connect(self._acao_principal)
        form_layout.addWidget(self.btn_principal)

        self.btn_alternar = QPushButton("Não tenho conta - Criar conta")
        self.btn_alternar.setObjectName("ghost")
        self.btn_alternar.clicked.connect(self._alternar_modo)
        form_layout.addWidget(self.btn_alternar)

        wrap = QHBoxLayout()
        wrap.addStretch()
        wrap.addWidget(card)
        wrap.addStretch()
        root.addLayout(wrap)

        if self.permitir_pular:
            btn_pular = QPushButton("Continuar sem conta")
            btn_pular.setObjectName("ghost")
            btn_pular.setStyleSheet(
                f"QPushButton {{ background: transparent; color: {C_MUTED};"
                f" border: none; font-size: 12px; }}"
                f"QPushButton:hover {{ color: {C_TEXT}; }}"
            )
            btn_pular.clicked.connect(self.pular_solicitado.emit)
            root.addWidget(btn_pular, alignment=Qt.AlignCenter)

        root.addStretch(2)

    def _estilo_input(self):
        return (
            f"QLineEdit {{ background-color: {C_CARD}; color: {C_TEXT};"
            f" border: 1px solid {C_BORDER}; border-radius: 8px;"
            f" padding: 10px 12px; font-size: 13px; }}"
            f"QLineEdit:focus {{ border: 1px solid {C_ACCENT}; }}"
        )

    def _alternar_modo(self):
        if self.modo == "login":
            self.modo = "registrar"
            self.lbl_titulo_form.setText("Criar conta")
            self.btn_principal.setText("Criar conta")
            self.btn_alternar.setText("Já tenho conta - Entrar")
        else:
            self.modo = "login"
            self.lbl_titulo_form.setText("Entrar")
            self.btn_principal.setText("Entrar")
            self.btn_alternar.setText("Não tenho conta - Criar conta")
        self.lbl_erro.setText("")

    def _acao_principal(self):
        email = self.input_email.text().strip()
        senha = self.input_senha.text()
        self.lbl_erro.setText("")
        self.btn_principal.setEnabled(False)
        self.btn_alternar.setEnabled(False)
        self.btn_principal.setText("Aguarde...")

        self.worker = AuthWorker(self.modo, email, senha)
        self.worker.ok.connect(self._on_ok)
        self.worker.erro.connect(self._on_erro)
        self.worker.start()

    def _on_ok(self, user):
        self._resetar_botoes()
        self.logado.emit(user)

    def _on_erro(self, mensagem):
        self.lbl_erro.setText(mensagem)
        self._resetar_botoes()

    def _resetar_botoes(self):
        self.btn_principal.setEnabled(True)
        self.btn_alternar.setEnabled(True)
        self.btn_principal.setText("Entrar" if self.modo == "login" else "Criar conta")
