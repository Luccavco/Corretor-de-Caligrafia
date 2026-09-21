import cv2
import numpy as np
from PIL import Image


# ─── CARREGAMENTO E TRATAMENTO BASICO ────────────────────────────────────────

def load_image(path):
    """Carrega a imagem do disco. Erro claro se o arquivo nao existir."""
    image = cv2.imread(path)
    if image is None:
        raise ValueError(f"Imagem nao encontrada: {path}")
    return image


def to_grayscale(image):
    """Remove as cores. Texto nao precisa de cor para ser reconhecido."""
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def binarize(gray):
    """Binarizacao adaptativa: fundo 100% branco, tinta 100% preta,
    mesmo com sombra ou iluminacao irregular na foto."""
    blur = cv2.GaussianBlur(gray, (3, 3), 0)
    binary = cv2.adaptiveThreshold(
        blur, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31, 12
    )
    # Fecha pequenos buracos no traco da caneta
    kernel = np.ones((2, 2), np.uint8)
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
    return remover_linhas_pauta(binary)


def remover_linhas_pauta(binary, fracao_largura=0.6):
    """Apaga linhas horizontais longas (pauta de caderno) da imagem
    binarizada. Uma linha de pauta atravessa boa parte da largura da foto;
    nenhum traco de letra faz isso, entao tudo que sobrevive a uma abertura
    morfologica horizontal desse comprimento e pauta, nao escrita."""
    h, w = binary.shape[:2]
    comprimento = max(40, int(w * fracao_largura))
    if comprimento >= w:
        return binary
    tinta = cv2.bitwise_not(binary)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (comprimento, 1))
    linhas = cv2.morphologyEx(tinta, cv2.MORPH_OPEN, kernel)
    if not linhas.any():
        return binary
    # engrossa um pouco a linha detectada para levar junto as bordas serrilhadas
    linhas = cv2.dilate(linhas, np.ones((5, 1), np.uint8))
    return cv2.bitwise_or(binary, linhas)


def correct_perspective(image):
    """Detecta a inclinacao geral do texto e endireita a imagem."""
    coords = np.column_stack(np.where(image < 128))
    if len(coords) == 0:
        return image
    rect = cv2.minAreaRect(coords)
    angle = rect[-1]
    if angle < -45:
        angle += 90
    elif angle > 45:
        angle -= 90
    # Rotacoes muito grandes costumam ser falso positivo em fotos normais
    if abs(angle) > 30:
        return image
    h, w = image.shape[:2]
    center = (w // 2, h // 2)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    return cv2.warpAffine(image, matrix, (w, h),
                          flags=cv2.INTER_CUBIC,
                          borderMode=cv2.BORDER_REPLICATE)


# ─── SEGMENTACAO DE LINHAS (suporte a redacoes) ──────────────────────────────

