"""Modo Praticar Caligrafia:
- Aba Letras: grid estilo WaniKani com seletor de estilo (forma/cursiva).
  Cada estilo tem progresso proprio (letras vs letras_cursiva no Firestore).
  No estilo cursiva, o alvo e exibido com uma fonte cursiva real carregada
  de fonts/cursiva.ttf (fallback para fontes do sistema se ausente).
- Aba Palavras: 3 fases fixas + card "Minhas Palavras" gerenciavel.
"""

import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFileDialog, QTabWidget, QProgressBar, QSizePolicy, QFrame,
    QStackedWidget, QScrollArea, QGridLayout, QComboBox, QDialog,
    QLineEdit, QListWidget, QListWidgetItem, QMessageBox
)
from PyQt5.QtGui import QPixmap, QCursor, QRegExpValidator
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QRegExp

from PyQt5.QtWidgets import QWidget as _QWidget
from PyQt5.QtGui import QPainter, QColor
from image_pipeline import process
from handwriting_evaluator import avaliar_texto
from ui_theme import (
    C_BG, C_CARD, C_PANEL, C_TEXT, C_MUTED, C_BORDER, C_ACCENT,
    C_GOOD, C_OK, C_BAD, make_card,
)
import progresso as prog


class BarraSegmentada(_QWidget):
    """Barra de progresso dividida em segmentos visiveis (tequinhos).
    Cada segmento e preenchido individualmente. Fica verde apenas
    quando todos os segmentos estao preenchidos (nivel maximo)."""

    def __init__(self, total, valor, altura=14):
        super().__init__()
        self.total = max(1, total)
        self.valor = valor
        self.setFixedHeight(altura)
        self.setMinimumWidth(60)

    def set_valor(self, valor):
        self.valor = valor
        self.update()

    def _cor(self):
        if self.valor >= self.total:
            return QColor(C_GOOD)
        elif self.valor >= self.total * 0.6:
            return QColor(C_ACCENT)
        elif self.valor >= 1:
            return QColor(C_OK)
        return QColor(C_BORDER)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w = self.width()
        h = self.height()
        gap = 3
        n = self.total
        seg_w = (w - gap * (n - 1)) / n
        cor_on = self._cor()
        cor_off = QColor(C_CARD)
        borda = QColor(C_BORDER)
        for i in range(n):
            x = i * (seg_w + gap)
            p.setPen(borda)
            cor = cor_on if i < self.valor else cor_off
            p.setBrush(cor)
            p.drawRoundedRect(int(x), 0, int(seg_w), h - 1, 3, 3)
        p.end()


FASES = [
    {
        "nome": "Iniciante",
        "descricao": "Palavras curtas de 3 a 4 letras, uteis para se acostumar com o traco basico.",
        "palavras": ["CASA", "GATO", "PAO", "SOL", "MAR"],
    },
    {
        "nome": "Intermediario",
        "descricao": "Palavras medias de 5 a 6 letras, com combinacoes mais desafiadoras.",
        "palavras": ["LIVRO", "PORTA", "MESA", "FLOR", "PRAIA"],
    },
    {
        "nome": "Avancado",
        "descricao": "Palavras mais longas e menos comuns, para consolidar a fluencia da escrita.",
        "palavras": ["ESCOLA", "ARVORE", "JANELA", "CADERNO", "MENINO"],
    },
]

LETRAS = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")

FONTE_FORMA = "'Cambria', 'Georgia', serif"


class VerificarWorker(QThread):
    finished = pyqtSignal(str, object)
    error = pyqtSignal(str)

    def __init__(self, image_path):
        super().__init__()
        self.image_path = image_path

    def run(self):
        try:
            from htr_google import predict_from_path
            texto = predict_from_path(self.image_path)
            _, characters, _ = process(self.image_path)
            avaliacao = avaliar_texto(characters)
            self.finished.emit(texto, avaliacao)
        except Exception as e:
            self.error.emit(str(e))


