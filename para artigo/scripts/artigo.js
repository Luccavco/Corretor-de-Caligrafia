// Gera o artigo do Calligraphos no formato SBC (Word .docx)
const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, ImageRun, Table, TableRow, TableCell,
  AlignmentType, WidthType, BorderStyle, LevelFormat, TabStopType,
} = require("docx");

const FIGS = require("path").join(__dirname, "..", "entrega", "figuras") + "/";
const OUT = process.argv[2];

// ── unidades: 1 cm = 567 DXA ─────────────────────────────────────────────
const cm = (v) => Math.round(v * 567);
const FONTE = "Times New Roman";
const HELV = "Arial";

// ── blocos de texto ──────────────────────────────────────────────────────
function runs(texto, extra = {}) {
  // aceita marcacao simples: *italico* e **negrito**
  const partes = texto.split(/(\*\*[^*]+\*\*|\*[^*]+\*)/g).filter(Boolean);
  return partes.map((p) => {
    if (p.startsWith("**")) return new TextRun({ text: p.slice(2, -2), bold: true, font: FONTE, size: 24, ...extra });
    if (p.startsWith("*")) return new TextRun({ text: p.slice(1, -1), italics: true, font: FONTE, size: 24, ...extra });
    return new TextRun({ text: p, font: FONTE, size: 24, ...extra });
  });
}
const P = (texto, { indent = true, before = 120, after = 0, align = AlignmentType.JUSTIFIED } = {}) =>
  new Paragraph({
    alignment: align,
    spacing: { before, after, line: 240 },
    indent: indent ? { firstLine: cm(1.27) } : undefined,
    children: runs(texto),
  });
// primeiro paragrafo da secao: sem recuo
const P0 = (texto, opts = {}) => P(texto, { indent: false, ...opts });

const H1 = (texto) => new Paragraph({
  spacing: { before: 240, after: 0 }, keepNext: true,
  children: [new TextRun({ text: texto, bold: true, font: FONTE, size: 26 })],
});
const H2 = (texto) => new Paragraph({
  spacing: { before: 240, after: 0 }, keepNext: true,
  children: [new TextRun({ text: texto, bold: true, font: FONTE, size: 24 })],
});
const H3 = (texto) => new Paragraph({
  spacing: { before: 200, after: 0 }, keepNext: true,
  children: [new TextRun({ text: texto, bold: true, italics: true, font: FONTE, size: 24 })],
});

const item = (texto, ref) => new Paragraph({
  numbering: { reference: ref, level: 0 },
  alignment: AlignmentType.JUSTIFIED,
  spacing: { before: 60, after: 0 },
  children: runs(texto),
});

// figura centralizada + legenda (Helvetica 10 negrito, 6pt antes/depois)
function figura(arquivo, larguraCm, legenda) {
  const buf = fs.readFileSync(FIGS + arquivo);
  const dim = tamanhoPng(buf);
  const largura = Math.round(larguraCm / 2.54 * 96);
  const altura = Math.round(largura * dim.h / dim.w);
  return [
    new Paragraph({
      alignment: AlignmentType.CENTER, spacing: { before: 120, after: 0 }, keepNext: true,
      children: [new ImageRun({ type: "png", data: buf, transformation: { width: largura, height: altura } })],
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER, spacing: { before: 120, after: 120 },
      children: [new TextRun({ text: legenda, bold: true, font: HELV, size: 20 })],
    }),
  ];
}
function tamanhoPng(buf) {
  return { w: buf.readUInt32BE(16), h: buf.readUInt32BE(20) };
}

// tabela sem sombreamento, linhas finas
function tabela(cabecalho, linhas, largurasCm) {
  const larguras = largurasCm.map(cm);
  const borda = { style: BorderStyle.SINGLE, size: 4, color: "000000" };
  const cel = (t, negrito = false) => new TableCell({
    width: { size: larguras[0], type: WidthType.DXA },
    margins: { top: 60, bottom: 60, left: 100, right: 100 },
    children: [new Paragraph({ spacing: { before: 0, after: 0 }, children: [new TextRun({ text: t, bold: negrito, font: FONTE, size: 22 })] })],
  });
  const linha = (cels, negrito) => new TableRow({
    children: cels.map((t, i) => new TableCell({
      width: { size: larguras[i], type: WidthType.DXA },
      margins: { top: 60, bottom: 60, left: 100, right: 100 },
      children: [new Paragraph({ spacing: { before: 0, after: 0 }, children: [new TextRun({ text: t, bold: negrito, font: FONTE, size: 22 })] })],
    })),
  });
  return new Table({
    width: { size: larguras.reduce((a, b) => a + b, 0), type: WidthType.DXA },
    columnWidths: larguras,
    alignment: AlignmentType.CENTER,
    borders: { top: borda, bottom: borda, left: borda, right: borda, insideHorizontal: borda, insideVertical: borda },
    rows: [linha(cabecalho, true), ...linhas.map((l) => linha(l, false))],
  });
}
const legendaTabela = (t) => new Paragraph({
  alignment: AlignmentType.CENTER, spacing: { before: 120, after: 120 }, keepNext: true,
  children: [new TextRun({ text: t, bold: true, font: HELV, size: 20 })],
});

const ref = (texto) => new Paragraph({
  alignment: AlignmentType.JUSTIFIED,
  spacing: { before: 120, after: 0 },
  indent: { left: cm(0.5), hanging: cm(0.5) },
  children: runs(texto),
});

// ── conteudo ─────────────────────────────────────────────────────────────
const filhos = [];
const add = (...x) => filhos.push(...x.flat());

