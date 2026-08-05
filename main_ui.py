"""Janela principal do Calligraphos. Coordena o fluxo:
- login (ou autologin)
- onboarding (na primeira vez)
- tela inicial com 2 modos + configuracoes + sobre/tutorial + idioma
- praticar / analise / configuracoes
"""

import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QStackedWidget, QFrame, QSizePolicy, QComboBox,
    QMessageBox
)
from PyQt5.QtGui import QCursor
from PyQt5.QtCore import Qt

from ui_theme import (
    STYLE, C_PANEL, C_CARD, C_TEXT, C_MUTED, C_BORDER, C_ACCENT,
)


class ModoCard(QFrame):
    def __init__(self, icone, titulo, descricao, on_click):
        super().__init__()
        self.on_click = on_click
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setFixedSize(370, 410)
        self.setStyleSheet(
            f"QFrame {{ background-color: {C_PANEL};"
            f" border: 1px solid {C_BORDER}; border-radius: 20px; }}"
            f"QFrame:hover {{ border: 1px solid {C_ACCENT}; }}"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 34, 30, 30)
        layout.setSpacing(16)
        layout.setAlignment(Qt.AlignTop)

        icon_wrap = QLabel(icone)
        icon_wrap.setAlignment(Qt.AlignCenter)
        icon_wrap.setFixedSize(140, 140)
        icon_wrap.setStyleSheet(
            f"background-color: {C_CARD}; color: {C_ACCENT};"
            f" border: 2px solid {C_ACCENT}; border-radius: 70px;"
            f" font-size: 62px; font-weight: 800;"
        )
        layout.addWidget(icon_wrap, alignment=Qt.AlignHCenter)

        lbl_titulo = QLabel(titulo)
        lbl_titulo.setAlignment(Qt.AlignCenter)
        lbl_titulo.setFixedHeight(32)
        lbl_titulo.setStyleSheet(
            f"color: {C_TEXT}; font-size: 23px; font-weight: 800; border: none;"
        )
        layout.addWidget(lbl_titulo)

        lbl_desc = QLabel(descricao)
        lbl_desc.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        lbl_desc.setWordWrap(True)
        lbl_desc.setFixedHeight(110)
        lbl_desc.setStyleSheet(
            f"color: {C_MUTED}; font-size: 15px; border: none;"
        )
        layout.addWidget(lbl_desc)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.on_click()


