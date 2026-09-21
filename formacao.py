"""Parcela geometrica da nota: compara a letra desenhada com moldes de
letra de forma renderizados de fontes do sistema.

Quatro medidas, cada uma mapeada para 0..1 (1 = dentro do esperado):
  iou         semelhanca de forma com o melhor molde (F1 com tolerancia de TOL_PIXELS)
  proporcao   razao altura/largura vs. a do molde
  inclinacao  inclinacao media dos tracos verticais vs. a do molde
  espessura   regularidade da largura do traco (nao depende do molde)
"""

import math

import cv2
import numpy as np

import letra_prep as lp

PESOS = {"iou": 0.45, "proporcao": 0.20, "inclinacao": 0.15, "espessura": 0.20}
IOU_BOM, IOU_ZERO = 0.85, 0.45   # semelhanca >= BOM vale 1.0; <= ZERO vale 0.0
TOL_PIXELS = 2          # tolerancia de alinhamento em pixels
PROP_TOL, PROP_ZERO = 0.10, 0.50     # desvio relativo: <= TOL vale 1, >= ZERO vale 0
INCL_TOL, INCL_ZERO = 4.0, 20.0      # graus
ESP_TOL, ESP_ZERO = 0.25, 0.70       # coeficiente de variacao da espessura
ESCALAS = (0.9, 1.0, 1.1)
DESLOCS = (-4, 0, 4)

_cache_moldes = {}


def moldes_da_letra(letra):
    """Mascaras normalizadas da letra nas fontes disponiveis (cache)."""
    letra = letra.upper()
    if letra not in _cache_moldes:
        moldes = []
        for nome in lp.FONTES_MOLDE:
            caminho = lp.localizar_fonte(nome)
            if caminho:
                m = lp.normalizar_mascara(lp.mascara_de_glifo(letra, caminho))
                if m.any():
                    moldes.append(m)
        _cache_moldes[letra] = moldes
    return _cache_moldes[letra]


def _rampa(valor, bom, zero):
    """1.0 ate `bom`, cai linearmente ate 0.0 em `zero`."""
    if valor <= bom:
        return 1.0
    if valor >= zero:
        return 0.0
    return 1.0 - (valor - bom) / (zero - bom)


def _rampa_sobe(valor, zero, bom):
    """0.0 ate `zero`, sobe linearmente ate 1.0 em `bom`."""
    if valor >= bom:
        return 1.0
    if valor <= zero:
        return 0.0
    return (valor - zero) / (bom - zero)


def _variantes(mascara):
    """Pequenos ajustes de escala/deslocamento para alinhar antes do IoU."""
    h, w = mascara.shape
    for esc in ESCALAS:
        M = cv2.getRotationMatrix2D((w / 2, h / 2), 0, esc)
        base = cv2.warpAffine(mascara, M, (w, h), flags=cv2.INTER_NEAREST)
        for dx in DESLOCS:
            for dy in DESLOCS:
                yield np.roll(np.roll(base, dy, axis=0), dx, axis=1)


def _f1_tolerante(mascara, molde, tol):
    """Precisao (tinta da letra perto do molde) x cobertura (molde perto da
    tinta), com tolerancia `tol` em pixels, combinadas em F1."""
    dist_ao_molde = cv2.distanceTransform((molde == 0).astype(np.uint8), cv2.DIST_L2, 5)
    dist_a_letra = cv2.distanceTransform((mascara == 0).astype(np.uint8), cv2.DIST_L2, 5)
    tinta, alvo = mascara > 0, molde > 0
    if not tinta.any() or not alvo.any():
        return 0.0
    prec = float((dist_ao_molde[tinta] <= tol).mean())
    cob = float((dist_a_letra[alvo] <= tol).mean())
    return 2 * prec * cob / max(prec + cob, 1e-9)