// Titulo, autores, endereco, e-mail
add(new Paragraph({
  alignment: AlignmentType.CENTER, spacing: { before: 240, after: 240 },
  children: [new TextRun({ text: "Calligraphos: Sistema de Reconhecimento e Avaliação de Caligrafia Baseado em Aprendizado de Máquina", bold: true, font: FONTE, size: 32 })],
}));
add(new Paragraph({
  alignment: AlignmentType.CENTER, spacing: { before: 0, after: 240 },
  children: [
    new TextRun({ text: "Lucca Vasconcelos Costa Oliveira", bold: true, font: FONTE, size: 24 }),
    new TextRun({ text: "1", bold: true, font: FONTE, size: 24, superScript: true }),
    new TextRun({ text: ", Antonio Paulo Salgado Forster", bold: true, font: FONTE, size: 24 }),
    new TextRun({ text: "1", bold: true, font: FONTE, size: 24, superScript: true }),
  ],
}));
add(new Paragraph({
  alignment: AlignmentType.CENTER, spacing: { before: 0, after: 0 },
  children: [
    new TextRun({ text: "1", font: FONTE, size: 24, superScript: true }),
    new TextRun({ text: "Faculdade de Engenharia de Computação – Pontifícia Universidade Católica de Campinas (PUC-Campinas)", font: FONTE, size: 24 }),
  ],
}));
add(new Paragraph({
  alignment: AlignmentType.CENTER, spacing: { before: 0, after: 240 },
  children: [new TextRun({ text: "Rua Professor Dr. Euryclides de Jesus Zerbini, 1516 – Parque das Universidades – Campinas – SP – Brasil", font: FONTE, size: 24 })],
}));
add(new Paragraph({
  alignment: AlignmentType.CENTER, spacing: { before: 120, after: 120 },
  children: [new TextRun({ text: "lucca.vco@puccampinas.edu.br, antonio.forster@puc-campinas.edu.br", font: "Courier New", size: 20 })],
}));

const resumo = (rotulo, texto) => new Paragraph({
  alignment: AlignmentType.JUSTIFIED,
  spacing: { before: 240, after: 0, line: 240 },
  indent: { left: cm(0.8), right: cm(0.8) },
  children: [
    new TextRun({ text: rotulo + " ", bold: true, italics: true, font: FONTE, size: 24 }),
    new TextRun({ text: texto, italics: true, font: FONTE, size: 24 }),
  ],
});
add(resumo("Abstract.", "Legible handwriting remains a fundamental skill despite the digitalization of communication, yet its improvement traditionally depends on subjective, non-scalable manual correction. This paper presents Calligraphos, a software system that combines handwritten text recognition (HTR) with automatic assessment of handwriting quality. Transcription uses the Google Cloud Vision API as the main engine and the TrOCR model as an offline alternative. Quality assessment is hybrid: a MobileNetV2 network trained on EMNIST (93.9% validation accuracy, temperature-calibrated) estimates legibility, and five geometric measures against block-letter templates estimate letter formation; both are combined into a 0–100 score per letter, with a visual difference map. The system also provides a guided practice module with progress history and a companion web application sharing the same account."));
add(resumo("Resumo.", "A escrita legível permanece uma habilidade fundamental apesar da digitalização da comunicação, mas seu aprimoramento depende tradicionalmente de correção manual, subjetiva e não escalável. Este trabalho apresenta o Calligraphos, um sistema de software que combina o reconhecimento de texto manuscrito (HTR) e a avaliação automática da qualidade da caligrafia. A transcrição utiliza a API Google Cloud Vision como motor principal e o modelo TrOCR como alternativa offline. A avaliação é híbrida: uma rede MobileNetV2 treinada sobre o EMNIST (93,9% de acurácia de validação, calibrada por temperatura) estima a legibilidade, e cinco medidas geométricas contra moldes de letra de forma estimam a formação; ambas se combinam em uma nota de 0 a 100 por letra, com mapa visual de diferenças. O sistema oferece ainda um módulo de prática guiada com histórico de evolução e uma aplicação web complementar que compartilha a mesma conta."));

