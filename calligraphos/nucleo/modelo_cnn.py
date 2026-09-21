"""Arquitetura da CNN de legibilidade (MobileNetV2 com 26 saidas) e a
lista de classes. Compartilhada pelo treino e pela inferencia."""

import torch.nn as nn
from torchvision import models

CLASSES = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def construir_modelo(pretreinado=True):
    pesos = models.MobileNet_V2_Weights.DEFAULT if pretreinado else None
    modelo = models.mobilenet_v2(weights=pesos)
    modelo.classifier[1] = nn.Linear(modelo.last_channel, len(CLASSES))
    return modelo
