import os
import cv2
from image_pipeline import process
from htr_engine import predict
from handwriting_evaluator import avaliar_texto, formatar_feedback, load_modelo

def testar_imagem(path):
    print(f"\n{'='*40}")
    print(f"Arquivo: {os.path.basename(path)}")
    print(f"{'='*40}")
    try:
        pil_image, characters = process(path)
        texto = predict(pil_image)
        print(f"Texto reconhecido: {texto}")
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
        and "ruim" not in f.lower()
    ]
    imagens.sort()

    print(f"Testando {len(imagens)} imagem(ns)...\n")
    for path in imagens:
        testar_imagem(path)

    print(f"\n{'='*40}")
    print("Testes concluidos.")