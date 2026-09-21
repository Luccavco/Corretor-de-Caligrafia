"""Normalizacao de letras compartilhada entre treino e inferencia.

Toda letra (recorte do pipeline, imagem do EMNIST ou glifo de fonte) vira
uma MASCARA uint8 com tinta = 255 e fundo = 0, e depois e enquadrada num
quadrado de TAMANHO x TAMANHO com margem. Treino e inferencia passam pelo
mesmo caminho, entao a CNN ve exatamente o mesmo tipo de imagem nos dois."""

import glob
import os
import subprocess

import cv2
import numpy as np
import torch
from PIL import Image, ImageDraw, ImageFont

TAMANHO = 96
MARGEM = 0.10

FONTES_MOLDE = ["DejaVu Sans", "Liberation Sans", "Noto Sans", "Noto Serif"]
_ARQUIVOS_FONTE = {
    "DejaVu Sans": "DejaVuSans.ttf",
    "DejaVu Sans Mono": "DejaVuSansMono.ttf",
    "Liberation Sans": "LiberationSans-Regular.ttf",
    "Noto Sans": "NotoSans-Regular.ttf",
    "Noto Serif": "NotoSerif-Regular.ttf",
}

_MEDIA = torch.tensor([0.485, 0.456, 0.406]).view(3, 1, 1)
_DESVIO = torch.tensor([0.229, 0.224, 0.225]).view(3, 1, 1)


def mascara_de_recorte(crop):
    """Recorte do image_pipeline (fundo claro, tinta escura) -> mascara."""
    if crop.ndim == 3:
        crop = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    mascara = np.where(crop < 128, 255, 0).astype(np.uint8)
    return remover_fragmentos_de_borda(mascara)


def remover_fragmentos_de_borda(mascara, fracao=0.25):
    """Apaga componentes pequenos (< `fracao` da area do maior) que encostam
    na borda do recorte: sao quase sempre pedacos de letras vizinhas que a
    segmentacao deixou entrar na caixa (ex.: um traco do O ao lado do F).
    Partes legitimas da letra ou sao grandes ou nao tocam a borda."""
    n, rotulos, stats, _ = cv2.connectedComponentsWithStats(mascara, connectivity=8)
    if n <= 2:
        return mascara
    h, w = mascara.shape
    areas = stats[1:, cv2.CC_STAT_AREA]
    maior = areas.max()
    saida = mascara.copy()
    for i in range(1, n):
        x, y, cw, ch, area = stats[i]
        toca_borda = x == 0 or y == 0 or x + cw == w or y + ch == h
        if area < fracao * maior and toca_borda:
            saida[rotulos == i] = 0
    return saida


def mascara_de_emnist(img_pil):
    """Imagem PIL do torchvision EMNIST (28x28, guardada transposta)."""
    arr = np.array(img_pil, dtype=np.uint8).T
    return np.where(arr > 127, 255, 0).astype(np.uint8)


def mascara_de_glifo(letra, caminho_fonte, tamanho_fonte=160):
    """Renderiza a letra numa fonte e devolve a mascara (tinta = 255)."""
    fonte = ImageFont.truetype(caminho_fonte, tamanho_fonte)
    img = Image.new("L", (tamanho_fonte * 2, tamanho_fonte * 2), 0)
    ImageDraw.Draw(img).text((tamanho_fonte // 2, tamanho_fonte // 4), letra,
                             fill=255, font=fonte)
    return np.where(np.array(img) > 127, 255, 0).astype(np.uint8)


def caixa_tinta(mascara):
    ys, xs = np.where(mascara > 0)
    if len(xs) == 0:
        return None
    return int(xs.min()), int(ys.min()), int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1)


def normalizar_mascara(mascara):
    """Recorta na caixa da tinta, enquadra num quadrado com margem e
    redimensiona para TAMANHO x TAMANHO. Mascara vazia -> zeros."""
    caixa = caixa_tinta(mascara)
    if caixa is None:
        return np.zeros((TAMANHO, TAMANHO), np.uint8)
    x, y, w, h = caixa
    recorte = mascara[y:y + h, x:x + w]
    lado = max(w, h)
    quadro = np.zeros((lado, lado), np.uint8)
    oy, ox = (lado - h) // 2, (lado - w) // 2
    quadro[oy:oy + h, ox:ox + w] = recorte
    util = int(round(TAMANHO * (1 - 2 * MARGEM)))
    interp = cv2.INTER_AREA if lado > util else cv2.INTER_LINEAR
    miolo = cv2.resize(quadro, (util, util), interpolation=interp)
    saida = np.zeros((TAMANHO, TAMANHO), np.uint8)
    off = (TAMANHO - util) // 2
    saida[off:off + util, off:off + util] = miolo
    return np.where(saida > 127, 255, 0).astype(np.uint8)


def tensor_de_mascara(mascara_norm):
    t = torch.from_numpy(mascara_norm.astype(np.float32) / 255.0)
    t = t.unsqueeze(0).repeat(3, 1, 1)
    return (t - _MEDIA) / _DESVIO


def localizar_fonte(nome):
    """Caminho do .ttf de uma fonte: fc-match primeiro, glob como reserva."""
    arquivo = _ARQUIVOS_FONTE.get(nome)
    try:
        saida = subprocess.run(["fc-match", "-f", "%{file}", nome],
                               capture_output=True, text=True, timeout=5).stdout.strip()
        # fc-match sempre devolve alguma fonte; so aceita se for a pedida
        if saida and (arquivo is None or os.path.basename(saida) == arquivo):
            return saida
    except (OSError, subprocess.SubprocessError):
        pass
    if arquivo:
        achados = glob.glob(f"/usr/share/fonts/**/{arquivo}", recursive=True)
        if achados:
            return achados[0]
    return None