// 1. Introducao
add(H1("1. Introdução"));
add(H3("Contextualização do problema"));
add(P0("A escrita à mão acompanha a humanidade há milênios e, mesmo diante da crescente digitalização da comunicação, permanece uma competência fundamental. No processo de alfabetização, o traçado manual das letras está diretamente associado ao desenvolvimento cognitivo, à memorização e à coordenação motora fina. Em contextos escolares e profissionais, a legibilidade da escrita continua sendo requisitada em provas, formulários, anotações e registros diversos."));
add(P("Apesar dessa relevância, observa-se uma deterioração progressiva da qualidade da caligrafia, atribuída em grande parte ao uso intensivo de teclados e telas sensíveis ao toque. Uma caligrafia pouco legível pode comprometer a comunicação, gerar erros de interpretação e, no ambiente escolar, prejudicar a avaliação do estudante independentemente do conteúdo produzido."));
add(P("O aprimoramento da caligrafia, tradicionalmente, depende da correção manual realizada por professores ou da autoavaliação do próprio indivíduo. Ambos os processos apresentam limitações: a correção manual é trabalhosa, subjetiva e não escalável, enquanto a autoavaliação carece de parâmetros objetivos. Não há, para o público geral, uma ferramenta amplamente acessível que avalie de forma automática e consistente a qualidade da escrita manual."));
add(H3("Definição do problema"));
add(P0("O problema central abordado neste trabalho é a ausência de sistemas acessíveis capazes de avaliar objetivamente a qualidade da caligrafia, isto é, a formação física das letras, e de oferecer retorno estruturado que apoie o seu aprimoramento contínuo. Aplicativos de aprendizado de idiomas e plataformas educacionais populares concentram-se em vocabulário, gramática, pronúncia e memorização, e não no ato motor de escrever. Ferramentas de reconhecimento de texto manuscrito, por sua vez, transcrevem o que foi escrito sem julgar como foi escrito. Existe, portanto, uma lacuna entre a tecnologia de reconhecimento disponível e a necessidade específica de avaliação e treino da caligrafia."));
add(H3("Apresentação da solução"));
add(P0("Diante desse quadro, foi desenvolvido o Calligraphos, um sistema de software que une, em uma única ferramenta, o reconhecimento e a avaliação de caligrafia, apoiados por um módulo de prática guiada. O sistema é composto por um aplicativo desktop, que concentra as funcionalidades completas, e por uma aplicação web complementar que compartilha a mesma conta e o mesmo progresso. As principais funcionalidades são:"));
add(item("Transcrição de texto manuscrito para texto digital, a partir de fotografia ou de um quadro de desenho integrado ao aplicativo;", "num1"));
add(item("Avaliação de cada letra por um método híbrido, que reúne a legibilidade estimada por rede neural e a formação medida geometricamente contra moldes de letra de forma, com nota de 0 a 100, pontuação geral e imagem anotada na qual cada caractere é contornado na cor da sua classificação;", "num1"));
add(item("Módulo de prática guiada, com exercícios de letras e palavras, letra-guia para traçado, mapa de diferenças entre o traço e o molde, progresso por nível, metas diárias, sequência de dias consecutivos (streak), conquistas e histórico de evolução da nota;", "num1"));
add(item("Dicionário integrado para consulta de significados e inclusão de novas palavras no treino;", "num1"));
add(item("Aplicação web que permite acompanhar o progresso e praticar o traçado de letras diretamente no navegador.", "num1"));
add(H3("Objetivos"));
add(P0("O objetivo geral deste trabalho é desenvolver e validar um sistema de software para o reconhecimento e a avaliação automática de caligrafia manuscrita, dotado de recursos de apoio à prática. Como objetivos específicos, o projeto visa:"));
add(item("Implementar um pipeline de processamento de imagem capaz de preparar fotografias e desenhos de texto manuscrito para análise;", "bul1"));
add(item("Integrar mecanismos de transcrição de texto manuscrito, avaliando alternativas online e offline;", "bul1"));
add(item("Desenvolver um avaliador de qualidade de caligrafia que combine uma rede neural convolucional, treinada por transferência de aprendizado, com medidas geométricas explicáveis;", "bul1"));
add(item("Construir uma interface gráfica clara, que apresente os resultados e o motivo de cada avaliação de forma compreensível ao usuário leigo;", "bul1"));
add(item("Implementar autenticação de usuários e sincronização de progresso em nuvem, integrando aplicativo e site.", "bul1"));
add(H3("Estrutura do trabalho"));
add(P0("O restante deste artigo está organizado da seguinte forma. A Seção 2 apresenta a fundamentação teórica. A Seção 3 detalha o desenvolvimento do sistema: arquitetura, pipeline de imagem, transcrição, avaliador híbrido, interface, persistência e aplicação web. A Seção 4 discute os resultados, o diferencial em relação a outras plataformas, os desafios e as limitações. A Seção 5 apresenta as considerações finais e os trabalhos futuros."));

