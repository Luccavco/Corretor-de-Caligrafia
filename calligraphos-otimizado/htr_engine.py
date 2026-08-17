import warnings
import logging
import os

os.environ["TRANSFORMERS_VERBOSITY"] = "error"
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
logging.getLogger("transformers").setLevel(logging.ERROR)

from transformers import TrOCRProcessor, VisionEncoderDecoderModel

processor = None
model = None


def load_model():
    """Carrega o TrOCR uma unica vez. O download acontece so na
    primeira execucao; depois o modelo fica em cache local."""
    global processor, model
    print("Carregando modelo TrOCR...")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        processor = TrOCRProcessor.from_pretrained("microsoft/trocr-base-printed")
        model = VisionEncoderDecoderModel.from_pretrained("microsoft/trocr-base-printed")
    model.config.max_new_tokens = 64
    print("Modelo carregado!")


def predict(pil_image):
    """Transcreve uma unica imagem (uma linha de texto ou palavra)."""
    if processor is None or model is None:
        load_model()
    pixel_values = processor(images=pil_image, return_tensors="pt").pixel_values
    generated_ids = model.generate(pixel_values, max_new_tokens=64)
    text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
    return text.strip()


def predict_lines(line_images):
    """Transcreve uma lista de linhas de texto (redacoes, paragrafos)
    e devolve o texto completo com quebras de linha preservadas.

    O TrOCR foi treinado com linhas individuais de texto, entao
    transcrever linha a linha e mais preciso do que a pagina inteira."""
    if not line_images:
        return ""
    textos = []
    for img in line_images:
        texto = predict(img)
        if texto:
            textos.append(texto)
    return "\n".join(textos)


def predict_words(linhas_de_palavras):
    """Transcreve palavra por palavra (lista de linhas, cada linha e uma
    lista de imagens PIL de palavras individuais). Junta as palavras com
    espaco e as linhas com quebra de linha.

    Este e o modo mais confiavel do TrOCR: em palavras isoladas o modelo
    tem muito menos espaco para 'inventar' texto do que em linhas inteiras."""
    if not linhas_de_palavras:
        return ""
    linhas_texto = []
    for palavras in linhas_de_palavras:
        tokens = []
        for img in palavras:
            token = predict(img)
            token = token.strip().strip(".")
            if token:
                tokens.append(token)
        if tokens:
            linhas_texto.append(" ".join(tokens))
    return "\n".join(linhas_texto)
