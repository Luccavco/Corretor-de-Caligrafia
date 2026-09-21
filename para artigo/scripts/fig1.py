import sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
fig, ax = plt.subplots(figsize=(10.5, 6.4), dpi=200); ax.set_xlim(0, 105); ax.set_ylim(0, 60); ax.axis("off")
def box(x, y, w, h, titulo, sub="", fc="#f2f2f2", ec="#333", lw=1.2, fs=10.5):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.4,rounding_size=1.2", fc=fc, ec=ec, lw=lw))
    ax.text(x + w/2, y + h/2 + (2.2 if sub else 0), titulo, ha="center", va="center", fontsize=fs, fontweight="bold", color="#111")
    if sub: ax.text(x + w/2, y + h/2 - 2.6, sub, ha="center", va="center", fontsize=8.6, color="#333", linespacing=1.25)
def seta(x1, y1, x2, y2, txt="", ls="-"):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=14, lw=1.3, color="#222", ls=ls))
    if txt: ax.text((x1+x2)/2, (y1+y2)/2 + 1.6, txt, ha="center", fontsize=8, color="#222", style="italic")
# faixa 1: entrada e pre-processamento
box(2, 44, 22, 14, "Entrada", "quadro de desenho\nou fotografia", fc="#ffffff")
box(30, 44, 26, 14, "Pré-processamento", "OpenCV: binarização, remoção de\npauta, linhas e segmentação\nde letras", fc="#e8e8e8")
box(62, 44, 40, 14, "Transcrição (HTR)", "Google Cloud Vision (principal) ·\nTrOCR (offline, palavra única)", fc="#e8e8e8")
seta(24.4, 51, 29.6, 51); seta(56.4, 51, 61.6, 51)
# faixa 2: avaliacao
box(2, 22, 30, 15, "Legibilidade", "CNN MobileNetV2 (26 letras,\nEMNIST + augmentation)\nconfiança calibrada", fc="#d9d9d9")
box(37, 22, 30, 15, "Formação", "5 medidas contra moldes de letra\nde forma: semelhança, traços,\nproporção, inclinação, espessura", fc="#d9d9d9")
box(72, 22, 30, 15, "Nota por letra", "100 · √legib · formação^1,25\nBoa ≥ 75 · Aceitável ≥ 50\nmapa de diferenças", fc="#bfbfbf")
seta(43, 43.6, 17, 37.4, "letras recortadas"); seta(43, 43.6, 52, 37.4)
seta(82, 43.6, 87, 37.4, "letra-alvo"); seta(32.4, 29.5, 36.6, 29.5); seta(67.4, 29.5, 71.6, 29.5)
# faixa 3: interface e nuvem
box(2, 2, 46, 13, "Aplicativo desktop (PyQt5)", "Análise Individual · Prática (letras, palavras,\nquiz, dicionário) · progresso e conquistas", fc="#ffffff")
box(54, 2, 22, 13, "Firebase", "Authentication ·\nFirestore (progresso,\nhistórico de notas)", fc="#e8e8e8")
box(81, 2, 21, 13, "Site (React)", "painel, evolução\ne prática por\ntraçado", fc="#ffffff")
seta(87, 21.6, 40, 15.4, "resultado, feedback"); seta(48.4, 8.5, 53.6, 8.5); seta(80.6, 8.5, 76.4, 8.5)
plt.savefig(sys.argv[1] if False else "/tmp/claude-1000/-home-luccavco-Calligraphos/aa2c64d4-2803-4a0b-92aa-5dcef1cd3e7f/scratchpad/figs/fig1_arquitetura.png", bbox_inches="tight", facecolor="white")
print("ok")
