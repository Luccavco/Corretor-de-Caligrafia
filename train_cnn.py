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


# ─── 1. PREPARAR DATASET ────────────────────────────────────────────────────

def classificar_qualidade(imagem_tensor):
    arr = imagem_tensor.numpy().flatten()
    variancia = np.var(arr)

    if variancia < 0.0939:
        return 0  # ruim
    elif variancia < 0.1179:
        return 1  # aceitável
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

    contadores = {0: 0, 1: 0, 2: 0}
    imagens = []
    labels = []

    print("Classificando imagens por qualidade...")
    for img, _ in dataset:
        qualidade = classificar_qualidade(img)
        if contadores[qualidade] < max_por_classe:
            imagens.append(img)
            labels.append(qualidade)
            contadores[qualidade] += 1

        if all(v >= max_por_classe for v in contadores.values()):
            break

    print(f"Dataset montado: {contadores}")
    return imagens, labels


# ─── 2. DATASET CUSTOMIZADO ──────────────────────────────────────────────────

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

# ─── 3. TREINAR CNN ──────────────────────────────────────────────────────────

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
        print(f"Epoch {epoch+1}/10 — Loss: {loss_total/len(train_loader):.4f} — Acurácia val: {acuracia:.1f}%")

    # Salva o modelo
    torch.save(modelo.state_dict(), "modelo_caligrafia.pth")
    print("Modelo salvo em modelo_caligrafia.pth")


if __name__ == "__main__":
    treinar()