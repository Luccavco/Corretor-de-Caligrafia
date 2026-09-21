// Slides da apresentacao do TCC Calligraphos (~10 min, 14 slides)
const pptxgen = require("pptxgenjs");
const FIGS = "/tmp/claude-1000/-home-luccavco-Calligraphos/aa2c64d4-2803-4a0b-92aa-5dcef1cd3e7f/scratchpad/figs/";
const OUT = process.argv[2];

const pres = new pptxgen();
pres.layout = "LAYOUT_16x9";           // 10 x 5.625 in
pres.author = "Lucca Vasconcelos Costa Oliveira";
pres.title = "Calligraphos";

// paleta: identidade do app (escuro + azul), verde/ambar/vermelho das avaliacoes
const C = { escuro: "12141A", painel: "1E2230", texto: "1F2430", suave: "5B6478", claro: "FFFFFF",
            cinza: "F3F5F9", azul: "2F7FE0", azulEsc: "1B5FB5", verde: "3E9B6C", ambar: "D89A2B", verm: "D65454" };
const TIT = "Cambria", COR = "Calibri";

// ── helpers ──────────────────────────────────────────────────────────────
function titulo(s, texto, cor = C.texto) {
  s.addText(texto, { x: 0.5, y: 0.35, w: 9, h: 0.7, fontFace: TIT, fontSize: 30, bold: true, color: cor, isTextBox: true, margin: 0 });
}
function rodape(s, n) {
  s.addText("Calligraphos  ·  TCC Engenharia de Computação  ·  PUC-Campinas", { x: 0.5, y: 5.2, w: 7, h: 0.3, fontFace: COR, fontSize: 9, color: "9AA3B5", isTextBox: true, margin: 0 });
  s.addText(String(n), { x: 9, y: 5.2, w: 0.5, h: 0.3, fontFace: COR, fontSize: 9, color: "9AA3B5", align: "right", isTextBox: true, margin: 0 });
}
function cartao(s, x, y, w, h, opts = {}) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, fill: { color: opts.fill || C.cinza }, line: { color: opts.line || "E3E7EE", width: 0.75 }, rectRadius: 0.12,
    shadow: opts.sombra ? { type: "outer", blur: 6, offset: 2, angle: 90, color: "000000", opacity: 0.10 } : undefined });
}
function chip(s, x, y, letra, cor, tam = 0.55) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: tam, h: tam, fill: { color: cor }, line: { color: cor }, rectRadius: 0.1 });
  s.addText(letra, { x, y, w: tam, h: tam, fontFace: TIT, fontSize: tam * 36, bold: true, color: C.claro, align: "center", valign: "middle", isTextBox: true, margin: 0 });
}
function bullets(s, itens, x, y, w, h, opts = {}) {
  s.addText(itens.map((t, i) => ({ text: t, options: { bullet: { indent: 14 }, breakLine: i < itens.length - 1, paraSpaceAfter: opts.esp ?? 6 } })),
    { x, y, w, h, fontFace: COR, fontSize: opts.fs || 15, color: opts.cor || C.texto, valign: "top", isTextBox: true, margin: 0 });
}
function foto(s, arquivo, x, y, w, h) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: x - 0.05, y: y - 0.05, w: w + 0.1, h: h + 0.1, fill: { color: C.claro }, line: { color: "D8DDE6", width: 0.75 }, rectRadius: 0.08,
    shadow: { type: "outer", blur: 8, offset: 3, angle: 90, color: "000000", opacity: 0.18 } });
  s.addImage({ path: FIGS + arquivo, x, y, w, h, rounding: false });
}
function notas(s, t) { s.addNotes(t); }
let n = 0;

