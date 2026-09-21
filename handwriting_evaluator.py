"""Avaliador hibrido de caligrafia.

Para cada letra recortada:
  legibilidade  = P(letra-alvo) da CNN (calibrada por temperatura),
                  penalizada pela probabilidade da segunda opcao
  formacao      = medidas geometricas contra moldes (formacao.py)
  nota          = 100 * sqrt(legibilidade) * formacao ** EXPOENTE_FORMACAO

A legibilidade age como porta (uma letra irreconhecivel nunca pontua bem)
e a formacao manda na nota: o criterio adotado e "parecer o molde de letra
de forma", nao apenas ser legivel. Calibrado com letras sinteticas, fotos
reais de letra de forma e desenhos propositalmente ruins do quadro.
Categorias: Boa >= 75, Aceitavel >= 50, Ruim < 50.
"""

import os

import numpy as np
import torch

import letra_prep as lp
from formacao import avaliar_formacao
from train_cnn import construir_modelo, CLASSES

_AQUI = os.path.dirname(os.path.abspath(__file__))
MODELO_PATH = os.path.join(_AQUI, "modelo_caligrafia.pth")

EXPOENTE_LEGIBILIDADE = 0.5    # raiz quadrada: porta suave
EXPOENTE_FORMACAO = 1.25       # > 1 acentua diferencas de formacao
NOTA_BOA = 75
NOTA_ACEITAVEL = 50
PENALIDADE_SEGUNDA = 0.5

CATEGORIAS = {0: "Ruim", 1: "Aceitável", 2: "Boa"}
_EXPLICACOES = {
    "iou": "pouco parecida com o molde",
    "tracos": "com curvas ou ângulos onde o molde tem traços retos",
    "proporcao": "com proporção fora do molde (muito larga ou estreita)",
    "inclinacao": "muito inclinada",
    "espessura": "com traço irregular",
}

modelo_cnn = None
temperatura = 1.0
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


def load_modelo():
    """Carrega a CNN de legibilidade e a temperatura de calibração."""
    global modelo_cnn, temperatura
    print("Carregando modelo de avaliação...")
    salvo = torch.load(MODELO_PATH, map_location=device)
    if not (isinstance(salvo, dict) and "state_dict" in salvo):
        raise RuntimeError(
            "modelo_caligrafia.pth está no formato antigo (3 classes). "
            "Rode 'python train_cnn.py' para treinar o avaliador novo."
        )
    modelo_cnn = construir_modelo(pretreinado=False)
    modelo_cnn.load_state_dict(salvo["state_dict"])
    modelo_cnn.to(device).eval()
    temperatura = float(salvo.get("temperatura", 1.0))
    print("Modelo de avaliação carregado!")


def _classe_para_nota(nota):
    if nota >= NOTA_BOA:
        return 2
    if nota >= NOTA_ACEITAVEL:
        return 1
    return 0


def _legibilidade(probs, alvo_idx):
    p_alvo = float(probs[alvo_idx])
    outros = probs.clone()
    outros[alvo_idx] = 0.0
    p_segunda = float(outros.max())
    return p_alvo * (1.0 - PENALIDADE_SEGUNDA * p_segunda)