// 2. Fundamentacao
add(H1("2. Fundamentação Teórica"));
add(H2("2.1. Reconhecimento de Texto Manuscrito"));
add(P0("O reconhecimento de texto manuscrito, ou HTR (*Handwritten Text Recognition*), consiste na conversão de texto escrito à mão em texto digital editável. Trata-se de uma especialização do reconhecimento óptico de caracteres (OCR), historicamente voltado a texto impresso. A principal dificuldade do HTR reside na altíssima variabilidade da escrita humana: a mesma letra pode assumir formas radicalmente distintas conforme a pessoa, o instrumento, a inclinação e a velocidade de quem escreve [Memon et al. 2020]."));
add(P("As abordagens clássicas baseavam-se em extração manual de características e em modelos estatísticos, como os Modelos Ocultos de Markov. Com a popularização do aprendizado profundo, tornaram-se dominantes as arquiteturas neurais, que combinam redes convolucionais, para a extração de características visuais, com redes recorrentes ou mecanismos de atenção, para modelar a sequência de caracteres. Modelos recentes baseados na arquitetura Transformer, como o TrOCR [Li et al. 2021], tratam o reconhecimento como uma tradução de imagem para texto. Serviços em nuvem, como o Google Cloud Vision, oferecem APIs de HTR robustas, treinadas em grandes volumes de dados e capazes de lidar com múltiplos idiomas e texto de várias linhas."));
add(H2("2.2. Redes Neurais Convolucionais"));
add(P0("As redes neurais convolucionais (CNNs) constituem uma classe de arquiteturas de aprendizado profundo particularmente eficaz no processamento de imagens [Goodfellow et al. 2016]. Sua característica distintiva é o uso de camadas convolucionais, que aplicam filtros deslizantes sobre a imagem para detectar padrões locais, como bordas, texturas e formas, de maneira invariante à posição. As primeiras camadas capturam características de baixo nível, enquanto as mais profundas combinam essas informações em representações de alto nível. Essa hierarquia, aprendida automaticamente, dispensa a engenharia manual de atributos."));
add(P("A arquitetura MobileNetV2 [Sandler et al. 2018], empregada neste trabalho, foi projetada para ser eficiente em dispositivos com recursos limitados: utiliza convoluções separáveis em profundidade e blocos residuais invertidos, reduzindo o número de parâmetros e operações em relação a arquiteturas convencionais sem grande perda de acurácia, o que a torna adequada para execução em computadores pessoais."));
add(H2("2.3. Transferência de Aprendizado e Calibração de Confiança"));
add(P0("A transferência de aprendizado (*transfer learning*) reaproveita um modelo previamente treinado em uma tarefa com grande volume de dados como ponto de partida para uma nova tarefa relacionada [Goodfellow et al. 2016]. Neste trabalho, a MobileNetV2 é utilizada com pesos pré-treinados no conjunto ImageNet: as camadas iniciais, que já reconhecem bordas e formas genéricas, são refinadas com taxa de aprendizado reduzida, enquanto a camada classificadora é substituída e treinada para a tarefa específica."));
add(P("Redes neurais modernas tendem a ser excessivamente confiantes em suas previsões. O escalonamento de temperatura [Guo et al. 2017] corrige esse efeito dividindo os *logits* por um escalar *T* ajustado em um conjunto de validação, de modo que a probabilidade emitida passe a refletir a frequência real de acerto. Essa calibração é relevante quando a confiança da rede é usada como medida, situação que ocorre na parcela de legibilidade do avaliador aqui proposto."));
add(H2("2.4. O Conjunto de Dados EMNIST"));
add(P0("O EMNIST (*Extended MNIST*) [Cohen et al. 2017] é um conjunto de caracteres manuscritos derivado da base NIST Special Database 19, que estende o MNIST para incluir letras. Utiliza-se aqui a divisão *letters*, com 26 classes (maiúsculas e minúsculas fundidas), 124.800 imagens de treino e 20.800 de validação, cada uma em escala de cinza com 28×28 pixels. Por sua padronização e volume, o EMNIST é uma base conveniente para treinar o reconhecimento de letras, ainda que seus traços finos difiram da escrita real capturada por fotografia ou pelo quadro de desenho. Essa diferença é tratada na Seção 3.4 por meio de aumento de dados."));

// 3. Desenvolvimento
add(H1("3. Desenvolvimento"));
add(P0("O desenvolvimento adotou uma abordagem incremental e iterativa, na qual cada funcionalidade foi construída, testada e refinada de forma sucessiva. O código-fonte foi organizado em um pacote Python com três subpacotes, responsáveis pelo núcleo (visão computacional e avaliação), pela nuvem (autenticação e progresso) e pela interface, além de testes automatizados executados a cada alteração por integração contínua."));
add(H2("3.1. Visão Geral da Arquitetura"));
add(P0("O Calligraphos organiza-se em dois aplicativos que compartilham uma mesma infraestrutura de nuvem. O aplicativo desktop, desenvolvido em Python com a biblioteca PyQt5, concentra as funcionalidades completas, incluindo a transcrição e a avaliação por aprendizado de máquina. A aplicação web, desenvolvida em React, oferece uma versão leve voltada ao acompanhamento do progresso e à prática básica de traçado. Ambos autenticam o usuário e persistem o progresso por meio da plataforma Firebase, de modo que a conta e a evolução são as mesmas independentemente do ponto de acesso. A Figura 1 apresenta a arquitetura geral, do pré-processamento à apresentação dos resultados e ao registro do progresso."));
add(figura("fig1_arquitetura.png", 14.5, "Figura 1. Arquitetura geral do sistema Calligraphos"));
add(H2("3.2. Pipeline de Processamento de Imagem"));
add(P0("Antes de qualquer reconhecimento ou avaliação, a imagem de entrada, proveniente de uma fotografia ou do quadro de desenho, passa por um pipeline de pré-processamento implementado com a biblioteca OpenCV [Bradski 2000], cujo objetivo é padronizar a imagem e isolar os caracteres. As etapas são: conversão para escala de cinza; binarização adaptativa, que calcula o limiar localmente e confere robustez a variações de iluminação; remoção de linhas de pauta, por abertura morfológica horizontal; correção de inclinação do plano do papel; detecção das linhas de texto por projeção horizontal; e segmentação de caracteres por contornos, delimitados por caixas envolventes."));
add(P("Dois problemas recorrentes da segmentação receberam tratamento específico. O primeiro é a fragmentação de letras compostas por traços separados, como a barra do A ou o pingo do i: fragmentos que se sobrepõem horizontalmente, ou que são estreitos e estão contidos na altura de uma caixa vizinha, são fundidos em um único caractere. O segundo problema é o oposto: letras encostadas que formam um único contorno. Nesse caso, as caixas mais largas que 1,35 vez a altura são divididas, de forma recursiva, na coluna de menor quantidade de tinta do perfil vertical. A Figura 2 ilustra as etapas sobre uma fotografia real."));
add(figura("fig2_pipeline.png", 15, "Figura 2. Etapas do pré-processamento: (a) imagem original, (b) binarizada e (c) segmentada"));
add(H2("3.3. Transcrição de Texto Manuscrito"));
add(P0("A transcrição é realizada por dois motores complementares. O motor principal é a API Google Cloud Vision, escolhida por seu desempenho consistente com o português e por reconhecer texto de múltiplas palavras e linhas; a API devolve, além do texto, a posição de cada símbolo, o que permite associar cada letra reconhecida à sua região na imagem e, assim, informar ao avaliador qual letra era esperada em cada recorte."));
add(P("Como alternativa offline integrou-se o modelo TrOCR, restrito ao reconhecimento de palavra única. Testes evidenciaram que seu decodificador de linguagem, majoritariamente treinado em inglês, produz transcrições incorretas para sentenças em português; por isso, ao detectar mais de uma palavra com o motor offline selecionado, o sistema sugere a troca para o Google Vision. Quando o serviço em nuvem está indisponível, por falta de conexão ou de credenciais, o módulo de prática recorre à própria rede de legibilidade para reconhecer letras isoladas e ao TrOCR para palavras, com aviso na interface."));

