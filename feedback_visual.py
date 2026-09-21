"""Mapa de diferencas entre a letra escrita e o molde, para feedback visual
no exercicio: verde onde o traco coincide com o molde, vermelho onde saiu
dele e uma sombra azul-clara onde o molde esperava traco e nao houve.

Trabalha nas coordenadas da imagem original (a mesma que o usuario ve),
projetando o molde escolhido pelo avaliador sobre a caixa de cada letra."""

import cv2
import numpy as np

import formacao as fm
import letra_prep as lp

COR_FUNDO = (255, 255, 255)
COR_DENTRO = (125, 175, 76)      # BGR de #4caf7d (verde)
COR_FORA = (90, 90, 224)         # BGR de #e05a5a (vermelho)
COR_FALTA = (255, 224, 190)      # azul-clara: molde sem traco por cima
FRACAO_TOLERANCIA = 2.0 / lp.TAMANHO   # TOL_PIXELS a 96 px, escalado ao tamanho real


def molde_na_caixa(letra, molde_indice, w, h):
    """Molde da letra (mascara 0/255) esticado para uma caixa w x h."""
    moldes = fm.moldes_da_letra(letra)
    if not moldes or molde_indice is None:
        return None
    molde = moldes[molde_indice]
    cx = lp.caixa_tinta(molde)
    if cx is None:
        return None
    mx, my, mw, mh = cx
    return cv2.resize(molde[my:my + mh, mx:mx + mw], (w, h), interpolation=cv2.INTER_NEAREST)


def mapa_diferencas_letra(crop, letra, molde_indice):
    """Devolve (imagem BGR do tamanho do recorte, fracao do traco fora do
    molde). Se nao houver molde, pinta o traco todo de verde."""
    mascara = lp.mascara_de_recorte(crop)
    h, w = mascara.shape
    saida = np.full((h, w, 3), COR_FUNDO, np.uint8)
    caixa = lp.caixa_tinta(mascara)
    if caixa is None:
        return saida, 0.0
    x, y, cw, ch = caixa
    molde = molde_na_caixa(letra, molde_indice, cw, ch)
    if molde is None:
        saida[mascara > 0] = COR_DENTRO
        return saida, 0.0

    molde_cheio = np.zeros_like(mascara)
    molde_cheio[y:y + ch, x:x + cw] = molde
    tol = max(2.0, FRACAO_TOLERANCIA * max(cw, ch))
    dist_ao_molde = cv2.distanceTransform((molde_cheio == 0).astype(np.uint8), cv2.DIST_L2, 5)
    dist_a_letra = cv2.distanceTransform((mascara == 0).astype(np.uint8), cv2.DIST_L2, 5)

    tinta = mascara > 0
    dentro = tinta & (dist_ao_molde <= tol)
    fora = tinta & ~dentro
    falta = (molde_cheio > 0) & (dist_a_letra > tol)

    saida[falta] = COR_FALTA
    saida[dentro] = COR_DENTRO
    saida[fora] = COR_FORA
    fracao_fora = float(fora.sum() / max(tinta.sum(), 1))
    return saida, fracao_fora


def mapa_diferencas(characters, avaliacao, tamanho, recortar=True):
    """Compoe o mapa de todas as letras numa imagem BGR `tamanho` = (h, w).
    Com `recortar`, devolve so a regiao das letras (com margem), para a
    letra aparecer grande na tela em vez de perdida no quadro inteiro."""
    h, w = tamanho
    canvas = np.full((h, w, 3), COR_FUNDO, np.uint8)
    if not avaliacao:
        return canvas
    for (x, y, cw, ch, crop), r in zip(characters, avaliacao["caracteres"]):
        mapa, _ = mapa_diferencas_letra(crop, r["letra_alvo"], r.get("molde_indice"))
        alvo = canvas[y:y + ch, x:x + cw]
        mh, mw = min(alvo.shape[0], mapa.shape[0]), min(alvo.shape[1], mapa.shape[1])
        # so pinta onde o mapa tem algo (mantem o fundo branco entre letras)
        recorte = mapa[:mh, :mw]
        marcado = np.any(recorte != COR_FUNDO, axis=2)
        alvo[:mh, :mw][marcado] = recorte[marcado]
    if recortar and characters:
        x0 = min(c[0] for c in characters)
        y0 = min(c[1] for c in characters)
        x1 = max(c[0] + c[2] for c in characters)
        y1 = max(c[1] + c[3] for c in characters)
        margem = int(0.15 * max(x1 - x0, y1 - y0)) + 8
        canvas = canvas[max(0, y0 - margem):min(h, y1 + margem),
                        max(0, x0 - margem):min(w, x1 + margem)]
    return canvas
