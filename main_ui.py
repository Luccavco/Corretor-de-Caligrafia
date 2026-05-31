import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QPushButton, QLabel, QFileDialog,
    QTextEdit, QFrame, QProgressBar
)
from PyQt5.QtGui import QPixmap, QFont
from PyQt5.QtCore import Qt, QThread, pyqtSignal

from image_pipeline import process
from htr_engine import predict


class WorkerThread(QThread):
    finished = pyqtSignal(str, list)
    error = pyqtSignal(str)

    def __init__(self, image_path):
        super().__init__()
        self.image_path = image_path

    def run(self):
        try:
            pil_image, characters = process(self.image_path)
            texto = predict(pil_image)
            self.finished.emit(texto, characters)
        except Exception as e:
            self.error.emit(str(e))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Avaliador de Caligrafia — TCC")
        self.setMinimumSize(900, 600)
        self.image_path = None
        self.worker = None
        self.setup_ui()

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)

        # Coluna esquerda — imagem
        left = QVBoxLayout()

        self.btn_carregar = QPushButton("Carregar Imagem")
        self.btn_carregar.setFixedHeight(40)
        self.btn_carregar.clicked.connect(self.carregar_imagem)
        left.addWidget(self.btn_carregar)

        self.label_imagem = QLabel("Nenhuma imagem carregada")
        self.label_imagem.setAlignment(Qt.AlignCenter)
        self.label_imagem.setFrameShape(QFrame.Box)
        self.label_imagem.setMinimumSize(400, 400)
        self.label_imagem.setStyleSheet("background-color: #1e1e1e; color: #888;")
        left.addWidget(self.label_imagem)

        self.btn_transcrever = QPushButton("Transcrever e Avaliar")
        self.btn_transcrever.setFixedHeight(40)
        self.btn_transcrever.setEnabled(False)
        self.btn_transcrever.clicked.connect(self.transcrever)
        left.addWidget(self.btn_transcrever)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setRange(0, 0)
        left.addWidget(self.progress)

        layout.addLayout(left, 55)

        # Coluna direita — resultados
        right = QVBoxLayout()

        label_transcricao = QLabel("Texto Reconhecido")
        label_transcricao.setFont(QFont("Arial", 11, QFont.Bold))
        right.addWidget(label_transcricao)

        self.texto_resultado = QTextEdit()
        self.texto_resultado.setReadOnly(True)
        self.texto_resultado.setPlaceholderText("O texto transcrito aparecerá aqui...")
        self.texto_resultado.setMaximumHeight(120)
        right.addWidget(self.texto_resultado)

        label_avaliacao = QLabel("Avaliação de Caligrafia")
        label_avaliacao.setFont(QFont("Arial", 11, QFont.Bold))
        right.addWidget(label_avaliacao)

        self.painel_avaliacao = QLabel(
            "Aguardando imagem...\n\n"
            "O avaliador de caligrafia analisará:\n"
            "  • Proporção das letras\n"
            "  • Inclinação dos caracteres\n"
            "  • Espaçamento entre letras\n\n"
            "Pontuação geral e feedback\naparecerão aqui após a transcrição."
        )
        self.painel_avaliacao.setAlignment(Qt.AlignTop)
        self.painel_avaliacao.setFrameShape(QFrame.Box)
        self.painel_avaliacao.setStyleSheet(
            "background-color: #1e1e1e; color: #888; padding: 12px;"
        )
        self.painel_avaliacao.setWordWrap(True)
        right.addWidget(self.painel_avaliacao, 1)

        self.btn_copiar = QPushButton("Copiar Texto")
        self.btn_copiar.setFixedHeight(36)
        self.btn_copiar.setEnabled(False)
        self.btn_copiar.clicked.connect(self.copiar_texto)
        right.addWidget(self.btn_copiar)

        layout.addLayout(right, 45)

    def carregar_imagem(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Selecionar Imagem", "",
            "Imagens (*.png *.jpg *.jpeg)"
        )
        if path:
            self.image_path = path
            pixmap = QPixmap(path).scaled(
                400, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.label_imagem.setPixmap(pixmap)
            self.btn_transcrever.setEnabled(True)
            self.texto_resultado.clear()
            self.painel_avaliacao.setText("Imagem carregada. Clique em 'Transcrever e Avaliar'.")
            self.painel_avaliacao.setStyleSheet(
                "background-color: #1e1e1e; color: #aaa; padding: 12px;"
            )

    def transcrever(self):
        if not self.image_path:
            return
        self.btn_transcrever.setEnabled(False)
        self.btn_carregar.setEnabled(False)
        self.progress.setVisible(True)
        self.painel_avaliacao.setText("Processando imagem...")

        self.worker = WorkerThread(self.image_path)
        self.worker.finished.connect(self.on_resultado)
        self.worker.error.connect(self.on_erro)
        self.worker.start()

    def on_resultado(self, texto, characters):
        from handwriting_evaluator import avaliar_texto, formatar_feedback

        self.progress.setVisible(False)
        self.btn_transcrever.setEnabled(True)
        self.btn_carregar.setEnabled(True)
        self.btn_copiar.setEnabled(True)

        self.texto_resultado.setText(texto)

        avaliacao = avaliar_texto(characters)
        feedback = formatar_feedback(avaliacao)

        self.painel_avaliacao.setText(feedback)
        self.painel_avaliacao.setStyleSheet(
            "background-color: #1e1e1e; color: #ccc; padding: 12px;"
        )

    def on_erro(self, mensagem):
        self.progress.setVisible(False)
        self.btn_transcrever.setEnabled(True)
        self.btn_carregar.setEnabled(True)
        self.painel_avaliacao.setText(f"Erro: {mensagem}")

    def copiar_texto(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.texto_resultado.toPlainText())


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())