// 3.4 avaliador
add(H2("3.4. Avaliação da Qualidade da Caligrafia"));
add(P0("O componente de avaliação constitui o principal diferencial do Calligraphos. Uma versão inicial derivava rótulos de qualidade a partir da variância de pixels das imagens do EMNIST e treinava uma rede para reproduzi-los; a validação com escrita real mostrou, porém, que a variância mede sobretudo a quantidade de tinta, e não a formação da letra: traçados espessos eram classificados como bons independentemente da forma, e até rabiscos aleatórios recebiam a pontuação máxima. O módulo foi então reformulado como um avaliador híbrido, que combina duas evidências independentes para cada letra recortada: a *legibilidade*, estimada por uma rede neural, e a *formação*, medida geometricamente contra moldes de letra de forma."));
add(P("A parcela de legibilidade provém de uma MobileNetV2 pré-treinada no ImageNet e ajustada para reconhecer qual das 26 letras está na imagem, com o EMNIST e seus rótulos reais. Para aproximar o domínio do EMNIST das letras reais, cada amostra passa por aumento de dados de dilatação e erosão (espessura do traço), rotação, escala, cisalhamento, translação e variação de largura, de modo a cobrir letras condensadas ou estendidas. Treino e inferência compartilham o mesmo pré-processamento: a letra é convertida em máscara binária, recortada em sua caixa envolvente, enquadrada em um quadrado com margem de 10% e redimensionada para 96×96 pixels. Após o treino, a confiança é calibrada por escalonamento de temperatura. A legibilidade de uma letra em relação à letra-alvo L é definida como P(L)·(1 − 0,5·P₂), em que P(L) é a probabilidade calibrada da letra esperada e P₂ a maior probabilidade entre as demais; a penalidade reduz a nota de letras ambíguas, como um A que se assemelha a um O."));
add(P("A parcela de formação compara a letra normalizada com moldes da letra-alvo renderizados a partir de quatro fontes de letra de forma (DejaVu Sans, Liberation Sans, Noto Sans e Noto Serif, esta última a mesma fonte da letra-guia do quadro). Cinco medidas, cada uma mapeada para o intervalo [0, 1] por rampas com tolerâncias configuráveis, compõem essa parcela: (i) *semelhança de forma*, um escore F1 entre precisão e cobertura com tolerância de 2 pixels, calculado após esticar a letra até a caixa do molde e escolhendo o melhor entre pequenos ajustes de escala e deslocamento; (ii) *direção dos traços*, a distância entre os histogramas de orientação dos segmentos de contorno da letra e do molde, que detecta curvas onde o molde possui retas; (iii) *proporção* altura/largura em relação ao molde; (iv) *inclinação*, obtida da direção média dos segmentos quase verticais do contorno, estável para letras simétricas; e (v) *regularidade da espessura*, o coeficiente de variação da largura do traço ao longo de sua crista, calculado pela transformada de distância. A formação é a soma ponderada dessas medidas, com pesos 0,40, 0,20, 0,15, 0,10 e 0,15, respectivamente."));
add(new Paragraph({ alignment: AlignmentType.JUSTIFIED, spacing: { before: 120, after: 0, line: 240 }, indent: { firstLine: cm(1.27) }, children: [
  new TextRun({ text: "A nota final de cada letra é dada por nota = 100 · legibilidade", font: FONTE, size: 24 }),
  new TextRun({ text: "0,5", font: FONTE, size: 24, superScript: true }),
  new TextRun({ text: " · formação", font: FONTE, size: 24 }),
  new TextRun({ text: "1,25", font: FONTE, size: 24, superScript: true }),
  new TextRun({ text: ". A forma multiplicativa torna a legibilidade uma condição necessária, de modo que uma letra irreconhecível nunca obtém nota alta, enquanto a formação determina a magnitude da nota. Esse arranjo é coerente com o critério adotado, segundo o qual uma letra é considerada boa quando se aproxima do molde de letra de forma, e não apenas quando é legível. As categorias são Boa (nota ≥ 75), Aceitável (≥ 50) e Ruim; a pontuação geral de um texto é a média das notas de suas letras. No módulo de prática, uma tentativa é aceita apenas quando a letra é reconhecida como a letra-alvo e obtém nota mínima de 65. Limiares, pesos e expoentes ficam em um arquivo de configuração, permitindo ajustar a exigência sem alterar o código.", font: FONTE, size: 24 }),
] }));
add(H2("3.4.1. Calibração"));
add(P0("Os pesos e limiares foram calibrados com três conjuntos de referência: (a) letras sintéticas, que compreendem letra limpa de fonte, letra cisalhada em 25°, letra com topo arredondado e pernas abertas, rabisco aleatório e letra trocada (O no lugar de A); (b) fotografias de palavras escritas pelo autor em letra de forma; e (c) desenhos feitos no quadro do aplicativo propositalmente de forma descuidada. A calibração buscou que a letra limpa obtivesse nota próxima de 100, que o rabisco e a letra trocada ficassem abaixo de 10, que a letra arredondada, reconhecida corretamente pela rede mas distante do molde, reprovasse no exercício, e que as letras bem formadas das fotografias fossem classificadas como boas. Esses casos foram consolidados em testes automatizados, executados a cada alteração do módulo."));
add(H2("3.4.2. Treinamento e Inferência"));
add(P0("O treinamento executa seis épocas com o otimizador Adam (taxas de 10⁻⁴ para as camadas convolucionais e 10⁻³ para o classificador, com decaimento cosseno), suavização de rótulos de 0,05 e lotes de 128 imagens, em cerca de 15 minutos em uma GPU de notebook (RTX 3050). O modelo, a temperatura e a acurácia de validação são salvos em um único arquivo, carregado uma vez durante a execução. Na inferência, as letras são avaliadas em lote na GPU, quando disponível, e os moldes de cada letra são renderizados uma única vez e mantidos em cache. Além da nota, o avaliador devolve a letra prevista, as parcelas de legibilidade e formação e as cinco medidas, que a interface apresenta em barras no detalhe de cada letra e usa para explicar o principal problema encontrado (\"muito inclinada\", \"com curvas onde o molde tem traços retos\"). No módulo de prática, um *mapa de diferenças* projeta o molde sobre a letra escrita, colorindo em verde o traço que coincide com o molde, em vermelho o que se afasta dele e em azul-claro as regiões do molde sem traço."));

