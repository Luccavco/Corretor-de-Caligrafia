"""Aba Dicionario: busca de definicoes em segundo plano e adicao ao treino."""

import re
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFrame, QScrollArea, QLineEdit
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from calligraphos.ui.ui_helpers import cabecalho_aba, rotulo
from calligraphos.ui.ui_theme import C_CARD, C_PANEL, C_TEXT, C_MUTED, C_BORDER, C_ACCENT
from calligraphos.nuvem import progresso as prog


class DicionarioWorker(QThread):
    """Busca a definição em segundo plano para não travar a interface."""
    encontrado = pyqtSignal(object)   # dict ou None
    erro = pyqtSignal(str)

    def __init__(self, palavra):
        super().__init__()
        self.palavra = palavra

    def run(self):
        try:
            from calligraphos.nuvem import dicionario_service
            resultado = dicionario_service.buscar(self.palavra)
            self.encontrado.emit(resultado)
        except Exception as e:
            self.erro.emit(str(e))

class AbaDicionario(QWidget):
    """Aba de dicionario/glossario: a pessoa busca uma palavra, ve a
    definicao e os exemplos, e pode treina-la (adiciona em Minhas
    Palavras). Usa a API publica do Dicionario Aberto."""
    treinar_palavra = pyqtSignal(str)   # emite ao clicar em Treinar

    def __init__(self, uid, estado):
        super().__init__()
        self.uid = uid
        self.estado = estado
        self.worker = None
        self.palavra_atual = None
        self.setup_ui()

    def setup_ui(self):
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(20, 20, 20, 20)
        raiz.setSpacing(14)

        raiz.addWidget(
            cabecalho_aba("Dicionário", "busque uma palavra e adicione ao seu treino")
        )

        # Barra de busca
        busca_row = QHBoxLayout()
        self.input_busca = QLineEdit()
        self.input_busca.setPlaceholderText(
            "Pesquise uma palavra para ver seu significado..."
        )
        self.input_busca.setMinimumHeight(44)
        self.input_busca.setStyleSheet(
            f"QLineEdit {{ background-color: {C_CARD}; color: {C_TEXT};"
            f" border: 1px solid {C_BORDER}; border-radius: 10px;"
            f" padding: 10px 14px; font-size: 15px; }}"
            f"QLineEdit:focus {{ border: 1px solid {C_ACCENT}; }}"
        )
        self.input_busca.returnPressed.connect(self._buscar)
        busca_row.addWidget(self.input_busca, 1)

        self.btn_buscar = QPushButton("Buscar")
        self.btn_buscar.setObjectName("primary")
        self.btn_buscar.setMinimumHeight(44)
        self.btn_buscar.clicked.connect(self._buscar)
        busca_row.addWidget(self.btn_buscar)
        raiz.addLayout(busca_row)

        # Area de resultado (card)
        self.card_resultado = QFrame()
        self.card_resultado.setStyleSheet(
            f"QFrame {{ background-color: {C_PANEL};"
            f" border: 1px solid {C_BORDER}; border-radius: 12px; }}"
        )
        card_layout = QVBoxLayout(self.card_resultado)
        card_layout.setContentsMargins(24, 22, 24, 22)
        card_layout.setSpacing(14)

        self.lbl_palavra = QLabel("")
        self.lbl_palavra.setStyleSheet(
            f"color: {C_TEXT}; font-size: 30px; font-weight: 800;"
            f" border: none; font-family: 'Cambria', 'Georgia', serif;"
        )
        # Comeca escondido: sem isso, o espaco reservado para esse texto
        # (mesmo vazio) empurra a mensagem abaixo para mais longe do topo
        self.lbl_palavra.setVisible(False)
        card_layout.addWidget(self.lbl_palavra)

        self.lbl_status = QLabel(
            "Pesquise uma palavra para ver seu significado..."
        )
        self.lbl_status.setWordWrap(True)
        self.lbl_status.setStyleSheet(
            f"color: {C_MUTED}; font-size: 19px; font-weight: 500; border: none;"
        )
        card_layout.addWidget(self.lbl_status)

        # Scroll para definicao longa
        self.scroll_def = QScrollArea()
        self.scroll_def.setWidgetResizable(True)
        self.scroll_def.setStyleSheet("border: none; background: transparent;")
        self.def_container = QWidget()
        self.def_container.setObjectName("transparente")
        self.def_layout = QVBoxLayout(self.def_container)
        self.def_layout.setContentsMargins(0, 0, 0, 0)
        self.def_layout.setSpacing(12)
        self.def_layout.setAlignment(Qt.AlignTop)
        self.scroll_def.setWidget(self.def_container)
        card_layout.addWidget(self.scroll_def, 1)

        # Botao adicionar (so aparece quando ha uma palavra valida)
        self.btn_treinar = QPushButton()
        self.btn_treinar.setObjectName("primary")
        self.btn_treinar.setMinimumHeight(44)
        self.btn_treinar.setVisible(False)
        self.btn_treinar.clicked.connect(self._treinar)
        card_layout.addWidget(self.btn_treinar)

        raiz.addWidget(self.card_resultado, 1)

    # ── Busca ───────────────────────────────────────────────────────

    def _buscar(self):
        palavra = (self.input_busca.text() or "").strip()
        if len(palavra) < 2:
            return
        # Se ja ha uma busca em andamento, ignora (evita threads sobrepostas)
        if self.worker is not None and self.worker.isRunning():
            return
        self.btn_buscar.setEnabled(False)
        self.btn_treinar.setVisible(False)
        self.lbl_palavra.setText("")
        self.lbl_palavra.setVisible(False)
        self._limpar_definicao()
        self.lbl_status.setText("Buscando...")
        self.lbl_status.setVisible(True)

        self.worker = DicionarioWorker(palavra)
        self.worker.encontrado.connect(self._on_encontrado)
        self.worker.erro.connect(self._on_erro)
        self.worker.finished.connect(self._on_worker_fim)
        self.worker.start()

    def _on_worker_fim(self):
        # Libera a referencia quando a thread termina de fato
        self.worker = None

    def _limpar_definicao(self):
        while self.def_layout.count():
            item = self.def_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _on_encontrado(self, resultado):
        try:
            self.btn_buscar.setEnabled(True)
        except RuntimeError:
            return   # widget ja foi destruido
        if resultado is None:
            self.lbl_palavra.setText("")
            self.lbl_palavra.setVisible(False)
            self.lbl_status.setText(
                "Palavra não encontrada no dicionário, ou sem conexão com a "
                "internet. Verifique a grafia e tente novamente."
            )
            self.lbl_status.setVisible(True)
            self.btn_treinar.setVisible(False)
            return

        self.palavra_atual = resultado["palavra"]
        self.lbl_palavra.setText(resultado["palavra"])
        self.lbl_palavra.setVisible(True)
        self.lbl_status.setVisible(False)
        self._limpar_definicao()

        # Classe gramatical (quando a fonte fornece, ex: "substantivo feminino")
        classe = resultado.get("classe", "")
        if classe:
            lbl_classe = QLabel(classe)
            lbl_classe.setStyleSheet(
                f"color: {C_ACCENT}; font-size: 15px; font-weight: 700;"
                f" font-style: italic; border: none;"
            )
            self.def_layout.addWidget(lbl_classe)

        # Separa a definicao em: significados (acepcoes) e exemplos.
        # No Dicio, cada acepcao vem numa linha; a parte apos ':' costuma
        # ser um exemplo de uso.
        significados, exemplos = self._separar(resultado["definicao"])
        # Junta com os exemplos explicitos da fonte (Dicionario Aberto)
        exemplos = exemplos + list(resultado.get("exemplos", []))

        # ── BLOCO 1: SIGNIFICADO ──
        self.def_layout.addWidget(self._bloco_titulo("SIGNIFICADO"))
        card_sig = self._bloco_card()
        lay_sig = card_sig.layout()
        if significados:
            for i, s in enumerate(significados, 1):
                lbl = QLabel(f"{i}.  {s}")
                lbl.setWordWrap(True)
                lbl.setStyleSheet(
                    f"color: {C_TEXT}; font-size: 15px; border: none;"
                )
                lay_sig.addWidget(lbl)
        else:
            lbl = QLabel(resultado["definicao"])
            lbl.setWordWrap(True)
            lbl.setStyleSheet(
                f"color: {C_TEXT}; font-size: 15px; border: none;"
            )
            lay_sig.addWidget(lbl)
        self.def_layout.addWidget(card_sig)

        # ── BLOCO 2: EXEMPLOS DE USO ── (so se houver)
        if exemplos:
            self.def_layout.addWidget(self._bloco_titulo("EXEMPLOS DE USO"))
            card_ex = self._bloco_card()
            lay_ex = card_ex.layout()
            for ex in exemplos:
                lbl = QLabel(f"\u201c{ex}\u201d")
                lbl.setWordWrap(True)
                lbl.setStyleSheet(
                    f"color: {C_MUTED}; font-size: 14px; border: none;"
                    f" font-style: italic;"
                )
                lay_ex.addWidget(lbl)
            self.def_layout.addWidget(card_ex)

        # Rodape com a fonte
        fonte = resultado.get("fonte", "")
        if fonte:
            lbl_fonte = rotulo(f"Fonte: {fonte}", C_MUTED, 11)
            self.def_layout.addWidget(lbl_fonte)

        # Botao de adicionar (so para palavra unica, sem espacos)
        if self.palavra_atual and self.palavra_atual.isalpha():
            self.btn_treinar.setVisible(True)
            ja_tem = self.palavra_atual in self.estado.get(
                "palavras_customizadas", []
            )
            if ja_tem:
                self.btn_treinar.setText("Já está em Minhas Palavras")
                self.btn_treinar.setEnabled(False)
            else:
                # 'Minhas Palavras' em negrito via HTML
                self.btn_treinar.setText("Adicionar em Minhas Palavras")
                self.btn_treinar.setEnabled(True)
        else:
            self.btn_treinar.setVisible(False)

    def _bloco_titulo(self, texto):
        lbl = QLabel(texto)
        lbl.setStyleSheet(
            f"color: {C_MUTED}; font-size: 12px; font-weight: 700;"
            f" letter-spacing: 1.4px; border: none;"
        )
        return lbl

    def _bloco_card(self):
        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background-color: {C_CARD};"
            f" border: 1px solid {C_BORDER}; border-radius: 10px; }}"
        )
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(10)
        return card

    def _separar(self, definicao):
        """Divide o texto da definicao em (significados, exemplos).
        Cada acepcao costuma vir em uma linha; a parte apos ':' geralmente
        e um exemplo de uso, entao a separamos."""
        significados, exemplos = [], []
        linhas = [ln.strip() for ln in definicao.split("\n") if ln.strip()]
        # Se veio tudo numa linha so, tenta quebrar por ponto final
        if len(linhas) == 1:
            linhas = [p.strip() for p in re.split(r"(?<=\.)\s+", linhas[0]) if p.strip()]
        for ln in linhas:
            if ":" in ln:
                antes, depois = ln.split(":", 1)
                antes = antes.strip()
                depois = depois.strip().rstrip(".")
                if antes:
                    significados.append(antes + ".")
                if depois:
                    exemplos.append(depois)
            else:
                significados.append(ln)
        return significados, exemplos

    def _on_erro(self, _mensagem):
        self.btn_buscar.setEnabled(True)
        self.lbl_status.setText(
            "Não foi possível buscar agora. Verifique sua conexão e tente de novo."
        )
        self.lbl_status.setVisible(True)

    def _treinar(self):
        if not self.palavra_atual:
            return
        ok = prog.adicionar_palavra_customizada(
            self.uid, self.estado, self.palavra_atual
        )
        if ok:
            self.btn_treinar.setText("Adicionada a Minhas Palavras!")
            self.btn_treinar.setEnabled(False)
            self.treinar_palavra.emit(self.palavra_atual)

    def reconstruir(self):
        # Atualiza o estado do botao treinar caso a lista tenha mudado
        if self.palavra_atual:
            ja_tem = self.palavra_atual in self.estado.get(
                "palavras_customizadas", []
            )
            if ja_tem and self.btn_treinar.isVisible():
                self.btn_treinar.setText("Já está em Minhas Palavras")
                self.btn_treinar.setEnabled(False)
