"""Modo Praticar Caligrafia: cabecalho, abas (QTabWidget) e troca para o painel de
exercicio; registra acertos, tentativas e conquistas no progresso."""

import random
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTabWidget, QStackedWidget, QMessageBox
from PyQt5.QtCore import pyqtSignal
from calligraphos.ui.ui_theme import C_TEXT, C_MUTED
from calligraphos.ui.ui_helpers import rotulo
from calligraphos.nuvem import progresso as prog
from calligraphos.ui.praticar.aba_dicionario import AbaDicionario
from calligraphos.ui.praticar.aba_letras import AbaLetras
from calligraphos.ui.praticar.aba_palavras import AbaPalavras
from calligraphos.ui.praticar.aba_progresso import AbaProgresso
from calligraphos.ui.praticar.aba_quiz import AbaQuiz
from calligraphos.ui.praticar.constantes import FASES, LETRAS
from calligraphos.ui.praticar.exercicio import PainelExercicio
from calligraphos.ui.praticar.gerenciar_palavras import GerenciarPalavrasDialog


class PraticarWidget(QWidget):
    voltar_solicitado = pyqtSignal()

    def __init__(self, uid, estado):
        super().__init__()
        self.uid = uid
        self.estado = estado

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 14, 18, 16)
        root.setSpacing(12)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        btn_voltar = QPushButton("Voltar")
        btn_voltar.setObjectName("ghost")
        btn_voltar.setFixedWidth(90)
        btn_voltar.clicked.connect(self._voltar_ao_inicio)
        header.addWidget(btn_voltar)

        titulo = QLabel("Praticar Caligrafia")
        titulo.setStyleSheet(f"font-size: 20px; font-weight: 800; color: {C_TEXT};")
        sub = rotulo("Treine sua escrita com exercícios guiados", C_MUTED, 14)
        header.addSpacing(10)
        header.addWidget(titulo)
        header.addSpacing(12)
        header.addWidget(sub)
        header.addStretch()
        root.addLayout(header)

        self.stack = QStackedWidget()
        root.addWidget(self.stack, 1)

        self.menu = QTabWidget()
        self.aba_letras = AbaLetras(self.uid, self.estado)
        self.aba_letras.letra_selecionada.connect(self.iniciar_letra)
        self.aba_palavras = AbaPalavras(self.estado)
        self.aba_palavras.fase_selecionada.connect(self.iniciar_fase)
        self.aba_palavras.fase_custom_selecionada.connect(self.iniciar_fase_custom)
        self.aba_palavras.gerenciar_solicitado.connect(self.abrir_gerenciador)
        self.aba_quiz = AbaQuiz(self.estado)
        self.aba_quiz.quiz_selecionado.connect(self.iniciar_quiz)
        self.aba_dicionario = AbaDicionario(self.uid, self.estado)
        self.aba_dicionario.treinar_palavra.connect(self._palavra_do_dicionario)
        self.aba_progresso = AbaProgresso(self.estado)
        self.menu.addTab(self.aba_letras, "Letras")
        self.menu.addTab(self.aba_palavras, "Palavras")
        self.menu.addTab(self.aba_quiz, "Quiz")
        self.menu.addTab(self.aba_dicionario, "Dicionário")
        self.menu.addTab(self.aba_progresso, "Progresso")
        self.menu.currentChanged.connect(self._aba_mudou)

        self.stack.addWidget(self.menu)
        self.painel_exercicio = None

    def _aba_mudou(self, indice):
        # Ao entrar na aba Progresso, reconstroi para refletir dados atuais
        if self.menu.widget(indice) is self.aba_progresso:
            self.aba_progresso.reconstruir()

    def _voltar_ao_inicio(self):
        if self.stack.currentWidget() != self.menu:
            self._voltar_menu()
        else:
            self.voltar_solicitado.emit()

    def _voltar_menu(self):
        self.aba_letras.reconstruir()
        self.aba_palavras.reconstruir()
        self.aba_quiz.reconstruir()
        self.aba_dicionario.reconstruir()
        self.aba_progresso.reconstruir()
        self.stack.setCurrentWidget(self.menu)
        if self.painel_exercicio is not None:
            self.stack.removeWidget(self.painel_exercicio)
            self.painel_exercicio.deleteLater()
            self.painel_exercicio = None

    def iniciar_letra(self, letra):
        self.painel_exercicio = PainelExercicio(
            titulo_alvo="ESCREVA A LETRA",
            alvos=[letra],
            modo="letra",
            nivel_atual=self.estado["letras"].get(letra, 0),
        )
        self.painel_exercicio.voltar.connect(self._voltar_menu)
        self.painel_exercicio.tentativa.connect(self._registrar_tentativa)
        self.painel_exercicio.acerto.connect(self._acertou_letra)
        self.stack.addWidget(self.painel_exercicio)
        self.stack.setCurrentWidget(self.painel_exercicio)

    def _registrar_tentativa(self, letra, nota):
        prog.registrar_tentativa(self.uid, self.estado, letra, nota)

    def _acertou_letra(self, letra):
        novas = prog.registrar_acerto_letra(self.uid, self.estado, letra)
        self._avisar_conquistas(novas)

    def _avisar_conquistas(self, novas):
        """Mostra um aviso quando o usuário desbloqueia conquistas."""
        if not novas:
            return
        nomes = {cid: titulo for cid, titulo, _d, _t in prog.CONQUISTAS}
        titulos = [nomes.get(cid, cid) for cid in novas]
        if len(titulos) == 1:
            texto = f"Você desbloqueou a conquista: {titulos[0]}!"
        else:
            texto = "Você desbloqueou novas conquistas:\n\n" + "\n".join(
                f"- {t}" for t in titulos
            )
        QMessageBox.information(self, "Nova conquista!", texto)

    def iniciar_fase(self, indice):
        fase = FASES[indice]
        self.painel_exercicio = PainelExercicio(
            titulo_alvo=f"FASE {indice + 1} - ESCREVA A PALAVRA",
            alvos=fase["palavras"],
            modo="fase",
        )
        self.painel_exercicio.voltar.connect(self._voltar_menu)
        self.painel_exercicio.tentativa.connect(self._registrar_tentativa)
        self.painel_exercicio.finalizou.connect(
            lambda i=indice: self._concluiu_fase(i)
        )
        self.stack.addWidget(self.painel_exercicio)
        self.stack.setCurrentWidget(self.painel_exercicio)

    def iniciar_fase_custom(self):
        palavras = list(self.estado.get("palavras_customizadas", []))
        if not palavras:
            return
        self.painel_exercicio = PainelExercicio(
            titulo_alvo="MINHAS PALAVRAS - ESCREVA A PALAVRA",
            alvos=palavras,
            modo="fase",
            custom=True,
        )
        self.painel_exercicio.voltar.connect(self._voltar_menu)
        self.painel_exercicio.tentativa.connect(self._registrar_tentativa)
        self.stack.addWidget(self.painel_exercicio)
        self.stack.setCurrentWidget(self.painel_exercicio)

    def iniciar_quiz(self, tipo):
        """Inicia um quiz de letras ou de palavras. Os itens sao
        sorteados em ordem aleatoria; a pessoa escreve cada um e ao
        final ve o total de acertos. Reaproveita o modo 'fase' do
        PainelExercicio (sequencia de alvos), mas embaralhada."""
        if tipo == "letras":
            itens = list(LETRAS)
            # Sorteia um subconjunto para o quiz nao ficar longo demais
            random.shuffle(itens)
            itens = itens[:10]
            titulo = "QUIZ DE LETRAS - ESCREVA A LETRA SORTEADA"
            tamanho_alvo = 200   # letra unica: alvo grande
        else:
            itens = list(self.estado.get("palavras_customizadas", []))
            if not itens:
                return
            random.shuffle(itens)
            titulo = "QUIZ DE PALAVRAS - ESCREVA A PALAVRA SORTEADA"
            tamanho_alvo = 84    # palavras: alvo menor para caber

        self.painel_exercicio = PainelExercicio(
            titulo_alvo=titulo,
            alvos=itens,
            modo="fase",     # sequencia de alvos, sem alterar niveis
            custom=True,     # nao desbloqueia fases nem conta progresso
            tamanho_alvo=tamanho_alvo,
        )
        self.painel_exercicio.voltar.connect(self._voltar_menu)
        self.painel_exercicio.tentativa.connect(self._registrar_tentativa)
        self.stack.addWidget(self.painel_exercicio)
        self.stack.setCurrentWidget(self.painel_exercicio)

    def _concluiu_fase(self, indice):
        novas = prog.registrar_fase_completa(self.uid, self.estado, indice + 1)
        self._avisar_conquistas(novas)

    def _palavra_do_dicionario(self, _palavra):
        """Quando o dicionario adiciona uma palavra, atualiza as abas que
        mostram a lista de palavras customizadas."""
        self.aba_palavras.reconstruir()
        self.aba_quiz.reconstruir()

    def abrir_gerenciador(self):
        dlg = GerenciarPalavrasDialog(self.uid, self.estado, parent=self)
        dlg.exec_()
        self.aba_palavras.reconstruir()

    def abrir_letra_direto(self, letra):
        if not self.estado.get("iniciou_letras", False):
            prog.marcar_iniciou_letras(self.uid, self.estado)
            self.aba_letras.reconstruir()
        self.menu.setCurrentIndex(0)
        if self.stack.currentWidget() != self.menu:
            self._voltar_menu()
        self.iniciar_letra(letra)
