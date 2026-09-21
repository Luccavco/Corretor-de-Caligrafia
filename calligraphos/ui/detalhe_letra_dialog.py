"""Dialog de detalhe de letra na Analise Individual.
Cenarios: letra identificada / letra '?' / adicao manual.
No modo de adicao manual o botao principal e apenas 'Adicionar' -
a sugestao de treino acontece depois, em quem chamou o dialog."""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QLineEdit, QWidget
)
from PyQt5.QtCore import Qt, pyqtSignal, QRegExp
from PyQt5.QtGui import QRegExpValidator

from calligraphos.ui.ui_theme import (
    C_BG, C_PANEL, C_CARD, C_TEXT, C_MUTED, C_BORDER, C_ACCENT, C_GOOD, C_OK, C_BAD, com_alpha, make_card,
)
from calligraphos.ui.ui_helpers import rotulo


class DetalheLetraDialog(QDialog):
    treinar_solicitado = pyqtSignal(str)
    letra_corrigida = pyqtSignal(int, str)
    letra_adicionada = pyqtSignal(str)     # so no modo adicao manual

    def __init__(self, letra, categoria, classe, confianca,
                 indice_caractere=None,
                 estado_letras=None,
                 tem_conta=True, parent=None,
                 modo_adicao_manual=False, resultado=None):
        super().__init__(parent)
        # `resultado` e o dicionario da letra devolvido pelo avaliador
        # (nota, legibilidade, formacao, medidas); None nos modos '?'/manual
        self.resultado = resultado
        self.letra = letra or "?"
        self.indice_caractere = indice_caractere
        self.estado_letras = estado_letras
        self.tem_conta = tem_conta
        self.modo_adicao_manual = modo_adicao_manual
        self.categoria = categoria
        self.classe = classe
        self.confianca = confianca
        self.letra_efetiva = self.letra

        self.setWindowTitle(
            "Adicionar letra manualmente" if modo_adicao_manual
            else "Detalhe da letra"
        )
        self.setFixedSize(440, 790 if resultado else 620)
        self.setStyleSheet(f"QDialog {{ background-color: {C_BG}; }}")
        self.setup_ui()

    def setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(14)

        self.lbl_letra_grande = QLabel(self.letra_efetiva)
        self.lbl_letra_grande.setAlignment(Qt.AlignCenter)
        self.lbl_letra_grande.setFixedHeight(120)
        self.lbl_letra_grande.setStyleSheet(
            f"color: {C_TEXT}; font-size: 88px; font-weight: 800;"
            f" font-family: 'Cambria', 'Georgia', serif;"
            f" background-color: {C_PANEL}; border: 1px solid {C_BORDER};"
            f" border-radius: 12px;"
        )
        root.addWidget(self.lbl_letra_grande)

        if self.modo_adicao_manual:
            root.addWidget(self._card_adicao_manual())
        elif self.letra == "?":
            root.addWidget(self._card_nao_identificada())
        else:
            root.addWidget(self._card_avaliacao())

        self.card_progresso = self._card_progresso()
        root.addWidget(self.card_progresso)
        self._atualizar_card_progresso()

        root.addWidget(self._card_correcao())
        root.addStretch(1)

        botoes = QHBoxLayout()
        botoes.setSpacing(10)
        btn_fechar = QPushButton("Fechar")
        btn_fechar.setObjectName("ghost")
        btn_fechar.clicked.connect(self.reject)
        botoes.addWidget(btn_fechar)

        self.btn_principal = QPushButton()
        self.btn_principal.setMinimumHeight(40)
        self.btn_principal.clicked.connect(self._acao_principal)
        botoes.addWidget(self.btn_principal, 1)
        root.addLayout(botoes)

        self._atualizar_botao_principal()

    # ── Cards ──────────────────────────────────────────────────────

    def _make_card(self, titulo, cor_borda=None):
        return make_card(None, titulo, margens=(16, 12, 16, 12), espacamento=6, raio=10,
                         cor_borda=cor_borda, fonte_titulo=10, espacamento_letras=1.2)

    def _card_avaliacao(self):
        card, lay = self._make_card("AVALIAÇÃO DA CALIGRAFIA")
        cores = {0: C_BAD, 1: C_OK, 2: C_GOOD}
        cor = cores.get(self.classe, C_MUTED)
        linha = QHBoxLayout()
        lbl_categoria = QLabel(self.categoria or "-")
        lbl_categoria.setStyleSheet(
            f"color: {cor}; font-size: 20px; font-weight: 800;"
            f" border: none; background: transparent;"
        )
        linha.addWidget(lbl_categoria)
        linha.addStretch()
        r = self.resultado
        texto_dir = f"nota {r['nota']:.0f}/100" if r else f"{self.confianca:.0%} de confiança"
        lbl_conf = rotulo(texto_dir, C_MUTED, 12)
        linha.addWidget(lbl_conf)
        lay.addLayout(linha)

        if r:
            from calligraphos.nucleo.handwriting_evaluator import explicar_letra
            itens = [("Legibilidade", r["legibilidade"]), ("Formação", r["formacao"])]
            nomes = {"iou": "Semelhança com o molde", "tracos": "Direção dos traços", "proporcao": "Proporção",
                     "inclinacao": "Inclinação", "espessura": "Regularidade do traço"}
            itens += [(nomes[k], v) for k, v in r["medidas"].items()]
            for nome, valor in itens:
                lay.addWidget(self._barra_medida(nome, valor))
            if r["classe"] < 2:
                dica = QLabel(f"Principal ponto: letra {explicar_letra(r)}.")
                dica.setWordWrap(True)
                dica.setStyleSheet(f"color: {C_MUTED}; font-size: 12px; border: none;")
                lay.addWidget(dica)
        return card

    def _barra_medida(self, nome, valor):
        wrap = QWidget()
        wrap.setObjectName("transparente")
        lay = QHBoxLayout(wrap)
        lay.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel(nome)
        lbl.setFixedWidth(170)
        lbl.setStyleSheet(f"color: {C_TEXT}; font-size: 12px; border: none;")
        barra = QProgressBar()
        barra.setRange(0, 100)
        barra.setValue(int(round(valor * 100)))
        barra.setTextVisible(False)
        barra.setFixedHeight(8)
        cor = C_GOOD if valor >= 0.75 else C_OK if valor >= 0.5 else C_BAD
        barra.setStyleSheet(f"QProgressBar::chunk {{ background-color: {cor}; border-radius: 3px; }}")
        lay.addWidget(lbl)
        lay.addWidget(barra, 1)
        return wrap

    def _card_nao_identificada(self):
        card, lay = self._make_card("LETRA NÃO IDENTIFICADA", cor_borda=f"{com_alpha(C_BAD, 0x55)}")
        aviso = QLabel(
            "O programa não conseguiu identificar essa letra automaticamente. "
            "Verifique se a imagem está com boa iluminação, foco e contraste. "
            "Caso o problema não seja a imagem, informe abaixo qual letra era "
            "para poder treina-la."
        )
        aviso.setWordWrap(True)
        aviso.setStyleSheet(f"color: {C_MUTED}; font-size: 12px; border: none;")
        lay.addWidget(aviso)
        return card

    def _card_adicao_manual(self):
        card, lay = self._make_card("ADICIONAR LETRA MANUAL", cor_borda=C_ACCENT)
        aviso = QLabel(
            "Você está adicionando uma letra que não foi detectada pela "
            "segmentação automática. Informe qual letra é abaixo e clique "
            "em Adicionar."
        )
        aviso.setWordWrap(True)
        aviso.setStyleSheet(f"color: {C_MUTED}; font-size: 12px; border: none;")
        lay.addWidget(aviso)
        return card

    def _card_progresso(self):
        card, lay = self._make_card("SEU PROGRESSO NESSA LETRA")
        self.lbl_status_prog = QLabel()
        self.lbl_status_prog.setStyleSheet(
            f"color: {C_ACCENT}; font-size: 16px; font-weight: 700;"
            f" border: none; background: transparent;"
        )
        lay.addWidget(self.lbl_status_prog)

        self.barra_prog = QProgressBar()
        self.barra_prog.setRange(0, 5)
        self.barra_prog.setTextVisible(False)
        self.barra_prog.setFixedHeight(8)
        lay.addWidget(self.barra_prog)
        return card

    def _card_correcao(self):
        titulo = "INFORME QUAL E A LETRA" if (
            self.letra == "?" or self.modo_adicao_manual
        ) else "CORRIGIR LETRA IDENTIFICADA"
        card, lay = self._make_card(titulo)

        dica = QLabel(
            "Se necessário, informe qual é a letra correta (apenas A-Z)."
            if not (self.letra == "?" or self.modo_adicao_manual)
            else "Digite a letra correspondente (apenas A-Z)."
        )
        dica.setWordWrap(True)
        dica.setStyleSheet(f"color: {C_MUTED}; font-size: 11px; border: none;")
        lay.addWidget(dica)

        linha = QHBoxLayout()
        self.input_letra = QLineEdit()
        self.input_letra.setMaxLength(1)
        self.input_letra.setAlignment(Qt.AlignCenter)
        self.input_letra.setValidator(QRegExpValidator(QRegExp("[A-Za-z]")))
        if self.letra != "?" and not self.modo_adicao_manual:
            self.input_letra.setText(self.letra)
        self.input_letra.setPlaceholderText("A")
        self.input_letra.setStyleSheet(
            f"QLineEdit {{ background-color: {C_CARD}; color: {C_TEXT};"
            f" border: 1px solid {C_BORDER}; border-radius: 8px;"
            f" padding: 10px; font-size: 22px; font-weight: 700; }}"
            f"QLineEdit:focus {{ border: 1px solid {C_ACCENT}; }}"
        )
        self.input_letra.setFixedWidth(70)
        self.input_letra.textChanged.connect(self._on_input_mudou)
        self.input_letra.returnPressed.connect(self._aplicar_correcao)
        linha.addWidget(self.input_letra)

        self.btn_aplicar = QPushButton("Aplicar")
        self.btn_aplicar.clicked.connect(self._aplicar_correcao)
        linha.addWidget(self.btn_aplicar)
        linha.addStretch()
        lay.addLayout(linha)
        return card

    # ── Comportamento ──────────────────────────────────────────────

    def _nivel_da_letra(self, letra):
        if not self.estado_letras:
            return None
        return self.estado_letras.get(letra, 0)

    def _atualizar_card_progresso(self):
        letra = self.letra_efetiva.upper() if self.letra_efetiva else "?"
        nivel = self._nivel_da_letra(letra) if letra != "?" else None
        if self.tem_conta and letra != "?" and nivel is not None:
            self.card_progresso.setVisible(True)
            texto = "Dominada" if nivel >= 5 else f"Nível {nivel} de 5"
            cor = C_GOOD if nivel >= 5 else C_ACCENT
            self.lbl_status_prog.setText(texto)
            self.lbl_status_prog.setStyleSheet(
                f"color: {cor}; font-size: 16px; font-weight: 700;"
                f" border: none; background: transparent;"
            )
            self.barra_prog.setValue(nivel)
            self.barra_prog.setStyleSheet(
                f"QProgressBar {{ background-color: {C_CARD}; border: none;"
                f" border-radius: 4px; }}"
                f"QProgressBar::chunk {{ background-color: {cor}; border-radius: 4px; }}"
            )
        else:
            self.card_progresso.setVisible(False)

    def _atualizar_botao_principal(self):
        letra = self.letra_efetiva.upper() if self.letra_efetiva else "?"
        valida = letra and letra != "?" and letra.isalpha()

        if self.modo_adicao_manual:
            texto_ok = "Adicionar"
            texto_off = "Informe a letra para adicionar"
        else:
            texto_ok = f"Treinar a letra {letra}"
            texto_off = "Informe a letra para treinar"

        if valida:
            self.btn_principal.setText(texto_ok)
            self.btn_principal.setEnabled(True)
            self.btn_principal.setStyleSheet(
                f"QPushButton {{ background-color: {C_ACCENT}; color: #fff;"
                f" border: none; border-radius: 8px; padding: 10px 16px;"
                f" font-size: 13px; font-weight: 700; }}"
                f"QPushButton:hover {{ background-color: #62adff; }}"
            )
        else:
            self.btn_principal.setText(texto_off)
            self.btn_principal.setEnabled(False)
            self.btn_principal.setStyleSheet(
                f"QPushButton {{ background-color: {C_CARD}; color: {C_MUTED};"
                f" border: 1px solid {C_BORDER}; border-radius: 8px;"
                f" padding: 10px 16px; font-size: 13px; font-weight: 600; }}"
            )

    def _on_input_mudou(self, texto):
        letra = (texto or "").strip().upper()
        self.btn_aplicar.setEnabled(bool(letra) and letra.isalpha())
        # No modo adicao, digitar ja habilita o botao principal apos Aplicar;
        # para agilizar, aplicamos automaticamente quando ha letra valida
        if self.modo_adicao_manual and letra and letra.isalpha():
            self.letra_efetiva = letra
            self.lbl_letra_grande.setText(letra)
            self._atualizar_card_progresso()
            self._atualizar_botao_principal()

    def _aplicar_correcao(self):
        letra_nova = (self.input_letra.text() or "").strip().upper()
        if not letra_nova or not letra_nova.isalpha():
            return
        self.letra_efetiva = letra_nova
        self.lbl_letra_grande.setText(letra_nova)
        if self.indice_caractere is not None:
            self.letra_corrigida.emit(self.indice_caractere, letra_nova)
        self._atualizar_card_progresso()
        self._atualizar_botao_principal()

    def _acao_principal(self):
        letra = self.letra_efetiva.upper() if self.letra_efetiva else ""
        if not (letra and letra != "?" and letra.isalpha()):
            return
        if self.modo_adicao_manual:
            self.letra_adicionada.emit(letra)
        else:
            self.treinar_solicitado.emit(letra)
        self.accept()
