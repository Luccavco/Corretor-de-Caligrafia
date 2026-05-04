import cv2
import numpy as np
from PIL import Image


def load_image(path):                                                   #Carrega a imagem selecionada
    image = cv2.imread(path)
    if image is None:
        raise ValueError(f"Imagem não encontrada: {path}")
    return image


def to_grayscale(image):                                                # Isso remove as cores da imagem, priorizando uma escala de cinza.
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)                      # Nao ha necessidade desse dissernimento para a identificacao de letras
                                                                        

def binarize(gray):                                                     # A binarizacao atua para a formacao do monocromatico na imagem.
    return cv2.adaptiveThreshold(                                       # Mesmo com presenca de sombra, determinada regiao se torna
        gray, 255,                                                      # 100% branco ou 100% preto.
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31, 10
    )


def correct_perspective(image):                                         # Detecta inclinacao do texto.
    coords = np.column_stack(np.where(image < 128))                     # Detecta todos os pixels com valor inferior a 128 (escuros). O np.column_stack junta o X e Y deles em pares.
    if len(coords) == 0:                                                # Para, caso nao haja pixel escuro.
        return image
    rect = cv2.minAreaRect(coords)                                      # Isso calcula o menor retangulo do pixel escuro. Fornece centro, tamanho e angulo.
    angle = rect[-1]                                                    # Este pega o angulo.
    if angle < -45:
        angle += 90
    h, w = image.shape[:2]
    center = (w // 2, h // 2)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)                # no fim, aplica correcoes.
    return cv2.warpAffine(image, matrix, (w, h),                        # matriz matematica de rotacao, aplicada em toda a imagem e endireita o texto.
                          flags=cv2.INTER_CUBIC,
                          borderMode=cv2.BORDER_REPLICATE)


def segment_characters(binary):                                         # Detecta manchas e perturbacoes na imagens.
    contours, _ = cv2.findContours(                                     # Averigua a prossiblidade de ser uma letra.
        cv2.bitwise_not(binary),                                        # Inverte a cor bruta da imagem (branco vira preto e preto vira branco)
        cv2.RETR_EXTERNAL,                                              # Pega contornos externos.
        cv2.CHAIN_APPROX_SIMPLE                                         # Comprime, guardando pontos essenciais (economiza uso da memoria).
    )
    characters = []
    for cnt in contours:                                                # PARA CADA CONTORNO, calcula o menor retangulo.
        x, y, w, h = cv2.boundingRect(cnt)                              # Devolve X, Y, Largura e Altura.
        if w > 8 and h > 8:                                             # Filtra detalhes muito pequenos (pontos, sujeira, manchas pequenas etc).
            char_img = binary[y:y+h, x:x+w]                             # Recorte final.
            characters.append((x, y, w, h, char_img))
    characters.sort(key=lambda c: c[0])                                 # Ordena a lista pelo valor de x da cada caractere. Da esquerda pra direita em ordem de leitura.
    return characters


def process(path):                                                      # Executa tudo em sequencia
    image = load_image(path)
    gray = to_grayscale(image)
    binary = binarize(gray)
    corrected = correct_perspective(binary)
    characters = segment_characters(corrected)
    pil_image = Image.fromarray(corrected).convert("RGB")
    return pil_image, characters