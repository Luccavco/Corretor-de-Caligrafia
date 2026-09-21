import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from calligraphos.nucleo.image_pipeline import process
from calligraphos.nucleo.htr_engine import predict_lines
from calligraphos.nucleo.handwriting_evaluator import avaliar_texto, formatar_feedback, load_modelo


def testar_imagem(path):
    print(f"\n{'=' * 44}")
    print(f"Arquivo: {os.path.basename(path)}")
    print(f"{'=' * 44}")
    try:
        pil_image, characters, line_images = process(path)
        print(f"Linhas de texto detectadas: {len(line_images)}")
        print(f"Caracteres detectados: {len(characters)}")
        texto = predict_lines(line_images)
        print(f"Texto reconhecido:\n{texto}")
        print("-" * 44)
        avaliacao = avaliar_texto(characters)
        print(formatar_feedback(avaliacao))
    except Exception as e:
        print(f"Erro: {e}")


if __name__ == "__main__":
    load_modelo()
    pasta = "test_images"
    imagens = [
        os.path.join(pasta, f)
        for f in os.listdir(pasta)
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
        and "segmentado" not in f
        and "debug" not in f
    ]
    imagens.sort()

    print(f"Testando {len(imagens)} imagem(ns)...")
    for path in imagens:
        testar_imagem(path)

    print(f"\n{'=' * 44}")
    print("Testes concluidos.")
