"""Modo Analise Individual com:
- Letras identificadas pelo Google Vision simbolo a simbolo
- Correcao de letra (I -> L) via popup
- Adicao manual de letras nao detectadas (botao Adicionar letra)
- Remocao de letras erradas (botao Remover letra + clique no chip,
  com confirmacao)
"""

import os
import cv2
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFileDialog, QTextEdit, QProgressBar, QScrollArea, QGridLayout,
    QSizePolicy, QComboBox, QApplication, QMessageBox,
    QDialog, QListWidget, QListWidgetItem, QStackedWidget
)
from PyQt5.QtGui import QPixmap, QImage, QCursor
from PyQt5.QtCore import Qt, QThread, pyqtSignal

from image_pipeline import (
    annotate_image, characters_from_boxes, annotate_from_characters,
)
from handwriting_evaluator import avaliar_texto, gerar_relatorio

from ui_theme import (
    C_CARD, C_TEXT, C_MUTED, C_BORDER, C_GOOD, C_OK, C_BAD, C_ACCENT,
    make_card, stat_chip, com_alpha,
)
from detalhe_letra_dialog import DetalheLetraDialog


class AnaliseWorker(QThread):
    finished = pyqtSignal(str, object, object, object)
    error = pyqtSignal(str)

    def __init__(self, image_path, motor):
        super().__init__()
        self.image_path = image_path
        self.motor = motor

    def run(self):
        try:
            if self.motor == "google":
                from htr_google import predict_detailed
                texto, simbolos = predict_detailed(self.image_path)
                boxes = [(s["x"], s["y"], s["w"], s["h"]) for s in simbolos]
                characters = characters_from_boxes(self.image_path, boxes)
                avaliacao = avaliar_texto(characters)
                letras = {i: s["letra"] for i, s in enumerate(simbolos)}
                anotada = annotate_from_characters(self.image_path, avaliacao)
                self.finished.emit(texto, avaliacao, anotada, letras)
            else:
                # TrOCR offline: analisa APENAS uma palavra isolada.
                from image_pipeline import first_word_data
                from htr_engine import predict
                dados = first_word_data(self.image_path)
                if dados is None:
                    raise RuntimeError("Nenhuma palavra detectada na imagem.")
                if dados == "SENTENCA":
                    # Sinaliza erro especifico para a interface oferecer
                    # a troca para o Google Vision
                    self.error.emit("__SENTENCA__")
                    return
                pil_word, characters = dados
                texto = predict(pil_word).strip().strip(".")
                avaliacao = avaliar_texto(characters)
                anotada = annotate_image(self.image_path, avaliacao)
                self.finished.emit(texto, avaliacao, anotada, None)
        except Exception as e:
            self.error.emit(str(e))


class LetraChip(QLabel):
    clicado = pyqtSignal(int)

    def __init__(self, indice, letra_reconhecida, cor, texto_visivel):
        super().__init__(texto_visivel)
        self.indice = indice
        self.letra_reconhecida = letra_reconhecida
        self.setAlignment(Qt.AlignCenter)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setStyleSheet(
            f"background-color: {com_alpha(cor, 0x18)}; color: {cor};"
            f" border: 1px solid {com_alpha(cor, 0x45)}; border-radius: 6px;"
            f" padding: 6px 4px; font-size: 11px; font-weight: 600;"
        )
        if letra_reconhecida and letra_reconhecida != "?":
            self.setToolTip(f"Letra: {letra_reconhecida}  (clique para ver detalhes)")
        else:
            self.setToolTip("Letra não identificada  (clique para ver detalhes)")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicado.emit(self.indice)


class ImagemClicavel(QLabel):
    clicou_para_adicionar = pyqtSignal(int, int)
    clicou_selecao = pyqtSignal(int, int)   # clique normal (selecionar caixa)

    def __init__(self):
        super().__init__()
        self.modo_adicionar = False
        self.pixmap_original = None
        self.escala_atual = 1.0
        self.offset_x = 0
        self.offset_y = 0

    def setImagemOriginal(self, qimg):
        self.pixmap_original = QPixmap.fromImage(qimg)
        self._reexibir()

    def setModoAdicionar(self, ativo):
        self.modo_adicionar = ativo
        self.setCursor(QCursor(Qt.CrossCursor if ativo else Qt.ArrowCursor))

    def _reexibir(self):
        if self.pixmap_original is None:
            return
        w_disp = max(1, self.width() - 12)
        h_disp = max(1, self.height() - 12)
        escalado = self.pixmap_original.scaled(
            w_disp, h_disp, Qt.KeepAspectRatio, Qt.SmoothTransformation,
        )
        self.escala_atual = escalado.width() / self.pixmap_original.width()
        self.offset_x = (self.width() - escalado.width()) // 2
        self.offset_y = (self.height() - escalado.height()) // 2
        self.setPixmap(escalado)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reexibir()

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton or self.pixmap_original is None:
            return
        x_widget = event.x() - self.offset_x
        y_widget = event.y() - self.offset_y
        esc_w = self.pixmap_original.width() * self.escala_atual
        esc_h = self.pixmap_original.height() * self.escala_atual
        if not (0 <= x_widget <= esc_w and 0 <= y_widget <= esc_h):
            return
        x_orig = int(x_widget / self.escala_atual)
        y_orig = int(y_widget / self.escala_atual)
        if self.modo_adicionar:
            self.clicou_para_adicionar.emit(x_orig, y_orig)
        else:
            self.clicou_selecao.emit(x_orig, y_orig)


