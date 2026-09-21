"""Gera a Figura 2 do artigo: as tres etapas do pre-processamento
(original, binarizada, segmentada) lado a lado, usando as funcoes REAIS
do image_pipeline.py do projeto.

Para usar com uma foto SUA de verdade:
    python gerar_figura2.py /caminho/da/sua/foto.jpg
Sem argumento, ele usa uma imagem de exemplo gerada aqui.
"""
import sys
import os
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# Importa o pipeline real do projeto
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from calligraphos.nucleo import image_pipeline as ip
def imagem_exemplo():
    """Cria uma imagem de exemplo com uma palavra em 'letra de forma',
    simulando uma foto de texto manuscrito sobre papel."""
    W, H = 640, 240
    img = Image.new("RGB", (W, H), (245, 244, 240))  # papel levemente creme
    d = ImageDraw.Draw(img)
    # tenta uma fonte manuscrita/serifada; cai para a padrao se nao houver
    fonte = None
    for cam in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
        "/usr/share/fonts/dejavu/DejaVuSerif.ttf",
    ]:
        if os.path.exists(cam):
            fonte = ImageFont.truetype(cam, 130)
            break
    if fonte is None:
        fonte = ImageFont.load_default()
    # desenha "CASA" com leve variacao de posicao (imita escrita a mao)
    texto = "CASA"
    x = 90
    for i, ch in enumerate(texto):
        dy = [0, 8, -6, 4][i % 4]
        d.text((x, 55 + dy), ch, font=fonte, fill=(30, 30, 40))
        x += 120
    caminho = "_exemplo_entrada.png"
    img.save(caminho)
    return caminho


def rotular(img_bgr, texto):
    """Adiciona uma faixa branca embaixo com o rotulo da etapa."""
    h, w = img_bgr.shape[:2]
    faixa = np.full((46, w, 3), 255, np.uint8)
    out = np.vstack([img_bgr, faixa])
    cv2.putText(out, texto, (12, h + 32), cv2.FONT_HERSHEY_SIMPLEX,
                0.7, (30, 30, 30), 2, cv2.LINE_AA)
    return out


def para_altura(img_bgr, alvo=260):
    h, w = img_bgr.shape[:2]
    esc = alvo / h
    return cv2.resize(img_bgr, (int(w * esc), alvo), interpolation=cv2.INTER_AREA)


def main():
    if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
        entrada = sys.argv[1]
        print(f"Usando sua imagem: {entrada}")
    else:
        entrada = imagem_exemplo()
        print("Usando imagem de EXEMPLO (passe o caminho de uma foto sua para trocar)")

    # ── Etapa 1: original ──
    original = ip.load_image(entrada)

    # ── Etapa 2: binarizada (funcoes reais do projeto) ──
    gray = ip.to_grayscale(original)
    binary = ip.binarize(gray)
    corrected = ip.correct_perspective(binary)
    binar_bgr = cv2.cvtColor(corrected, cv2.COLOR_GRAY2BGR)

    # ── Etapa 3: segmentada (caixas em cada caractere) ──
    _, characters, _ = ip.process(entrada)
    seg = cv2.cvtColor(corrected, cv2.COLOR_GRAY2BGR)
    for c in characters:
        x, y, w, h = c[0], c[1], c[2], c[3]
        cv2.rectangle(seg, (x, y), (x + w, y + h), (255, 100, 40), 3)
    print(f"Caracteres segmentados: {len(characters)}")

    # ── Monta a figura tripla ──
    e1 = rotular(para_altura(original), "(a) Imagem original")
    e2 = rotular(para_altura(binar_bgr), "(b) Binarizada")
    e3 = rotular(para_altura(seg), "(c) Segmentada")

    # iguala alturas
    alt = max(e1.shape[0], e2.shape[0], e3.shape[0])
    def pad(im):
        if im.shape[0] < alt:
            faixa = np.full((alt - im.shape[0], im.shape[1], 3), 255, np.uint8)
            im = np.vstack([im, faixa])
        return im
    e1, e2, e3 = pad(e1), pad(e2), pad(e3)

    # separadores brancos
    sep = np.full((alt, 30, 3), 255, np.uint8)
    figura = np.hstack([e1, sep, e2, sep, e3])

    # moldura branca ao redor
    figura = cv2.copyMakeBorder(figura, 20, 20, 20, 20,
                                cv2.BORDER_CONSTANT, value=(255, 255, 255))
    saida = "Figura2_Pipeline.png"
    cv2.imwrite(saida, figura)
    print(f"Figura salva em {saida}")


if __name__ == "__main__":
    main()
