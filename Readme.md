# Calligraphos — Reconhecimento e Avaliação de Caligrafia

[![testes](https://github.com/Luccavco/Corretor-de-Caligrafia/actions/workflows/testes.yml/badge.svg)](https://github.com/Luccavco/Corretor-de-Caligrafia/actions/workflows/testes.yml)

Sistema de reconhecimento e avaliação de texto manuscrito desenvolvido como Trabalho de Conclusão de Curso (TCC).

O Calligraphos tem dois objetivos centrais: **transcrever** texto escrito à mão (de uma palavra a uma redação com várias linhas) para texto digital, e **avaliar a qualidade da caligrafia** letra por letra, destacando quais estão bem formadas e quais precisam melhorar. Além da análise, o programa traz um modo de **prática guiada** com exercícios, progresso salvo, sequência diária e conquistas, para quem quer treinar e aperfeiçoar a própria letra.

O projeto é composto por um **aplicativo desktop** (Python + PyQt5) e um **site web** complementar (React), que compartilham a mesma conta e o mesmo progresso.

---

## Recursos

**Análise de caligrafia**
- Transcrição de texto manuscrito via Google Cloud Vision (motor principal, online) ou TrOCR (motor offline para palavra única)
- Avaliação de cada letra com nota 0–100: legibilidade (CNN MobileNetV2 treinada no EMNIST, calibrada) combinada com formação geométrica contra moldes de letra de forma (semelhança, proporção, inclinação, regularidade do traço)
- Imagem anotada: cada letra é contornada na cor da sua classificação (verde, âmbar ou vermelho)
- Correção manual: adicionar, remover ou corrigir letras detectadas
- Exportação de relatório da análise

**Prática guiada**
- Letras: pratica as 26 letras do alfabeto com progresso por nível
- Palavras: fases progressivas e lista de palavras personalizadas
- Quiz: exercícios com itens sorteados aleatoriamente
- Dicionário: busca de significados e adição de palavras ao treino
- Quadro de desenho com letra-guia transparente para traçar por cima
- Progresso: anel de desempenho, mapa de calor do alfabeto, sequência diária (streak) e conquistas

**Conta e sincronização**
- Login com Firebase (mesma conta no aplicativo e no site)
- Progresso salvo na nuvem (Firestore) e sincronizado entre dispositivos
- Meta diária com lembrete pela bandeja do sistema

---

## Como funciona a análise

1. O usuário escreve no quadro de desenho ou carrega uma foto de texto manuscrito
2. O pré-processamento (OpenCV) limpa e normaliza a imagem
3. O texto é transcrito para digital (Google Vision ou TrOCR)
4. Cada letra detectada é recortada e recebe uma nota: a CNN diz o quanto ela é legível como a letra esperada, e medidas geométricas comparam a forma com moldes de letra de forma
5. O resultado aparece na tela: texto transcrito, pontuação geral, detalhe por letra e a imagem com cada letra contornada na cor da sua avaliação

---

## Requisitos

- Python 3.11
- GPU NVIDIA recomendada (funciona em CPU, porém mais lento)
- Conexão com internet (para o Google Vision e a sincronização com o Firebase)
- Credenciais do Google Cloud Vision e do Firebase (ver seção Configuração)

---

## Instalação

### Pelo pacote (recomendado)

Baixe `Calligraphos-<versão>-linux.zip` na página de [Releases](https://github.com/Luccavco/Corretor-de-Caligrafia/releases), extraia e rode:
```
./instalar.sh
```
O instalador cria o ambiente virtual, instala as dependências e registra o atalho "Calligraphos" no menu de aplicativos. Depois, coloque as credenciais (seção Configuração) na pasta e abra com `./calligraphos.sh`.

### Pelo código-fonte

Clone o repositório:
```
git clone https://github.com/Luccavco/Corretor-de-Caligrafia.git
cd Corretor-de-Caligrafia
```

Crie e ative o ambiente virtual:
```
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows
```

Instale as dependências:
```
pip install -r requirements.txt
```

---

## Configuração

O aplicativo depende de dois serviços externos, cujas credenciais **não** ficam no repositório (são ignoradas pelo `.gitignore`):

- **Google Cloud Vision**: coloque o arquivo de credenciais da conta de serviço como `google_credentials.json` na raiz do projeto.
- **Firebase**: coloque a chave de admin do Firestore como `firebase_credentials.json` na raiz do projeto. A chave pública (apiKey) do login já está em `firebase_config.py`.

Sem esses arquivos, o app abre, mas o login não funciona. Sem o Google Vision (ou sem internet), o exercício e a análise passam automaticamente para o reconhecimento local (CNN para letras isoladas, TrOCR para palavras), com aviso na tela.

---

## Ajustes (`config.json`)

Os limiares da nota (Boa/Aceitável), a nota mínima para acertar no exercício, os pesos das medidas de formação e o motor de HTR padrão ficam em `config.json`, na raiz do projeto. Edite o arquivo e reabra o app — não é preciso mexer no código. Os valores padrão estão em `config.py`.

Erros e avisos ficam registrados em `calligraphos.log` (rotativo), útil para diagnosticar problemas relatados por outros usuários.

---

## Como usar

### Aplicativo
```
python -m calligraphos
```
(`python main_ui.py` continua funcionando como atalho.)
Faça login (ou crie uma conta), e use os dois modos principais:
- **Analisar**: escreva no quadro ou carregue uma foto e veja a transcrição e a avaliação da caligrafia.
- **Praticar**: treine letras e palavras, faça quizzes, consulte o dicionário e acompanhe seu progresso.

### Retreinar o modelo de avaliação
```
python -m calligraphos.nucleo.train_cnn
```
Baixa o dataset EMNIST (split *letters*, 26 classes) e treina a CNN de legibilidade com augmentation de espessura, rotação, escala e cisalhamento (para aproximar o EMNIST das letras reais). Ao final calibra a confiança (temperatura) e imprime a acurácia de validação. O modelo é salvo em `modelo_caligrafia.pth`.

Testes do avaliador (letras sintéticas):
```
python tests/test_letra_prep.py
python tests/test_formacao.py
python tests/test_avaliador.py
python tests/test_api.py
```

---

## Serviço HTTP (API)

O avaliador também pode ser usado por outros clientes (o site instalado no celular, por exemplo) sem duplicar código:
```
python -m calligraphos.api
```
Sobe em `http://localhost:8000` (documentação interativa em `/docs`). Para hospedar, há um `Dockerfile` (CPU, sem interface gráfica) e o guia em `../HOSPEDAGEM.md`. `POST /avaliar` recebe a imagem e a letra/palavra esperada e devolve as notas por letra, o texto, a imagem anotada e o mapa de diferenças.

---

## Site web

O site (pasta `calligraphos-web/`) é uma versão leve, no estilo do AnkiWeb: a pessoa entra com a mesma conta do aplicativo, acompanha o progresso e pratica o básico por *tracing* (traçar sobre um molde, com verificação geométrica, sem IA). Os recursos pesados (transcrição e avaliação) ficam apenas no aplicativo.

```
cd calligraphos-web
npm install
npm run dev
```

---

## Estrutura do projeto

```
├── calligraphos/                 # Pacote do aplicativo (python -m calligraphos)
│   ├── __main__.py               # Ponto de entrada
│   ├── caminhos.py               # Caminhos dos arquivos da raiz (modelo, config, credenciais)
│   ├── config.py                 # Leitura do config.json (padrões embutidos)
│   ├── log_config.py             # Logging em calligraphos.log
│   ├── api.py                    # Serviço HTTP do avaliador (FastAPI)
│   ├── nucleo/                   # Visão computacional e avaliação
│   │   ├── image_pipeline.py     #   Pré-processamento e segmentação (OpenCV)
│   │   ├── letra_prep.py         #   Normalização de letras (treino e inferência)
│   │   ├── formacao.py           #   Medidas geométricas contra moldes de letra de forma
│   │   ├── feedback_visual.py    #   Mapa de diferenças letra × molde
│   │   ├── handwriting_evaluator.py  # Nota por letra: legibilidade (CNN) + formação
│   │   ├── modelo_cnn.py         #   Arquitetura da CNN (MobileNetV2, 26 classes)
│   │   ├── train_cnn.py          #   Treino da CNN (python -m calligraphos.nucleo.train_cnn)
│   │   ├── htr_google.py         #   Transcrição via Google Cloud Vision
│   │   └── htr_engine.py         #   Transcrição via TrOCR (offline)
│   ├── nuvem/                    # Conta e dados
│   │   ├── firebase_config.py    #   Configuração do Firebase
│   │   ├── auth_service.py       #   Autenticação e sessão persistente
│   │   ├── progresso.py          #   Progresso e histórico do usuário no Firestore
│   │   └── dicionario_service.py #   Busca de definições
│   └── ui/                       # Interface (PyQt5)
│       ├── main_ui.py            #   Janela principal, splash e fluxo do app
│       ├── login_widget.py, onboarding_widget.py, config_widget.py
│       ├── analise/              #   Modo Análise Individual (widget, worker, componentes, diálogos)
│       ├── praticar/             #   Modo Praticar (abas, cartões, painel de exercício, constantes)
│       ├── canvas_desenho.py     #   Quadro de desenho com letra-guia
│       ├── detalhe_letra_dialog.py, sobre_dialog.py
│       ├── anel_progresso.py, grafico_evolucao.py
│       └── ui_helpers.py, ui_theme.py
├── tests/                        # test_letra_prep, test_formacao, test_avaliador, test_api
├── scripts/                      # gerar_figura2.py (artigo), testar_pipeline.py, empacotar.sh (release)
├── instalar.sh                   # Instalador do pacote distribuído
├── main_ui.py                    # Atalho de compatibilidade (chama o pacote)
├── config.json                   # Ajustes (limiares, pesos, motor padrão)
├── requirements.txt / pyproject.toml
├── modelo_caligrafia.pth         # Modelo treinado (gerado pelo train_cnn)
└── calligraphos-web/             # Site web complementar (React)
```

## Detalhes técnicos

O pipeline de imagem detecta automaticamente as linhas de texto por projeção horizontal, o que permite processar redações e parágrafos inteiros mantendo a ordem de leitura. Fragmentos de letras (como a barra do A ou o pingo do i) são unidos de volta ao corpo da letra por análise de sobreposição, em vez de contados como caracteres separados. A avaliação das letras roda em lote na GPU para manter o tempo de resposta baixo mesmo em textos longos, e as bibliotecas pesadas são pré-carregadas em segundo plano durante a tela de abertura, para eliminar a demora ao entrar nos modos de análise e prática.

Para o reconhecimento, o Google Cloud Vision é o motor principal, por lidar bem com português e com texto de várias palavras; o TrOCR fica disponível como opção offline para palavra única.

---

## Limitações conhecidas

- O sistema foi desenvolvido para texto em **letra de forma**
- A parcela de formação da nota compara a letra com moldes de fontes de letra de forma; estilos pessoais válidos podem perder pontos. Os pesos e limiares são ajustáveis em `config.json`
- O motor offline (TrOCR) é otimizado para inglês e serve apenas para palavra única; para texto em português e frases, use o Google Vision
- Fotos com iluminação muito irregular ou sombra forte podem reduzir a precisão da transcrição

---

## Tecnologias utilizadas

O projeto foi construído com Python 3.11. O OpenCV cuida do pré-processamento das imagens (binarização, correção de perspectiva e segmentação de linhas e caracteres). A transcrição usa o Google Cloud Vision (principal) e o TrOCR da Microsoft via Transformers do Hugging Face (offline). A avaliação de caligrafia combina uma CNN (PyTorch, MobileNetV2 com Transfer Learning, treinada para reconhecer as 26 letras do EMNIST e calibrada por temperatura) com medidas geométricas em OpenCV contra moldes de letra de forma. A interface é feita em PyQt5, a autenticação e o armazenamento em nuvem usam o Firebase (Authentication e Firestore), e o site complementar é feito em React com Vite.
