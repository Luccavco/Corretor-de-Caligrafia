import torch
import torchvision.transforms as transforms
from torchvision import models
import torch.nn as nn
from PIL import Image
import numpy as np

modelo_cnn = None
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

CATEGORIAS = {
    0: "Ruim",
    1: "Aceitavel",
    2: "Boa",
}

_transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
])


def load_modelo():
    """Carrega a CNN treinada (modelo_caligrafia.pth) uma unica vez."""
    global modelo_cnn
    print("Carregando modelo de avaliacao...")
    modelo_cnn = models.mobilenet_v2(weights=None)
    modelo_cnn.classifier[1] = nn.Linear(modelo_cnn.last_channel, 3)
    modelo_cnn.load_state_dict(
        torch.load("modelo_caligrafia.pth", map_location=device)
    )
    modelo_cnn.to(device)
    modelo_cnn.eval()
    print("Modelo de avaliacao carregado!")


def _preparar_tensor(char_img_array):
    img = Image.fromarray(char_img_array).convert("RGB")
    return _transform(img)


def avaliar_texto(characters, batch_size=32):
    """Avalia todas as letras de uma vez, em lotes (mais rapido que
    uma chamada por letra, principalmente em textos longos).

    Recebe a lista de caracteres do image_pipeline e devolve um
    dicionario com o resultado por letra e a pontuacao geral."""
    if not characters:
        return None
    if modelo_cnn is None:
        load_modelo()

    tensores = torch.stack([_preparar_tensor(c[4]) for c in characters])

    classes = []
    confiancas = []
    with torch.no_grad():
        for i in range(0, len(tensores), batch_size):
            lote = tensores[i:i + batch_size].to(device)
            saida = modelo_cnn(lote)
            probs = torch.softmax(saida, dim=1)
            conf, cls = torch.max(probs, dim=1)
            classes.extend(cls.cpu().tolist())
            confiancas.extend(conf.cpu().tolist())

    resultados = []
    for i, (x, y, w, h, _) in enumerate(characters):
        resultados.append({
            "indice": i + 1,
            "posicao": (x, y, w, h),
            "classe": classes[i],
            "categoria": CATEGORIAS[classes[i]],
            "confianca": round(confiancas[i], 3),
        })

    pontuacao = np.mean([r["classe"] for r in resultados]) / 2 * 100

    return {
        "caracteres": resultados,
        "pontuacao_geral": round(pontuacao, 1),
        "total": len(resultados),
        "boas": sum(1 for r in resultados if r["classe"] == 2),
        "aceitaveis": sum(1 for r in resultados if r["classe"] == 1),
        "ruins": sum(1 for r in resultados if r["classe"] == 0),
    }


def formatar_feedback(avaliacao):
    """Feedback em texto simples para terminal e testes."""
    if avaliacao is None:
        return "Nenhum caractere detectado."

    linhas = []
    linhas.append(f"Pontuacao geral: {avaliacao['pontuacao_geral']}/100")
    linhas.append(f"Caracteres analisados: {avaliacao['total']}")
    linhas.append("-" * 32)
    linhas.append(f"Boa formacao:     {avaliacao['boas']} letra(s)")
    linhas.append(f"Aceitavel:        {avaliacao['aceitaveis']} letra(s)")
    linhas.append(f"Precisa melhorar: {avaliacao['ruins']} letra(s)")

    ruins = [r for r in avaliacao["caracteres"] if r["classe"] == 0]
    if ruins:
        linhas.append("-" * 32)
        linhas.append("Letras que precisam de atencao:")
        for r in ruins:
            linhas.append(f"  Letra {r['indice']} (confianca {r['confianca']:.0%})")

    return "\n".join(linhas)


def gerar_relatorio(texto, avaliacao):
    """Relatorio completo em texto, pronto para salvar em arquivo."""
    linhas = []
    linhas.append("=" * 48)
    linhas.append("RELATORIO DE ANALISE DE CALIGRAFIA")
    linhas.append("=" * 48)
    linhas.append("")
    linhas.append("TEXTO RECONHECIDO:")
    linhas.append(texto if texto else "(nenhum texto reconhecido)")
    linhas.append("")
    linhas.append(formatar_feedback(avaliacao))
    linhas.append("")
    if avaliacao:
        linhas.append("DETALHE POR LETRA:")
        for r in avaliacao["caracteres"]:
            linhas.append(
                f"  Letra {r['indice']:>3}  {r['categoria']:<10}"
                f" confianca {r['confianca']:.0%}"
            )
    return "\n".join(linhas)