// 1 ── capa
{
  const s = pres.addSlide(); n++;
  s.background = { color: C.escuro };
  s.addImage({ path: FIGS + "icone.png", x: 0.6, y: 0.7, w: 1.1, h: 1.1 });
  s.addText("Calligraphos", { x: 0.6, y: 2.0, w: 8.8, h: 0.9, fontFace: TIT, fontSize: 48, bold: true, color: C.claro, isTextBox: true, margin: 0 });
  s.addText("Sistema de reconhecimento e avaliação de caligrafia baseado em aprendizado de máquina", { x: 0.6, y: 2.9, w: 8.4, h: 0.8, fontFace: COR, fontSize: 18, color: "C7CEDB", isTextBox: true, margin: 0 });
  ["C", "A", "S", "A"].forEach((l, i) => chip(s, 6.2 + i * 0.75, 0.95, l, [C.verde, C.verde, C.ambar, C.verm][i], 0.62));
  s.addText([{ text: "Aluno  ", options: { color: "9AA3B5" } }, { text: "Lucca Vasconcelos Costa Oliveira", options: { color: C.claro, bold: true } }], { x: 0.6, y: 4.25, w: 5.5, h: 0.35, fontFace: COR, fontSize: 14, isTextBox: true, margin: 0 });
  s.addText([{ text: "Orientador  ", options: { color: "9AA3B5" } }, { text: "Prof. Antonio Paulo Salgado Forster", options: { color: C.claro, bold: true } }], { x: 0.6, y: 4.6, w: 6, h: 0.35, fontFace: COR, fontSize: 14, isTextBox: true, margin: 0 });
  s.addText("Trabalho de Conclusão de Curso · Engenharia de Computação · PUC-Campinas · 2026", { x: 0.6, y: 5.05, w: 8.5, h: 0.3, fontFace: COR, fontSize: 11, color: "9AA3B5", isTextBox: true, margin: 0 });
  notas(s, "Bom dia. Vou apresentar o Calligraphos, um sistema que lê o que foi escrito à mão e avalia a qualidade da caligrafia, letra por letra. (~30 s)");
}

// 2 ── motivacao
{
  const s = pres.addSlide(); n++; s.background = { color: C.claro };
  titulo(s, "Por que avaliar caligrafia?");
  const cards = [
    ["Habilidade que continua importando", "Alfabetização, coordenação motora, provas, formulários e anotações ainda dependem da escrita à mão."],
    ["Está piorando", "Teclados e telas reduziram a prática; letra ilegível gera erros de interpretação e prejudica a avaliação do aluno."],
    ["Corrigir é caro e subjetivo", "Depende do professor ou da autoavaliação — trabalhoso, não escalável e sem parâmetro objetivo."],
  ];
  cards.forEach(([t, d], i) => {
    const x = 0.5 + i * 3.1;
    cartao(s, x, 1.35, 2.9, 3.4, { sombra: true });
    chip(s, x + 0.25, 1.6, ["A", "B", "C"][i], [C.azul, C.ambar, C.verm][i], 0.5);
    s.addText(t, { x: x + 0.25, y: 2.25, w: 2.4, h: 0.7, fontFace: COR, fontSize: 16, bold: true, color: C.texto, isTextBox: true, margin: 0 });
    s.addText(d, { x: x + 0.25, y: 3.0, w: 2.45, h: 1.6, fontFace: COR, fontSize: 13, color: C.suave, isTextBox: true, margin: 0, valign: "top" });
  });
  rodape(s, n);
  notas(s, "Três pontos: a escrita à mão continua necessária; a qualidade vem caindo; e corrigir depende de trabalho manual e subjetivo. Não existe ferramenta acessível que avalie a caligrafia de forma objetiva. (~45 s)");
}

// 3 ── lacuna + objetivo
{
  const s = pres.addSlide(); n++; s.background = { color: C.claro };
  titulo(s, "A lacuna e o objetivo");
  cartao(s, 0.5, 1.35, 4.35, 3.5);
  s.addText("O que existe", { x: 0.8, y: 1.55, w: 3.8, h: 0.4, fontFace: COR, fontSize: 16, bold: true, color: C.texto, isTextBox: true, margin: 0 });
  bullets(s, ["Apps de idiomas (Duolingo, WaniKani): vocabulário, gramática, pronúncia — não a letra", "Ferramentas de HTR/OCR: transcrevem o que foi escrito, sem julgar como foi escrito"], 0.8, 2.05, 3.8, 2.6, { fs: 14, cor: C.suave });
  cartao(s, 5.15, 1.35, 4.35, 3.5, { fill: C.azul, line: C.azul });
  s.addText("Objetivo do trabalho", { x: 5.45, y: 1.55, w: 3.8, h: 0.4, fontFace: COR, fontSize: 16, bold: true, color: C.claro, isTextBox: true, margin: 0 });
  s.addText("Um sistema que transcreve o texto manuscrito, dá uma nota explicável a cada letra e apoia a prática — com progresso sincronizado entre aplicativo e site.", { x: 5.45, y: 2.05, w: 3.8, h: 1.4, fontFace: COR, fontSize: 14, color: C.claro, isTextBox: true, margin: 0, valign: "top" });
  bullets(s, ["Pipeline de imagem (OpenCV)", "Transcrição online e offline", "Avaliador híbrido: CNN + geometria", "Interface e nuvem (PyQt5, React, Firebase)"], 5.45, 3.4, 3.8, 1.4, { fs: 13, cor: "E6EEFB", esp: 3 });
  rodape(s, n);
  notas(s, "As plataformas educacionais populares não olham para a letra; as de reconhecimento só transcrevem. O objetivo é unir reconhecimento e avaliação numa ferramenta de prática. (~40 s)");
}