def avaliar_texto(characters, alvos=None, batch_size=32):
    """Avalia as letras em lote. `alvos` e uma lista opcional de letras
    esperadas (A-Z ou None por posicao); sem alvo, usa a letra prevista."""
    if not characters:
        return None
    if modelo_cnn is None:
        load_modelo()
    if alvos is None:
        alvos = [None] * len(characters)

    mascaras = [lp.normalizar_mascara(lp.mascara_de_recorte(c[4])) for c in characters]
    tensores = torch.stack([lp.tensor_de_mascara(m) for m in mascaras])

    probs_todos = []
    with torch.no_grad():
        for i in range(0, len(tensores), batch_size):
            logits = modelo_cnn(tensores[i:i + batch_size].to(device))
            probs_todos.append(torch.softmax(logits / temperatura, dim=1).cpu())
    probs_todos = torch.cat(probs_todos)

    resultados = []
    for i, (x, y, w, h, _) in enumerate(characters):
        probs = probs_todos[i]
        prevista = CLASSES[int(probs.argmax())]
        alvo = (alvos[i] or "").upper()
        if len(alvo) != 1 or alvo not in CLASSES:
            alvo = prevista
        legib = _legibilidade(probs, CLASSES.index(alvo))
        form = avaliar_formacao(mascaras[i], alvo)
        nota = 100.0 * (legib ** EXPOENTE_LEGIBILIDADE) * (form["formacao"] ** EXPOENTE_FORMACAO)
        classe = _classe_para_nota(nota)
        resultados.append({
            "indice": i + 1,
            "posicao": (x, y, w, h),
            "nota": round(nota, 1),
            "classe": classe,
            "categoria": CATEGORIAS[classe],
            "confianca": round(legib, 3),
            "letra_alvo": alvo,
            "letra_prevista": prevista,
            "legibilidade": round(legib, 3),
            "formacao": round(form["formacao"], 3),
            "medidas": form["medidas"],
            "pior_medida": form["pior"],
        })

    return {
        "caracteres": resultados,
        "pontuacao_geral": round(float(np.mean([r["nota"] for r in resultados])), 1),
        "total": len(resultados),
        "boas": sum(1 for r in resultados if r["classe"] == 2),
        "aceitaveis": sum(1 for r in resultados if r["classe"] == 1),
        "ruins": sum(1 for r in resultados if r["classe"] == 0),
    }


def explicar_letra(r):
    """Frase curta dizendo o principal problema da letra."""
    if r["legibilidade"] < 0.4 and r["letra_prevista"] != r["letra_alvo"]:
        return f"parecendo '{r['letra_prevista']}'"
    if r["legibilidade"] < 0.4:
        return "difícil de reconhecer"
    return _EXPLICACOES.get(r["pior_medida"], "com formação irregular")


def formatar_feedback(avaliacao):
    """Feedback em texto simples para terminal e testes."""
    if avaliacao is None:
        return "Nenhum caractere detectado."
    linhas = [
        f"Pontuação geral: {avaliacao['pontuacao_geral']}/100",
        f"Caracteres analisados: {avaliacao['total']}",
        "-" * 32,
        f"Boa formação:     {avaliacao['boas']} letra(s)",
        f"Aceitável:        {avaliacao['aceitaveis']} letra(s)",
        f"Precisa melhorar: {avaliacao['ruins']} letra(s)",
    ]
    ruins = [r for r in avaliacao["caracteres"] if r["classe"] == 0]
    if ruins:
        linhas.append("-" * 32)
        linhas.append("Letras que precisam de atenção:")
        for r in ruins:
            linhas.append(f"  Letra {r['indice']} ({r['nota']:.0f}/100): {explicar_letra(r)}")
    return "\n".join(linhas)


def gerar_relatorio(texto, avaliacao):
    """Relatório completo em texto, pronto para salvar em arquivo."""
    linhas = ["=" * 48, "RELATÓRIO DE ANÁLISE DE CALIGRAFIA", "=" * 48, "",
              "TEXTO RECONHECIDO:", texto if texto else "(nenhum texto reconhecido)", "",
              formatar_feedback(avaliacao), ""]
    if avaliacao:
        linhas.append("DETALHE POR LETRA:")
        for r in avaliacao["caracteres"]:
            linhas.append(
                f"  Letra {r['indice']:>3}  {r['letra_alvo']}  {r['categoria']:<10}"
                f" nota {r['nota']:>5.1f}  legibilidade {r['legibilidade']:.0%}"
                f"  formação {r['formacao']:.0%}"
            )
    return "\n".join(linhas)
