"""Modo Praticar Caligrafia, dividido em abas (QTabWidget):
- Letras: grid de 26 letras com progresso por nivel (0-5).
- Palavras: 3 fases fixas + card "Minhas Palavras" gerenciavel.
- Quiz: sorteia letras ou palavras da lista pessoal.
- Dicionario: busca definicoes e adiciona palavras ao treino.
- Progresso: anel, estatisticas, mapa de calor e conquistas.
"""

import os
import re
import random

import cv2
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFileDialog, QTabWidget, QProgressBar, QSizePolicy, QFrame,
    QStackedWidget, QScrollArea, QGridLayout, QDialog,
    QLineEdit, QListWidget, QListWidgetItem, QMessageBox
)
from PyQt5.QtGui import (
    QPixmap, QCursor, QRegExpValidator, QPainter, QColor, QImage
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QRegExp

from image_pipeline import process
from handwriting_evaluator import avaliar_texto
from ui_helpers import limpar_layout, cabecalho_aba, FlowLayout
from ui_theme import (
    C_BG, C_CARD, C_PANEL, C_TEXT, C_MUTED, C_BORDER, C_ACCENT,
    C_GOOD, C_OK, C_BAD, make_card, com_alpha,
)
import progresso as prog
from config import CONFIG


class BarraSegmentada(QWidget):
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
        "descricao": "Palavras curtas de 3 a 4 letras, úteis para se acostumar com o traço básico.",
        "palavras": ["CASA", "GATO", "PAO", "SOL", "MAR"],
    },
    {
        "nome": "Intermediário",
        "descricao": "Palavras médias de 5 a 6 letras, com combinações mais desafiadoras.",
        "palavras": ["LIVRO", "PORTA", "MESA", "FLOR", "PRAIA"],
    },
    {
        "nome": "Avançado",
        "descricao": "Palavras mais longas e menos comuns, para consolidar a fluência da escrita.",
        "palavras": ["ESCOLA", "ARVORE", "JANELA", "CADERNO", "MENINO"],
    },
]

LETRAS = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")

FONTE_FORMA = "'Cambria', 'Georgia', serif"
# Ajustaveis em config.json (secao "exercicio")
NOTA_MINIMA_LETRA = CONFIG["exercicio"]["nota_minima_letra"]              # acerto no exercicio
NOTA_MINIMA_PIOR = CONFIG["exercicio"]["nota_minima_pior_letra_palavra"]  # numa palavra, piso por letra


class VerificarWorker(QThread):
    finished = pyqtSignal(str, object, object, bool)   # texto, avaliacao, mapa, offline
    error = pyqtSignal(str)

    def __init__(self, image_path, alvo="", apagar_ao_fim=False):
        super().__init__()
        self.image_path = image_path
        self.alvo = alvo
        # Quando a imagem e um PNG temporario do quadro, apaga apos usar
        # para nao acumular arquivos desenho_*.png em /tmp.
        self.apagar_ao_fim = apagar_ao_fim

    def run(self):
        try:
            _, characters, linhas = process(self.image_path)
            # A letra-alvo entra na nota (legibilidade e molde); so quando o
            # numero de letras segmentadas bate com o esperado
            alvos = list(self.alvo) if len(self.alvo) == len(characters) else None
            avaliacao = avaliar_texto(characters, alvos=alvos)

            # Transcricao: Google Vision quando disponivel; sem internet ou
            # sem credenciais, cai para o reconhecimento local e avisa.
            offline = False
            try:
                from htr_google import predict_from_path
                texto = predict_from_path(self.image_path)
            except Exception:
                offline = True
                texto = self._transcrever_offline(characters, avaliacao, linhas)

            # Mapa verde/vermelho/azul da letra contra o molde, para o
            # usuario ver onde o traco saiu do esperado
            from feedback_visual import mapa_diferencas
            from image_pipeline import load_image
            mapa = mapa_diferencas(characters, avaliacao, load_image(self.image_path).shape[:2])
            self.finished.emit(texto, avaliacao, mapa, offline)
        except Exception as e:
            self.error.emit(str(e))
        finally:
            if self.apagar_ao_fim:
                try:
                    os.remove(self.image_path)
                except OSError:
                    pass

    def _transcrever_offline(self, characters, avaliacao, linhas):
        """Reconhecimento sem internet: para uma letra, a propria CNN do
        avaliador (classificador de 26 letras); para palavras, o TrOCR
        local linha a linha."""
        if len(self.alvo) <= 1 and avaliacao and avaliacao["total"] >= 1:
            return "".join(r["letra_prevista"] for r in avaliacao["caracteres"])
        from htr_engine import predict
        return " ".join(predict(linha).strip() for linha in linhas)


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
            f" border: 1px solid {cor_borda}; border-radius: 16px; }}"
            + hover_rule
        )
        if desbloqueada:
            self.setCursor(QCursor(Qt.PointingHandCursor))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        topo = QHBoxLayout()
        num = QLabel("Personalizada" if custom else f"Fase {indice + 1}")
        num.setStyleSheet(
            f"color: {C_MUTED}; font-size: 13px; font-weight: 700;"
            f" letter-spacing: 1.5px; border: none;"
        )
        topo.addWidget(num)
        topo.addStretch()
        if custom:
            status_txt, cor_st = ("Disponível", C_ACCENT) if desbloqueada else ("Vazia", C_MUTED)
        elif completa:
            status_txt, cor_st = "Concluída", C_GOOD
        elif desbloqueada:
            status_txt, cor_st = "Disponível", C_ACCENT
        else:
            status_txt, cor_st = "Bloqueada", C_MUTED
        status = QLabel(status_txt)
        status.setStyleSheet(
            f"color: {cor_st}; font-size: 13px; font-weight: 700; border: none;"
        )
        topo.addWidget(status)
        layout.addLayout(topo)

        lbl_nome = QLabel(nome)
        lbl_nome.setWordWrap(True)
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
            f" font-size: 14px; font-weight: 600; border: none;"
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


