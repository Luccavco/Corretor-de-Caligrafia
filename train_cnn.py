"""Treino da CNN de avaliacao de caligrafia (MobileNetV2 + transfer
learning), usando o EMNIST como base.

CALIBRACAO DE LIMIARES (importante):
Os limiares que decidem se uma imagem e "ruim", "aceitavel" ou "boa" nao
sao mais numeros fixos chutados - sao calculados dinamicamente a partir
dos PERCENTIS reais da variancia de pixel na amostra do EMNIST usada no
treino (funcao calcular_limiares). Isso evita o problema de calibrar as
constantes "no olho" e depois descobrir que elas nao refletem a
distribuicao real dos dados.

Os percentis padrao (P_BAIXO=60, P_ALTO=85) foram propositalmente
elevados em relacao a calibracao anterior, para exigir mais para uma
letra ser classificada como "boa" - antes, quase qualquer escrita real
(que tende a ter variancia de pixel mais alta que os caracteres finos e
normalizados do EMNIST) caia no balde "boa". Rode
diagnostico_variancia.py antes de treinar para ver a distribuicao real
e ajustar esses percentis se quiser um padrao ainda mais (ou menos)
exigente.

LIMITACAO HONESTA: esta calibracao usa SOMENTE o EMNIST como referencia.
Letras reais desenhadas a mao (mouse, caneta) podem ter uma distribuicao
de variancia diferente da dos caracteres do EMNIST, entao mesmo com um
padrao mais alto, pode ser que a exigencia ainda nao fique perfeita para
escrita real. Se depois de retreinar o resultado ainda nao parecer justo,
o proximo passo seria calibrar com exemplos reais (fotos de letras boas/
regulares/ruins) em vez de so o EMNIST.
"""

import cv2
import torch
import torchvision.datasets as datasets
import torchvision.transforms as transforms
from torchvision import models
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset
import numpy as np
import os
from PIL import Image


# ─── 1. CALIBRACAO DOS LIMIARES DE QUALIDADE ────────────────────────────────

# Percentis usados para definir os limiares (mais altos = padrao mais
# exigente para uma letra ser considerada "boa"). Ajuste aqui se quiser
# recalibrar - rode diagnostico_variancia.py antes para ver o efeito.
P_BAIXO = 60   # abaixo deste percentil de variancia -> "ruim"
P_ALTO = 85    # acima deste percentil de variancia -> "boa"