// 4 ── arquitetura
{
  const s = pres.addSlide(); n++; s.background = { color: C.claro };
  titulo(s, "Arquitetura");
  foto(s, "fig1_arquitetura.png", 0.75, 1.25, 6.2, 3.81);
  cartao(s, 7.2, 1.25, 2.3, 3.8);
  s.addText("Tecnologias", { x: 7.4, y: 1.4, w: 2, h: 0.35, fontFace: COR, fontSize: 14, bold: true, color: C.texto, isTextBox: true, margin: 0 });
  bullets(s, ["Python 3.11 · PyQt5", "OpenCV", "PyTorch · MobileNetV2", "Google Cloud Vision · TrOCR", "Firebase (Auth + Firestore)", "React + Vite (site)"], 7.4, 1.85, 2.0, 3.1, { fs: 12, cor: C.suave, esp: 4 });
  rodape(s, n);
  notas(s, "Fluxo: entrada pelo quadro ou foto; pré-processamento; transcrição; avaliação em duas parcelas; resultado na interface; progresso no Firebase compartilhado com o site. (~40 s)");
}

// 5 ── pipeline
{
  const s = pres.addSlide(); n++; s.background = { color: C.claro };
  titulo(s, "Pré-processamento e segmentação");
  foto(s, "slide_pipeline.png", 0.5, 1.3, 9, 1.24);
  const passos = [["1", "Binarização adaptativa", "separa a tinta do papel mesmo com iluminação irregular; remove linhas de pauta"], ["2", "Linhas e letras", "projeção horizontal encontra as linhas; contornos delimitam cada letra"], ["3", "Fragmentos e letras coladas", "barra do A e pingo do i são fundidos; caixas largas demais são divididas no vale de tinta"]];
  passos.forEach(([num, t, d], i) => {
    const x = 0.5 + i * 3.1;
    cartao(s, x, 2.85, 2.9, 2.1);
    s.addShape(pres.shapes.OVAL, { x: x + 0.2, y: 3.05, w: 0.45, h: 0.45, fill: { color: C.azul }, line: { color: C.azul } });
    s.addText(num, { x: x + 0.2, y: 3.05, w: 0.45, h: 0.45, fontFace: COR, fontSize: 14, bold: true, color: C.claro, align: "center", valign: "middle", isTextBox: true, margin: 0 });
    s.addText(t, { x: x + 0.75, y: 3.05, w: 2.05, h: 0.45, fontFace: COR, fontSize: 13, bold: true, color: C.texto, valign: "middle", isTextBox: true, margin: 0 });
    s.addText(d, { x: x + 0.2, y: 3.6, w: 2.5, h: 1.25, fontFace: COR, fontSize: 12, color: C.suave, isTextBox: true, margin: 0, valign: "top" });
  });
  rodape(s, n);
  notas(s, "Antes de qualquer IA, a foto é limpa e cada letra é isolada. Os dois problemas clássicos — letra quebrada em pedaços e letras encostadas — receberam tratamento próprio. (~45 s)");
}

