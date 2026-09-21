"""Thread da analise: transcricao (Google Vision ou TrOCR), avaliacao das letras
e imagem anotada, sem travar a interface."""

from PyQt5.QtCore import QThread, pyqtSignal
from calligraphos.nucleo.image_pipeline import annotate_image, characters_from_boxes, annotate_from_characters
from calligraphos.nucleo.handwriting_evaluator import avaliar_texto


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
                from calligraphos.nucleo.htr_google import predict_detailed
                try:
                    texto, simbolos = predict_detailed(self.image_path)
                except Exception as e:
                    # Sem internet/credenciais: sinaliza para a interface
                    # oferecer o motor offline em vez de so mostrar o erro
                    self.error.emit(f"__OFFLINE__{e}")
                    return
                boxes = [(s["x"], s["y"], s["w"], s["h"]) for s in simbolos]
                characters = characters_from_boxes(self.image_path, boxes)
                avaliacao = avaliar_texto(characters, alvos=[s["letra"] for s in simbolos])
                letras = {i: s["letra"] for i, s in enumerate(simbolos)}
                anotada = annotate_from_characters(self.image_path, avaliacao)
                self.finished.emit(texto, avaliacao, anotada, letras)
            else:
                # TrOCR offline: analisa APENAS uma palavra isolada.
                from calligraphos.nucleo.image_pipeline import first_word_data
                from calligraphos.nucleo.htr_engine import predict
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
                letras_texto = [c for c in texto.upper() if "A" <= c <= "Z"]
                alvos = letras_texto if len(letras_texto) == len(characters) else None
                avaliacao = avaliar_texto(characters, alvos=alvos)
                anotada = annotate_image(self.image_path, avaliacao)
                self.finished.emit(texto, avaliacao, anotada, None)
        except Exception as e:
            self.error.emit(str(e))