// 3.5 interface
add(H2("3.5. Interface Gráfica e Módulo de Prática"));
add(P0("A interface do aplicativo desktop foi organizada em dois modos principais, Análise Individual e Prática Guiada, acessíveis a partir de uma tela inicial, que também exibe a meta diária e as letras a revisar. Bibliotecas pesadas são pré-carregadas em segundo plano durante a tela de abertura, eliminando a demora ao entrar nos modos."));
add(P0("No modo de Análise Individual, o usuário escreve em um quadro de desenho ou carrega uma fotografia. Após o processamento, o sistema exibe o texto transcrito, a pontuação geral e a imagem anotada, com cada letra contornada em verde, âmbar ou vermelho (Figura 3). O clique em uma letra abre seu detalhe, com a nota, as parcelas e as cinco medidas em barras; o usuário pode ainda corrigir manualmente as letras detectadas e exportar um relatório."));
add(figura("fig4_analise.png", 12.5, "Figura 3. Resultado de uma análise: imagem anotada, pontuação geral e detalhe por letra"));
add(P0("No modo de Prática Guiada, organizado em abas, a aba de Letras apresenta as 26 letras em uma grade com o nível de domínio de cada uma; a de Palavras oferece fases progressivas e palavras personalizadas; a de Quiz sorteia letras ou palavras; a de Dicionário permite consultar significados e adicionar palavras ao treino; e a de Progresso reúne os indicadores de evolução."));
add(P0("Ao praticar uma letra, o alvo é exibido de forma tênue ao fundo do quadro, permitindo traçar por cima, à semelhança de um caderno de caligrafia; a guia é apenas visual e nunca é incorporada à imagem analisada. Após o envio, o quadro dá lugar ao mapa de diferenças, e a mensagem de retorno informa a nota e o principal motivo em caso de reprovação (Figura 4)."));
add(figura("fig6_exercicio.png", 12.5, "Figura 4. Exercício de letra após a verificação: mapa de diferenças entre o traço e o molde e retorno com a nota"));
add(H2("3.5.1. Progresso, Metas e Histórico de Evolução"));
add(P0("Para cada letra mantém-se um nível de domínio que avança conforme os acertos. A aba de Progresso apresenta um anel de desempenho, estatísticas, um mapa de calor do alfabeto e as conquistas. Cada verificação, aprovada ou não, grava a nota obtida em um histórico; a partir dele, a aba exibe um gráfico da média diária nos últimos 30 dias, com as faixas Boa, Aceitável e Ruim ao fundo, a comparação da semana atual com a anterior e as letras com pior média recente. Para estimular a regularidade, o sistema adota uma meta diária configurável, contabiliza uma sequência de dias consecutivos (*streak*) e sugere a revisão de letras em intervalos crescentes conforme o nível de domínio."));
add(H2("3.6. Autenticação e Persistência de Dados"));
add(P0("A autenticação utiliza o Firebase Authentication (e-mail e senha), e o progresso de cada usuário é persistido no Cloud Firestore, um banco de dados NoSQL orientado a documentos. Cada usuário corresponde a um documento identificado por seu identificador único, com os níveis das letras, as fases concluídas, as palavras personalizadas, as estatísticas, as conquistas e o histórico de notas. Como aplicativo e site acessam o mesmo documento, o progresso é compartilhado de forma transparente. A sessão é mantida localmente, dispensando novo login a cada abertura; as credenciais sensíveis ficam fora do repositório de código, e as regras de segurança do Firestore restringem o acesso de cada usuário ao seu próprio documento. Falhas de rede são registradas em um arquivo de log e nunca sobrescrevem o progresso salvo."));
add(H2("3.7. Aplicação Web Complementar"));
add(P0("A aplicação web, desenvolvida em React com a ferramenta Vite, segue o modelo de plataformas de estudo que oferecem uma interface web reduzida ao lado de um aplicativo completo. Sua parte pública organiza-se nas abas de início, como funciona, recursos, sobre e download; a área autenticada apresenta o painel de progresso, com o mesmo gráfico de evolução do aplicativo, e a prática de letras por traçado. Nessa prática, a verificação é puramente geométrica: o traço do usuário é comparado ponto a ponto contra a máscara da letra-molde, o que mantém a aplicação leve e executável inteiramente no navegador."));