def medir_iou(mascara, molde):
    """Semelhanca de forma com o molde (0..1), melhor entre pequenos
    ajustes de escala e deslocamento. Chama-se 'iou' por compatibilidade
    com o restante do codigo; e um F1 tolerante, mais criterioso que a
    intersecao/uniao de mascaras dilatadas para manchas densas."""
    melhor = 0.0
    for v in _variantes(mascara):
        melhor = max(melhor, _f1_tolerante(v, molde, TOL_PIXELS))
    return melhor


def _razao_hw(mascara):
    caixa = lp.caixa_tinta(mascara)
    if caixa is None:
        return None
    _, _, w, h = caixa
    return h / max(w, 1)


def medir_proporcao(mascara, molde):
    r_letra, r_molde = _razao_hw(mascara), _razao_hw(molde)
    if r_letra is None or r_molde is None:
        return 0.0
    return _rampa(abs(r_letra - r_molde) / r_molde, PROP_TOL, PROP_ZERO)


def _inclinacao_graus(mascara):
    """Inclinacao media dos tracos quase verticais (em graus, 0 = reto).

    Aproxima o contorno por segmentos, fica com os que estao a ate 45 graus
    da vertical e tira a media do angulo ponderada pelo comprimento. Numa
    letra simetrica (A, X) as pernas se cancelam; se a letra inteira tomba,
    a media tomba junto."""
    contornos, _ = cv2.findContours(mascara, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
    soma_ang, soma_peso = 0.0, 0.0
    for c in contornos:
        pts = cv2.approxPolyDP(c, 2.0, True).reshape(-1, 2)
        for i in range(len(pts)):
            x0, y0 = pts[i]
            x1, y1 = pts[(i + 1) % len(pts)]
            dx, dy = float(x1 - x0), float(y1 - y0)
            comp = math.hypot(dx, dy)
            if comp < 3 or dy == 0:
                continue
            ang = math.degrees(math.atan2(dx, dy))     # 0 = vertical
            if ang > 90:
                ang -= 180
            elif ang <= -90:
                ang += 180
            if abs(ang) <= 45:
                soma_ang += ang * comp
                soma_peso += comp
    return soma_ang / soma_peso if soma_peso else 0.0


def medir_inclinacao(mascara, molde):
    desvio = abs(_inclinacao_graus(mascara) - _inclinacao_graus(molde))
    return _rampa(desvio, INCL_TOL, INCL_ZERO)


def medir_espessura(mascara):
    """Coeficiente de variacao da largura do traco ao longo da crista."""
    if not mascara.any():
        return 0.0
    dist = cv2.distanceTransform(mascara, cv2.DIST_L2, 5)
    crista = (dist > 0) & (dist >= cv2.dilate(dist, np.ones((3, 3), np.uint8)) - 1e-6)
    larguras = 2 * dist[crista]
    if larguras.size < 10:
        return 0.0
    cv = float(larguras.std() / max(larguras.mean(), 1e-6))
    return _rampa(cv, ESP_TOL, ESP_ZERO)


def avaliar_formacao(mascara_norm, letra):
    moldes = moldes_da_letra(letra)
    if not moldes or not mascara_norm.any():
        esp = medir_espessura(mascara_norm)
        return {"formacao": esp, "medidas": {"iou": 0.0, "proporcao": 0.0,
                                             "inclinacao": 0.0, "espessura": esp},
                "pior": "iou"}
    ious = [medir_iou(mascara_norm, m) for m in moldes]
    melhor = int(np.argmax(ious))
    molde = moldes[melhor]
    medidas = {
        "iou": _rampa_sobe(ious[melhor], IOU_ZERO, IOU_BOM),
        "proporcao": medir_proporcao(mascara_norm, molde),
        "inclinacao": medir_inclinacao(mascara_norm, molde),
        "espessura": medir_espessura(mascara_norm),
    }
    formacao = sum(PESOS[k] * medidas[k] for k in PESOS)
    pior = min(medidas, key=lambda k: medidas[k])
    return {"formacao": float(formacao), "medidas": {k: float(v) for k, v in medidas.items()},
            "pior": pior}
