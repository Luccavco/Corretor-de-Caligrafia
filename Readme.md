# Corretor de Caligrafia

Sistema de reconhecimento e avaliação de texto manuscrito desenvolvido como Trabalho de Conclusão de Curso (TCC).

O programa recebe uma foto de texto escrito à mão em letra de forma, transcreve o conteúdo para texto digital e avalia a qualidade da caligrafia de cada letra detectada.

---

## Como funciona

1. O usuário carrega uma foto de texto manuscrito pela interface
2. O sistema aplica pré-processamento de imagem para limpar e normalizar a foto
3. O modelo TrOCR (Microsoft) transcreve o texto manuscrito para texto digital
4. Uma rede neural convolucional (CNN) avalia a qualidade de cada letra
5. O resultado é exibido na tela com pontuação geral e feedback por letra

---

## Requisitos

- Python 3.11
- GPU NVIDIA recomendada (funciona em CPU, porém mais lento)
- Conexão com internet na primeira execução (para baixar o modelo TrOCR)

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

## Como usar

### Interface gráfica
```
python main_ui.py
```
1. Clique em **Carregar Imagem** e selecione uma foto de texto manuscrito
2. Clique em **Transcrever e Avaliar**
3. O texto reconhecido e a avaliação de caligrafia aparecerão no painel direito

### Testes automáticos
```
python test_pipeline.py
```
Roda o pipeline completo em todas as imagens da pasta `test_images/` e exibe os resultados no terminal.

### Retreinar o modelo
```
python train_cnn.py
```
Baixa o dataset EMNIST e retreina a CNN de avaliação de caligrafia. O modelo treinado é salvo em `modelo_caligrafia.pth`.

---

## Estrutura do projeto

```
├── main_ui.py               # Interface gráfica (PyQt5)
├── image_pipeline.py        # Pré-processamento de imagem (OpenCV)
├── htr_engine.py            # Reconhecimento de texto (TrOCR)
├── handwriting_evaluator.py # Avaliação de caligrafia (CNN)
├── train_cnn.py             # Script de treino da CNN
├── test_pipeline.py         # Testes automáticos
├── requirements.txt         # Dependências do projeto
├── modelo_caligrafia.pth    # Modelo treinado (gerado pelo train_cnn.py)
└── test_images/             # Imagens de teste
```

---

## Limitações conhecidas

- O sistema foi desenvolvido para texto em **letra de forma maiúscula**
- Letra cursiva não é suportada
- A avaliação de caligrafia é baseada em variância de pixels — letras com traço muito fino podem ser classificadas como boas mesmo com formação irregular
- O modelo TrOCR é otimizado para inglês, podendo ter dificuldade com caracteres especiais do português (ã, ç, é)
- Fotos com iluminação muito irregular ou sombra forte podem reduzir a precisão da transcrição

---

## Tecnologias utilizadas

O projeto foi construído com Python 3.11 e utiliza as seguintes bibliotecas principais:

O OpenCV cuida de todo o pré-processamento das imagens antes de enviá-las para a IA, aplicando filtros de binarização e correção de perspectiva. 
O modelo TrOCR da Microsoft, carregado via biblioteca Transformers do Hugging Face, é responsável por transcrever o texto manuscrito para texto digital. 
O PyTorch serve como framework base para a rede neural convolucional de avaliação de caligrafia, que utiliza a arquitetura MobileNetV2 com Transfer Learning. 
A interface gráfica foi construída com PyQt5, e o dataset EMNIST foi utilizado para o treino da CNN.