// 4. Resultados
add(H1("4. Resultados e Discussão"));
add(H2("4.1. Sistema Desenvolvido"));
add(P0("O principal resultado do trabalho é um sistema completo e funcional, capaz de receber uma imagem de texto manuscrito, transcrevê-la, avaliar a formação de cada letra, explicar o motivo da avaliação e oferecer um ambiente estruturado de prática com histórico de evolução, sincronizado entre o aplicativo e a aplicação web."));
add(P("A rede de legibilidade alcançou 93,9% de acurácia no conjunto de validação do EMNIST (20.800 imagens), com temperatura de calibração de 0,74. A Tabela 1 resume o comportamento do avaliador híbrido nos casos de referência usados na calibração. A letra limpa recebe nota próxima de 100. A letra arredondada, que a rede reconhece corretamente como A mas cuja forma se afasta do molde, reprova no exercício, e a medida de direção dos traços é apontada como principal problema. O rabisco e a letra trocada ficam abaixo de 10. Nas fotografias de escrita do autor, as letras bem formadas obtiveram notas entre 77 e 86 (Boa), enquanto os desenhos descuidados do quadro variaram de 42 a 90 conforme a letra."));
add(legendaTabela("Tabela 1. Notas do avaliador híbrido nos casos de referência (alvo: letra A)"));
add(tabela(["Caso", "Legibilidade", "Formação", "Nota", "Categoria"], [
  ["Letra limpa de fonte (não usada como molde)", "1,00", "0,99", "99,9", "Boa"],
  ["Letra bem formada em fotografia (média)", "0,97", "0,83", "77–86", "Boa"],
  ["A arredondado, pernas abertas (desenho)", "0,99", "0,66", "59,4", "Aceitável"],
  ["A descuidado no quadro (\"ALGO\")", "1,00", "0,49", "41,9", "Ruim"],
  ["Letra cisalhada em 25°", "0,98", "0,43", "34,4", "Ruim"],
  ["Rabisco aleatório", "0,00", "0,46", "1,9", "Ruim"],
  ["Letra O no lugar de A", "0,00", "0,40", "0,8", "Ruim"],
], [5.7, 2.7, 2.1, 1.5, 2.6]));
add(H2("4.2. Diferencial em Relação a Outras Plataformas"));
add(P0("Plataformas populares de aprendizado, voltadas à aquisição de idiomas, avaliam vocabulário, gramática e pronúncia, mas não a caligrafia. O Calligraphos distingue-se por concentrar-se na formação física das letras: fornece retorno no nível de cada letra, e não da palavra, tem como entrada a escrita real, produzida à mão ou na tela, e explica o que precisa melhorar. A Tabela 2 sintetiza as diferenças. Seu público-alvo abrange estudantes em fase de alfabetização, pessoas que desejam aprimorar a própria letra e educadores interessados em acompanhar a evolução da escrita de seus alunos."));
add(legendaTabela("Tabela 2. Comparação entre plataformas de idioma e o Calligraphos"));
add(tabela(["Aspecto", "Plataformas de idioma", "Calligraphos"], [
  ["Foco", "Vocabulário, gramática e pronúncia", "Formação física da letra"],
  ["Feedback", "Certo ou errado, no nível da palavra", "Nota e motivo para cada letra"],
  ["Entrada", "Digitação ou seleção de opções", "Escrita real, à mão ou na tela"],
  ["Aplicação", "Aprender um idioma novo", "Melhorar a letra em qualquer idioma"],
], [3.0, 5.8, 5.8]));
add(H2("4.3. Principais Desafios e Decisões de Projeto"));
add(P0("O desenvolvimento envolveu a superação de desafios cujas soluções ilustram o caráter empírico e iterativo do processo:"));
add(item("O critério inicial de avaliação, baseado na variância de pixels, aprovava qualquer traço espesso. A substituição por um avaliador híbrido, com rótulos reais na rede e medidas geométricas verificáveis, tornou a nota sensível à forma;", "bul2"));
add(item("A rede treinada apenas com os traços finos do EMNIST errava letras condensadas ou espessas. O aumento de dados de espessura e largura elevou a legibilidade das letras reais de fotografia de valores próximos de zero para acima de 0,95 em vários casos;", "bul2"));
add(item("Na segmentação de fotografias, letras encostadas e fragmentos de letras vizinhas prejudicavam o reconhecimento. A divisão no vale do perfil de tinta, a fusão de fragmentos contidos e a limpeza de componentes de borda resolveram os casos observados;", "bul2"));
add(item("O reconhecimento offline em português mostrou-se limitado, pois o TrOCR produzia transcrições incorretas para sentenças. Adotou-se o Google Vision como motor principal, mantendo o TrOCR para palavra única e como recurso quando a nuvem está indisponível;", "bul2"));
add(item("Para a sincronização entre aplicativo e web, a adoção de um mesmo documento Firestore por usuário permitiu que as duas aplicações compartilhassem o progresso e o histórico de forma transparente.", "bul2"));
add(H2("4.4. Limitações"));
add(P0("A parcela de formação compara a letra com moldes tipográficos de letra de forma; estilos pessoais legítimos, como a escrita condensada, podem perder pontos, sobretudo na medida de proporção, ainda que os pesos sejam ajustáveis. A calibração do avaliador foi feita com casos sintéticos e com um número reduzido de amostras reais do próprio autor; uma validação com letras de múltiplos escritores, rotuladas por avaliadores humanos, é o passo natural para quantificar a concordância do sistema com o julgamento humano. A segmentação de fotografias ainda pode falhar quando os caracteres estão muito próximos ou sob iluminação muito irregular. Por fim, o motor offline é otimizado para o inglês e restrito a palavra única, e o sistema foi desenvolvido e validado para texto em letra de forma."));