def segment_lines(binary):
    """Divide a imagem em faixas horizontais, uma por linha de texto.
    Usa projecao horizontal: soma a tinta de cada linha de pixels e
    detecta onde ha texto e onde ha espaco em branco entre linhas."""
    inv = cv2.bitwise_not(binary)
    proj = np.sum(inv, axis=1).astype(np.float64)

    if proj.max() == 0:
        return []

    # Suaviza a projecao para nao quebrar linha em acentos/espacos internos
    kernel_size = max(3, binary.shape[0] // 200)
    proj = np.convolve(proj, np.ones(kernel_size) / kernel_size, mode="same")

    threshold = proj.max() * 0.04
    has_ink = proj > threshold

    bands = []
    start = None
    for i, ink in enumerate(has_ink):
        if ink and start is None:
            start = i
        elif not ink and start is not None:
            bands.append((start, i))
            start = None
    if start is not None:
        bands.append((start, len(has_ink)))

    # Junta faixas separadas por espacos muito pequenos (ex: pingo do i)
    min_gap = max(6, binary.shape[0] // 80)
    merged = []
    for s, e in bands:
        if merged and s - merged[-1][1] < min_gap:
            merged[-1] = (merged[-1][0], e)
        else:
            merged.append((s, e))

    # Remove faixas finas demais para serem uma linha de texto
    min_height = max(10, binary.shape[0] // 100)
    merged = [(s, e) for s, e in merged if e - s >= min_height]

    # Adiciona uma folga vertical em cada faixa
    pad = 4
    result = []
    for s, e in merged:
        s = max(0, s - pad)
        e = min(binary.shape[0], e + pad)
        result.append((s, e))
    return result


# ─── SEGMENTACAO DE CARACTERES ───────────────────────────────────────────────

def _merge_overlapping(boxes):
    """Une caixas que se sobrepoem horizontalmente (barra do A,
    pingo do i, acentos) na mesma letra em vez de conta-las separadas."""
    if not boxes:
        return []
    boxes = sorted(boxes, key=lambda b: b[0])
    merged = [list(boxes[0])]
    for x, y, w, h in boxes[1:]:
        mx, my, mw, mh = merged[-1]
        # Sobreposicao horizontal entre a caixa atual e a anterior
        overlap = min(mx + mw, x + w) - max(mx, x)
        smaller = min(w, mw)
        # Fragmento de traco quebrado: caixa bem mais estreita que a outra,
        # contida na altura dela e encostando na horizontal (perna de um A
        # que a binarizacao separou do corpo, por exemplo)
        menor, maior = ((x, y, w, h), (mx, my, mw, mh)) if w < mw else ((mx, my, mw, mh), (x, y, w, h))
        contido = (menor[1] >= maior[1] - 2 and menor[1] + menor[3] <= maior[1] + maior[3] + 2)
        fragmento = overlap > 0 and menor[2] < 0.6 * maior[2] and contido
        if overlap > smaller * 0.4 or fragmento:
            nx = min(mx, x)
            ny = min(my, y)
            nx2 = max(mx + mw, x + w)
            ny2 = max(my + mh, y + h)
            merged[-1] = [nx, ny, nx2 - nx, ny2 - ny]
        else:
            merged.append([x, y, w, h])
    return [tuple(b) for b in merged]


# Uma letra maiuscula de forma raramente e mais larga que alta (M e W chegam
# a ~1.2). Caixas mais largas que isso costumam ser duas letras encostadas.
RAZAO_MAX_LETRA = 1.35


def _dividir_letras_coladas(line_binary, box, profundidade=0):
    """Se a caixa for larga demais para uma letra, procura o vale do perfil
    vertical de tinta (coluna com menos tinta, longe das bordas) e divide
    ali, recursivamente. Devolve a lista de caixas resultante."""
    x, y, w, h = box
    if profundidade > 3 or w < 12 or w / max(h, 1) <= RAZAO_MAX_LETRA:
        return [box]
    tinta = (line_binary[y:y + h, x:x + w] < 128).sum(axis=0)
    margem = max(3, int(w * 0.2))
    interior = tinta[margem:w - margem]
    if interior.size == 0:
        return [box]
    corte = int(np.argmin(interior)) + margem
    # So divide se o vale for bem mais raso que o traco tipico da caixa
    if tinta[corte] > 0.35 * np.median(tinta[tinta > 0]):
        return [box]
    esquerda = (x, y, corte, h)
    direita = (x + corte, y, w - corte, h)
    return (_dividir_letras_coladas(line_binary, esquerda, profundidade + 1)
            + _dividir_letras_coladas(line_binary, direita, profundidade + 1))


def _reajustar_caixa(line_binary, box):
    """Encolhe a caixa ate a tinta que ela realmente contem (apos um corte
    a altura pode ficar sobrando)."""
    x, y, w, h = box
    sub = line_binary[y:y + h, x:x + w] < 128
    linhas = np.where(sub.any(axis=1))[0]
    colunas = np.where(sub.any(axis=0))[0]
    if linhas.size == 0 or colunas.size == 0:
        return box
    return (x + int(colunas[0]), y + int(linhas[0]),
            int(colunas[-1] - colunas[0] + 1), int(linhas[-1] - linhas[0] + 1))


def segment_characters_in_line(line_binary, offset_y=0):
    """Encontra e recorta cada letra dentro de uma linha de texto."""
    contours, _ = cv2.findContours(
        cv2.bitwise_not(line_binary),
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )
    boxes = []
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        if w > 4 and h > 4:
            boxes.append((x, y, w, h))

    boxes = _merge_overlapping(boxes)

    # Letras encostadas (ex.: "CA" num contorno so) viram caixas separadas
    divididas = []
    for b in boxes:
        for parte in _dividir_letras_coladas(line_binary, b):
            divididas.append(_reajustar_caixa(line_binary, parte))
    boxes = sorted(divididas, key=lambda b: b[0])

    # Filtro final: descarta fragmentos que sobraram (muito pequenos
    # ou desproporcionais demais para serem uma letra)
    line_h = line_binary.shape[0]
    characters = []
    for x, y, w, h in boxes:
        # Largura minima baixa: letras como I e l sao legitimamente finas
        if w < 3 or h < 8:
            continue
        if h < line_h * 0.15:
            continue
        char_img = line_binary[y:y + h, x:x + w]
        characters.append((x, y + offset_y, w, h, char_img))

    characters.sort(key=lambda c: c[0])
    return characters


# ─── PIPELINE COMPLETO ───────────────────────────────────────────────────────

def process(path):
    """Executa o pipeline completo e devolve:
    - pil_image: imagem inteira tratada (para referencia/exibicao)
    - characters: lista de todas as letras [(x, y, w, h, recorte), ...]
      em ordem de leitura (linha por linha, esquerda para direita)
    - line_images: lista de imagens PIL, uma por linha de texto
      (o TrOCR transcreve melhor linha a linha)
    """
    image = load_image(path)
    gray = to_grayscale(image)
    binary = binarize(gray)
    corrected = correct_perspective(binary)

    bands = segment_lines(corrected)

    characters = []
    line_images = []
    for (y1, y2) in bands:
        line = corrected[y1:y2, :]
        chars = segment_characters_in_line(line, offset_y=y1)
        characters.extend(chars)
        line_images.append(Image.fromarray(line).convert("RGB"))

    # Fallback: se nenhuma linha foi detectada, trata a imagem inteira
    if not line_images:
        line_images = [Image.fromarray(corrected).convert("RGB")]
        characters = segment_characters_in_line(corrected, offset_y=0)

    pil_image = Image.fromarray(corrected).convert("RGB")
    return pil_image, characters, line_images


def annotate_image(path, avaliacao):
    """Gera uma copia colorida da imagem tratada com um retangulo em
    cada letra, na cor da classificacao (verde/ambar/vermelho).
    Retorna um array BGR pronto para exibir na interface."""
    image = load_image(path)
    gray = to_grayscale(image)
    binary = binarize(gray)
    corrected = correct_perspective(binary)
    canvas = cv2.cvtColor(corrected, cv2.COLOR_GRAY2BGR)

    if avaliacao is None:
        return canvas

    cores = {
        0: (60, 60, 230),    # vermelho (BGR)
        1: (40, 170, 240),   # ambar
        2: (80, 190, 80),    # verde
    }
    for r in avaliacao["caracteres"]:
        x, y, w, h = r["posicao"]
        cor = cores.get(r["classe"], (200, 200, 200))
        cv2.rectangle(canvas, (x, y), (x + w, y + h), cor, 2)
    return canvas


# ─── SUPORTE A CAIXAS EXTERNAS (Google Vision por simbolo) ───────────────────

def characters_from_boxes(path, boxes):
    """Recorta caracteres a partir de caixas fornecidas externamente
    (ex: caixas por simbolo do Google Vision). As caixas estao em
    coordenadas da imagem ORIGINAL, entao aqui binarizamos sem aplicar
    correcao de perspectiva para as coordenadas continuarem validas.

    boxes: lista de (x, y, w, h)
    Retorna lista no mesmo formato do pipeline: [(x, y, w, h, recorte)]"""
    image = load_image(path)
    gray = to_grayscale(image)
    binary = binarize(gray)
    H, W = binary.shape[:2]

    characters = []
    for (x, y, w, h) in boxes:
        x = max(0, min(int(x), W - 1))
        y = max(0, min(int(y), H - 1))
        w = max(1, min(int(w), W - x))
        h = max(1, min(int(h), H - y))
        crop = binary[y:y + h, x:x + w]
        characters.append((x, y, w, h, crop))
    return characters


def annotate_from_characters(path, avaliacao):
    """Como annotate_image, mas desenha sobre a imagem binarizada SEM
    correcao de perspectiva (coordenadas do Google Vision sao da
    imagem original)."""
    image = load_image(path)
    gray = to_grayscale(image)
    binary = binarize(gray)
    canvas = cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)

    if avaliacao is None:
        return canvas

    cores = {
        0: (60, 60, 230),
        1: (40, 170, 240),
        2: (80, 190, 80),
    }
    for r in avaliacao["caracteres"]:
        x, y, w, h = r["posicao"]
        cor = cores.get(r["classe"], (200, 200, 200))
        cv2.rectangle(canvas, (x, y), (x + w, y + h), cor, 2)
    return canvas


# ─── SEGMENTACAO DE PALAVRAS (para o TrOCR palavra a palavra) ────────────────

def segment_words_in_line(line_binary):
    """Divide uma linha de texto em palavras usando os espacos em branco
    entre grupos de tinta. Devolve lista de (x1, x2) por palavra."""
    inv = cv2.bitwise_not(line_binary)
    col = np.sum(inv, axis=0)
    has_ink = col > 0

    runs = []
    start = None
    for i, v in enumerate(has_ink):
        if v and start is None:
            start = i
        elif not v and start is not None:
            runs.append((start, i))
            start = None
    if start is not None:
        runs.append((start, len(has_ink)))
    if not runs:
        return []

    # Espaco entre palavras e proporcional a altura da linha
    h = line_binary.shape[0]
    gap_thr = max(6, int(h * 0.35))

    grupos = [[runs[0]]]
    for prev, nxt in zip(runs, runs[1:]):
        gap = nxt[0] - prev[1]
        if gap > gap_thr:
            grupos.append([nxt])
        else:
            grupos[-1].append(nxt)

    boxes = []
    for grp in grupos:
        x1 = max(0, grp[0][0] - 2)
        x2 = min(line_binary.shape[1], grp[-1][1] + 2)
        if x2 - x1 >= 4:
            boxes.append((x1, x2))
    return boxes


def process_words(path):
    """Pipeline para o TrOCR palavra a palavra: detecta linhas, divide
    cada linha em palavras e devolve uma lista de linhas, onde cada
    linha e uma lista de imagens PIL (uma por palavra).

    O TrOCR e muito mais preciso em palavras isoladas do que em linhas
    inteiras (menos espaco para o decoder 'inventar' texto)."""
    image = load_image(path)
    gray = to_grayscale(image)
    binary = binarize(gray)
    corrected = correct_perspective(binary)

    bands = segment_lines(corrected)
    if not bands:
        bands = [(0, corrected.shape[0])]

    linhas = []
    for (y1, y2) in bands:
        line = corrected[y1:y2, :]
        palavras = []
        for (x1, x2) in segment_words_in_line(line):
            crop = line[:, x1:x2]
            palavras.append(Image.fromarray(crop).convert("RGB"))
        if palavras:
            linhas.append(palavras)
    return linhas


def first_word_data(path):
    """Extrai apenas a PRIMEIRA palavra da imagem (primeira linha,
    primeiro grupo de tinta), com recorte apertado nas quatro bordas.

    O recorte apertado e essencial: se o TrOCR recebe uma faixa com
    muito espaco em branco ou pedacos de outras palavras, ele 'chuta'
    texto aleatorio (tipicamente 'THANK YOU'). Isolando bem a palavra,
    ele se comporta como quando recebe uma foto so daquela palavra.

    Devolve (pil_da_palavra, characters) ou None se nada detectado.
    As coordenadas dos characters sao da imagem corrigida completa."""
    image = load_image(path)
    gray = to_grayscale(image)
    binary = binarize(gray)
    corrected = correct_perspective(binary)

    bands = segment_lines(corrected)
    if not bands:
        bands = [(0, corrected.shape[0])]
    y1, y2 = bands[0]
    line = corrected[y1:y2, :]

    wboxes = segment_words_in_line(line)
    if not wboxes:
        return None

    # Se ha mais de uma palavra na primeira linha OU mais de uma linha,
    # e uma sentenca/texto - o TrOCR offline nao lida bem com isso.
    # Sinaliza para a interface pedir o Google Vision.
    n_linhas = len(bands)
    if len(wboxes) > 1 or n_linhas > 1:
        return "SENTENCA"

    x1, x2 = wboxes[0]

    # Segmenta os caracteres da palavra primeiro (coordenadas relativas a linha)
    word_slice = line[:, x1:x2]
    chars_rel = segment_characters_in_line(word_slice, offset_y=0)
    if not chars_rel:
        return None

    # Recorte vertical apertado: usa a extensao real das letras da palavra,
    # nao a altura inteira da faixa da linha (que inclui espaco em branco)
    tops = [c[1] for c in chars_rel]
    bottoms = [c[1] + c[3] for c in chars_rel]
    top = max(0, min(tops) - 4)
    bottom = min(word_slice.shape[0], max(bottoms) + 4)

    # Recorte horizontal apertado: da primeira a ultima letra detectada
    lefts = [c[0] for c in chars_rel]
    rights = [c[0] + c[2] for c in chars_rel]
    left = max(0, min(lefts) - 4)
    right = min(word_slice.shape[1], max(rights) + 4)

    word = word_slice[top:bottom, left:right]

    # Margem branca ao redor ajuda o TrOCR (foi treinado com margens)
    word = cv2.copyMakeBorder(
        word, 12, 12, 12, 12, cv2.BORDER_CONSTANT, value=255
    )

    # Coordenadas dos characters para a imagem completa (para anotacao)
    chars = [
        (x + x1, y + y1, w, h, img)
        for (x, y, w, h, img) in chars_rel
    ]

    pil_word = Image.fromarray(word).convert("RGB")
    return pil_word, chars