class LetraCard(QFrame):
    clicked = pyqtSignal(str)

    def __init__(self, letra, nivel, fonte):
        super().__init__()
        self.letra = letra
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setFixedSize(140, 165)
        self._apply_style(nivel)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 12, 8, 12)
        layout.setSpacing(8)

        lbl_letra = QLabel(letra)
        lbl_letra.setAlignment(Qt.AlignCenter)
        lbl_letra.setStyleSheet(
            f"color: {C_TEXT}; font-size: 56px; font-weight: 800;"
            f" border: none; background: transparent;"
            f" font-family: {fonte};"
        )
        layout.addWidget(lbl_letra, 1)

        self.barra = BarraSegmentada(5, nivel, altura=12)
        layout.addWidget(self.barra)

    def _apply_style(self, nivel):
        borda = C_GOOD if nivel >= 5 else C_BORDER
        self.setStyleSheet(
            f"QFrame {{ background-color: {C_PANEL};"
            f" border: 1px solid {borda}; border-radius: 12px; }}"
            f"QFrame:hover {{ border: 1px solid {C_ACCENT}; }}"
        )

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.letra)


class FaseCard(QFrame):
    clicked = pyqtSignal(int)

    def __init__(self, indice, nome, descricao, n_palavras,
                 desbloqueada, completa, custom=False):
        super().__init__()
        self.indice = indice
        self.desbloqueada = desbloqueada
        self.setFixedSize(250, 250)
        if custom:
            cor_borda = C_ACCENT
        else:
            cor_borda = C_GOOD if completa else (C_ACCENT if desbloqueada else C_BORDER)
        hover_rule = f"QFrame:hover {{ border: 1px solid {C_ACCENT}; }}" if desbloqueada else ""
        self.setStyleSheet(
            f"QFrame {{ background-color: {C_PANEL};"
            f" border: 1px solid {cor_borda}; border-radius: 14px; }}"
            + hover_rule
        )
        if desbloqueada:
            self.setCursor(QCursor(Qt.PointingHandCursor))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(10)

        topo = QHBoxLayout()
        num = QLabel("Personalizada" if custom else f"Fase {indice + 1}")
        num.setStyleSheet(
            f"color: {C_MUTED}; font-size: 11px; font-weight: 700;"
            f" letter-spacing: 1.5px; border: none;"
        )
        topo.addWidget(num)
        topo.addStretch()
        if custom:
            status_txt, cor_st = ("Disponivel", C_ACCENT) if desbloqueada else ("Vazia", C_MUTED)
        elif completa:
            status_txt, cor_st = "Concluida", C_GOOD
        elif desbloqueada:
            status_txt, cor_st = "Disponivel", C_ACCENT
        else:
            status_txt, cor_st = "Bloqueada", C_MUTED
        status = QLabel(status_txt)
        status.setStyleSheet(
            f"color: {cor_st}; font-size: 11px; font-weight: 700; border: none;"
        )
        topo.addWidget(status)
        layout.addLayout(topo)

        lbl_nome = QLabel(nome)
        lbl_nome.setStyleSheet(
            f"color: {C_TEXT}; font-size: 22px; font-weight: 800; border: none;"
        )
        layout.addWidget(lbl_nome)

        desc = QLabel(descricao)
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {C_MUTED}; font-size: 13px; border: none;")
        desc.setAlignment(Qt.AlignTop)
        layout.addWidget(desc, 1)

        info = QLabel(f"{n_palavras} palavra(s)")
        info.setStyleSheet(
            f"color: {C_ACCENT if desbloqueada else C_MUTED};"
            f" font-size: 12px; font-weight: 600; border: none;"
        )
        layout.addWidget(info)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.desbloqueada:
            self.clicked.emit(self.indice)


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

        titulo = QLabel("Gerenciar minhas palavras")
        titulo.setStyleSheet(
            f"color: {C_TEXT}; font-size: 18px; font-weight: 800;"
        )
        root.addWidget(titulo)

        dica = QLabel(
            "Adicione palavras que voce quer treinar (apenas letras A-Z, "
            "sem espacos ou acentos)."
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
            f"QListWidget::item:selected {{ background-color: {C_ACCENT}33; }}"
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


class PainelExercicio(QWidget):
    voltar = pyqtSignal()
    acerto = pyqtSignal(str)
    finalizou = pyqtSignal()

    def __init__(self, titulo_alvo, alvos, modo, nivel_atual=None,
                 meta=5, fonte_alvo=FONTE_FORMA, custom=False):
        super().__init__()
        self.titulo_alvo = titulo_alvo
        self.alvos = alvos
        self.modo = modo
        self.custom = custom
        self.indice = 0
        self.acertos = nivel_atual if modo == "letra" else 0
        self.meta = meta if modo == "letra" else len(alvos)
        self.fonte_alvo = fonte_alvo
        self.worker = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        header = QHBoxLayout()
        btn_voltar = QPushButton("Voltar")
        btn_voltar.setObjectName("ghost")
        btn_voltar.setFixedWidth(90)
        btn_voltar.clicked.connect(self.voltar.emit)
        header.addWidget(btn_voltar)
        header.addStretch()

        self.label_progresso = QLabel()
        self.label_progresso.setStyleSheet(
            f"color: {C_MUTED}; font-size: 12px; font-weight: 600;"
        )
        header.addWidget(self.label_progresso)
        layout.addLayout(header)

        if self.modo == "letra":
            self.barra = BarraSegmentada(self.meta, self.acertos, altura=14)
        else:
            self.barra = QProgressBar()
            self.barra.setRange(0, self.meta)
            self.barra.setTextVisible(False)
            self.barra.setFixedHeight(12)
        layout.addWidget(self.barra)

        body = QHBoxLayout()
        body.setSpacing(16)
        layout.addLayout(body, 1)

        alvo_card, alvo_layout = make_card(None)
        body.addWidget(alvo_card, 45)

        instrucao = QLabel(self.titulo_alvo)
        instrucao.setStyleSheet(
            f"color: {C_MUTED}; font-size: 12px; font-weight: 700;"
            f" letter-spacing: 1.5px; border: none;"
        )
        instrucao.setAlignment(Qt.AlignCenter)
        alvo_layout.addWidget(instrucao)

        self.label_alvo = QLabel()
        self.label_alvo.setAlignment(Qt.AlignCenter)
        tamanho = 200 if self.modo == "letra" else 84
        self.label_alvo.setStyleSheet(
            f"color: {C_TEXT}; font-size: {tamanho}px; font-weight: 800;"
            f" border: none; font-family: {self.fonte_alvo};"
        )
        self.label_alvo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        alvo_layout.addWidget(self.label_alvo, 1)

        envio_card, envio_layout = make_card(None)
        body.addWidget(envio_card, 55)

        self.label_imagem = QLabel("Fotografe sua tentativa\ne carregue aqui")
        self.label_imagem.setAlignment(Qt.AlignCenter)
        self.label_imagem.setMinimumSize(360, 300)
        self.label_imagem.setStyleSheet(
            f"background-color: {C_CARD}; color: {C_MUTED};"
            f" border: 2px dashed {C_BORDER}; border-radius: 10px; font-size: 13px;"
        )
        self.label_imagem.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        envio_layout.addWidget(self.label_imagem, 1)

        self.label_feedback = QLabel()
        self.label_feedback.setAlignment(Qt.AlignCenter)
        self.label_feedback.setStyleSheet(
            f"color: {C_MUTED}; font-size: 13px; padding: 8px; border: none;"
        )
        self.label_feedback.setWordWrap(True)
        self.label_feedback.setMinimumHeight(60)
        envio_layout.addWidget(self.label_feedback)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setRange(0, 0)
        self.progress.setTextVisible(False)
        envio_layout.addWidget(self.progress)

        botoes = QHBoxLayout()
        self.btn_enviar = QPushButton("Enviar Tentativa")
        self.btn_enviar.setObjectName("primary")
        self.btn_enviar.clicked.connect(self.carregar_e_verificar)
        botoes.addWidget(self.btn_enviar)
        self.btn_pular = QPushButton("Pular")
        self.btn_pular.setObjectName("ghost")
        self.btn_pular.clicked.connect(self.pular)
        botoes.addWidget(self.btn_pular)
        layout.addLayout(botoes)

        self.mostrar_alvo_atual()

    def _set_barra(self, valor):
        if isinstance(self.barra, BarraSegmentada):
            self.barra.set_valor(valor)
        else:
            self.barra.setValue(valor)

    def mostrar_alvo_atual(self):
        if self.modo == "letra":
            if self.acertos >= self.meta:
                self.mostrar_final()
                return
            self.label_alvo.setText(self.alvos[0])
            self.label_progresso.setText(
                f"Progresso da letra: {self.acertos}/{self.meta}"
            )
            self._set_barra(self.acertos)
        else:
            if self.indice >= len(self.alvos):
                self.mostrar_final()
                return
            self.label_alvo.setText(self.alvos[self.indice])
            self.label_progresso.setText(
                f"{self.indice + 1}/{len(self.alvos)}  ·  {self.acertos} acertos"
            )
            self._set_barra(self.indice)

        self.label_imagem.clear()
        self.label_imagem.setText("Fotografe sua tentativa\ne carregue aqui")
        self.label_imagem.setStyleSheet(
            f"background-color: {C_CARD}; color: {C_MUTED};"
            f" border: 2px dashed {C_BORDER}; border-radius: 10px; font-size: 13px;"
        )
        self.label_feedback.setText("")
        self.label_feedback.setStyleSheet(
            f"color: {C_MUTED}; font-size: 13px; padding: 8px; border: none;"
        )
        self._reset_botao_enviar()

    def mostrar_final(self):
        if self.modo == "letra":
            self.label_alvo.setText("OK")
            self.label_progresso.setText(f"Letra '{self.alvos[0]}' dominada!")
            self._set_barra(self.meta)
            self.label_imagem.setText("Voce dominou esta letra.\nVolte para escolher outra.")
        else:
            total = len(self.alvos)
            percentual = round(100 * self.acertos / total) if total else 0
            self.label_alvo.setText(f"{percentual}%")
            self.label_progresso.setText(f"Concluido - {self.acertos}/{total} acertos")
            self._set_barra(total)
            if self.custom:
                self.label_imagem.setText("Treino das suas palavras concluido!")
            else:
                self.label_imagem.setText("Fase completa! Voce desbloqueou a proxima.")
            self.finalizou.emit()

        self.label_imagem.setStyleSheet(
            f"background-color: {C_CARD}; color: {C_TEXT};"
            f" border: 1px solid {C_BORDER}; border-radius: 10px;"
            f" font-size: 15px; font-weight: 600;"
        )
        self.label_feedback.setText("")
        self.btn_enviar.setText("Voltar")
        self._desconectar_btn_enviar()
        self.btn_enviar.clicked.connect(self.voltar.emit)
        self.btn_pular.setEnabled(False)

    def pular(self):
        if self.modo == "letra":
            self.voltar.emit()
        else:
            self.indice += 1
            self.mostrar_alvo_atual()

    def _reset_botao_enviar(self):
        self.btn_enviar.setText("Enviar Tentativa")
        self._desconectar_btn_enviar()
        self.btn_enviar.clicked.connect(self.carregar_e_verificar)
        self.btn_pular.setEnabled(True)

    def _desconectar_btn_enviar(self):
        try:
            self.btn_enviar.clicked.disconnect()
        except TypeError:
            pass

    def carregar_e_verificar(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Selecionar sua tentativa", "",
            "Imagens (*.png *.jpg *.jpeg)"
        )
        if not path:
            return
        pixmap = QPixmap(path).scaled(
            self.label_imagem.width() - 12,
            self.label_imagem.height() - 12,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.label_imagem.setPixmap(pixmap)
        self.label_imagem.setStyleSheet(
            f"background-color: {C_CARD}; border: 1px solid {C_BORDER};"
            f" border-radius: 10px;"
        )
        self.btn_enviar.setEnabled(False)
        self.btn_pular.setEnabled(False)
        self.progress.setVisible(True)
        self.label_feedback.setText("Analisando sua tentativa...")
        self.worker = VerificarWorker(path)
        self.worker.finished.connect(self.on_verificado)
        self.worker.error.connect(self.on_erro)
        self.worker.start()

    def on_verificado(self, texto, avaliacao):
        self.progress.setVisible(False)
        self.btn_enviar.setEnabled(True)
        self.btn_pular.setEnabled(True)
        alvo = self.alvos[0] if self.modo == "letra" else self.alvos[self.indice]
        acertou, motivo = self._validar(alvo, texto, avaliacao)
        if acertou:
            self.acerto.emit(alvo)
            self.acertos += 1
            self.label_feedback.setText("Muito bem! Voce acertou.")
            self.label_feedback.setStyleSheet(
                f"color: {C_GOOD}; font-size: 15px; font-weight: 700;"
                f" padding: 8px; border: none;"
            )
            self.btn_enviar.setText("Continuar")
            self._desconectar_btn_enviar()
            self.btn_enviar.clicked.connect(self._continuar)
        else:
            self.label_feedback.setText(motivo)
            self.label_feedback.setStyleSheet(
                f"color: {C_BAD}; font-size: 14px; font-weight: 600;"
                f" padding: 8px; border: none;"
            )

    def _continuar(self):
        if self.modo == "fase":
            self.indice += 1
        self.mostrar_alvo_atual()

    def on_erro(self, mensagem):
        self.progress.setVisible(False)
        self.btn_enviar.setEnabled(True)
        self.btn_pular.setEnabled(True)
        self.label_feedback.setText(f"Erro ao processar: {mensagem}")
        self.label_feedback.setStyleSheet(
            f"color: {C_BAD}; font-size: 13px; padding: 8px; border: none;"
        )

    def _validar(self, alvo, texto, avaliacao):
        limpo = "".join(c for c in (texto or "").upper() if c.isalpha())
        if self.modo == "letra":
            if not limpo:
                return False, "Nao consegui identificar nenhuma letra. Tente outra foto."
            if limpo[0] != alvo:
                return False, f"O sistema reconheceu '{limpo[0]}', mas o alvo era '{alvo}'."
            if not avaliacao or avaliacao["total"] == 0:
                return False, "Nao consegui detectar o traco. Tente uma foto mais clara."
            if avaliacao["caracteres"][0]["classe"] == 0:
                return False, "A letra foi reconhecida, mas a formacao esta muito irregular."
            return True, ""
        else:
            if limpo != alvo:
                return False, f"Reconhecido: '{texto.strip() if texto else '(nada)'}'. Esperado: '{alvo}'."
            if not avaliacao or avaliacao["total"] == 0:
                return False, "Nao consegui detectar as letras. Tente uma foto mais clara."
            if avaliacao["ruins"] > len(alvo) * 0.3:
                return False, f"Palavra correta, mas {avaliacao['ruins']} letra(s) com formacao ruim."
            return True, ""


class AbaLetras(QWidget):
    letra_selecionada = pyqtSignal(str)

    def __init__(self, uid, estado):
        super().__init__()
        self.uid = uid
        self.estado = estado
        self._layout_raiz = QVBoxLayout(self)
        self._layout_raiz.setContentsMargins(20, 20, 20, 20)
        self._layout_raiz.setSpacing(14)
        self.cards = {}
        self._construir()

    def _limpar(self):
        while self._layout_raiz.count():
            item = self._layout_raiz.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
            else:
                sub = item.layout()
                if sub is not None:
                    self._limpar_layout(sub)
        self.cards.clear()

    def _limpar_layout(self, lay):
        while lay.count():
            item = lay.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
            else:
                sub = item.layout()
                if sub is not None:
                    self._limpar_layout(sub)

    def _construir(self):
        if not self.estado.get("iniciou_letras", False):
            self._construir_boas_vindas()
        else:
            self._construir_grid()

    def _construir_boas_vindas(self):
        self._layout_raiz.addStretch(1)
        titulo = QLabel("Aprender caligrafia")
        titulo.setAlignment(Qt.AlignCenter)
        titulo.setStyleSheet(
            f"color: {C_TEXT}; font-size: 28px; font-weight: 800;"
            f" font-family: 'Cambria', 'Georgia', serif;"
        )
        self._layout_raiz.addWidget(titulo)

        desc = QLabel(
            "Voce vai treinar as 26 letras do alfabeto uma por uma.\n"
            "Cada letra tem uma barra de progresso de 0 a 5.\n"
            "A cada acerto, a barra sobe. Quando chegar em 5, a letra esta dominada."
        )
        desc.setAlignment(Qt.AlignCenter)
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {C_MUTED}; font-size: 14px;")
        self._layout_raiz.addWidget(desc)
        self._layout_raiz.addStretch(1)

        btn_wrap = QHBoxLayout()
        btn_wrap.addStretch()
        btn = QPushButton("Comecar a aprender caligrafia!")
        btn.setMinimumHeight(48)
        btn.setStyleSheet(
            f"QPushButton {{ background-color: {C_ACCENT}; color: #fff;"
            f" border: none; border-radius: 10px; padding: 12px 32px;"
            f" font-size: 15px; font-weight: 700; }}"
            f"QPushButton:hover {{ background-color: #62adff; }}"
        )
        btn.clicked.connect(self._on_iniciar)
        btn_wrap.addWidget(btn)
        btn_wrap.addStretch()
        self._layout_raiz.addLayout(btn_wrap)
        self._layout_raiz.addStretch(2)

    def _construir_grid(self):
        letras_estado = self.estado.get("letras", {})
        dominadas = sum(1 for n in letras_estado.values() if n >= 5)
        fonte = FONTE_FORMA

        # Cabecalho padronizado (mesma estrutura da aba Palavras):
        # linha 1 = titulo + subtitulo + acao a direita (altura fixa)
        # linha 2 = barra de progresso geral (altura fixa)
        header = QHBoxLayout()
        titulo = QLabel("Progresso das Letras")
        titulo.setStyleSheet(
            f"color: {C_TEXT}; font-size: 18px; font-weight: 800;"
        )
        sub = QLabel("clique em uma letra para praticar")
        sub.setStyleSheet(f"color: {C_MUTED}; font-size: 13px;")
        header.addWidget(titulo)
        header.addSpacing(12)
        header.addWidget(sub)
        header.addStretch()
        header_wrap = QWidget()
        header_wrap.setFixedHeight(36)
        header_wrap.setLayout(header)
        self._layout_raiz.addWidget(header_wrap)

        # Barra de progresso geral (linha propria, altura fixa)
        prog_row = QHBoxLayout()
        lbl_prog = QLabel(f"Progresso geral: {dominadas}/26 dominadas")
        lbl_prog.setStyleSheet(f"color: {C_MUTED}; font-size: 13px;")
        lbl_prog.setFixedWidth(220)
        barra_geral = BarraSegmentada(len(LETRAS), dominadas, altura=10)
        prog_row.addWidget(lbl_prog)
        prog_row.addSpacing(10)
        prog_row.addWidget(barra_geral, 1)
        prog_wrap = QWidget()
        prog_wrap.setFixedHeight(28)
        prog_wrap.setLayout(prog_row)
        self._layout_raiz.addWidget(prog_wrap)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        container.setStyleSheet("background: transparent; border: none;")
        grid = QGridLayout(container)
        grid.setSpacing(10)
        grid.setAlignment(Qt.AlignTop | Qt.AlignHCenter)

        cols = 6
        for i, letra in enumerate(LETRAS):
            nivel = letras_estado.get(letra, 0)
            card = LetraCard(letra, nivel, fonte)
            card.clicked.connect(self.letra_selecionada.emit)
            self.cards[letra] = card
            grid.addWidget(card, i // cols, i % cols)

        scroll.setWidget(container)
        self._layout_raiz.addWidget(scroll, 1)

    def _on_iniciar(self):
        prog.marcar_iniciou_letras(self.uid, self.estado)
        self.reconstruir()

    def reconstruir(self):
        self._limpar()
        self._construir()


class AbaPalavras(QWidget):
    fase_selecionada = pyqtSignal(int)
    fase_custom_selecionada = pyqtSignal()
    gerenciar_solicitado = pyqtSignal()

    def __init__(self, estado):
        super().__init__()
        self.estado = estado
        self._layout_raiz = QVBoxLayout(self)
        self._layout_raiz.setContentsMargins(20, 20, 20, 20)
        self._layout_raiz.setSpacing(14)
        self._construir()

    def _limpar(self):
        while self._layout_raiz.count():
            item = self._layout_raiz.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
            else:
                sub = item.layout()
                if sub is not None:
                    self._limpar_layout(sub)

    def _limpar_layout(self, lay):
        while lay.count():
            item = lay.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
            else:
                sub = item.layout()
                if sub is not None:
                    self._limpar_layout(sub)

    def _construir(self):
        completas = self.estado["fases_completas"]

        # Cabecalho padronizado (mesma estrutura da aba Letras):
        # linha 1 = titulo + subtitulo + acao a direita (altura fixa)
        # linha 2 = barra de progresso geral (altura fixa)
        header = QHBoxLayout()
        titulo = QLabel("Fases de Palavras")
        titulo.setStyleSheet(
            f"color: {C_TEXT}; font-size: 18px; font-weight: 800;"
        )
        sub = QLabel("complete uma fase para desbloquear a proxima")
        sub.setStyleSheet(f"color: {C_MUTED}; font-size: 13px;")
        header.addWidget(titulo)
        header.addSpacing(12)
        header.addWidget(sub)
        header.addStretch()
        btn_gerenciar = QPushButton("Adicionar palavras")
        btn_gerenciar.clicked.connect(self.gerenciar_solicitado.emit)
        header.addWidget(btn_gerenciar)
        header_wrap = QWidget()
        header_wrap.setFixedHeight(36)
        header_wrap.setLayout(header)
        self._layout_raiz.addWidget(header_wrap)

        # Barra de progresso geral (linha propria, altura fixa)
        prog_row = QHBoxLayout()
        lbl_prog = QLabel(f"Progresso das fases: {completas}/{len(FASES)}")
        lbl_prog.setStyleSheet(f"color: {C_MUTED}; font-size: 13px;")
        lbl_prog.setFixedWidth(220)
        barra_geral = BarraSegmentada(len(FASES), completas, altura=10)
        prog_row.addWidget(lbl_prog)
        prog_row.addSpacing(10)
        prog_row.addWidget(barra_geral, 1)
        prog_wrap = QWidget()
        prog_wrap.setFixedHeight(28)
        prog_wrap.setLayout(prog_row)
        self._layout_raiz.addWidget(prog_wrap)

        self._layout_raiz.addStretch(1)

        cards_wrap = QHBoxLayout()
        cards_wrap.setSpacing(18)
        cards_wrap.addStretch()
        for i, fase in enumerate(FASES):
            desbloqueada = i <= self.estado["fases_completas"]
            completa = i < self.estado["fases_completas"]
            card = FaseCard(
                i, fase["nome"], fase["descricao"], len(fase["palavras"]),
                desbloqueada, completa,
            )
            card.clicked.connect(self.fase_selecionada.emit)
            cards_wrap.addWidget(card)

        minhas = self.estado.get("palavras_customizadas", [])
        card_custom = FaseCard(
            99, "Minhas Palavras",
            "Treine as palavras que voce mesmo adicionou."
            if minhas else
            "Adicione palavras pelo botao acima para liberar este treino.",
            len(minhas),
            desbloqueada=len(minhas) > 0,
            completa=False,
            custom=True,
        )
        card_custom.clicked.connect(lambda _i: self.fase_custom_selecionada.emit())
        cards_wrap.addWidget(card_custom)

        cards_wrap.addStretch()
        self._layout_raiz.addLayout(cards_wrap)
        self._layout_raiz.addStretch(2)

    def reconstruir(self):
        self._limpar()
        self._construir()


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
        btn_voltar = QPushButton("Voltar")
        btn_voltar.setObjectName("ghost")
        btn_voltar.setFixedWidth(90)
        btn_voltar.clicked.connect(self._voltar_ao_inicio)
        header.addWidget(btn_voltar)

        titulo = QLabel("Praticar Caligrafia")
        titulo.setStyleSheet(f"font-size: 20px; font-weight: 800; color: {C_TEXT};")
        sub = QLabel("Treine sua escrita com exercicios guiados")
        sub.setStyleSheet(f"color: {C_MUTED}; font-size: 14px;")
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
        self.menu.addTab(self.aba_letras, "Letras")
        self.menu.addTab(self.aba_palavras, "Palavras")

        self.stack.addWidget(self.menu)
        self.painel_exercicio = None

    def _voltar_ao_inicio(self):
        if self.stack.currentWidget() != self.menu:
            self._voltar_menu()
        else:
            self.voltar_solicitado.emit()

    def _voltar_menu(self):
        self.aba_letras.reconstruir()
        self.aba_palavras.reconstruir()
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
        self.painel_exercicio.acerto.connect(self._acertou_letra)
        self.stack.addWidget(self.painel_exercicio)
        self.stack.setCurrentWidget(self.painel_exercicio)

    def _acertou_letra(self, letra):
        prog.registrar_acerto_letra(self.uid, self.estado, letra)

    def iniciar_fase(self, indice):
        fase = FASES[indice]
        self.painel_exercicio = PainelExercicio(
            titulo_alvo=f"FASE {indice + 1} - ESCREVA A PALAVRA",
            alvos=fase["palavras"],
            modo="fase",
        )
        self.painel_exercicio.voltar.connect(self._voltar_menu)
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
        self.stack.addWidget(self.painel_exercicio)
        self.stack.setCurrentWidget(self.painel_exercicio)

    def _concluiu_fase(self, indice):
        prog.registrar_fase_completa(self.uid, self.estado, indice + 1)

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