def _variancia_processada(img_tensor):
    """Reproduz o mesmo pre-processamento usado no dataset de treino
    (binarizacao Otsu + normalizacao), para a variancia calculada aqui
    ser diretamente comparavel a que o modelo vai ver."""
    arr = (img_tensor.numpy()[0] * 255).astype(np.uint8)
    _, arr_bin = cv2.threshold(arr, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    normalizado = arr_bin.astype(np.float32) / 255.0
    return float(np.var(normalizado))


def calcular_limiares(dataset, amostra=6000):
    """Calcula os limiares de variancia dinamicamente a partir dos
    percentis P_BAIXO/P_ALTO de uma amostra real do dataset, em vez de
    usar constantes fixas chutadas a mao."""
    print(f"Calibrando limiares de qualidade (amostra de {amostra})...")
    variancias = []
    for i, (img, _label) in enumerate(dataset):
        if i >= amostra:
            break
        variancias.append(_variancia_processada(img))
    variancias = np.array(variancias)
    limiar_baixo = float(np.percentile(variancias, P_BAIXO))
    limiar_alto = float(np.percentile(variancias, P_ALTO))
    print(
        f"Limiares calibrados: ruim < {limiar_baixo:.4f} <= aceitavel "
        f"< {limiar_alto:.4f} <= boa"
    )
    return limiar_baixo, limiar_alto


# ─── 2. PREPARAR DATASET ────────────────────────────────────────────────────

def classificar_qualidade(imagem_tensor, limiar_baixo, limiar_alto):
    variancia = _variancia_processada(imagem_tensor)
    if variancia < limiar_baixo:
        return 0  # ruim
    elif variancia < limiar_alto:
        return 1  # aceitavel
    else:
        return 2  # boa


def preparar_dataset(max_por_classe=3000):
    print("Carregando EMNIST...")
    transform = transforms.Compose([
        transforms.ToTensor(),
    ])
    dataset = datasets.EMNIST(
        root='./data',
        split='letters',
        train=True,
        download=False,
        transform=transform
    )

    # Calibra os limiares a partir da distribuicao real ANTES de rotular,
    # em vez de usar numeros fixos que podem nao refletir os dados atuais.
    limiar_baixo, limiar_alto = calcular_limiares(dataset)

    contadores = {0: 0, 1: 0, 2: 0}
    imagens = []
    labels = []

    print("Classificando imagens por qualidade...")
    for img, _ in dataset:
        qualidade = classificar_qualidade(img, limiar_baixo, limiar_alto)
        if contadores[qualidade] < max_por_classe:
            imagens.append(img)
            labels.append(qualidade)
            contadores[qualidade] += 1

        if all(v >= max_por_classe for v in contadores.values()):
            break

    print(f"Dataset montado: {contadores}")
    return imagens, labels


# ─── 3. DATASET CUSTOMIZADO ──────────────────────────────────────────────────

class CaligrafiDataset(Dataset):
    def __init__(self, imagens, labels, transform=None):
        self.imagens = imagens
        self.labels = labels
        self.transform = transform

    def __len__(self):
        return len(self.imagens)

    def __getitem__(self, idx):
        img = self.imagens[idx]
        arr = (img.numpy()[0] * 255).astype(np.uint8)
        _, arr_bin = cv2.threshold(arr, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        img = torch.from_numpy(arr_bin).float() / 255.0
        img = img.unsqueeze(0).repeat(3, 1, 1)
        img = transforms.functional.resize(img, (224, 224))
        return img, self.labels[idx]

# ─── 4. TREINAR CNN ──────────────────────────────────────────────────────────

def treinar():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Usando: {device}")

    imagens, labels = preparar_dataset(max_por_classe=2000)

    # Split treino/validação 80/20
    split = int(len(imagens) * 0.8)
    train_dataset = CaligrafiDataset(imagens[:split], labels[:split])
    val_dataset = CaligrafiDataset(imagens[split:], labels[split:])

    train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=32)

    # MobileNet com Transfer Learning
    print("Carregando MobileNet...")
    modelo = models.mobilenet_v2(weights=models.MobileNet_V2_Weights.DEFAULT)

    # Descongela só as últimas 3 camadas convolucionais
    for param in modelo.parameters():
        param.requires_grad = False
    for param in modelo.features[-3:].parameters():
        param.requires_grad = True

    # Substitui a última camada para 3 classes
    modelo.classifier[1] = nn.Linear(modelo.last_channel, 3)
    modelo = modelo.to(device)

    criterio = nn.CrossEntropyLoss()
    otimizador = optim.Adam([
        {"params": modelo.features[-3:].parameters(), "lr": 0.0001},
        {"params": modelo.classifier.parameters(), "lr": 0.001}
    ])

    print("Iniciando treino...")
    for epoch in range(20):
        modelo.train()
        loss_total = 0
        for imgs, lbls in train_loader:
            imgs, lbls = imgs.to(device), lbls.to(device)
            otimizador.zero_grad()
            saida = modelo(imgs)
            loss = criterio(saida, lbls)
            loss.backward()
            otimizador.step()
            loss_total += loss.item()

        # Validação
        modelo.eval()
        corretos = 0
        total = 0
        with torch.no_grad():
            for imgs, lbls in val_loader:
                imgs, lbls = imgs.to(device), lbls.to(device)
                saida = modelo(imgs)
                _, pred = torch.max(saida, 1)
                corretos += (pred == lbls).sum().item()
                total += lbls.size(0)

        acuracia = 100 * corretos / total
        print(f"Epoch {epoch+1}/20 — Loss: {loss_total/len(train_loader):.4f} — Acurácia val: {acuracia:.1f}%")

    # Salva o modelo
    torch.save(modelo.state_dict(), "modelo_caligrafia.pth")
    print("Modelo salvo em modelo_caligrafia.pth")


if __name__ == "__main__":
    treinar()
