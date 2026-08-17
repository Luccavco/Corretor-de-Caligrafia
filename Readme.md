# Calligraphos — Reconhecimento e Avaliação de Caligrafia

Sistema de reconhecimento e avaliação de texto manuscrito desenvolvido como Trabalho de Conclusão de Curso (TCC).

O Calligraphos tem dois objetivos centrais: **transcrever** texto escrito à mão (de uma palavra a uma redação com várias linhas) para texto digital, e **avaliar a qualidade da caligrafia** letra por letra, destacando quais estão bem formadas e quais precisam melhorar. Além da análise, o programa traz um modo de **prática guiada** com exercícios, progresso salvo, sequência diária e conquistas, para quem quer treinar e aperfeiçoar a própria letra.

O projeto é composto por um **aplicativo desktop** (Python + PyQt5) e um **site web** complementar (React), que compartilham a mesma conta e o mesmo progresso.

---

## Recursos

**Análise de caligrafia**
- Transcrição de texto manuscrito via Google Cloud Vision (motor principal, online) ou TrOCR (motor offline para palavra única)
- Avaliação da qualidade de cada letra por uma rede neural (CNN MobileNetV2)
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
4. Cada letra detectada é recortada e avaliada pela CNN
5. O resultado aparece na tela: texto transcrito, pontuação geral, detalhe por letra e a imagem com cada letra contornada na cor da sua avaliação

---

## Requisitos

- Python 3.11
- GPU NVIDIA recomendada (funciona em CPU, porém mais lento)
- Conexão com internet (para o Google Vision e a sincronização com o Firebase)
- Credenciais do Google Cloud Vision e do Firebase (ver seção Configuração)

---

## Instalação

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

Sem esses arquivos, o app abre, mas a transcrição online e o login não funcionam.

---

## Como usar

### Aplicativo
```
python main_ui.py
```
Faça login (ou crie uma conta), e use os dois modos principais:
- **Analisar**: escreva no quadro ou carregue uma foto e veja a transcrição e a avaliação da caligrafia.
- **Praticar**: treine letras e palavras, faça quizzes, consulte o dicionário e acompanhe seu progresso.

### Retreinar o modelo de avaliação
```
python train_cnn.py
```
Baixa o dataset EMNIST e treina a CNN de avaliação. Os limiares de qualidade são calibrados automaticamente a partir da distribuição real dos dados. O modelo é salvo em `modelo_caligrafia.pth`.

Para inspecionar a calibração antes de treinar:
```
python diagnostico_variancia.py
```

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
├── main_ui.py                # Janela principal e fluxo do app (PyQt5)
├── login_widget.py           # Tela de login/cadastro
├── onboarding_widget.py      # Introdução na primeira execução
├── analise_widget.py         # Modo Análise Individual
├── praticar_widget.py        # Modo Praticar (letras, palavras, quiz, dicionário, progresso)
├── config_widget.py          # Configurações
├── canvas_desenho.py         # Quadro de desenho com letra-guia
├── ui_helpers.py             # Utilitários de interface compartilhados
├── ui_theme.py               # Cores e estilos
│
├── image_pipeline.py         # Pré-processamento e segmentação (OpenCV)
├── htr_google.py             # Transcrição via Google Cloud Vision
├── htr_engine.py             # Transcrição via TrOCR (offline)
├── handwriting_evaluator.py  # Avaliação de caligrafia em lote (CNN)
├── train_cnn.py              # Treino da CNN
├── diagnostico_variancia.py  # Inspeção da calibração de qualidade
│
├── auth_service.py           # Autenticação e sessão persistente
├── firebase_config.py        # Configuração do Firebase
├── progresso.py              # Progresso do usuário no Firestore
├── dicionario_service.py     # Busca de definições
│
├── requirements.txt          # Dependências do projeto
├── modelo_caligrafia.pth     # Modelo treinado (gerado pelo train_cnn.py)
└── calligraphos-web/         # Site web complementar (React)
```

---

## Detalhes técnicos

O pipeline de imagem detecta automaticamente as linhas de texto por projeção horizontal, o que permite processar redações e parágrafos inteiros mantendo a ordem de leitura. Fragmentos de letras (como a barra do A ou o pingo do i) são unidos de volta ao corpo da letra por análise de sobreposição, em vez de contados como caracteres separados. A avaliação das letras roda em lote na GPU para manter o tempo de resposta baixo mesmo em textos longos, e as bibliotecas pesadas são pré-carregadas em segundo plano durante a tela de abertura, para eliminar a demora ao entrar nos modos de análise e prática.

Para o reconhecimento, o Google Cloud Vision é o motor principal, por lidar bem com português e com texto de várias palavras; o TrOCR fica disponível como opção offline para palavra única.

---

## Limitações conhecidas

- O sistema foi desenvolvido para texto em **letra de forma**
- A avaliação de caligrafia é baseada na variância de pixels da letra; a calibração usa o dataset EMNIST, então letras reais (mais grossas que as do EMNIST) podem ainda ser avaliadas de forma mais branda que o ideal
- O motor offline (TrOCR) é otimizado para inglês e serve apenas para palavra única; para texto em português e frases, use o Google Vision
- Fotos com iluminação muito irregular ou sombra forte podem reduzir a precisão da transcrição

---

## Tecnologias utilizadas

O projeto foi construído com Python 3.11. O OpenCV cuida do pré-processamento das imagens (binarização, correção de perspectiva e segmentação de linhas e caracteres). A transcrição usa o Google Cloud Vision (principal) e o TrOCR da Microsoft via Transformers do Hugging Face (offline). A avaliação de caligrafia usa PyTorch com a arquitetura MobileNetV2 e Transfer Learning, treinada sobre o EMNIST. A interface é feita em PyQt5, a autenticação e o armazenamento em nuvem usam o Firebase (Authentication e Firestore), e o site complementar é feito em React com Vite.
