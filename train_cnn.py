"""Treina a CNN de LEGIBILIDADE: MobileNetV2 (transfer learning) que
reconhece qual das 26 letras esta na imagem, usando o EMNIST-letters com
rotulos reais.

A qualidade da caligrafia NAO e rotulada aqui (o EMNIST nao tem isso). O
que a rede entrega ao avaliador e a probabilidade calibrada de a imagem ser
a letra-alvo; a parte de "formacao" fica em formacao.py, sem treino.

Augmentation fecha a diferenca entre o EMNIST (traco fino, 28x28) e as
letras reais (foto/quadro, traco grosso): dilatacao/erosao, rotacao,
escala, cisalhamento e translacao aleatorios.

Ao final ajusta uma temperatura no conjunto de validacao (calibracao) e
salva tudo em modelo_caligrafia.pth. Uso: venv/bin/python train_cnn.py
"""

import os
import random

import cv2
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset
from torchvision import datasets, models

import letra_prep as lp

_AQUI = os.path.dirname(os.path.abspath(__file__))
PASTA_DADOS = os.path.join(_AQUI, "data")
MODELO_PATH = os.path.join(_AQUI, "modelo_caligrafia.pth")
CLASSES = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
EPOCAS = 6
BATCH = 128


def augmentar(mascara, rng):
    """Deforma a mascara 28x28 do EMNIST para parecer uma letra real."""
    m = mascara
    # espessura: dilata (traco grosso, como caneta/quadro) ou afina
    k = int(rng.choice([0, 1, 1, 2, 3]))
    if k:
        kernel = np.ones((k + 1, k + 1), np.uint8)
        m = cv2.dilate(m, kernel) if rng.random() < 0.8 else cv2.erode(m, kernel)
    # afim: rotacao, escala, cisalhamento, translacao
    h, w = m.shape
    ang = rng.uniform(-12, 12)
    esc = rng.uniform(0.85, 1.15)
    cis = np.tan(np.radians(rng.uniform(-8, 8)))
    M = cv2.getRotationMatrix2D((w / 2, h / 2), ang, esc)
    M[0, 1] += cis
    M[0, 2] += rng.uniform(-2, 2)
    M[1, 2] += rng.uniform(-2, 2)
    m = cv2.warpAffine(m, M, (w, h), flags=cv2.INTER_NEAREST, borderValue=0)
    # largura: letra condensada (estreita) ou estendida, estilo comum em
    # escrita real e raro no EMNIST. A normalizacao posterior recentra.
    fator_x = rng.uniform(0.55, 1.25)
    nova_w = max(4, int(round(w * fator_x)))
    m = cv2.resize(m, (nova_w, h), interpolation=cv2.INTER_NEAREST)
    return m


class DatasetLetras(Dataset):
    """EMNIST-letters -> mascara normalizada (96x96) + rotulo 0..25."""

    def __init__(self, treino, limite=None, semente=0):
        self.base = datasets.EMNIST(PASTA_DADOS, split="letters", train=treino, download=True)
        self.treino = treino
        self.indices = list(range(len(self.base)))
        if limite:
            random.Random(semente).shuffle(self.indices)
            self.indices = self.indices[:limite]
        self.semente = semente
        self.rng = None

    def __len__(self):
        return len(self.indices)

    def __getitem__(self, i):
        if self.rng is None:
            # um gerador por worker do DataLoader, para nao repetir augmentations
            self.rng = np.random.default_rng(self.semente + os.getpid())
        img, rotulo = self.base[self.indices[i]]
        m = lp.mascara_de_emnist(img)
        if self.treino:
            m = augmentar(m, self.rng)
        return lp.tensor_de_mascara(lp.normalizar_mascara(m)), int(rotulo) - 1


def construir_modelo(pretreinado=True):
    pesos = models.MobileNet_V2_Weights.DEFAULT if pretreinado else None
    modelo = models.mobilenet_v2(weights=pesos)
    modelo.classifier[1] = nn.Linear(modelo.last_channel, len(CLASSES))
    return modelo


def _avaliar(modelo, loader, device):
    modelo.eval()
    logits_todos, rotulos_todos = [], []
    with torch.no_grad():
        for x, y in loader:
            logits_todos.append(modelo(x.to(device)).cpu())
            rotulos_todos.append(y)
    logits = torch.cat(logits_todos)
    rotulos = torch.cat(rotulos_todos)
    acuracia = (logits.argmax(1) == rotulos).float().mean().item() * 100
    return logits, rotulos, acuracia


def calibrar_temperatura(logits, rotulos):
    """Escala os logits por 1/T minimizando a NLL (Guo et al., 2017)."""
    log_t = torch.zeros(1, requires_grad=True)
    otim = optim.LBFGS([log_t], lr=0.1, max_iter=100)
    criterio = nn.CrossEntropyLoss()

    def passo():
        otim.zero_grad()
        perda = criterio(logits / log_t.exp(), rotulos)
        perda.backward()
        return perda

    otim.step(passo)
    return float(log_t.exp().item())


def treinar():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Usando: {device}")
    ds_treino = DatasetLetras(treino=True)
    ds_val = DatasetLetras(treino=False)
    ld_treino = DataLoader(ds_treino, batch_size=BATCH, shuffle=True, num_workers=4, pin_memory=True)
    ld_val = DataLoader(ds_val, batch_size=256, num_workers=4)
    print(f"Treino: {len(ds_treino)} imagens | Validação: {len(ds_val)}")

    modelo = construir_modelo().to(device)
    criterio = nn.CrossEntropyLoss(label_smoothing=0.05)
    otim = optim.Adam([
        {"params": modelo.features.parameters(), "lr": 1e-4},
        {"params": modelo.classifier.parameters(), "lr": 1e-3},
    ])
    agenda = optim.lr_scheduler.CosineAnnealingLR(otim, T_max=EPOCAS)

    for epoca in range(EPOCAS):
        modelo.train()
        perda_total = 0.0
        for x, y in ld_treino:
            x, y = x.to(device, non_blocking=True), y.to(device, non_blocking=True)
            otim.zero_grad()
            perda = criterio(modelo(x), y)
            perda.backward()
            otim.step()
            perda_total += perda.item()
        agenda.step()
        _, _, acc = _avaliar(modelo, ld_val, device)
        print(f"Época {epoca + 1}/{EPOCAS} — perda {perda_total / len(ld_treino):.4f} — acurácia val {acc:.2f}%", flush=True)

    logits, rotulos, acc = _avaliar(modelo, ld_val, device)
    temperatura = calibrar_temperatura(logits, rotulos)
    print(f"Acurácia final (EMNIST letters, validação): {acc:.2f}%")
    print(f"Temperatura de calibração: {temperatura:.3f}")
    torch.save({
        "state_dict": modelo.state_dict(),
        "temperatura": temperatura,
        "classes": CLASSES,
        "tamanho": lp.TAMANHO,
        "acuracia_val": acc,
    }, MODELO_PATH)
    print(f"Modelo salvo em {MODELO_PATH}")


if __name__ == "__main__":
    treinar()