class TelaInicial(QWidget):
    def __init__(self, email, ir_para_praticar, ir_para_analise, ir_para_config):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 24, 40, 24)
        layout.setSpacing(0)

        # Topo: idioma a esquerda, email + configuracoes a direita
        topo = QHBoxLayout()
        lbl_idioma = QLabel("Idioma:")
        lbl_idioma.setStyleSheet(f"color: {C_MUTED}; font-size: 13px;")
        combo_idioma = QComboBox()
        combo_idioma.addItem("Portugues (BR)")
        combo_idioma.setToolTip("Outros idiomas serao adicionados futuramente")
        topo.addWidget(lbl_idioma)
        topo.addWidget(combo_idioma)
        topo.addStretch()
        lbl_email = QLabel(email)
        lbl_email.setStyleSheet(f"color: {C_MUTED}; font-size: 13px;")
        topo.addWidget(lbl_email)
        btn_config = QPushButton("Configuracoes")
        btn_config.setObjectName("ghost")
        btn_config.clicked.connect(ir_para_config)
        topo.addWidget(btn_config)
        layout.addLayout(topo)

        layout.addStretch(1)

        titulo = QLabel("Calligraphos")
        titulo.setAlignment(Qt.AlignCenter)
        titulo.setStyleSheet(
            f"color: {C_TEXT}; font-size: 48px; font-weight: 800;"
            f" font-family: 'Cambria', 'Georgia', serif;"
        )
        layout.addWidget(titulo)

        # Espacamento IGUAL entre titulo -> subtitulo -> cards
        layout.addSpacing(28)

        sub = QLabel("Escolha o que voce quer fazer")
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet(f"color: {C_MUTED}; font-size: 17px;")
        layout.addWidget(sub)

        layout.addSpacing(28)

        cards_row = QHBoxLayout()
        cards_row.setSpacing(36)
        cards_row.addStretch()

        card_praticar = ModoCard(
            "A",
            "Praticar Caligrafia",
            "Treine sua escrita com exercicios guiados de letras e palavras. Receba retorno automatico sobre cada tentativa.",
            ir_para_praticar,
        )
        cards_row.addWidget(card_praticar)

        card_analise = ModoCard(
            "?",
            "Analise Individual",
            "Envie uma foto de qualquer texto manuscrito. O sistema transcreve o conteudo e avalia a caligrafia letra por letra.",
            ir_para_analise,
        )
        cards_row.addWidget(card_analise)

        cards_row.addStretch()
        layout.addLayout(cards_row)

        layout.addStretch(1)

        # Rodape: Sobre e Tutorial no canto inferior direito
        rodape = QHBoxLayout()
        rodape.addStretch()
        btn_sobre = QPushButton("Sobre")
        btn_sobre.setObjectName("ghost")
        btn_sobre.clicked.connect(self._abrir_sobre)
        rodape.addWidget(btn_sobre)
        btn_tutorial = QPushButton("Tutorial / Como usar")
        btn_tutorial.setObjectName("ghost")
        btn_tutorial.clicked.connect(self._abrir_tutorial)
        rodape.addWidget(btn_tutorial)
        layout.addLayout(rodape)

    def _abrir_sobre(self):
        QMessageBox.about(
            self, "Sobre o Calligraphos",
            "<h3>Calligraphos</h3>"
            "<p>Sistema de reconhecimento e avaliacao de caligrafia "
            "desenvolvido como Trabalho de Conclusao de Curso.</p>"
            "<p>O programa transcreve texto manuscrito usando visao "
            "computacional (Google Cloud Vision) e avalia a qualidade da "
            "escrita de cada letra com uma rede neural convolucional "
            "(MobileNetV2) treinada com o dataset EMNIST.</p>"
            "<p><b>Desenvolvido por:</b> Lucca</p>",
        )

    def _abrir_tutorial(self):
        QMessageBox.information(
            self, "Como usar o Calligraphos",
            "<h3>Praticar Caligrafia</h3>"
            "<p>Treine as 26 letras do alfabeto (cada uma tem uma barra de "
            "progresso de 0 a 5) e complete fases de palavras com "
            "dificuldade crescente. Escreva o alvo em um papel, fotografe "
            "e envie - o sistema diz se voce acertou.</p>"
            "<h3>Analise Individual</h3>"
            "<p>Envie a foto de qualquer texto manuscrito (de uma palavra "
            "a uma redacao inteira). O sistema transcreve o texto e avalia "
            "cada letra: verde (boa), ambar (aceitavel) e vermelho "
            "(precisa melhorar).</p>"
            "<p>Clique em qualquer letra (na imagem ou na lista) para ver "
            "detalhes, corrigir a identificacao ou treinar aquela letra. "
            "Use os botoes Adicionar/Remover letra para ajustar deteccoes "
            "manualmente.</p>"
            "<h3>Dicas de foto</h3>"
            "<p>Use boa iluminacao, evite sombras e prefira letra de forma "
            "maiuscula para a avaliacao mais precisa.</p>",
        )


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Calligraphos - Reconhecimento e Avaliacao de Caligrafia")
        self.setMinimumSize(1180, 720)
        self.setStyleSheet(STYLE)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.sessao = None
        self.estado = None

        self.login = None
        self.onboarding = None
        self.inicio = None
        self.praticar = None
        self.analise = None
        self.config = None

        self._tentar_autologin()

    # ── Fluxo inicial ──────────────────────────────────────────────

    def _tentar_autologin(self):
        from auth_service import carregar_sessao
        sessao = carregar_sessao()
        if sessao:
            self._entrar_com_sessao(sessao)
        else:
            self._mostrar_login()

    def _mostrar_login(self):
        from login_widget import LoginWidget
        self.login = LoginWidget(permitir_pular=False)
        self.login.logado.connect(self._on_logado)
        self.stack.addWidget(self.login)
        self.stack.setCurrentWidget(self.login)

    def _on_logado(self, user):
        sessao = {
            "email": user.get("email"),
            "uid": user.get("localId"),
            "idToken": user.get("idToken"),
            "refreshToken": user.get("refreshToken"),
        }
        self._entrar_com_sessao(sessao)

    def _entrar_com_sessao(self, sessao):
        self.sessao = sessao
        import progresso as prog
        self.estado = prog.carregar(sessao["uid"])

        if not self.estado.get("onboarding_visto", False):
            self._mostrar_onboarding()
        else:
            self._mostrar_inicio()

    # ── Onboarding ─────────────────────────────────────────────────

    def _mostrar_onboarding(self):
        from onboarding_widget import OnboardingWidget
        self.onboarding = OnboardingWidget()
        self.onboarding.concluido.connect(self._on_onboarding_completo)
        self.onboarding.pular.connect(self._on_onboarding_completo)
        self.stack.addWidget(self.onboarding)
        self.stack.setCurrentWidget(self.onboarding)

    def _on_onboarding_completo(self):
        import progresso as prog
        prog.marcar_onboarding_visto(self.sessao["uid"], self.estado)
        self._mostrar_inicio()

    # ── Tela inicial ───────────────────────────────────────────────

    def _mostrar_inicio(self):
        if self.inicio is None:
            self.inicio = TelaInicial(
                self.sessao["email"],
                self._abrir_praticar,
                self._abrir_analise,
                self._abrir_config,
            )
            self.stack.addWidget(self.inicio)
        self.stack.setCurrentWidget(self.inicio)

    # ── Modos ──────────────────────────────────────────────────────

    def _abrir_praticar(self):
        if self.praticar is None:
            from praticar_widget import PraticarWidget
            self.praticar = PraticarWidget(self.sessao["uid"], self.estado)
            self.praticar.voltar_solicitado.connect(self._voltar_inicio)
            self.stack.addWidget(self.praticar)
        self.stack.setCurrentWidget(self.praticar)

    def _abrir_analise(self):
        if self.analise is None:
            from analise_widget import AnaliseWidget
            self.analise = AnaliseWidget(
                tem_conta=True,
                estado_progresso=self.estado,
            )
            self.analise.voltar_solicitado.connect(self._voltar_inicio)
            self.analise.treinar_letra.connect(self._pediu_treinar_letra)
            self.stack.addWidget(self.analise)
        else:
            self.analise.atualizar_estado_progresso(self.estado)
        self.stack.setCurrentWidget(self.analise)

    def _abrir_config(self):
        if self.config is None:
            from config_widget import ConfigWidget
            self.config = ConfigWidget(self.sessao, self.estado)
            self.config.voltar_solicitado.connect(self._voltar_inicio_reset_praticar)
            self.config.logout_solicitado.connect(self._sair)
            self.stack.addWidget(self.config)
        self.stack.setCurrentWidget(self.config)

    def _voltar_inicio(self):
        if self.analise is not None:
            self.analise.atualizar_estado_progresso(self.estado)
        self._mostrar_inicio()

    def _voltar_inicio_reset_praticar(self):
        if self.praticar is not None:
            self.stack.removeWidget(self.praticar)
            self.praticar.deleteLater()
            self.praticar = None
        self._mostrar_inicio()

    def _pediu_treinar_letra(self, letra):
        if self.praticar is None:
            from praticar_widget import PraticarWidget
            self.praticar = PraticarWidget(self.sessao["uid"], self.estado)
            self.praticar.voltar_solicitado.connect(self._voltar_inicio)
            self.stack.addWidget(self.praticar)
        self.stack.setCurrentWidget(self.praticar)
        self.praticar.abrir_letra_direto(letra)

    def _sair(self):
        from auth_service import logout
        logout()
        for w in (self.inicio, self.praticar, self.analise, self.config,
                  self.onboarding):
            if w is not None:
                self.stack.removeWidget(w)
                w.deleteLater()
        self.inicio = self.praticar = self.analise = None
        self.config = self.onboarding = None
        self.sessao = None
        self.estado = None
        self._mostrar_login()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