// 6 ── transcricao
{
  const s = pres.addSlide(); n++; s.background = { color: C.claro };
  titulo(s, "Transcrição do texto (HTR)");
  cartao(s, 0.5, 1.35, 4.35, 3.5, { sombra: true });
  s.addText("Google Cloud Vision", { x: 0.8, y: 1.55, w: 3.8, h: 0.4, fontFace: COR, fontSize: 17, bold: true, color: C.texto, isTextBox: true, margin: 0 });
  s.addText("motor principal · online", { x: 0.8, y: 1.95, w: 3.8, h: 0.3, fontFace: COR, fontSize: 12, italic: true, color: C.azul, isTextBox: true, margin: 0 });
  bullets(s, ["Bom desempenho em português", "Múltiplas palavras e linhas (redações)", "Devolve a posição de cada símbolo → o avaliador sabe qual letra era esperada em cada recorte"], 0.8, 2.4, 3.8, 2.3, { fs: 14, cor: C.suave });
  cartao(s, 5.15, 1.35, 4.35, 3.5, { sombra: true });
  s.addText("TrOCR (Microsoft)", { x: 5.45, y: 1.55, w: 3.8, h: 0.4, fontFace: COR, fontSize: 17, bold: true, color: C.texto, isTextBox: true, margin: 0 });
  s.addText("alternativa · offline", { x: 5.45, y: 1.95, w: 3.8, h: 0.3, fontFace: COR, fontSize: 12, italic: true, color: C.ambar, isTextBox: true, margin: 0 });
  bullets(s, ["Transformer pré-treinado, roda localmente", "Restrito a palavra única: decodificador treinado em inglês erra frases em português", "Sem internet, o exercício de letra usa a própria CNN do avaliador"], 5.45, 2.4, 3.8, 2.3, { fs: 14, cor: C.suave });
  rodape(s, n);
  notas(s, "Dois motores: o Google Vision como principal, por lidar com português e várias linhas; o TrOCR como reserva offline para uma palavra. Sem internet o sistema continua funcionando e avisa. (~35 s)");
}

// 7 ── avaliador: a licao
{
  const s = pres.addSlide(); n++; s.background = { color: C.escuro };
  titulo(s, "Avaliador: a primeira versão falhou", C.claro);
  cartao(s, 0.5, 1.4, 4.35, 3.4, { fill: C.painel, line: "2C3140" });
  s.addText("Versão 1", { x: 0.8, y: 1.6, w: 3.8, h: 0.4, fontFace: COR, fontSize: 16, bold: true, color: C.verm, isTextBox: true, margin: 0 });
  bullets(s, ["Rótulos 'boa/aceitável/ruim' gerados pela variância de pixels do EMNIST", "A CNN aprendeu a medir quantidade de tinta, não forma", "Traço grosso = 'boa'. Até um rabisco aleatório recebia nota 100"], 0.8, 2.05, 3.8, 2.6, { fs: 14, cor: "C7CEDB" });
  cartao(s, 5.15, 1.4, 4.35, 3.4, { fill: C.painel, line: "2C3140" });
  s.addText("Versão 2 — avaliador híbrido", { x: 5.45, y: 1.6, w: 3.8, h: 0.4, fontFace: COR, fontSize: 16, bold: true, color: C.verde, isTextBox: true, margin: 0 });
  bullets(s, ["Legibilidade: CNN reconhece qual letra é (rótulos reais)", "Formação: 5 medidas geométricas contra moldes de letra de forma", "Nota explicável: o usuário recebe o motivo, não só o número"], 5.45, 2.05, 3.8, 2.6, { fs: 14, cor: "C7CEDB" });
  rodape(s, n);
  notas(s, "A lição mais importante do projeto. A primeira versão treinava uma rede, mas os rótulos eram inventados a partir da variância de pixels; ela aprendeu a medir tinta. Só a validação com escrita real revelou isso. A solução foi separar o que a rede sabe fazer — reconhecer letras — do que é explicável — geometria. (~60 s)");
}

