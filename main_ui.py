"""Janela principal do Calligraphos. Coordena o fluxo:
- login (ou autologin)
- onboarding (na primeira vez)
- tela inicial com 2 modos + configuracoes + sobre/tutorial + idioma
- praticar / analise / configuracoes
"""

import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QStackedWidget, QFrame, QComboBox,
    QMessageBox, QSplashScreen, QSystemTrayIcon, QMenu, QAction
)
from PyQt5.QtGui import QCursor, QPixmap, QPainter, QColor, QFont, QIcon
from PyQt5.QtCore import Qt, QTimer, QThread

from ui_theme import (
    STYLE, C_PANEL, C_CARD, C_TEXT, C_MUTED, C_BORDER, C_ACCENT, C_BG,
    C_GOOD, C_OK,
)


def _caminho_icone():
    """Acha o calligraphos.png na raiz do projeto (mesma pasta deste
    arquivo). Devolve None se nao existir, para o app nao quebrar caso
    o icone ainda nao tenha sido copiado para a pasta."""
    caminho = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "calligraphos.png"
    )
    return caminho if os.path.exists(caminho) else None


def criar_splash():
    """Cria uma tela de abertura (splash) estilo Adobe: fundo escuro,
    nome do programa ao centro e uma mensagem de carregamento embaixo.
    Desenhada em memoria, sem depender de arquivo de imagem."""
    largura, altura = 560, 340
    pix = QPixmap(largura, altura)
    pix.fill(QColor(C_BG))

    painter = QPainter(pix)
    painter.setRenderHint(QPainter.Antialiasing)

    # Moldura sutil
    painter.setPen(QColor(C_BORDER))
    painter.drawRect(0, 0, largura - 1, altura - 1)

    # Nome do programa ao centro
    fonte_titulo = QFont("Cambria", 46, QFont.Bold)
    painter.setFont(fonte_titulo)
    painter.setPen(QColor(C_TEXT))
    painter.drawText(
        0, 90, largura, 80, Qt.AlignHCenter | Qt.AlignVCenter, "Calligraphos"
    )

    # Subtitulo
    fonte_sub = QFont("Arial", 13)
    painter.setFont(fonte_sub)
    painter.setPen(QColor(C_MUTED))
    painter.drawText(
        0, 170, largura, 30, Qt.AlignHCenter,
        "Reconhecimento e Avaliacao de Caligrafia"
    )

    # Linha de destaque
    painter.setPen(QColor(C_ACCENT))
    painter.drawLine(largura // 2 - 60, 215, largura // 2 + 60, 215)

    painter.end()

    splash = QSplashScreen(pix)
    splash.setWindowFlag(Qt.WindowStaysOnTopHint)
    return splash


class ModoCard(QFrame):
    def __init__(self, icone, titulo, descricao, on_click):
        super().__init__()
        self.on_click = on_click
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setFixedSize(360, 360)
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
    def __init__(self, email, estado, ir_para_praticar, ir_para_analise,
                 ir_para_config):
        super().__init__()
        self.estado = estado
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 24, 40, 24)
        layout.setSpacing(0)

        # Topo: idioma a esquerda, email + configuracoes a direita
        topo = QHBoxLayout()
        topo.setSpacing(10)
        lbl_idioma = QLabel("Idioma:")
        lbl_idioma.setStyleSheet(f"color: {C_MUTED}; font-size: 13px;")
        combo_idioma = QComboBox()
        combo_idioma.addItem("Português (BR)")
        combo_idioma.setToolTip("Outros idiomas serão adicionados futuramente")
        topo.addWidget(lbl_idioma)
        topo.addWidget(combo_idioma)
        topo.addStretch()
        lbl_email = QLabel(email)
        lbl_email.setStyleSheet(f"color: {C_MUTED}; font-size: 13px;")
        topo.addWidget(lbl_email)
        topo.addSpacing(6)
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

        layout.addSpacing(20)

        # Faixa de lembrete: meta diaria + revisoes pendentes
        faixa = self._faixa_lembrete()
        if faixa is not None:
            layout.addWidget(faixa, alignment=Qt.AlignHCenter)
            layout.addSpacing(20)

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

    def _faixa_lembrete(self):
        """Monta a faixa com meta diaria e revisoes pendentes. Devolve None
        se o usuario ainda nao comecou a praticar (nada a lembrar)."""
        import progresso as prog
        if self.estado is None:
            return None

        feitos, meta = prog.progresso_meta_diaria(self.estado)
        pendentes = prog.revisoes_pendentes(self.estado)

        # Nada a mostrar se o usuario nunca praticou nem tem meta relevante
        exercicios = self.estado.get("exercicios_feitos", 0)
        if exercicios == 0 and not pendentes:
            return None

        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background-color: {C_PANEL};"
            f" border: 1px solid {C_BORDER}; border-radius: 14px; }}"
        )
        card.setMaximumWidth(760)
        lay = QHBoxLayout(card)
        lay.setContentsMargins(24, 16, 24, 16)
        lay.setSpacing(30)

        # Bloco meta diaria
        bloco_meta = QVBoxLayout()
        bloco_meta.setSpacing(2)
        cumpriu = feitos >= meta
        cor_meta = C_ACCENT if not cumpriu else C_GOOD
        lbl_meta_val = QLabel(f"{feitos} / {meta}")
        lbl_meta_val.setStyleSheet(
            f"color: {cor_meta}; font-size: 22px; font-weight: 800;"
            f" border: none; background: transparent;"
        )
        bloco_meta.addWidget(lbl_meta_val)
        lbl_meta_rot = QLabel(
            "meta diaria cumprida!" if cumpriu else "exercicios hoje (meta diaria)"
        )
        lbl_meta_rot.setStyleSheet(
            f"color: {C_MUTED}; font-size: 12px; border: none;"
            f" background: transparent;"
        )
        bloco_meta.addWidget(lbl_meta_rot)
        lay.addLayout(bloco_meta)

        # Separador
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet(f"color: {C_BORDER}; background: {C_BORDER};")
        sep.setFixedWidth(1)
        lay.addWidget(sep)

        # Bloco revisoes pendentes
        bloco_rev = QVBoxLayout()
        bloco_rev.setSpacing(2)
        n_pend = len(pendentes)
        cor_rev = C_OK if n_pend > 0 else C_MUTED
        lbl_rev_val = QLabel(str(n_pend))
        lbl_rev_val.setStyleSheet(
            f"color: {cor_rev}; font-size: 22px; font-weight: 800;"
            f" border: none; background: transparent;"
        )
        bloco_rev.addWidget(lbl_rev_val)
        if n_pend > 0:
            texto_rev = (
                f"letra para revisar: {', '.join(pendentes)}" if n_pend <= 8
                else f"letras para revisar hoje"
            )
        else:
            texto_rev = "nenhuma revisao pendente"
        lbl_rev_rot = QLabel(texto_rev)
        lbl_rev_rot.setWordWrap(True)
        lbl_rev_rot.setStyleSheet(
            f"color: {C_MUTED}; font-size: 12px; border: none;"
            f" background: transparent;"
        )
        bloco_rev.addWidget(lbl_rev_rot)
        lay.addLayout(bloco_rev, 1)

        return card

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

        icone_path = _caminho_icone()
        if icone_path:
            self.setWindowIcon(QIcon(icone_path))

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

        # Controle da bandeja/lembrete diario
        self.tray = None
        self._avisou_bandeja = False   # avisa 1x que o app continua na bandeja
        self._saindo_de_verdade = False
        self._timer_lembrete = None

        self._configurar_bandeja()
        self._tentar_autologin()

    # ── Bandeja do sistema e lembrete diario ──────────────────────────

    def _configurar_bandeja(self):
        """Cria o icone na bandeja do sistema, com menu de acesso rapido.
        O app continua rodando ai mesmo com a janela fechada, para poder
        lembrar a pessoa de praticar mais tarde no dia."""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return   # ambiente sem bandeja (raro, mas nao pode quebrar o app)

        icone_path = _caminho_icone()
        icone = QIcon(icone_path) if icone_path else self.windowIcon()

        self.tray = QSystemTrayIcon(icone, self)
        self.tray.setToolTip("Calligraphos")

        menu = QMenu()
        acao_abrir = QAction("Abrir Calligraphos", self)
        acao_abrir.triggered.connect(self._mostrar_janela)
        menu.addAction(acao_abrir)

        acao_praticar = QAction("Praticar agora", self)
        acao_praticar.triggered.connect(self._praticar_pela_bandeja)
        menu.addAction(acao_praticar)

        menu.addSeparator()

        acao_sair = QAction("Sair", self)
        acao_sair.triggered.connect(self._sair_de_verdade)
        menu.addAction(acao_sair)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._bandeja_clicada)
        self.tray.show()

    def _bandeja_clicada(self, motivo):
        # Clique simples ou duplo alterna: mostra a janela
        if motivo in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self._mostrar_janela()

    def _mostrar_janela(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _praticar_pela_bandeja(self):
        self._mostrar_janela()
        if self.sessao is not None:
            self._abrir_praticar()

    def _sair_de_verdade(self):
        """Encerra o app de verdade (diferente de fechar a janela, que
        so minimiza para a bandeja)."""
        self._saindo_de_verdade = True
        if self.tray:
            self.tray.hide()
        QApplication.instance().quit()

    def closeEvent(self, event):
        # Fechar a janela (X) minimiza para a bandeja em vez de encerrar
        # o app - assim o lembrete diario continua funcionando mesmo com
        # a janela fechada. "Sair" no menu da bandeja encerra de verdade.
        if self._saindo_de_verdade or self.tray is None:
            event.accept()
            return
        event.ignore()
        self.hide()
        if not self._avisou_bandeja:
            self._avisou_bandeja = True
            self.tray.showMessage(
                "Calligraphos continua rodando",
                "O programa continua na bandeja do sistema. Clique no "
                "icone para abrir de novo, ou use 'Sair' para encerrar.",
                QSystemTrayIcon.Information,
                5000,
            )

    def _iniciar_lembrete_diario(self):
        """Configura a verificacao periodica da meta diaria (roda mesmo
        com a janela minimizada na bandeja)."""
        if self._timer_lembrete is None:
            self._timer_lembrete = QTimer(self)
            self._timer_lembrete.timeout.connect(self._verificar_lembrete_diario)
            self._timer_lembrete.start(3 * 60 * 60 * 1000)   # a cada 3 horas
        # Primeira checagem pouco depois do login
        QTimer.singleShot(4000, self._verificar_lembrete_diario)

    def _verificar_lembrete_diario(self):
        if self.tray is None or self.estado is None:
            return
        import progresso as prog
        feitos, meta = prog.progresso_meta_diaria(self.estado)
        if feitos < meta:
            faltam = meta - feitos
            self.tray.showMessage(
                "Hora de praticar!",
                f"Voce ainda nao bateu sua meta diaria. Faltam {faltam} "
                f"exercicio(s) para chegar em {meta}.",
                QSystemTrayIcon.Information,
                6000,
            )

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

        # Comeca a verificacao periodica da meta diaria (bandeja)
        self._iniciar_lembrete_diario()

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
        # Recria a tela inicial para a faixa de lembrete refletir o
        # progresso mais recente (meta diaria, revisoes pendentes)
        if self.inicio is not None:
            self.stack.removeWidget(self.inicio)
            self.inicio.deleteLater()
        self.inicio = TelaInicial(
            self.sessao["email"],
            self.estado,
            self._abrir_praticar,
            self._abrir_analise,
            self._abrir_config,
        )
        self.stack.addWidget(self.inicio)
        self.stack.setCurrentWidget(self.inicio)

    # ── Modos ──────────────────────────────────────────────────────

    def _abrir_praticar(self):
        if self.praticar is None:
            # Primeira abertura carrega o modulo: mostra cursor de espera
            QApplication.setOverrideCursor(Qt.WaitCursor)
            try:
                from praticar_widget import PraticarWidget
                self.praticar = PraticarWidget(self.sessao["uid"], self.estado)
                self.praticar.voltar_solicitado.connect(self._voltar_inicio)
                self.stack.addWidget(self.praticar)
            finally:
                QApplication.restoreOverrideCursor()
        self.stack.setCurrentWidget(self.praticar)

    def _abrir_analise(self):
        if self.analise is None:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            try:
                from analise_widget import AnaliseWidget
                self.analise = AnaliseWidget(
                    tem_conta=True,
                    estado_progresso=self.estado,
                )
                self.analise.voltar_solicitado.connect(self._voltar_inicio)
                self.analise.treinar_letra.connect(self._pediu_treinar_letra)
                self.stack.addWidget(self.analise)
            finally:
                QApplication.restoreOverrideCursor()
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


class PreCarregador(QThread):
    """Carrega em segundo plano as bibliotecas pesadas (OpenCV, PyTorch,
    Transformers) enquanto a splash screen aparece. O primeiro 'import'
    dessas bibliotecas e lento (varios segundos); depois de importadas
    uma vez, o Python guarda em cache e reusa instantaneamente. Isso
    elimina a demora perceptivel ao abrir Praticar ou Analise Individual
    pela primeira vez, porque quando o usuario clica, essas bibliotecas
    ja estao carregadas na memoria.

    So faz os IMPORTS (nada de carregar modelo nem criar janelas - isso
    continua acontecendo sob demanda, como antes)."""

    def run(self):
        try:
            import cv2          # noqa: F401
            import torch        # noqa: F401
            import transformers  # noqa: F401
        except Exception:
            # Se algo falhar aqui, nao tem problema: os imports normais
            # (mais lentos) acontecem de qualquer forma quando a pessoa
            # abrir Praticar ou Analise
            pass


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    # O app continua rodando na bandeja mesmo com a janela escondida
    # (fechar pelo X so minimiza; "Sair" no menu da bandeja e que encerra)
    app.setQuitOnLastWindowClosed(False)

    # Tela de abertura (splash) estilo Adobe
    splash = criar_splash()
    splash.show()
    splash.showMessage(
        "  Iniciando...", Qt.AlignBottom | Qt.AlignHCenter, QColor(C_MUTED)
    )
    app.processEvents()

    # Comeca a carregar as bibliotecas pesadas (OpenCV, PyTorch,
    # Transformers) EM PARALELO, enquanto a splash aparece e o Firebase
    # carrega a sessao. Isso e o que elimina o lag ao abrir Praticar ou
    # Analise Individual pela primeira vez - quando a pessoa clicar,
    # essas bibliotecas normalmente ja estarao prontas na memoria.
    precarregador = PreCarregador()
    precarregador.start()

    # A criacao da MainWindow dispara autologin, Firebase e imports pesados.
    # As mensagens dao a sensacao de progresso enquanto isso acontece.
    splash.showMessage(
        "  Carregando modulos...", Qt.AlignBottom | Qt.AlignHCenter, QColor(C_MUTED)
    )
    app.processEvents()

    window = MainWindow()

    splash.showMessage(
        "  Preparando interface...", Qt.AlignBottom | Qt.AlignHCenter, QColor(C_MUTED)
    )
    app.processEvents()

    # Garante um tempo minimo visivel da splash (sensacao de "programa pesado"
    # abrindo rapido) e entao troca para a janela principal
    def _exibir_janela_principal():
        window.show()
        splash.finish(window)

    QTimer.singleShot(1400, _exibir_janela_principal)
    sys.exit(app.exec_())