class AnaliseWidget(QWidget):
    voltar_solicitado = pyqtSignal()
    treinar_letra = pyqtSignal(str)

    def __init__(self, tem_conta=True, estado_progresso=None):
        super().__init__()
        self.tem_conta = tem_conta
        self.estado_progresso = estado_progresso
        self.image_path = None
        self.worker = None
        self.texto_atual = ""
        self.avaliacao_atual = None
        self.letras_por_indice = {}
        self.letras_manuais = []
        self.imagem_processada_bgr = None
        self.modo_adicionar_ativo = False
        self.modo_remover_ativo = False
        self.motor_usado = "google"
        self.indice_destacado = None      # caixa automatica destacada
        self.manual_destacado = None      # caixa manual destacada
        self.setAcceptDrops(True)
        self.setup_ui()

    def atualizar_estado_progresso(self, estado_progresso):
        self.estado_progresso = estado_progresso

    def _estado_letras(self):
        if self.tem_conta and self.estado_progresso:
            return self.estado_progresso.get("letras")
        return None

    def setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 14, 18, 16)
        root.setSpacing(12)

        header = QHBoxLayout()
        btn_voltar = QPushButton("Voltar")
        btn_voltar.setObjectName("ghost")
        btn_voltar.setFixedWidth(90)
        btn_voltar.clicked.connect(self.voltar_solicitado.emit)
        header.addWidget(btn_voltar)

        titulo = QLabel("Análise Individual")
        titulo.setStyleSheet(f"font-size: 20px; font-weight: 800; color: {C_TEXT};")
        sub = QLabel("Carregue uma imagem para transcrever e avaliar a caligrafia")
        sub.setStyleSheet(f"color: {C_MUTED}; font-size: 14px;")
        # O subtitulo pode encolher (e ser cortado) em janelas estreitas,
        # em vez de forcar a largura minima da tela inteira
        sub.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        header.addSpacing(10)
        header.addWidget(titulo)
        header.addSpacing(12)
        header.addWidget(sub, 1)
        header.addSpacing(12)

        lbl_motor = QLabel("Motor de HTR:")
        lbl_motor.setStyleSheet(f"color: {C_MUTED}; font-size: 13px;")
        self.combo_motor = QComboBox()
        self.combo_motor.addItem("Google Vision (online)", "google")
        self.combo_motor.addItem("TrOCR - palavra única (offline)", "trocr")
        self.combo_motor.currentIndexChanged.connect(self._on_motor_mudou)
        header.addWidget(lbl_motor)
        header.addWidget(self.combo_motor)
        root.addLayout(header)

        body = QHBoxLayout()
        body.setSpacing(12)
        root.addLayout(body, 1)

        left_card, left = make_card(None)
        body.addWidget(left_card, 58)

        # Alterna entre o quadro de desenho e a imagem (carregada/analisada)
        from canvas_desenho import CanvasDesenho
        self.stack_esquerda = QStackedWidget()

        self.canvas = CanvasDesenho()
        self.canvas.desenhou.connect(self._on_desenhou)

        self.label_imagem = ImagemClicavel()
        self.label_imagem.setAlignment(Qt.AlignCenter)
        self.label_imagem.setMinimumSize(420, 360)
        self.label_imagem.setText(
            "Arraste uma imagem aqui\nou clique em Carregar Imagem"
        )
        self.label_imagem.setStyleSheet(
            f"background-color: {C_CARD}; color: {C_MUTED};"
            f" border: 2px dashed {C_BORDER}; border-radius: 10px; font-size: 14px;"
        )
        self.label_imagem.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.label_imagem.clicou_para_adicionar.connect(self._adicionar_letra_no_ponto)
        self.label_imagem.clicou_selecao.connect(self._clicou_na_imagem)

        self.stack_esquerda.addWidget(self.canvas)        # indice 0 = desenho
        self.stack_esquerda.addWidget(self.label_imagem)  # indice 1 = imagem
        self.stack_esquerda.setCurrentIndex(0)
        left.addWidget(self.stack_esquerda, 1)

        legenda = QHBoxLayout()
        legenda.setSpacing(8)
        legenda.addWidget(stat_chip(C_GOOD, "Boa"))
        legenda.addWidget(stat_chip(C_OK, "Aceitável"))
        legenda.addWidget(stat_chip(C_BAD, "Precisa melhorar"))
        legenda.addStretch()

        self.btn_toggle_adicionar = QPushButton("Adicionar letra")
        self.btn_toggle_adicionar.setCheckable(True)
        self.btn_toggle_adicionar.setEnabled(False)
        self.btn_toggle_adicionar.setToolTip(
            "Ative e clique na imagem para adicionar uma letra não detectada"
        )
        self.btn_toggle_adicionar.clicked.connect(self._toggle_modo_adicionar)
        legenda.addWidget(self.btn_toggle_adicionar)

        self.btn_toggle_remover = QPushButton("Remover letra")
        self.btn_toggle_remover.setCheckable(True)
        self.btn_toggle_remover.setEnabled(False)
        self.btn_toggle_remover.setToolTip(
            "Ative e clique em uma letra no Detalhe por Letra para remove-la"
        )
        self.btn_toggle_remover.clicked.connect(self._toggle_modo_remover)
        legenda.addWidget(self.btn_toggle_remover)
        left.addLayout(legenda)

        botoes_img = QHBoxLayout()
        self.btn_carregar = QPushButton("Carregar Imagem")
        self.btn_carregar.clicked.connect(self.carregar_imagem)
        self.btn_voltar_quadro = QPushButton("Voltar ao Quadro")
        self.btn_voltar_quadro.setVisible(False)
        self.btn_voltar_quadro.clicked.connect(self._voltar_ao_quadro)
        self.btn_analisar = QPushButton("Analisar")
        self.btn_analisar.setObjectName("primary")
        self.btn_analisar.clicked.connect(self.analisar)
        botoes_img.addWidget(self.btn_carregar)
        botoes_img.addWidget(self.btn_voltar_quadro)
        botoes_img.addWidget(self.btn_analisar)
        left.addLayout(botoes_img)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setRange(0, 0)
        self.progress.setTextVisible(False)
        left.addWidget(self.progress)

        right = QVBoxLayout()
        right.setSpacing(12)
        body.addLayout(right, 42)

        score_card, score_layout = make_card(None, "PONTUAÇÃO GERAL")
        self.label_score = QLabel("--")
        self.label_score.setStyleSheet(
            f"font-size: 44px; font-weight: 800; color: {C_TEXT}; border: none;"
        )
        score_layout.addWidget(self.label_score)

        chips = QHBoxLayout()
        chips.setSpacing(8)
        self.chip_boas = stat_chip(C_GOOD, "0 boas")
        self.chip_ok = stat_chip(C_OK, "0 aceitáveis")
        self.chip_ruins = stat_chip(C_BAD, "0 a melhorar")
        chips.addWidget(self.chip_boas)
        chips.addWidget(self.chip_ok)
        chips.addWidget(self.chip_ruins)
        chips.addStretch()
        score_layout.addLayout(chips)
        right.addWidget(score_card)

        texto_card, texto_layout = make_card(None)
        head_texto = QHBoxLayout()
        lbl_tit_texto = QLabel("TEXTO RECONHECIDO")
        lbl_tit_texto.setStyleSheet(
            f"color: {C_MUTED}; font-size: 13px; font-weight: 700;"
            f" letter-spacing: 1px; border: none;"
        )
        head_texto.addWidget(lbl_tit_texto)
        head_texto.addStretch()
        self.btn_expandir_texto = QPushButton("Expandir")
        self.btn_expandir_texto.setObjectName("ghost")
        self.btn_expandir_texto.setEnabled(False)
        self.btn_expandir_texto.setToolTip(
            "Abre o texto em uma janela maior com verificação ortográfica"
        )
        self.btn_expandir_texto.clicked.connect(self._expandir_texto)
        head_texto.addWidget(self.btn_expandir_texto)
        texto_layout.addLayout(head_texto)
        self.texto_resultado = QTextEdit()
        self.texto_resultado.setReadOnly(True)
        self.texto_resultado.setPlaceholderText("O texto transcrito aparecerá aqui...")
        self.texto_resultado.setMinimumHeight(140)
        texto_layout.addWidget(self.texto_resultado)
        right.addWidget(texto_card)

        detalhe_card, detalhe_layout = make_card(None)
        head_det = QHBoxLayout()
        lbl_tit_det = QLabel("DETALHE POR LETRA")
        lbl_tit_det.setStyleSheet(
            f"color: {C_MUTED}; font-size: 13px; font-weight: 700;"
            f" letter-spacing: 1px; border: none;"
        )
        head_det.addWidget(lbl_tit_det)
        head_det.addStretch()
        self.btn_expandir_detalhe = QPushButton("Expandir")
        self.btn_expandir_detalhe.setObjectName("ghost")
        self.btn_expandir_detalhe.setEnabled(False)
        self.btn_expandir_detalhe.setToolTip(
            "Abre o detalhe por letra em uma janela maior"
        )
        self.btn_expandir_detalhe.clicked.connect(self._expandir_detalhe)
        head_det.addWidget(self.btn_expandir_detalhe)
        detalhe_layout.addLayout(head_det)
        self.hint_detalhe = QLabel("Clique em uma letra para ver detalhes")
        self.hint_detalhe.setStyleSheet(
            f"color: {C_MUTED}; font-size: 13px; border: none;"
        )
        detalhe_layout.addWidget(self.hint_detalhe)

        self.scroll_detalhe = QScrollArea()
        self.scroll_detalhe.setWidgetResizable(True)
        self.detalhe_container = QWidget()
        self.detalhe_container.setObjectName("transparente")
        self.detalhe_grid = QGridLayout(self.detalhe_container)
        self.detalhe_grid.setSpacing(6)
        self.detalhe_grid.setAlignment(Qt.AlignTop)
        self.scroll_detalhe.setWidget(self.detalhe_container)
        detalhe_layout.addWidget(self.scroll_detalhe)
        right.addWidget(detalhe_card, 1)

        acoes = QHBoxLayout()
        self.btn_copiar = QPushButton("Copiar Texto")
        self.btn_copiar.setEnabled(False)
        self.btn_copiar.clicked.connect(self.copiar_texto)
        self.btn_salvar = QPushButton("Salvar Relatório")
        self.btn_salvar.setEnabled(False)
        self.btn_salvar.clicked.connect(self.salvar_relatorio)
        acoes.addWidget(self.btn_copiar)
        acoes.addWidget(self.btn_salvar)
        right.addLayout(acoes)

    def _on_motor_mudou(self, _idx):
        if self.combo_motor.currentData() == "trocr":
            QMessageBox.information(
                self, "Modo palavra única",
                "O modo TrOCR (offline) analisa APENAS a primeira palavra "
                "da imagem.\n\n"
                "Para melhores resultados, fotografe uma única palavra em "
                "letra de forma. Para textos completos, use o Google Vision.",
            )

    # ── Drag & drop ─────────────────────────────────────────────────

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            path = event.mimeData().urls()[0].toLocalFile()
            if path.lower().endswith((".png", ".jpg", ".jpeg")):
                event.acceptProposedAction()

    def dropEvent(self, event):
        path = event.mimeData().urls()[0].toLocalFile()
        self.definir_imagem(path)

    # ── Acoes basicas ───────────────────────────────────────────────

    def _on_desenhou(self):
        """Primeiro traço no quadro: habilita o botão Analisar."""
        self.btn_analisar.setEnabled(True)

    def _voltar_ao_quadro(self):
        """Volta a exibir o quadro de desenho (some a imagem analisada)."""
        self.image_path = None
        self.imagem_processada_bgr = None
        self.letras_por_indice = {}
        self.letras_manuais = []
        self.stack_esquerda.setCurrentIndex(0)
        self.btn_voltar_quadro.setVisible(False)
        self.btn_toggle_adicionar.setEnabled(False)
        self.btn_toggle_remover.setEnabled(False)
        self._desativar_modos()
        self.texto_resultado.clear()
        self.label_score.setText("--")
        self.limpar_detalhe()
        self.atualizar_chips(None)
        self.btn_analisar.setEnabled(not self.canvas.esta_vazio())

    def carregar_imagem(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Selecionar Imagem", "",
            "Imagens (*.png *.jpg *.jpeg)"
        )
        if path:
            self.definir_imagem(path)

    def definir_imagem(self, path):
        self.image_path = path
        self.letras_por_indice = {}
        self.letras_manuais = []
        self.imagem_processada_bgr = None
        pixmap = QPixmap(path)
        self.label_imagem.setImagemOriginal(pixmap.toImage())
        self.label_imagem.setStyleSheet(
            f"background-color: {C_CARD}; border: 1px solid {C_BORDER};"
            f" border-radius: 10px;"
        )
        # Mostra a imagem (esconde o quadro) e oferece voltar ao quadro
        self.stack_esquerda.setCurrentIndex(1)
        self.btn_voltar_quadro.setVisible(True)
        self.btn_analisar.setEnabled(True)
        self.btn_toggle_adicionar.setEnabled(False)
        self.btn_toggle_remover.setEnabled(False)
        self._desativar_modos()
        self.texto_resultado.clear()
        self.label_score.setText("--")
        self.limpar_detalhe()
        self.atualizar_chips(None)

    def analisar(self):
        # Se estiver no modo quadro, salva o desenho como imagem primeiro
        if self.stack_esquerda.currentIndex() == 0:
            if self.canvas.esta_vazio():
                return
            path = self.canvas.salvar_png()
            self.definir_imagem(path)
        if not self.image_path:
            return
        self.btn_analisar.setEnabled(False)
        self.btn_carregar.setEnabled(False)
        self.btn_copiar.setEnabled(False)
        self.btn_salvar.setEnabled(False)
        self.btn_toggle_adicionar.setEnabled(False)
        self.btn_toggle_remover.setEnabled(False)
        self.combo_motor.setEnabled(False)
        self.progress.setVisible(True)
        self._desativar_modos()

        self.motor_usado = self.combo_motor.currentData()
        self.worker = AnaliseWorker(self.image_path, self.motor_usado)
        self.worker.finished.connect(self.on_resultado)
        self.worker.error.connect(self.on_erro)
        self.worker.start()

    def on_resultado(self, texto, avaliacao, anotada, letras):
        self.progress.setVisible(False)
        self.btn_analisar.setEnabled(True)
        self.btn_carregar.setEnabled(True)
        self.btn_copiar.setEnabled(True)
        self.btn_salvar.setEnabled(True)
        self.btn_toggle_adicionar.setEnabled(True)
        self.btn_toggle_remover.setEnabled(True)
        self.btn_expandir_texto.setEnabled(True)
        self.btn_expandir_detalhe.setEnabled(True)
        self.combo_motor.setEnabled(True)

        self.texto_atual = texto
        self.avaliacao_atual = avaliacao
        self.imagem_processada_bgr = anotada
        self.letras_manuais = []

        self.texto_resultado.setText(texto if texto else "(nenhum texto reconhecido)")
        self._exibir_imagem_anotada()

        if avaliacao:
            self.label_score.setText(f"{avaliacao['pontuacao_geral']:.0f}/100")
            self.atualizar_chips(avaliacao)
            if letras is not None:
                self.letras_por_indice = letras
            else:
                self._associar_letras_por_contagem(texto, avaliacao)
            self.preencher_detalhe()
        else:
            self.label_score.setText("--")
            self.atualizar_chips(None)

    def on_erro(self, mensagem):
        self.progress.setVisible(False)
        self.btn_analisar.setEnabled(True)
        self.btn_carregar.setEnabled(True)
        self.combo_motor.setEnabled(True)

        if mensagem == "__SENTENCA__":
            self.texto_resultado.clear()
            self.label_score.setText("--")
            self.limpar_detalhe()
            self.atualizar_chips(None)
            self._dialog_sentenca()
            return

        self.texto_resultado.setText(f"Erro: {mensagem}")

    def _dialog_sentenca(self):
        caixa = QMessageBox(self)
        caixa.setWindowTitle("Texto com mais de uma palavra")
        caixa.setIcon(QMessageBox.Warning)
        caixa.setText(
            "O modo TrOCR (offline) analisa apenas uma única palavra por vez."
        )
        caixa.setInformativeText(
            "A imagem enviada contem uma frase ou texto com varias palavras. "
            "Para analisar textos completos, use o motor Google Vision."
        )
        btn_trocar = caixa.addButton(
            "Trocar para Google Vision", QMessageBox.AcceptRole
        )
        caixa.addButton("Cancelar", QMessageBox.RejectRole)
        caixa.exec_()
        if caixa.clickedButton() == btn_trocar:
            # Seleciona Google Vision e reanalisa automaticamente
            idx = self.combo_motor.findData("google")
            if idx >= 0:
                self.combo_motor.setCurrentIndex(idx)
            self.analisar()

    def _associar_letras_por_contagem(self, texto, avaliacao):
        self.letras_por_indice = {}
        if not avaliacao or not texto:
            return
        letras_texto = [c.upper() for c in texto if c.isalpha()]
        n = avaliacao["total"]
        if len(letras_texto) == n:
            for i, letra in enumerate(letras_texto):
                self.letras_por_indice[i] = letra
        else:
            for i in range(n):
                self.letras_por_indice[i] = "?"

    def _clicou_na_imagem(self, x, y):
        """Clique normal na imagem: se o ponto cair dentro de uma caixa
        de letra (automatica ou manual), age como um clique no chip
        correspondente (abre detalhe ou remove, conforme o modo)."""
        if not self.avaliacao_atual:
            return
        # Procura primeiro nas caixas automaticas (a menor que contem o ponto,
        # para desempatar sobreposicoes)
        candidatos = []
        for i, r in enumerate(self.avaliacao_atual["caracteres"]):
            bx, by, bw, bh = r["posicao"]
            if bx <= x <= bx + bw and by <= y <= by + bh:
                candidatos.append((bw * bh, i))
        if candidatos:
            candidatos.sort()
            self._clique_chip_auto(candidatos[0][1])
            return
        # Depois nas manuais
        for j, info in enumerate(self.letras_manuais):
            bx, by, bw, bh = info["posicao"]
            if bx <= x <= bx + bw and by <= y <= by + bh:
                self._clique_chip_manual(j)
                return

    # ── Recalculo apos remocao ──────────────────────────────────────

    def _recalcular_avaliacao(self):
        a = self.avaliacao_atual
        if not a:
            return
        chars = a["caracteres"]
        for k, r in enumerate(chars):
            r["indice"] = k + 1
        a["total"] = len(chars)
        a["boas"] = sum(1 for r in chars if r["classe"] == 2)
        a["aceitaveis"] = sum(1 for r in chars if r["classe"] == 1)
        a["ruins"] = sum(1 for r in chars if r["classe"] == 0)
        if chars:
            media = sum(r["classe"] for r in chars) / len(chars)
            a["pontuacao_geral"] = round(media / 2 * 100, 1)
        else:
            a["pontuacao_geral"] = 0.0

    def _reanotar_imagem(self):
        """Refaz a imagem anotada apos remocao/alteracao."""
        if self.motor_usado == "google":
            self.imagem_processada_bgr = annotate_from_characters(
                self.image_path, self.avaliacao_atual
            )
        else:
            self.imagem_processada_bgr = annotate_image(
                self.image_path, self.avaliacao_atual
            )
        self._exibir_imagem_anotada()

    # ── Imagem anotada ──────────────────────────────────────────────

    def _exibir_imagem_anotada(self):
        if self.imagem_processada_bgr is None:
            return
        img = self.imagem_processada_bgr.copy()
        cor_manual = (255, 158, 74)
        for info in self.letras_manuais:
            x, y, w, h = info["posicao"]
            cv2.rectangle(img, (x, y), (x + w, y + h), cor_manual, 2)
            cv2.putText(
                img, info["letra"], (x, max(12, y - 6)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, cor_manual, 2,
            )

        # Destaque em vermelho grosso da letra selecionada, para o usuario
        # saber exatamente qual caixa esta editando
        cor_destaque = (0, 0, 255)  # vermelho puro em BGR
        if (self.indice_destacado is not None and self.avaliacao_atual
                and self.indice_destacado < len(self.avaliacao_atual["caracteres"])):
            x, y, w, h = self.avaliacao_atual["caracteres"][self.indice_destacado]["posicao"]
            cv2.rectangle(img, (x - 3, y - 3), (x + w + 3, y + h + 3), cor_destaque, 3)
        if (self.manual_destacado is not None
                and self.manual_destacado < len(self.letras_manuais)):
            x, y, w, h = self.letras_manuais[self.manual_destacado]["posicao"]
            cv2.rectangle(img, (x - 3, y - 3), (x + w + 3, y + h + 3), cor_destaque, 3)

        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        qimg = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)
        self.label_imagem.setImagemOriginal(qimg)

    def _destacar_auto(self, indice):
        self.indice_destacado = indice
        self.manual_destacado = None
        self._exibir_imagem_anotada()

    def _destacar_manual(self, indice_manual):
        self.manual_destacado = indice_manual
        self.indice_destacado = None
        self._exibir_imagem_anotada()

    def _limpar_destaque(self):
        self.indice_destacado = None
        self.manual_destacado = None
        self._exibir_imagem_anotada()

    # ── Grid de detalhe ─────────────────────────────────────────────

    def limpar_detalhe(self):
        while self.detalhe_grid.count():
            item = self.detalhe_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def preencher_detalhe(self):
        self.limpar_detalhe()
        if not self.avaliacao_atual:
            return
        cores = {0: C_BAD, 1: C_OK, 2: C_GOOD}
        col_max = 4

        chips = []
        for i, r in enumerate(self.avaliacao_atual["caracteres"]):
            cor = cores[r["classe"]]
            letra = self.letras_por_indice.get(i, "?")
            if letra and letra != "?":
                texto = f"{letra}  {r['confianca']:.0%}"
            else:
                texto = f"L{r['indice']}  {r['confianca']:.0%}"
            chip = LetraChip(i, letra, cor, texto)
            chip.clicado.connect(self._clique_chip_auto)
            chips.append(chip)

        for j, info in enumerate(self.letras_manuais):
            letra = info["letra"]
            cor = C_ACCENT
            chip = QLabel(f"{letra}  manual")
            chip.setAlignment(Qt.AlignCenter)
            chip.setCursor(QCursor(Qt.PointingHandCursor))
            chip.setStyleSheet(
                f"background-color: {com_alpha(cor, 0x18)}; color: {cor};"
                f" border: 1px solid {com_alpha(cor, 0x45)}; border-radius: 6px;"
                f" padding: 6px 4px; font-size: 11px; font-weight: 600;"
            )
            chip.setToolTip(f"Letra manual: {letra}")
            chip.mousePressEvent = (
                lambda ev, idx=j: self._clique_chip_manual(idx)
            )
            chips.append(chip)

        for k, chip in enumerate(chips):
            self.detalhe_grid.addWidget(chip, k // col_max, k % col_max)

    # ── Cliques nos chips (com modo remover) ────────────────────────

    def _clique_chip_auto(self, indice):
        if self.modo_remover_ativo:
            self._remover_chip_auto(indice)
        else:
            self._abrir_detalhe_auto(indice)

    def _clique_chip_manual(self, indice_manual):
        if self.modo_remover_ativo:
            self._remover_chip_manual(indice_manual)
        else:
            self._abrir_detalhe_manual(indice_manual)

    def _remover_chip_auto(self, indice):
        letra = self.letras_por_indice.get(indice, "?")
        nome = f"'{letra}'" if letra != "?" else f"L{indice + 1}"
        resposta = QMessageBox.question(
            self, "Remover letra",
            f"Tem certeza que deseja remover a letra {nome} da análise?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if resposta != QMessageBox.Yes:
            return
        # Remove da avaliacao e reindexar letras_por_indice
        del self.avaliacao_atual["caracteres"][indice]
        novas = {}
        for i, letra_i in self.letras_por_indice.items():
            if i < indice:
                novas[i] = letra_i
            elif i > indice:
                novas[i - 1] = letra_i
        self.letras_por_indice = novas
        self._recalcular_avaliacao()
        self.label_score.setText(
            f"{self.avaliacao_atual['pontuacao_geral']:.0f}/100"
            if self.avaliacao_atual["total"] > 0 else "--"
        )
        self.atualizar_chips(self.avaliacao_atual)
        self._reanotar_imagem()
        self.preencher_detalhe()
        self._desativar_modos()

    def _remover_chip_manual(self, indice_manual):
        info = self.letras_manuais[indice_manual]
        resposta = QMessageBox.question(
            self, "Remover letra",
            f"Tem certeza que deseja remover a letra manual '{info['letra']}'?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if resposta != QMessageBox.Yes:
            return
        del self.letras_manuais[indice_manual]
        self._exibir_imagem_anotada()
        self.preencher_detalhe()
        self._desativar_modos()

    # ── Popups de detalhe ───────────────────────────────────────────

    def _abrir_detalhe_auto(self, indice):
        if not self.avaliacao_atual:
            return
        # Destaca a caixa correspondente na imagem antes de abrir o popup
        self._destacar_auto(indice)
        r = self.avaliacao_atual["caracteres"][indice]
        letra = self.letras_por_indice.get(indice, "?")

        dlg = DetalheLetraDialog(
            letra=letra,
            categoria=r["categoria"],
            classe=r["classe"],
            confianca=r["confianca"],
            indice_caractere=indice,
            estado_letras=self._estado_letras(),
            tem_conta=self.tem_conta,
            parent=self,
        )
        dlg.treinar_solicitado.connect(self.treinar_letra.emit)
        dlg.letra_corrigida.connect(self._on_letra_corrigida)
        dlg.exec_()
        self._limpar_destaque()

    def _abrir_detalhe_manual(self, indice_manual):
        self._destacar_manual(indice_manual)
        info = self.letras_manuais[indice_manual]
        dlg = DetalheLetraDialog(
            letra=info["letra"],
            categoria="Adicionada manualmente",
            classe=None,
            confianca=1.0,
            indice_caractere=None,
            estado_letras=self._estado_letras(),
            tem_conta=self.tem_conta,
            parent=self,
        )
        dlg.treinar_solicitado.connect(self.treinar_letra.emit)
        dlg.exec_()
        self._limpar_destaque()

    def _on_letra_corrigida(self, indice, nova_letra):
        self.letras_por_indice[indice] = nova_letra
        self.preencher_detalhe()

    def atualizar_chips(self, avaliacao):
        if avaliacao is None:
            self.chip_boas.setText("0 boas")
            self.chip_ok.setText("0 aceitáveis")
            self.chip_ruins.setText("0 a melhorar")
        else:
            self.chip_boas.setText(f"{avaliacao['boas']} boas")
            self.chip_ok.setText(f"{avaliacao['aceitaveis']} aceitáveis")
            self.chip_ruins.setText(f"{avaliacao['ruins']} a melhorar")

    # ── Modos adicionar / remover ───────────────────────────────────

    def _toggle_modo_adicionar(self):
        if self.btn_toggle_adicionar.isChecked():
            self._desativar_modo_remover()
            self._ativar_modo_adicionar()
        else:
            self._desativar_modo_adicionar()

    def _toggle_modo_remover(self):
        if self.btn_toggle_remover.isChecked():
            self._desativar_modo_adicionar()
            self._ativar_modo_remover()
        else:
            self._desativar_modo_remover()

    def _ativar_modo_adicionar(self):
        self.modo_adicionar_ativo = True
        self.label_imagem.setModoAdicionar(True)
        self.btn_toggle_adicionar.setChecked(True)
        self.btn_toggle_adicionar.setText("Cancelar adição")
        self.btn_toggle_adicionar.setStyleSheet(
            f"QPushButton {{ background-color: {com_alpha(C_ACCENT, 0x18)}; color: {C_ACCENT};"
            f" border: 1px solid {C_ACCENT}; border-radius: 8px;"
            f" padding: 6px 12px; font-size: 12px; font-weight: 600; }}"
        )

    def _desativar_modo_adicionar(self):
        self.modo_adicionar_ativo = False
        self.label_imagem.setModoAdicionar(False)
        self.btn_toggle_adicionar.setChecked(False)
        self.btn_toggle_adicionar.setText("Adicionar letra")
        self.btn_toggle_adicionar.setStyleSheet("")

    def _ativar_modo_remover(self):
        self.modo_remover_ativo = True
        self.btn_toggle_remover.setChecked(True)
        self.btn_toggle_remover.setText("Cancelar remoção")
        self.btn_toggle_remover.setStyleSheet(
            f"QPushButton {{ background-color: {com_alpha(C_BAD, 0x18)}; color: {C_BAD};"
            f" border: 1px solid {C_BAD}; border-radius: 8px;"
            f" padding: 6px 12px; font-size: 12px; font-weight: 600; }}"
        )
        self.hint_detalhe.setText(
            "MODO REMOÇÃO: clique em uma letra abaixo para removê-la"
        )
        self.hint_detalhe.setStyleSheet(
            f"color: {C_BAD}; font-size: 13px; font-weight: 700; border: none;"
        )

    def _desativar_modo_remover(self):
        self.modo_remover_ativo = False
        self.btn_toggle_remover.setChecked(False)
        self.btn_toggle_remover.setText("Remover letra")
        self.btn_toggle_remover.setStyleSheet("")
        self.hint_detalhe.setText("Clique em uma letra para ver detalhes")
        self.hint_detalhe.setStyleSheet(
            f"color: {C_MUTED}; font-size: 13px; border: none;"
        )

    def _desativar_modos(self):
        self._desativar_modo_adicionar()
        self._desativar_modo_remover()

    # ── Adicao manual ───────────────────────────────────────────────

    def _adicionar_letra_no_ponto(self, x, y):
        h_padrao, w_padrao = 40, 30
        if self.avaliacao_atual and self.avaliacao_atual["total"] > 0:
            alturas = [c["posicao"][3] for c in self.avaliacao_atual["caracteres"]]
            larguras = [c["posicao"][2] for c in self.avaliacao_atual["caracteres"]]
            if alturas:
                h_padrao = int(sum(alturas) / len(alturas))
            if larguras:
                w_padrao = int(sum(larguras) / len(larguras))
        x0 = max(0, x - w_padrao // 2)
        y0 = max(0, y - h_padrao // 2)
        posicao = (x0, y0, w_padrao, h_padrao)

        dlg = DetalheLetraDialog(
            letra="?",
            categoria=None,
            classe=None,
            confianca=1.0,
            indice_caractere=None,
            estado_letras=self._estado_letras(),
            tem_conta=self.tem_conta,
            parent=self,
            modo_adicao_manual=True,
        )
        dlg.letra_adicionada.connect(
            lambda letra, pos=posicao: self._letra_manual_adicionada(letra, pos)
        )
        dlg.exec_()
        self._desativar_modo_adicionar()

    def _letra_manual_adicionada(self, letra, posicao):
        for m in self.letras_manuais:
            if m["posicao"] == posicao and m["letra"] == letra:
                return
        self.letras_manuais.append({"letra": letra, "posicao": posicao})
        self._exibir_imagem_anotada()
        self.preencher_detalhe()

        # Pergunta se o usuario quer treinar a letra recem-adicionada
        resposta = QMessageBox.question(
            self, "Treinar letra",
            f"Deseja treinar a letra '{letra}' agora?\n\n"
            "É recomendado caso o programa não tenha detectado essa letra "
            "por dificuldade de leitura da sua escrita.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes,
        )
        if resposta == QMessageBox.Yes:
            self.treinar_letra.emit(letra)

    # ── Expansao ────────────────────────────────────────────────────

    def _expandir_texto(self):
        dlg = TextoExpandidoDialog(self.texto_atual, parent=self)
        dlg.exec_()

    def _expandir_detalhe(self):
        dlg = DetalheExpandidoDialog(
            self.avaliacao_atual, self.letras_por_indice,
            self.letras_manuais, parent=self,
        )
        dlg.chip_clicado.connect(self._abrir_detalhe_auto)
        dlg.exec_()

    # ── Exportacao ──────────────────────────────────────────────────

    def copiar_texto(self):
        QApplication.clipboard().setText(self.texto_resultado.toPlainText())

    def salvar_relatorio(self):
        if not self.avaliacao_atual and not self.texto_atual:
            return
        sugestao = "relatorio_caligrafia.txt"
        if self.image_path:
            base = os.path.splitext(os.path.basename(self.image_path))[0]
            sugestao = f"relatorio_{base}.txt"
        path, _ = QFileDialog.getSaveFileName(
            self, "Salvar Relatório", sugestao, "Texto (*.txt)"
        )
        if path:
            conteudo = gerar_relatorio(self.texto_atual, self.avaliacao_atual)
            with open(path, "w", encoding="utf-8") as f:
                f.write(conteudo)


# ─── DIALOGO: TEXTO EXPANDIDO COM VERIFICACAO ORTOGRAFICA ────────────────────

class TextoExpandidoDialog(QDialog):
    """Mostra o texto reconhecido em uma janela maior, com uma lista de
    palavras possivelmente escritas erradas (verificacao ortografica em
    portugues, se a biblioteca pyspellchecker estiver instalada)."""

    def __init__(self, texto, parent=None):
        super().__init__(parent)
        self.texto = texto or ""
        self.setWindowTitle("Texto reconhecido")
        self.setMinimumSize(720, 560)
        from ui_theme import C_BG
        self.setStyleSheet(f"QDialog {{ background-color: {C_BG}; }}")
        self.setup_ui()

    def setup_ui(self):
        from ui_theme import C_PANEL, C_CARD, C_TEXT, C_MUTED, C_BORDER
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(12)

        titulo = QLabel("Texto reconhecido")
        titulo.setStyleSheet(
            f"color: {C_TEXT}; font-size: 18px; font-weight: 800;"
        )
        root.addWidget(titulo)

        corpo = QHBoxLayout()
        corpo.setSpacing(14)
        root.addLayout(corpo, 1)

        # Texto grande
        caixa = QTextEdit()
        caixa.setReadOnly(True)
        caixa.setText(self.texto)
        caixa.setStyleSheet(
            f"QTextEdit {{ background-color: {C_CARD}; color: {C_TEXT};"
            f" border: 1px solid {C_BORDER}; border-radius: 10px;"
            f" padding: 14px; font-size: 16px; line-height: 1.5; }}"
        )
        corpo.addWidget(caixa, 60)

        # Painel de ortografia
        painel = QVBoxLayout()
        painel.setSpacing(8)
        corpo.addLayout(painel, 40)

        lbl_orto = QLabel("POSSIVEIS ERROS DE ESCRITA")
        lbl_orto.setStyleSheet(
            f"color: {C_MUTED}; font-size: 10px; font-weight: 700;"
            f" letter-spacing: 1.2px;"
        )
        painel.addWidget(lbl_orto)

        self.lista_erros = QListWidget()
        self.lista_erros.setStyleSheet(
            f"QListWidget {{ background-color: {C_PANEL}; color: {C_TEXT};"
            f" border: 1px solid {C_BORDER}; border-radius: 10px;"
            f" padding: 6px; font-size: 13px; }}"
            f"QListWidget::item {{ padding: 7px; border-radius: 6px; }}"
        )
        painel.addWidget(self.lista_erros, 1)

        self._verificar_ortografia()

        btn_fechar = QPushButton("Fechar")
        btn_fechar.setObjectName("ghost")
        btn_fechar.clicked.connect(self.accept)
        root.addWidget(btn_fechar, alignment=Qt.AlignRight)

    def _verificar_ortografia(self):
        """Usa pyspellchecker (pt) se disponivel. As palavras marcadas
        como desconhecidas aparecem com a sugestao de correcao."""
        palavras = [
            "".join(c for c in t if c.isalpha())
            for t in self.texto.split()
        ]
        palavras = [p for p in palavras if len(p) >= 2]
        if not palavras:
            self.lista_erros.addItem(QListWidgetItem("Nenhum texto para verificar."))
            return
        try:
            from spellchecker import SpellChecker
            spell = SpellChecker(language="pt")
            desconhecidas = spell.unknown([p.lower() for p in palavras])
            if not desconhecidas:
                self.lista_erros.addItem(
                    QListWidgetItem("Nenhum erro aparente encontrado.")
                )
                return
            # Preserva a ordem em que aparecem no texto
            vistas = set()
            for p in palavras:
                pl = p.lower()
                if pl in desconhecidas and pl not in vistas:
                    vistas.add(pl)
                    sugestao = spell.correction(pl)
                    if sugestao and sugestao != pl:
                        item = QListWidgetItem(f"{p}  ->  {sugestao}")
                    else:
                        item = QListWidgetItem(f"{p}  (sem sugestão)")
                    self.lista_erros.addItem(item)
        except ImportError:
            self.lista_erros.addItem(QListWidgetItem(
                "Verificador ortográfico não instalado."
            ))
            self.lista_erros.addItem(QListWidgetItem(
                "Instale com: pip install pyspellchecker"
            ))
        except Exception as e:
            self.lista_erros.addItem(QListWidgetItem(f"Erro ao verificar: {e}"))


# ─── DIALOGO: DETALHE POR LETRA EXPANDIDO ────────────────────────────────────

class DetalheExpandidoDialog(QDialog):
    """Versao ampliada do grid Detalhe por Letra, com mais colunas e
    espaco. Clicar em uma letra abre o mesmo popup de detalhe."""
    chip_clicado = pyqtSignal(int)

    def __init__(self, avaliacao, letras_por_indice, letras_manuais, parent=None):
        super().__init__(parent)
        self.avaliacao = avaliacao
        self.letras_por_indice = letras_por_indice
        self.letras_manuais = letras_manuais
        self.setWindowTitle("Detalhe por letra")
        self.setMinimumSize(760, 560)
        from ui_theme import C_BG
        self.setStyleSheet(f"QDialog {{ background-color: {C_BG}; }}")
        self.setup_ui()

    def setup_ui(self):
        from ui_theme import (
            C_TEXT, C_MUTED, C_ACCENT,
            C_GOOD, C_OK, C_BAD,
        )
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(12)

        titulo = QLabel("Detalhe por letra")
        titulo.setStyleSheet(
            f"color: {C_TEXT}; font-size: 18px; font-weight: 800;"
        )
        root.addWidget(titulo)

        if self.avaliacao:
            resumo = QLabel(
                f"{self.avaliacao['total']} letras analisadas  ·  "
                f"{self.avaliacao['boas']} boas  ·  "
                f"{self.avaliacao['aceitaveis']} aceitáveis  ·  "
                f"{self.avaliacao['ruins']} precisam melhorar"
            )
            resumo.setStyleSheet(f"color: {C_MUTED}; font-size: 12px;")
            root.addWidget(resumo)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        container.setObjectName("transparente")
        grid = QGridLayout(container)
        grid.setSpacing(8)
        grid.setAlignment(Qt.AlignTop)

        cores = {0: C_BAD, 1: C_OK, 2: C_GOOD}
        col_max = 6
        chips = []
        if self.avaliacao:
            for i, r in enumerate(self.avaliacao["caracteres"]):
                cor = cores[r["classe"]]
                letra = self.letras_por_indice.get(i, "?")
                if letra and letra != "?":
                    texto = f"{letra}  {r['confianca']:.0%}"
                else:
                    texto = f"L{r['indice']}  {r['confianca']:.0%}"
                chip = LetraChip(i, letra, cor, texto)
                chip.clicado.connect(self.chip_clicado.emit)
                chips.append(chip)
        for info in self.letras_manuais:
            chip = QLabel(f"{info['letra']}  manual")
            chip.setAlignment(Qt.AlignCenter)
            chip.setStyleSheet(
                f"background-color: {com_alpha(C_ACCENT, 0x18)}; color: {C_ACCENT};"
                f" border: 1px solid {com_alpha(C_ACCENT, 0x45)}; border-radius: 6px;"
                f" padding: 8px 4px; font-size: 12px; font-weight: 600;"
            )
            chips.append(chip)

        for k, chip in enumerate(chips):
            grid.addWidget(chip, k // col_max, k % col_max)

        scroll.setWidget(container)
        root.addWidget(scroll, 1)

        btn_fechar = QPushButton("Fechar")
        btn_fechar.setObjectName("ghost")
        btn_fechar.clicked.connect(self.accept)
        root.addWidget(btn_fechar, alignment=Qt.AlignRight)