// 8 ── avaliador: como funciona
{
  const s = pres.addSlide(); n++; s.background = { color: C.claro };
  titulo(s, "Como a nota é calculada");
  cartao(s, 0.5, 1.3, 4.35, 2.45);
  s.addText("Legibilidade", { x: 0.75, y: 1.45, w: 3.9, h: 0.35, fontFace: COR, fontSize: 16, bold: true, color: C.azul, isTextBox: true, margin: 0 });
  bullets(s, ["MobileNetV2 (transfer learning) treinada nas 26 letras do EMNIST", "Augmentation: espessura, rotação, cisalhamento, largura", "Confiança calibrada por temperatura; penaliza letra ambígua (A que parece O)"], 0.75, 1.85, 3.9, 1.85, { fs: 12, cor: C.suave, esp: 4 });
  cartao(s, 5.15, 1.3, 4.35, 2.45);
  s.addText("Formação (contra o molde)", { x: 5.4, y: 1.45, w: 3.9, h: 0.35, fontFace: COR, fontSize: 16, bold: true, color: C.verde, isTextBox: true, margin: 0 });
  bullets(s, ["Semelhança de forma (F1 tolerante)  ·  40%", "Direção dos traços (curvas onde há retas)  ·  20%", "Proporção  ·  15%   ·   Inclinação  ·  10%", "Regularidade da espessura  ·  15%"], 5.4, 1.9, 3.9, 1.8, { fs: 12, cor: C.suave, esp: 4 });
  cartao(s, 0.5, 3.95, 9, 1.1, { fill: C.escuro, line: C.escuro });
  s.addText([{ text: "nota = 100 · √legibilidade · formação", options: { color: C.claro } }, { text: "1,25", options: { color: C.claro, superscript: true } }], { x: 0.75, y: 4.05, w: 5.1, h: 0.9, fontFace: TIT, fontSize: 18, bold: true, valign: "middle", isTextBox: true, margin: 0 });
  s.addText([{ text: "Boa ≥ 75", options: { color: C.verde, bold: true } }, { text: "   Aceitável ≥ 50", options: { color: C.ambar, bold: true } }, { text: "   Ruim < 50", options: { color: C.verm, bold: true } }, { text: "\nExercício aceita a letra com nota ≥ 65", options: { color: "C7CEDB" } }], { x: 5.95, y: 4.05, w: 3.4, h: 0.9, fontFace: COR, fontSize: 11.5, valign: "middle", isTextBox: true, margin: 0 });
  rodape(s, n);
  notas(s, "A legibilidade funciona como porta: letra irreconhecível nunca pontua bem. A formação manda na nota, porque o critério é parecer o molde de letra de forma. Tudo configurável. (~50 s)");
}

// 9 ── analise individual
{
  const s = pres.addSlide(); n++; s.background = { color: C.claro };
  titulo(s, "Análise Individual");
  foto(s, "slide_analise_esq.png", 0.5, 1.3, 3.7, 3.6);
  foto(s, "slide_analise_dir.png", 4.4, 1.3, 2.62, 3.54);
  cartao(s, 7.25, 1.3, 2.25, 3.6);
  bullets(s, ["Quadro de desenho ou foto", "Texto transcrito", "Pontuação geral = média das notas", "Cada letra contornada na cor da categoria", "Detalhe com as 5 medidas em barras", "Correção manual e relatório"], 7.45, 1.45, 1.95, 3.4, { fs: 11.5, cor: C.suave, esp: 4 });
  rodape(s, n);
  notas(s, "Na Análise, a foto ou o desenho vira texto, pontuação e imagem anotada; clicando numa letra o usuário vê as medidas. (~30 s)");
}

// 10 ── pratica + mapa
{
  const s = pres.addSlide(); n++; s.background = { color: C.claro };
  titulo(s, "Prática guiada: o retorno mostra o erro");
  foto(s, "slide_mapa.png", 0.5, 1.3, 4.3, 3.8);
  cartao(s, 5.1, 1.3, 4.4, 3.8);
  s.addText("Mapa de diferenças", { x: 5.35, y: 1.45, w: 3.9, h: 0.4, fontFace: COR, fontSize: 16, bold: true, color: C.texto, isTextBox: true, margin: 0 });
  const leg = [[C.verde, "traço que coincide com o molde"], [C.verm, "traço fora do molde"], ["9EC8FF", "molde sem traço (faltou)"]];
  leg.forEach(([c, t], i) => {
    s.addShape(pres.shapes.RECTANGLE, { x: 5.35, y: 2.0 + i * 0.42, w: 0.28, h: 0.28, fill: { color: c }, line: { color: c } });
    s.addText(t, { x: 5.75, y: 1.97 + i * 0.42, w: 3.5, h: 0.34, fontFace: COR, fontSize: 13, color: C.suave, valign: "middle", isTextBox: true, margin: 0 });
  });
  bullets(s, ["Letra-guia transparente para traçar por cima", "Mensagem diz a nota e o motivo: \"curvas onde o molde tem traços retos (42/100)\"", "Também: palavras por fases, quiz, dicionário, conquistas, meta diária e streak"], 5.35, 3.35, 3.9, 1.7, { fs: 12.5, cor: C.suave, esp: 4 });
  rodape(s, n);
  notas(s, "No exercício, depois de enviar, o quadro vira este mapa: verde onde bateu com o molde, vermelho onde saiu. O A da demonstração foi desenhado de propósito 'de qualquer jeito' e reprovou com o motivo. (~40 s)");
}

