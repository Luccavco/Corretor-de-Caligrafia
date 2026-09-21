import os, sys, random
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, "/home/luccavco/Calligraphos/tcc-caligrafia"); os.chdir("/home/luccavco/Calligraphos/tcc-caligrafia")
from datetime import date, timedelta
from PyQt5.QtWidgets import QApplication, QMainWindow, QStackedWidget
from calligraphos.nuvem import progresso as prog
prog._salvar = lambda uid, estado: None
app = QApplication([])
from calligraphos.ui.ui_theme import STYLE
from calligraphos.ui.main_ui import TelaInicial
from calligraphos.ui.praticar import PraticarWidget
from calligraphos.ui.analise import AnaliseWidget
from calligraphos.nucleo.image_pipeline import process, load_image
from calligraphos.nucleo.handwriting_evaluator import avaliar_texto
from calligraphos.nucleo.feedback_visual import mapa_diferencas
OUT = sys.argv[1]
estado = prog._estado_novo()
for i, l in enumerate("ABCDEFGHIJKLMNOP"):
    estado["letras"][l] = min(5, (i % 5) + 1)
for l in "EJ": estado["letras"][l] = 5
estado["letras"]["A"] = 2
estado.update(fases_completas=2, iniciou_letras=True, onboarding_visto=True, exercicios_feitos=63, streak_dias=6, streak_recorde=11, feitos_hoje=4)
estado["data_feitos_hoje"] = estado["ultima_pratica"] = date.today().isoformat()
estado["conquistas"] = ["primeira_letra", "cinco_letras", "dedicado"]
estado["palavras_customizadas"] = ["CASA", "GATO", "PORTA"]
random.seed(2)
for i in range(27, -1, -1):
    d = (date.today() - timedelta(days=i)).isoformat()
    if i % 4 == 0: continue
    for _ in range(random.randint(2, 5)):
        estado["historico"].append({"d": d, "l": random.choice("ABCDEGM"), "n": round(min(100, max(0, random.gauss(48 + (27 - i) * 1.3, 10))), 1)})
sessao = {"uid": "fake", "email": "lucca.vco@puccampinas.edu.br"}
win = QMainWindow(); win.setStyleSheet(STYLE); stack = QStackedWidget(); win.setCentralWidget(stack); win.resize(1280, 780)
def grab(w, nome):
    stack.addWidget(w); stack.setCurrentWidget(w); win.show(); app.processEvents(); app.processEvents()
    win.grab().save(f"{OUT}/{nome}.png"); print(nome)
grab(TelaInicial(sessao["email"], estado, lambda: None, lambda: None, lambda: None), "fig3_inicio")
p = PraticarWidget("fake", estado); grab(p, "fig5_letras")
p.menu.setCurrentIndex(4); app.processEvents(); win.grab().save(f"{OUT}/fig7_progresso.png"); print("fig7_progresso")
p.iniciar_letra("A"); app.processEvents()
img = load_image("test_images/ALGORUIM.png"); chars = process("test_images/ALGORUIM.png")[1][:1]
av = avaliar_texto(chars, alvos=["A"]); mapa = mapa_diferencas(chars, av, img.shape[:2])
p.painel_exercicio.on_verificado("A", av, mapa); app.processEvents(); app.processEvents()
win.grab().save(f"{OUT}/fig6_exercicio.png"); print("fig6_exercicio")
# Analise com foto real (sem Google): simula resultado com a CNN
a = AnaliseWidget(tem_conta=True, estado_progresso=estado); grab(a, "fig4_analise_vazia")
from calligraphos.nucleo.image_pipeline import annotate_image
path = "test_images/CASA.jpg"; chars = process(path)[1]
av = avaliar_texto(chars, alvos=list("CASA")); anot = annotate_image(path, av)
a.image_path = path
a.stack_esquerda.setCurrentIndex(1); app.processEvents()
a.on_resultado("CASA", av, anot, {i: L for i, L in enumerate("CASA")})
app.processEvents(); app.processEvents(); win.grab().save(f"{OUT}/fig4_analise.png"); print("fig4_analise")
