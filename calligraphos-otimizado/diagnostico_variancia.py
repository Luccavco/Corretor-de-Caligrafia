"""Diagnostico de calibracao: mostra a distribuicao real de variancia de
pixel no EMNIST (processado exatamente como no treino), para decidir
limiares de qualidade mais exigentes antes de retreinar o modelo.

Isso NAO altera o modelo - so mostra os numeros. Depois de rodar,
decida os percentis (p_baixo/p_alto) e ajuste train_cnn.py se quiser
valores diferentes dos usados por padrao (60 e 85).

Uso:
    python diagnostico_variancia.py
"""

import cv2
import numpy as np
import torchvision.datasets as datasets
import torchvision.transforms as transforms


def variancia_processada(img_tensor):
    """Reproduz EXATAMENTE o pre-processamento de CaligrafiDataset:
    binariza com Otsu e normaliza para 0-1, depois calcula a variancia."""
    arr = (img_tensor.numpy()[0] * 255).astype(np.uint8)
    _, arr_bin = cv2.threshold(arr, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    normalizado = arr_bin.astype(np.float32) / 255.0
    return float(np.var(normalizado))


def main():
    print("Carregando EMNIST (usa o cache local em ./data)...")
    transform = transforms.Compose([transforms.ToTensor()])
    dataset = datasets.EMNIST(
        root="./data", split="letters", train=True,
        download=False, transform=transform,
    )

    amostra = 8000
    print(f"Calculando variancia de {amostra} imagens...")
    variancias = []
    for i, (img, _label) in enumerate(dataset):
        if i >= amostra:
            break
        variancias.append(variancia_processada(img))
    variancias = np.array(variancias)

    print(f"\nTotal analisado: {len(variancias)} imagens")
    print("\n=== PERCENTIS DE VARIANCIA ===")
    for p in (10, 20, 30, 40, 50, 60, 70, 75, 80, 85, 90, 95):
        valor = np.percentile(variancias, p)
        print(f"  p{p:>2}: {valor:.4f}")

    print("\n=== SIMULACAO COM OS NOVOS LIMIARES PADRAO (p60 / p85) ===")
    p_baixo, p_alto = 60, 85
    lim_baixo = np.percentile(variancias, p_baixo)
    lim_alto = np.percentile(variancias, p_alto)
    ruim = np.sum(variancias < lim_baixo)
    aceitavel = np.sum((variancias >= lim_baixo) & (variancias < lim_alto))
    boa = np.sum(variancias >= lim_alto)
    total = len(variancias)
    print(f"  Limiar ruim/aceitavel (p{p_baixo}): {lim_baixo:.4f}")
    print(f"  Limiar aceitavel/boa  (p{p_alto}): {lim_alto:.4f}")
    print(f"  Ruim:      {ruim:>5} ({100*ruim/total:.1f}%)")
    print(f"  Aceitavel: {aceitavel:>5} ({100*aceitavel/total:.1f}%)")
    print(f"  Boa:       {boa:>5} ({100*boa/total:.1f}%)")
    print(
        "\nCom esses limiares, so o TOPO da distribuicao de variancia do "
        "EMNIST conta como 'boa' - um padrao bem mais exigente que antes."
    )
    print(
        "\nSe quiser ajustar, edite p_baixo/p_alto em train_cnn.py "
        "(funcao calcular_limiares) e rode o diagnostico de novo para "
        "conferir a nova distribuicao antes de treinar de verdade."
    )


if __name__ == "__main__":
    main()