// 11 ── progresso + site
{
  const s = pres.addSlide(); n++; s.background = { color: C.claro };
  titulo(s, "Progresso sincronizado: aplicativo e site");
  foto(s, "slide_evolucao.png", 0.5, 1.3, 5.2, 1.4);
  foto(s, "fig8_site.png", 0.5, 2.95, 3.0, 2.11);
  cartao(s, 3.75, 2.95, 1.95, 2.1);
  s.addText("Site (React)", { x: 3.9, y: 3.05, w: 1.7, h: 0.3, fontFace: COR, fontSize: 12, bold: true, color: C.texto, isTextBox: true, margin: 0 });
  bullets(s, ["Mesma conta", "Painel e gráfico", "Traçado no navegador (sem IA)"], 3.9, 3.4, 1.75, 1.6, { fs: 10.5, cor: C.suave, esp: 3 });
  cartao(s, 5.95, 1.3, 3.55, 3.75);
  s.addText("Histórico de evolução", { x: 6.15, y: 1.45, w: 3.2, h: 0.35, fontFace: COR, fontSize: 15, bold: true, color: C.texto, isTextBox: true, margin: 0 });
  bullets(s, ["Cada tentativa grava a nota no Firestore", "Média diária dos últimos 30 dias, com as faixas Boa/Aceitável/Ruim", "Semana atual × anterior e letras para reforçar", "Nível por letra, mapa de calor do alfabeto, conquistas e revisão espaçada"], 6.15, 1.9, 3.2, 3.0, { fs: 12.5, cor: C.suave, esp: 4 });
  rodape(s, n);
  notas(s, "Cada tentativa vira um ponto no histórico; o gráfico mostra a evolução. Aplicativo e site compartilham o mesmo documento no Firebase, no estilo do Anki e AnkiWeb. (~35 s)");
}

// 12 ── resultados
{
  const s = pres.addSlide(); n++; s.background = { color: C.claro };
  titulo(s, "Resultados");
  const stats = [["93,9%", "acurácia da CNN de legibilidade\n(EMNIST letters, 20.800 imagens)", C.azul], ["0,74", "temperatura de calibração\n(rede era confiante demais)", C.ambar], ["7", "casos de referência em testes automatizados,\nrodados a cada alteração (CI)", C.verde]];
  stats.forEach(([v, d, c], i) => {
    const x = 0.5 + i * 3.1;
    cartao(s, x, 1.3, 2.9, 1.55);
    s.addText(v, { x: x + 0.2, y: 1.35, w: 2.5, h: 0.75, fontFace: TIT, fontSize: 34, bold: true, color: c, isTextBox: true, margin: 0 });
    s.addText(d, { x: x + 0.2, y: 2.1, w: 2.6, h: 0.7, fontFace: COR, fontSize: 10.5, color: C.suave, isTextBox: true, margin: 0, valign: "top" });
  });
  const linhas = [
    [{ text: "Caso (alvo: A)", options: { bold: true } }, { text: "Legib.", options: { bold: true } }, { text: "Form.", options: { bold: true } }, { text: "Nota", options: { bold: true } }, { text: "Categoria", options: { bold: true } }],
    ["Letra limpa de fonte", "1,00", "0,99", "99,9", { text: "Boa", options: { color: C.verde, bold: true } }],
    ["Letras bem formadas em foto (média)", "0,97", "0,83", "77–86", { text: "Boa", options: { color: C.verde, bold: true } }],
    ["A arredondado, pernas abertas", "0,99", "0,66", "59,4", { text: "Aceitável — reprova", options: { color: C.ambar, bold: true } }],
    ["A descuidado no quadro", "1,00", "0,49", "41,9", { text: "Ruim", options: { color: C.verm, bold: true } }],
    ["Rabisco aleatório", "0,00", "0,46", "1,9", { text: "Ruim", options: { color: C.verm, bold: true } }],
    ["Letra O no lugar de A", "0,00", "0,40", "0,8", { text: "Ruim", options: { color: C.verm, bold: true } }],
  ];
  s.addTable(linhas, { x: 0.5, y: 3.05, w: 9, colW: [3.6, 1.1, 1.1, 1.0, 2.2], fontFace: COR, fontSize: 11, color: C.texto, border: { type: "solid", color: "E3E7EE", pt: 0.75 }, fill: { color: C.claro }, rowH: 0.27, margin: [2, 6, 2, 6] });
  rodape(s, n);
  notas(s, "A rede acerta 93,9% das letras do EMNIST. Mas o resultado que importa é a tabela: a letra limpa tira quase 100, o A arredondado é reconhecido mas reprova, e rabisco e letra trocada ficam perto de zero — exatamente a ordem que um professor daria. (~50 s)");
}