class PainelExercicio(QWidget):
    voltar = pyqtSignal()
    acerto = pyqtSignal(str)
    tentativa = pyqtSignal(str, float)   # letra-alvo, nota (toda verificacao)
    finalizou = pyqtSignal()

    def __init__(self, titulo_alvo, alvos, modo, nivel_atual=None,
                 meta=5, fonte_alvo=FONTE_FORMA, custom=False,
                 tamanho_alvo=None):
        super().__init__()
        self.titulo_alvo = titulo_alvo
        self.alvos = alvos
        self.modo = modo
        self.custom = custom
        self.indice = 0
        self.acertos = nivel_atual if modo == "letra" else 0
        self.meta = meta if modo == "letra" else len(alvos)
        self.fonte_alvo = fonte_alvo
        # Tamanho da fonte do alvo: usa o explicito, senao decide pelo modo
        self.tamanho_alvo = tamanho_alvo or (200 if modo == "letra" else 84)
        self.worker = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        # O botao "Voltar" do cabecalho do modo Praticar ja leva de volta
        # ao menu quando um exercicio esta aberto, entao aqui fica so o
        # indicador de progresso.
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.addStretch()
        self.label_progresso = QLabel()
        self.label_progresso.setStyleSheet(
            f"color: {C_MUTED}; font-size: 13px; font-weight: 600;"
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
        tamanho = self.tamanho_alvo
        self.label_alvo.setStyleSheet(
            f"color: {C_TEXT}; font-size: {tamanho}px; font-weight: 800;"
            f" border: none; font-family: {self.fonte_alvo};"
        )
        self.label_alvo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        alvo_layout.addWidget(self.label_alvo, 1)

        envio_card, envio_layout = make_card(None)
        body.addWidget(envio_card, 55)

        # Stack: quadro de desenho (padrao) OU imagem/foto enviada
        from canvas_desenho import CanvasDesenho
        self.stack_envio = QStackedWidget()

        self.canvas = CanvasDesenho()

        self.label_imagem = QLabel("Fotografe sua tentativa\ne carregue aqui")
        self.label_imagem.setAlignment(Qt.AlignCenter)
        self.label_imagem.setMinimumSize(360, 300)
        self.label_imagem.setStyleSheet(
            f"background-color: {C_CARD}; color: {C_MUTED};"
            f" border: 2px dashed {C_BORDER}; border-radius: 10px; font-size: 13px;"
        )
        self.label_imagem.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.stack_envio.addWidget(self.canvas)         # indice 0 = desenho
        self.stack_envio.addWidget(self.label_imagem)   # indice 1 = imagem
        self.stack_envio.setCurrentIndex(0)
        envio_layout.addWidget(self.stack_envio, 1)

        # Legenda do mapa de diferencas + volta ao quadro (so aparecem
        # depois de uma verificacao)
        self.linha_mapa = QWidget()
        self.linha_mapa.setObjectName("transparente")
        lay_mapa = QHBoxLayout(self.linha_mapa)
        lay_mapa.setContentsMargins(0, 0, 0, 0)
        legenda = QLabel(
            f"<span style='color:{C_GOOD}'>&#9632;</span> no molde&nbsp;&nbsp; "
            f"<span style='color:{C_BAD}'>&#9632;</span> fora do molde&nbsp;&nbsp; "
            f"<span style='color:#9ec8ff'>&#9632;</span> faltou traço"
        )
        legenda.setStyleSheet(f"color: {C_MUTED}; font-size: 12px; border: none;")
        lay_mapa.addWidget(legenda)
        lay_mapa.addStretch()
        self.btn_voltar_quadro = QPushButton("Voltar ao quadro")
        self.btn_voltar_quadro.setObjectName("ghost")
        self.btn_voltar_quadro.clicked.connect(self._voltar_ao_quadro)
        lay_mapa.addWidget(self.btn_voltar_quadro)
        self.linha_mapa.setVisible(False)
        envio_layout.addWidget(self.linha_mapa)

        self.label_offline = QLabel(
            "Sem conexão com o Google Vision: reconhecimento feito localmente "
            "(CNN para letras, TrOCR para palavras)."
        )
        self.label_offline.setAlignment(Qt.AlignCenter)
        self.label_offline.setWordWrap(True)
        self.label_offline.setStyleSheet(
            f"color: {C_OK}; font-size: 12px; border: none; padding: 2px;"
        )
        self.label_offline.setVisible(False)
        envio_layout.addWidget(self.label_offline)

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
        self.btn_enviar.clicked.connect(self.enviar_tentativa)
        botoes.addWidget(self.btn_enviar)
        self.btn_foto = QPushButton("Enviar Foto")
        self.btn_foto.setObjectName("ghost")
        self.btn_foto.clicked.connect(self.carregar_e_verificar)
        botoes.addWidget(self.btn_foto)
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
            alvo_atual = self.alvos[0]
            self.label_alvo.setText(alvo_atual)
            self.label_progresso.setText(
                f"Progresso da letra: {self.acertos}/{self.meta}"
            )
            self._set_barra(self.acertos)
        else:
            if self.indice >= len(self.alvos):
                self.mostrar_final()
                return
            alvo_atual = self.alvos[self.indice]
            self.label_alvo.setText(alvo_atual)
            self.label_progresso.setText(
                f"{self.indice + 1}/{len(self.alvos)}  ·  {self.acertos} acertos"
            )
            self._set_barra(self.indice)

        # Volta ao quadro de desenho limpo para a proxima tentativa, com
        # a letra/palavra-alvo como guia transparente para tracing
        self.canvas.limpar()
        self.canvas.definir_guia(alvo_atual)
        self.stack_envio.setCurrentIndex(0)
        self.linha_mapa.setVisible(False)
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
        self.canvas.limpar_guia()
        if self.modo == "letra":
            self.label_alvo.setText("OK")
            self.label_progresso.setText(f"Letra '{self.alvos[0]}' dominada!")
            self._set_barra(self.meta)
            self.label_imagem.setText("Você dominou esta letra.\nVolte para escolher outra.")
        else:
            total = len(self.alvos)
            percentual = round(100 * self.acertos / total) if total else 0
            # Mostra a fracao de acertos (mais claro que um "0%" solto)
            self.label_alvo.setText(f"{self.acertos}/{total}")
            self.label_progresso.setText(f"Concluído - {self.acertos} de {total} acertos")
            self._set_barra(total)
            # Mensagem varia conforme o desempenho
            if percentual >= 80:
                msg = "Excelente trabalho! Você mandou muito bem."
            elif percentual >= 50:
                msg = "Bom trabalho! Continue praticando para melhorar."
            elif percentual > 0:
                msg = "Você concluiu! Pratique mais para acertar todas."
            else:
                msg = "Não desanime! Tente de novo com calma, você consegue."
            if self.custom:
                self.label_imagem.setText(msg)
            elif percentual > 0:
                self.label_imagem.setText(
                    "Fase concluída! Você desbloqueou a próxima.\n\n" + msg
                )
            else:
                self.label_imagem.setText(msg)
            # So registra a fase como concluida se houve pelo menos um
            # acerto. Sem isso, dava para "desbloquear" fases pulando
            # todas as palavras (0 acertos) - a mensagem ja avisava que
            # nao desbloqueou, mas o backend registrava assim mesmo.
            # Fases personalizadas (custom) nao contam para o desbloqueio.
            if self.acertos > 0 and not self.custom:
                self.finalizou.emit()

        # Mostra a mensagem final no lugar do quadro
        self.stack_envio.setCurrentIndex(1)
        self.label_imagem.setStyleSheet(
            f"background-color: {C_CARD}; color: {C_TEXT};"
            f" border: 1px solid {C_BORDER}; border-radius: 10px;"
            f" font-size: 15px; font-weight: 600;"
        )
        self.label_feedback.setText("")
        self.btn_enviar.setText("Voltar")
        self._desconectar_btn_enviar()
        self.btn_enviar.clicked.connect(self.voltar.emit)
        self.btn_foto.setEnabled(False)
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
        self.btn_enviar.clicked.connect(self.enviar_tentativa)
        self.btn_foto.setEnabled(True)
        self.btn_pular.setEnabled(True)

    def _desconectar_btn_enviar(self):
        try:
            self.btn_enviar.clicked.disconnect()
        except TypeError:
            pass

    def enviar_tentativa(self):
        """Envia o que estiver no quadro de desenho para verificação."""
        # Garante que o quadro esteja visivel (caso viesse de uma foto ou do mapa)
        self.stack_envio.setCurrentIndex(0)
        self.linha_mapa.setVisible(False)
        if self.canvas.esta_vazio():
            self.label_feedback.setText("Escreva a resposta no quadro antes de enviar.")
            self.label_feedback.setStyleSheet(
                f"color: {C_OK}; font-size: 13px; padding: 8px; border: none;"
            )
            return
        path = self.canvas.salvar_png()
        self._verificar_path(path, temporario=True)

    def carregar_e_verificar(self):
        """Envia uma foto de arquivo para verificação."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Selecionar sua tentativa", "",
            "Imagens (*.png *.jpg *.jpeg)"
        )
        if not path:
            return
        # Mostra a foto no lugar do quadro
        self.stack_envio.setCurrentIndex(1)
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
        self._verificar_path(path)

    def _verificar_path(self, path, temporario=False):
        self.btn_enviar.setEnabled(False)
        self.btn_foto.setEnabled(False)
        self.btn_pular.setEnabled(False)
        self.progress.setVisible(True)
        self.label_feedback.setText("Analisando sua tentativa...")
        alvo = self.alvos[0] if self.modo == "letra" else self.alvos[self.indice]
        self.worker = VerificarWorker(path, alvo=alvo, apagar_ao_fim=temporario)
        self.worker.finished.connect(self.on_verificado)
        self.worker.error.connect(self.on_erro)
        self.worker.start()

    def _mostrar_mapa(self, mapa):
        """Exibe o mapa de diferencas (BGR) no lugar do quadro."""
        if mapa is None:
            return
        rgb = cv2.cvtColor(mapa, cv2.COLOR_BGR2RGB)
        h, w, _ = rgb.shape
        qimg = QImage(rgb.data, w, h, 3 * w, QImage.Format_RGB888).copy()
        pixmap = QPixmap.fromImage(qimg).scaled(
            self.label_imagem.width() - 12, self.label_imagem.height() - 12,
            Qt.KeepAspectRatio, Qt.SmoothTransformation,
        )
        self.label_imagem.setPixmap(pixmap)
        self.label_imagem.setStyleSheet(
            f"background-color: #ffffff; border: 1px solid {C_BORDER};"
            f" border-radius: 10px;"
        )
        self.stack_envio.setCurrentIndex(1)
        self.linha_mapa.setVisible(True)

    def _voltar_ao_quadro(self):
        """Sai do mapa e volta ao quadro (mantendo o desenho) para corrigir."""
        self.stack_envio.setCurrentIndex(0)
        self.linha_mapa.setVisible(False)

    def on_verificado(self, texto, avaliacao, mapa=None, offline=False):
        self.progress.setVisible(False)
        self.btn_enviar.setEnabled(True)
        self.btn_foto.setEnabled(True)
        self.btn_pular.setEnabled(True)
        self._mostrar_mapa(mapa)
        self.label_offline.setVisible(offline)
        alvo = self.alvos[0] if self.modo == "letra" else self.alvos[self.indice]
        acertou, motivo = self._validar(alvo, texto, avaliacao)
        # Historico de evolucao: uma entrada por letra avaliada, acertando ou nao
        if avaliacao:
            for r in avaliacao["caracteres"]:
                if r.get("letra_alvo"):
                    self.tentativa.emit(r["letra_alvo"], float(r["nota"]))
        if acertou:
            self.acerto.emit(alvo)
            self.acertos += 1
            self.label_feedback.setText("Muito bem! Você acertou.")
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
        self.btn_foto.setEnabled(True)
        self.btn_pular.setEnabled(True)
        self.label_feedback.setText(f"Erro ao processar: {mensagem}")
        self.label_feedback.setStyleSheet(
            f"color: {C_BAD}; font-size: 13px; padding: 8px; border: none;"
        )

    def _validar(self, alvo, texto, avaliacao):
        from handwriting_evaluator import explicar_letra
        limpo = "".join(c for c in (texto or "").upper() if c.isalpha())
        if self.modo == "letra":
            if not limpo:
                return False, "Não consegui identificar nenhuma letra. Tente outra foto."
            if limpo[0] != alvo:
                return False, f"O sistema reconheceu '{limpo[0]}', mas o alvo era '{alvo}'."
            if not avaliacao or avaliacao["total"] == 0:
                return False, "Não consegui detectar o traço. Tente uma foto mais clara."
            r = avaliacao["caracteres"][0]
            if r["nota"] < NOTA_MINIMA_LETRA:
                return False, (f"Reconheci o '{alvo}', mas a letra está {explicar_letra(r)} "
                               f"(nota {r['nota']:.0f}/100). Tente de novo.")
            return True, ""
        else:
            if limpo != alvo:
                return False, f"Reconhecido: '{texto.strip() if texto else '(nada)'}'. Esperado: '{alvo}'."
            if not avaliacao or avaliacao["total"] == 0:
                return False, "Não consegui detectar as letras. Tente uma foto mais clara."
            notas = [c["nota"] for c in avaliacao["caracteres"]]
            if avaliacao["pontuacao_geral"] < NOTA_MINIMA_LETRA or min(notas) < NOTA_MINIMA_PIOR:
                pior = min(avaliacao["caracteres"], key=lambda c: c["nota"])
                return False, (f"Palavra correta, mas a letra '{pior['letra_alvo']}' está "
                               f"{explicar_letra(pior)} (nota {pior['nota']:.0f}/100).")
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
        limpar_layout(self._layout_raiz)
        self.cards.clear()

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
            "Você vai treinar as 26 letras do alfabeto uma por uma.\n"
            "Cada letra tem uma barra de progresso de 0 a 5.\n"
            "A cada acerto, a barra sobe. Quando chegar em 5, a letra está dominada."
        )
        desc.setAlignment(Qt.AlignCenter)
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {C_MUTED}; font-size: 14px;")
        self._layout_raiz.addWidget(desc)
        self._layout_raiz.addStretch(1)

        btn_wrap = QHBoxLayout()
        btn_wrap.addStretch()
        btn = QPushButton("Começar a aprender caligrafia!")
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
        self._layout_raiz.addWidget(
            cabecalho_aba("Progresso das Letras", "clique em uma letra para praticar")
        )

        # Barra de progresso geral (linha propria, altura fixa)
        prog_row = QHBoxLayout()
        prog_row.setContentsMargins(0, 0, 0, 0)
        lbl_prog = QLabel(f"Progresso geral: {dominadas}/26 dominadas")
        lbl_prog.setStyleSheet(f"color: {C_MUTED}; font-size: 14px;")
        lbl_prog.setFixedWidth(260)
        barra_geral = BarraSegmentada(len(LETRAS), dominadas, altura=10)
        prog_row.addWidget(lbl_prog)
        prog_row.addSpacing(10)
        prog_row.addWidget(barra_geral, 1)
        prog_wrap = QWidget()
        prog_wrap.setMinimumHeight(40)
        prog_wrap.setLayout(prog_row)
        self._layout_raiz.addWidget(prog_wrap)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        container.setObjectName("transparente")
        # Grade fluida: o numero de colunas depende da largura da janela
        grid = FlowLayout(container, espacamento=12)

        for letra in LETRAS:
            nivel = letras_estado.get(letra, 0)
            card = LetraCard(letra, nivel, fonte)
            card.clicked.connect(self.letra_selecionada.emit)
            self.cards[letra] = card
            grid.addWidget(card)

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
        limpar_layout(self._layout_raiz)

    def _construir(self):
        completas = self.estado["fases_completas"]

        # Cabecalho padronizado (mesma estrutura da aba Letras):
        # linha 1 = titulo + subtitulo + acao a direita (altura fixa)
        # linha 2 = barra de progresso geral (altura fixa)
        btn_gerenciar = QPushButton("Adicionar palavras")
        btn_gerenciar.setFixedHeight(32)
        btn_gerenciar.setStyleSheet(
            f"QPushButton {{ background-color: {C_CARD}; color: {C_TEXT};"
            f" border: 1px solid {C_BORDER}; border-radius: 8px;"
            f" padding: 0px 16px; font-size: 13px; }}"
            f"QPushButton:hover {{ border: 1px solid {C_ACCENT}; }}"
        )
        btn_gerenciar.clicked.connect(self.gerenciar_solicitado.emit)
        self._layout_raiz.addWidget(
            cabecalho_aba(
                "Fases de Palavras",
                "complete uma fase para desbloquear a próxima",
                acao=btn_gerenciar,
            )
        )

        # Barra de progresso geral (linha propria, altura fixa)
        prog_row = QHBoxLayout()
        prog_row.setContentsMargins(0, 0, 0, 0)
        lbl_prog = QLabel(f"Progresso das fases: {completas}/{len(FASES)}")
        lbl_prog.setStyleSheet(f"color: {C_MUTED}; font-size: 14px;")
        lbl_prog.setFixedWidth(260)
        barra_geral = BarraSegmentada(len(FASES), completas, altura=10)
        prog_row.addWidget(lbl_prog)
        prog_row.addSpacing(10)
        prog_row.addWidget(barra_geral, 1)
        prog_wrap = QWidget()
        prog_wrap.setMinimumHeight(40)
        prog_wrap.setLayout(prog_row)
        self._layout_raiz.addWidget(prog_wrap)

        # Cartoes de fase em grade fluida: 4 lado a lado quando cabe,
        # 2x2 em janelas menores
        cards_container = QWidget()
        cards_container.setObjectName("transparente")
        cards_wrap = FlowLayout(cards_container, espacamento=18)
        cards_wrap.setContentsMargins(0, 12, 0, 12)
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
            "Treine as palavras que você mesmo adicionou."
            if minhas else
            "Adicione palavras pelo botão acima para liberar este treino.",
            len(minhas),
            desbloqueada=len(minhas) > 0,
            completa=False,
            custom=True,
        )
        card_custom.clicked.connect(lambda _i: self.fase_custom_selecionada.emit())
        cards_wrap.addWidget(card_custom)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(cards_container)
        self._layout_raiz.addWidget(scroll, 1)

    def reconstruir(self):
        self._limpar()
        self._construir()


class QuizCard(QFrame):
    """Card de selecao do tipo de quiz (Letras ou Minhas Palavras)."""
    clicked = pyqtSignal(str)   # "letras" ou "palavras"

    def __init__(self, tipo, icone, titulo, descricao, quantidade, disponivel):
        super().__init__()
        self.tipo = tipo
        self.disponivel = disponivel
        self.setFixedSize(440, 400)
        cor_borda = C_ACCENT if disponivel else C_BORDER
        hover = f"QFrame:hover {{ border: 1px solid {C_ACCENT}; }}" if disponivel else ""
        self.setStyleSheet(
            f"QFrame {{ background-color: {C_PANEL};"
            f" border: 1px solid {cor_borda}; border-radius: 18px; }}"
            + hover
        )
        if disponivel:
            self.setCursor(QCursor(Qt.PointingHandCursor))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 32, 30, 32)
        layout.setSpacing(18)
        layout.setAlignment(Qt.AlignTop)

        lbl_icone = QLabel(icone)
        lbl_icone.setAlignment(Qt.AlignCenter)
        lbl_icone.setFixedSize(132, 132)
        # Fonte do icone menor quando e texto (ABC) do que quando e um simbolo
        tam_icone = 44 if len(icone) > 1 else 58
        lbl_icone.setStyleSheet(
            f"background-color: {C_CARD}; color: {C_ACCENT};"
            f" border: 3px solid {C_ACCENT}; border-radius: 66px;"
            f" font-size: {tam_icone}px; font-weight: 800;"
        )
        layout.addWidget(lbl_icone, alignment=Qt.AlignHCenter)

        lbl_titulo = QLabel(titulo)
        lbl_titulo.setAlignment(Qt.AlignCenter)
        lbl_titulo.setStyleSheet(
            f"color: {C_TEXT}; font-size: 30px; font-weight: 800; border: none;"
        )
        layout.addWidget(lbl_titulo)

        lbl_desc = QLabel(descricao)
        lbl_desc.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        lbl_desc.setWordWrap(True)
        lbl_desc.setMinimumHeight(66)
        lbl_desc.setStyleSheet(
            f"color: {C_MUTED}; font-size: 17px; border: none;"
        )
        layout.addWidget(lbl_desc)

        info = QLabel(
            f"{quantidade} itens disponiveis" if disponivel
            else "Indisponível"
        )
        info.setAlignment(Qt.AlignCenter)
        info.setStyleSheet(
            f"color: {C_ACCENT if disponivel else C_MUTED};"
            f" font-size: 16px; font-weight: 600; border: none;"
        )
        layout.addWidget(info)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.disponivel:
            self.clicked.emit(self.tipo)


class AbaQuiz(QWidget):
    """Aba de quiz: a pessoa e questionada aleatoriamente sobre como se
    escreve uma letra do alfabeto ou uma das palavras que cadastrou."""
    quiz_selecionado = pyqtSignal(str)   # "letras" ou "palavras"

    def __init__(self, estado):
        super().__init__()
        self.estado = estado
        self._layout_raiz = QVBoxLayout(self)
        self._layout_raiz.setContentsMargins(20, 20, 20, 20)
        self._layout_raiz.setSpacing(14)
        self._construir()

    def _limpar(self):
        limpar_layout(self._layout_raiz)

    def _construir(self):
        # Cabecalho padronizado (mesma estrutura das outras abas)
        self._layout_raiz.addWidget(
            cabecalho_aba("Quiz de Caligrafia", "escolha um tipo e pratique com itens sorteados")
        )

        # Linha de instrucao (equivalente a barra de progresso das outras
        # abas), com texto bem visivel
        instrucao_row = QHBoxLayout()
        instrucao_row.setContentsMargins(0, 0, 0, 0)
        lbl_instrucao = QLabel(
            "Os itens sao sorteados aleatoriamente a cada quiz"
        )
        lbl_instrucao.setStyleSheet(f"color: {C_MUTED}; font-size: 17px;")
        instrucao_row.addWidget(lbl_instrucao)
        instrucao_row.addStretch()
        instrucao_wrap = QWidget()
        instrucao_wrap.setMinimumHeight(40)
        instrucao_wrap.setLayout(instrucao_row)
        self._layout_raiz.addWidget(instrucao_wrap)

        self._layout_raiz.addSpacing(16)

        # Conteudo com rolagem: garante que nada fica cortado, mesmo em
        # telas menores
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background: transparent;")
        container = QWidget()
        container.setObjectName("transparente")
        conteudo = QVBoxLayout(container)
        conteudo.setContentsMargins(0, 0, 8, 0)

        # Stretch antes E depois dos cards -> centralizados verticalmente
        # no espaco disponivel (nao mais colados ao topo)
        conteudo.addStretch(1)

        # Cards de escolha, centralizados e grandes
        cards_wrap = QHBoxLayout()
        cards_wrap.setSpacing(32)
        cards_wrap.addStretch()

        card_letras = QuizCard(
            "letras", "ABC", "Quiz de Letras",
            "Sorteia letras do alfabeto para você escrever.",
            len(LETRAS), disponivel=True,
        )
        card_letras.clicked.connect(self.quiz_selecionado.emit)
        cards_wrap.addWidget(card_letras)

        minhas = self.estado.get("palavras_customizadas", [])
        card_palavras = QuizCard(
            "palavras", "Aa", "Quiz de Palavras",
            "Sorteia palavras da sua lista 'Minhas Palavras'."
            if minhas else
            "Cadastre palavras em Palavras > Adicionar palavras para liberar.",
            len(minhas), disponivel=len(minhas) > 0,
        )
        card_palavras.clicked.connect(self.quiz_selecionado.emit)
        cards_wrap.addWidget(card_palavras)

        cards_wrap.addStretch()
        conteudo.addLayout(cards_wrap)
        conteudo.addStretch(1)

        scroll.setWidget(container)
        self._layout_raiz.addWidget(scroll, 1)

    def reconstruir(self):
        self._limpar()
        self._construir()


class DicionarioWorker(QThread):
    """Busca a definição em segundo plano para não travar a interface."""
    encontrado = pyqtSignal(object)   # dict ou None
    erro = pyqtSignal(str)

    def __init__(self, palavra):
        super().__init__()
        self.palavra = palavra

    def run(self):
        try:
            import dicionario_service
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
            lbl_fonte = QLabel(f"Fonte: {fonte}")
            lbl_fonte.setStyleSheet(
                f"color: {C_MUTED}; font-size: 11px; border: none;"
            )
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


class ConquistaCard(QFrame):
    """Card de uma conquista/medalha (desbloqueada ou bloqueada)."""

    def __init__(self, conquista):
        super().__init__()
        desbloqueada = conquista["desbloqueada"]
        self.setFixedSize(250, 104)
        cor_borda = C_GOOD if desbloqueada else C_BORDER
        self.setStyleSheet(
            f"QFrame {{ background-color: {C_PANEL};"
            f" border: 1px solid {cor_borda}; border-radius: 12px; }}"
        )
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(12)

        # Medalha (circulo)
        medalha = QLabel("*" if desbloqueada else "-")
        medalha.setAlignment(Qt.AlignCenter)
        medalha.setFixedSize(48, 48)
        cor_med = C_GOOD if desbloqueada else C_CARD
        cor_txt = "#ffffff" if desbloqueada else C_MUTED
        medalha.setStyleSheet(
            f"background-color: {cor_med}; color: {cor_txt};"
            f" border-radius: 24px; font-size: 22px; font-weight: 800;"
        )
        lay.addWidget(medalha)

        texto = QVBoxLayout()
        texto.setSpacing(2)
        titulo = QLabel(conquista["titulo"])
        cor_titulo = C_TEXT if desbloqueada else C_MUTED
        titulo.setStyleSheet(
            f"color: {cor_titulo}; font-size: 14px; font-weight: 700;"
            f" border: none; background: transparent;"
        )
        texto.addWidget(titulo)
        desc = QLabel(conquista["descricao"])
        desc.setWordWrap(True)
        desc.setStyleSheet(
            f"color: {C_MUTED}; font-size: 12px; border: none;"
            f" background: transparent;"
        )
        texto.addWidget(desc)
        lay.addLayout(texto, 1)


class AbaProgresso(QWidget):
    """Painel de progresso geral: anel de desempenho, estatisticas,
    mapa de calor das letras e conquistas."""

    def __init__(self, estado):
        super().__init__()
        self.estado = estado
        self._raiz = QVBoxLayout(self)
        self._raiz.setContentsMargins(20, 20, 20, 20)
        self._raiz.setSpacing(14)
        self._construir()

    def _limpar(self):
        limpar_layout(self._raiz)

    def _construir(self):
        from anel_progresso import AnelProgresso
        r = prog.resumo(self.estado)

        self._raiz.addWidget(
            cabecalho_aba("Seu Progresso", "acompanhe sua evolução na plataforma")
        )

        # Conteudo rolavel (pode ficar longo)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background: transparent;")
        container = QWidget()
        container.setObjectName("transparente")
        conteudo = QVBoxLayout(container)
        conteudo.setContentsMargins(0, 0, 8, 0)
        conteudo.setSpacing(18)

        # ── LINHA 1: anel + estatisticas ──
        topo = QHBoxLayout()
        topo.setSpacing(24)

        anel = AnelProgresso(r["percentual"], tamanho=220)
        topo.addWidget(anel, alignment=Qt.AlignTop)

        # Grade de estatisticas
        stats_grid = QGridLayout()
        stats_grid.setSpacing(12)
        cartoes = [
            ("Letras dominadas", f"{r['letras_dominadas']}/{r['letras_total']}", C_GOOD),
            ("Fases completas", f"{r['fases_completas']}/{r['fases_total']}", C_ACCENT),
            ("Minhas palavras", str(r["palavras"]), C_ACCENT),
            ("Exercícios feitos", str(r["exercicios_feitos"]), C_TEXT),
            ("Sequência atual", f"{r['streak_dias']} dia(s)", C_OK),
            ("Melhor sequência", f"{r['streak_recorde']} dia(s)", C_OK),
        ]
        for i, (rot, val, cor) in enumerate(cartoes):
            stats_grid.addWidget(self._stat_card(rot, val, cor), i // 3, i % 3)
        topo.addLayout(stats_grid, 1)
        conteudo.addLayout(topo)

        # ── LINHA 2: evolucao da nota ──
        conteudo.addWidget(self._titulo_secao("EVOLUÇÃO DA NOTA"))
        conteudo.addWidget(self._secao_evolucao())

        # ── LINHA 3: mapa de calor das letras ──
        conteudo.addWidget(self._titulo_secao("DOMÍNIO DO ALFABETO"))
        legenda = QLabel(
            "Cada quadrado mostra o nível de domínio da letra "
            "(cinza = não praticada, verde = dominada)."
        )
        legenda.setStyleSheet(f"color: {C_MUTED}; font-size: 12px; border: none;")
        conteudo.addWidget(legenda)
        conteudo.addWidget(self._mapa_calor())

        # ── LINHA 3: conquistas ──
        conqs = prog.conquistas_detalhadas(self.estado)
        feitas = sum(1 for c in conqs if c["desbloqueada"])
        conteudo.addWidget(
            self._titulo_secao(f"CONQUISTAS  ({feitas}/{len(conqs)})")
        )
        grid_conq = FlowLayout(espacamento=12)
        for c in conqs:
            grid_conq.addWidget(ConquistaCard(c))
        wrap_conq = QWidget()
        wrap_conq.setLayout(grid_conq)
        conteudo.addWidget(wrap_conq)

        conteudo.addStretch(1)
        scroll.setWidget(container)
        self._raiz.addWidget(scroll, 1)

    def _stat_card(self, rotulo, valor, cor):
        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background-color: {C_PANEL};"
            f" border: 1px solid {C_BORDER}; border-radius: 12px; }}"
        )
        card.setFixedHeight(92)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(4)
        lbl_val = QLabel(valor)
        lbl_val.setStyleSheet(
            f"color: {cor}; font-size: 26px; font-weight: 800;"
            f" border: none; background: transparent;"
        )
        lay.addWidget(lbl_val)
        lbl_rot = QLabel(rotulo)
        lbl_rot.setStyleSheet(
            f"color: {C_MUTED}; font-size: 12px; border: none;"
            f" background: transparent;"
        )
        lay.addWidget(lbl_rot)
        return card

    def _secao_evolucao(self):
        """Grafico da media diaria (30 dias) + resumo semana atual x anterior."""
        from grafico_evolucao import GraficoEvolucao
        card, lay = make_card(None)
        atual, n_atual = prog.media_periodo(self.estado, 7)
        anterior, _ = prog.media_periodo(self.estado, 7, deslocamento=7)
        if atual is None:
            resumo = "Sua média dos últimos 7 dias aparece aqui depois das primeiras tentativas."
        else:
            resumo = f"Média dos últimos 7 dias: <b>{atual:.0f}</b> ({n_atual} tentativa(s))"
            if anterior is not None:
                delta = atual - anterior
                cor = C_GOOD if delta >= 0 else C_BAD
                resumo += f" · <span style='color:{cor}'>{delta:+.0f}</span> em relação à semana anterior"
        lbl = QLabel(resumo)
        lbl.setStyleSheet(f"color: {C_MUTED}; font-size: 13px; border: none;")
        lay.addWidget(lbl)
        lay.addWidget(GraficoEvolucao(prog.evolucao_diaria(self.estado, 30), dias=30))

        # Letras com pior media recente: onde praticar
        por_letra = prog.evolucao_por_letra(self.estado)
        if por_letra:
            piores = sorted(por_letra.items(), key=lambda kv: kv[1][0])[:3]
            txt = "Letras para reforçar: " + "  ".join(
                f"<b>{l}</b> ({m:.0f})" for l, (m, _n) in piores
            )
            lbl2 = QLabel(txt)
            lbl2.setStyleSheet(f"color: {C_MUTED}; font-size: 12px; border: none;")
            lay.addWidget(lbl2)
        return card

    def _titulo_secao(self, texto):
        lbl = QLabel(texto)
        lbl.setStyleSheet(
            f"color: {C_MUTED}; font-size: 12px; font-weight: 700;"
            f" letter-spacing: 1.4px; border: none;"
        )
        return lbl

    def _mapa_calor(self):
        letras_estado = self.estado.get("letras", {})
        wrap = QWidget()
        grid = QGridLayout(wrap)
        grid.setSpacing(6)
        grid.setContentsMargins(0, 0, 0, 0)
        cols = 13
        for i, letra in enumerate(LETRAS):
            nivel = letras_estado.get(letra, 0)
            cor = self._cor_nivel(nivel)
            quad = QLabel(letra)
            quad.setAlignment(Qt.AlignCenter)
            quad.setFixedSize(48, 48)
            cor_txt = "#ffffff" if nivel >= 1 else C_MUTED
            quad.setStyleSheet(
                f"background-color: {cor}; color: {cor_txt};"
                f" border-radius: 8px; font-size: 18px; font-weight: 700;"
            )
            quad.setToolTip(
                f"{letra}: dominada" if nivel >= 5
                else f"{letra}: nível {nivel} de 5"
            )
            grid.addWidget(quad, i // cols, i % cols)
        return wrap

    def _cor_nivel(self, n):
        # Gradiente discreto: cinza -> ambar -> azul -> verde
        if n >= 5:
            return C_GOOD
        elif n >= 3:
            return C_ACCENT
        elif n >= 1:
            return C_OK
        return C_CARD

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
        header.setContentsMargins(0, 0, 0, 0)
        btn_voltar = QPushButton("Voltar")
        btn_voltar.setObjectName("ghost")
        btn_voltar.setFixedWidth(90)
        btn_voltar.clicked.connect(self._voltar_ao_inicio)
        header.addWidget(btn_voltar)

        titulo = QLabel("Praticar Caligrafia")
        titulo.setStyleSheet(f"font-size: 20px; font-weight: 800; color: {C_TEXT};")
        sub = QLabel("Treine sua escrita com exercícios guiados")
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
