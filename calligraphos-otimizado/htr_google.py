"""Integracao com o Google Cloud Vision para HTR.
Fornece duas funcoes:
- predict_from_path: devolve so o texto (compatibilidade)
- predict_detailed: devolve o texto E a lista de simbolos individuais,
  cada um com a letra identificada e sua caixa (x, y, w, h) na imagem.

A deteccao por simbolo e o que permite a Analise Individual saber
exatamente qual letra esta em cada regiao da imagem, mesmo em texto
cursivo ou redacoes longas.
"""

import os
import re
import unicodedata
from google.cloud import vision

# Credenciais resolvidas a partir da pasta deste arquivo (funciona nao
# importa de onde o programa foi iniciado). setdefault preserva um
# GOOGLE_APPLICATION_CREDENTIALS ja definido no ambiente, se houver.
_CRED_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "google_credentials.json"
)
os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", _CRED_PATH)

_client = None


def get_client():
    global _client
    if _client is None:
        _client = vision.ImageAnnotatorClient()
    return _client


def _remover_acento(ch):
    """E -> E, e com acento -> E, c cedilha -> C. Usado para mapear
    letras acentuadas do portugues para o alfabeto A-Z do treino."""
    norm = unicodedata.normalize("NFD", ch)
    base = "".join(c for c in norm if unicodedata.category(c) != "Mn")
    return base.upper()


def _fazer_requisicao(image_path):
    client = get_client()
    with open(image_path, "rb") as f:
        content = f.read()
    image = vision.Image(content=content)
    response = client.document_text_detection(
        image=image,
        image_context={"language_hints": ["pt"]}
    )
    if response.error.message:
        raise RuntimeError(f"Erro do Google Vision: {response.error.message}")
    return response


def _juntar_hifenizacao(texto):
    """Junta palavras quebradas por hifen no fim da linha:
    'peque-\nno' vira 'pequeno'. Comum em redacoes escritas a mao."""
    return re.sub(r"-\s*\n\s*", "", texto)


def predict_from_path(image_path):
    """Transcreve o texto manuscrito de uma imagem. Devolve so o texto."""
    response = _fazer_requisicao(image_path)
    texto = response.full_text_annotation.text.strip()
    return _juntar_hifenizacao(texto)


def predict_detailed(image_path):
    """Transcreve e devolve tambem os simbolos individuais.

    Retorna (texto, simbolos) onde simbolos e uma lista de dicts:
    { 'letra': 'A' (sem acento, maiuscula),
      'letra_original': 'a' (como o Vision reconheceu),
      'x': int, 'y': int, 'w': int, 'h': int }
    na ordem de leitura. Apenas simbolos alfabeticos sao incluidos."""
    response = _fazer_requisicao(image_path)
    texto = _juntar_hifenizacao(response.full_text_annotation.text.strip())

    simbolos = []
    for page in response.full_text_annotation.pages:
        for block in page.blocks:
            for paragraph in block.paragraphs:
                for word in paragraph.words:
                    for symbol in word.symbols:
                        ch = symbol.text
                        if not ch or not ch.isalpha():
                            continue
                        letra_base = _remover_acento(ch)
                        if not (len(letra_base) == 1 and "A" <= letra_base <= "Z"):
                            continue
                        vs = symbol.bounding_box.vertices
                        xs = [v.x for v in vs]
                        ys = [v.y for v in vs]
                        x, y = min(xs), min(ys)
                        w, h = max(xs) - x, max(ys) - y
                        if w < 2 or h < 2:
                            continue
                        simbolos.append({
                            "letra": letra_base,
                            "letra_original": ch,
                            "x": x, "y": y, "w": w, "h": h,
                        })
    return texto, simbolos