// 13 ── limitacoes e futuro
{
  const s = pres.addSlide(); n++; s.background = { color: C.claro };
  titulo(s, "Limitações e trabalhos futuros");
  cartao(s, 0.5, 1.3, 4.35, 3.75);
  s.addText("Limitações", { x: 0.8, y: 1.45, w: 3.8, h: 0.4, fontFace: COR, fontSize: 16, bold: true, color: C.verm, isTextBox: true, margin: 0 });
  bullets(s, ["Moldes tipográficos: estilos pessoais válidos (letra condensada) perdem pontos", "Calibração com casos sintéticos e poucas amostras reais do autor", "Fotos com letras muito próximas ou iluminação irregular", "Só letra de forma; offline restrito a palavra única"], 0.8, 1.95, 3.8, 3.0, { fs: 13, cor: C.suave });
  cartao(s, 5.15, 1.3, 4.35, 3.75, { fill: C.azul, line: C.azul });
  s.addText("Próximos passos", { x: 5.45, y: 1.45, w: 3.8, h: 0.4, fontFace: COR, fontSize: 16, bold: true, color: C.claro, isTextBox: true, margin: 0 });
  bullets(s, ["Coletar letras de vários escritores rotuladas por pessoas → medir concordância e ajustar pesos com dados", "Publicar pacote instalável (release)", "Site como PWA no celular, com um serviço expondo o avaliador", "Avaliação pedagógica com usuários reais"], 5.45, 1.95, 3.8, 3.0, { fs: 13, cor: "E6EEFB" });
  rodape(s, n);
  notas(s, "Sou honesto sobre os limites: o molde tipográfico penaliza estilos válidos e a calibração ainda usa poucas amostras reais. O próximo passo natural é a validação com vários escritores e avaliadores humanos. (~40 s)");
}

// 14 ── conclusao / obrigado
{
  const s = pres.addSlide(); n++; s.background = { color: C.escuro };
  s.addText("Conclusão", { x: 0.6, y: 0.5, w: 8.8, h: 0.6, fontFace: TIT, fontSize: 30, bold: true, color: C.claro, isTextBox: true, margin: 0 });
  bullets(s, ["Sistema funcional de ponta a ponta: transcreve, avalia letra por letra e apoia a prática, com progresso sincronizado", "A rede responde pelo que sabe (reconhecer letras); a geometria pelo que é explicável (forma, proporção, inclinação)", "O usuário recebe a nota e o motivo — e vê no mapa onde o traço saiu do molde"], 0.6, 1.3, 8.6, 2.2, { fs: 15, cor: "C7CEDB", esp: 8 });
  ["C", "A", "S", "A"].forEach((l, i) => chip(s, 0.6 + i * 0.75, 3.75, l, [C.verde, C.verde, C.ambar, C.verm][i], 0.62));
  s.addText("Obrigado!", { x: 0.6, y: 4.45, w: 4, h: 0.6, fontFace: TIT, fontSize: 28, bold: true, color: C.claro, isTextBox: true, margin: 0 });
  s.addText("lucca.vco@puccampinas.edu.br  ·  github.com/Luccavco/Corretor-de-Caligrafia", { x: 3.2, y: 4.6, w: 6.3, h: 0.35, fontFace: COR, fontSize: 11, color: "9AA3B5", align: "right", isTextBox: true, margin: 0 });
  notas(s, "Concluindo: o sistema faz o que se propôs, e a lição de projeto foi separar o papel da rede do papel da geometria. Agradeço ao professor Antonio Forster pela orientação e à PUC-Campinas. Estou à disposição para perguntas. (~35 s)");
}

pres.writeFile({ fileName: OUT }).then(() => console.log("gravado", OUT, n, "slides"));
