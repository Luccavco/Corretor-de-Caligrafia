import torch
import torchvision.transforms as transforms
from torchvision import models
import torch.nn as nn
from PIL import Image
import numpy as np

modelo_cnn = None
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

CATEGORIAS = {
    0: ("Ruim", "[!]"),
    1: ("Aceitavel", "[~]"),
    2: ("Boa", "[+]")
}


def load_modelo():
    global modelo_cnn
    print("Carregando modelo de avaliação...")
    modelo_cnn = models.mobilenet_v2(weights=None)
    modelo_cnn.classifier[1] = nn.Linear(modelo_cnn.last_channel, 3)
    modelo_cnn.load_state_dict(torch.load("modelo_caligrafia.pth", map_location=device))
    modelo_cnn.to(device)
    modelo_cnn.eval()
    print("Modelo de avaliação carregado!")


def avaliar_caractere(char_img_array):
    if modelo_cnn is None:
        load_modelo()

    img = Image.fromarray(char_img_array).convert("RGB")
    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
    ])
    tensor = transform(img).unsqueeze(0).to(device)

    with torch.no_grad():
        saida = modelo_cnn(tensor)
        probabilidades = torch.softmax(saida, dim=1)[0]
        classe = torch.argmax(probabilidades).item()
        confianca = probabilidades[classe].item()

    return classe, confianca


def avaliar_texto(characters):
    if not characters:
        return None

    resultados = []
    for i, (x, y, w, h, char_img) in enumerate(characters):
        classe, confianca = avaliar_caractere(char_img)
        nome, emoji = CATEGORIAS[classe]
        resultados.append({
            "indice": i + 1,
            "posicao": (x, y, w, h),
            "classe": classe,
            "categoria": nome,
            "emoji": emoji,
            "confianca": confianca
        })

    pontuacao_media = np.mean([r["classe"] for r in resultados]) / 2 * 100

    return {
        "caracteres": resultados,
        "pontuacao_geral": round(pontuacao_media, 1),
        "total": len(resultados)
    }


def formatar_feedback(avaliacao):
    if avaliacao is None:
        return "Nenhum caractere detectado."

    linhas = []
    linhas.append(f"Pontuacao geral: {avaliacao['pontuacao_geral']}/100")
    linhas.append(f"Caracteres analisados: {avaliacao['total']}")
    linhas.append("-" * 30)

    ruins = [r for r in avaliacao["caracteres"] if r["classe"] == 0]
    aceitaveis = [r for r in avaliacao["caracteres"] if r["classe"] == 1]
    boas = [r for r in avaliacao["caracteres"] if r["classe"] == 2]

    linhas.append(f"Boa formacao: {len(boas)} letra(s)")
    linhas.append(f"Aceitavel: {len(aceitaveis)} letra(s)")
    linhas.append(f"Precisa melhorar: {len(ruins)} letra(s)")

    if ruins:
        linhas.append("-" * 30)
        linhas.append("Letras que precisam de atencao:")
        for r in ruins:
            linhas.append(f"  Letra {r['indice']} - {r['categoria']}")

    return "\n".join(linhas)