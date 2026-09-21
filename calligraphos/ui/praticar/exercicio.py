"""Painel de exercicio (letra ou palavra): quadro/foto, verificacao em segundo
plano (worker), validacao da tentativa pela nota e mapa de diferencas."""

import os
import cv2
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFileDialog, QProgressBar, QSizePolicy, QStackedWidget
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from calligraphos.nucleo.image_pipeline import process
from calligraphos.nucleo.handwriting_evaluator import avaliar_texto
from calligraphos.ui.ui_theme import C_CARD, C_TEXT, C_MUTED, C_BORDER, C_GOOD, C_OK, C_BAD, make_card
from calligraphos.ui.ui_helpers import rotulo
from calligraphos.ui.praticar.cartoes import BarraSegmentada
from calligraphos.ui.praticar.constantes import FONTE_FORMA, NOTA_MINIMA_LETRA, NOTA_MINIMA_PIOR


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
                from calligraphos.nucleo.htr_google import predict_from_path
                texto = predict_from_path(self.image_path)
            except Exception:
                offline = True
                texto = self._transcrever_offline(characters, avaliacao, linhas)

            # Mapa verde/vermelho/azul da letra contra o molde, para o
            # usuario ver onde o traco saiu do esperado
            from calligraphos.nucleo.feedback_visual import mapa_diferencas
            from calligraphos.nucleo.image_pipeline import load_image
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
        from calligraphos.nucleo.htr_engine import predict
        return " ".join(predict(linha).strip() for linha in linhas)

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
        self.label_progresso = rotulo("", C_MUTED, peso=600)
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
        from calligraphos.ui.canvas_desenho import CanvasDesenho
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
        self._feedback("", C_MUTED)
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
            self._feedback("Escreva a resposta no quadro antes de enviar.", C_OK)
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
            self._feedback("Muito bem! Você acertou.", C_GOOD, tamanho=15, peso=700)
            self.btn_enviar.setText("Continuar")
            self._desconectar_btn_enviar()
            self.btn_enviar.clicked.connect(self._continuar)
        else:
            self._feedback(motivo, C_BAD, tamanho=14, peso=600)

    def _continuar(self):
        if self.modo == "fase":
            self.indice += 1
        self.mostrar_alvo_atual()

    def on_erro(self, mensagem):
        self.progress.setVisible(False)
        self.btn_enviar.setEnabled(True)
        self.btn_foto.setEnabled(True)
        self.btn_pular.setEnabled(True)
        self._feedback(f"Erro ao processar: {mensagem}", C_BAD)

    def _feedback(self, texto, cor, tamanho=13, peso=None):
        """Mostra uma mensagem na faixa de feedback com a cor/tamanho dados."""
        self.label_feedback.setText(texto)
        negrito = f" font-weight: {peso};" if peso else ""
        self.label_feedback.setStyleSheet(
            f"color: {cor}; font-size: {tamanho}px;{negrito} padding: 8px; border: none;"
        )

    def _validar(self, alvo, texto, avaliacao):
        from calligraphos.nucleo.handwriting_evaluator import explicar_letra
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