// 5. Consideracoes finais
add(H1("5. Considerações Finais"));
add(P0("Este trabalho apresentou o desenvolvimento do Calligraphos, um sistema de reconhecimento e avaliação de caligrafia que integra visão computacional, aprendizado de máquina, interface gráfica e sincronização em nuvem. Os objetivos propostos foram alcançados: o sistema transcreve texto manuscrito, avalia a formação de cada letra com uma nota justificada, mostra visualmente onde o traço se afasta do molde e oferece um ambiente de prática guiada com progresso e histórico sincronizados entre um aplicativo desktop e uma aplicação web."));
add(P("Cabe registrar uma lição metodológica obtida ao longo do projeto. A primeira versão do avaliador, ainda que treinasse uma rede neural, não media aquilo a que se propunha, e apenas a validação com escrita real revelou o problema. Na reformulação, atribuiu-se à rede a tarefa de reconhecer letras e às medidas geométricas a descrição da forma, da proporção e da inclinação. O resultado é um sistema cujo critério pode ser verificado e cuja nota vem acompanhada da justificativa correspondente."));
add(P("Como trabalhos futuros, propõem-se: a coleta de letras de múltiplos escritores rotuladas por avaliadores humanos, para medir a concordância do avaliador e ajustar seus pesos a partir de dados; a publicação de um pacote instalável; a evolução da aplicação web para um aplicativo web progressivo (PWA), instalável em dispositivos móveis, apoiado por um serviço que exponha o avaliador existente; e a realização de avaliações com usuários reais, a fim de medir o impacto pedagógico da ferramenta sobre a evolução da caligrafia."));

add(H1("Agradecimentos"));
add(P0("Agradeço ao meu orientador, Prof. Antonio Paulo Salgado Forster, pela orientação criteriosa e pelo apoio ao longo de todo o desenvolvimento deste trabalho, e à Pontifícia Universidade Católica de Campinas pela estrutura e pelos recursos disponibilizados. Agradeço também à minha família e aos amigos pelo incentivo constante."));

add(H1("Referências"));
add(ref("Bradski, G. (2000) \"The OpenCV Library\", Dr. Dobb's Journal of Software Tools."));
add(ref("Cohen, G., Afshar, S., Tapson, J. and van Schaik, A. (2017) \"EMNIST: an extension of MNIST to handwritten letters\", In: International Joint Conference on Neural Networks (IJCNN), p. 2921–2926."));
add(ref("Goodfellow, I., Bengio, Y. and Courville, A. (2016) \"Deep Learning\", MIT Press, Cambridge."));
add(ref("Guo, C., Pleiss, G., Sun, Y. and Weinberger, K. Q. (2017) \"On Calibration of Modern Neural Networks\", In: Proceedings of the 34th International Conference on Machine Learning (ICML), PMLR 70, p. 1321–1330."));
add(ref("Li, M., Lv, T., Cui, L., Lu, Y., Florencio, D., Zhang, C., Li, Z. and Wei, F. (2021) \"TrOCR: Transformer-based Optical Character Recognition with Pre-trained Models\", arXiv:2109.10282."));
add(ref("Memon, J., Sami, M., Khan, R. A. and Uddin, M. (2020) \"Handwritten Optical Character Recognition (OCR): A Comprehensive Systematic Literature Review (SLR)\", IEEE Access, v. 8, p. 142642–142668."));
add(ref("Paszke, A., Gross, S., Massa, F. et al. (2019) \"PyTorch: An Imperative Style, High-Performance Deep Learning Library\", In: Advances in Neural Information Processing Systems (NeurIPS), v. 32."));
add(ref("Sandler, M., Howard, A., Zhu, M., Zhmoginov, A. and Chen, L. (2018) \"MobileNetV2: Inverted Residuals and Linear Bottlenecks\", In: IEEE Conference on Computer Vision and Pattern Recognition (CVPR), p. 4510–4520."));

// ── documento ────────────────────────────────────────────────────────────
const doc = new Document({
  creator: "Lucca Vasconcelos Costa Oliveira",
  title: "Calligraphos: Sistema de Reconhecimento e Avaliação de Caligrafia Baseado em Aprendizado de Máquina",
  styles: { default: { document: { run: { font: FONTE, size: 24 } } } },
  numbering: {
    config: [
      { reference: "num1", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: cm(1.27), hanging: cm(0.63) } } } }] },
      { reference: "bul1", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: cm(1.27), hanging: cm(0.63) } } } }] },
      { reference: "bul2", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: cm(1.27), hanging: cm(0.63) } } } }] },
    ],
  },
  sections: [{
    properties: {
      page: {
        size: { width: 11906, height: 16838 },   // A4
        margin: { top: cm(3.5), bottom: cm(2.5), left: cm(3.0), right: cm(3.0) },
      },
    },
    children: filhos,
  }],
});

Packer.toBuffer(doc).then((buf) => { fs.writeFileSync(OUT, buf); console.log("gravado", OUT); });
