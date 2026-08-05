# CaligrafIA — Corretor de Caligrafia

Sistema de reconhecimento e avaliação de texto manuscrito desenvolvido como Trabalho de Conclusão de Curso (TCC).

O programa recebe uma foto de texto escrito à mão em letra de forma — de uma palavra a uma redação inteira com várias linhas — transcreve o conteúdo para texto digital e avalia a qualidade da caligrafia de cada letra detectada, destacando visualmente na imagem quais letras estão bem formadas e quais precisam melhorar.

---

## Como funciona

1. O usuário carrega uma foto pela interface (botão ou arrastando o arquivo)
2. O sistema aplica pré-processamento de imagem para limpar e normalizar a foto
3. As linhas de texto são detectadas e separadas automaticamente
4. O modelo TrOCR (Microsoft) transcreve cada linha para texto digital
5. Uma rede neural convolucional (CNN) avalia a qualidade de cada letra
6. O resultado aparece na tela: texto transcrito, pontuação geral, detalhe por letra e a imagem com cada letra contornada na cor da sua classificação (verde, âmbar ou vermelho)

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

Treine o modelo de avaliação (apenas na primeira vez):
```
python train_cnn.py
```

---

## Como usar

### Interface gráfica
```
python main_ui.py
```
1. Carregue uma foto de texto manuscrito (botão **Carregar Imagem** ou arraste o arquivo para a janela)
2. Clique em **Analisar**
3. O painel direito mostra a pontuação geral, o texto reconhecido e o detalhe por letra; a imagem exibe cada letra contornada na cor da sua avaliação
4. Use **Copiar Texto** para copiar a transcrição ou **Salvar Relatório** para exportar a análise completa em .txt

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
├── image_pipeline.py        # Pré-processamento e segmentação (OpenCV)
├── htr_engine.py            # Reconhecimento de texto por linha (TrOCR)
├── handwriting_evaluator.py # Avaliação de caligrafia em lote (CNN)
├── train_cnn.py             # Script de treino da CNN
├── test_pipeline.py         # Testes automáticos
├── requirements.txt         # Dependências do projeto
├── modelo_caligrafia.pth    # Modelo treinado (gerado pelo train_cnn.py)
└── test_images/             # Imagens de teste
```

---

## Principais recursos técnicos

O pipeline de imagem detecta automaticamente as linhas de texto por projeção horizontal, o que permite processar redações e parágrafos inteiros mantendo a ordem de leitura. Fragmentos de letras (como a barra do A ou o pingo do i) são unidos de volta ao corpo da letra por análise de sobreposição, em vez de contados como caracteres separados. A transcrição é feita linha a linha, formato em que o TrOCR tem melhor desempenho, e a avaliação das letras roda em lote na GPU para manter o tempo de resposta baixo mesmo em textos longos.

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

O OpenCV cuida de todo o pré-processamento das imagens antes de enviá-las para a IA, aplicando filtros de binarização, correção de perspectiva e a segmentação de linhas e caracteres.
O modelo TrOCR da Microsoft, carregado via biblioteca Transformers do Hugging Face, é responsável por transcrever o texto manuscrito para texto digital, linha a linha.
O PyTorch serve como framework base para a rede neural convolucional de avaliação de caligrafia, que utiliza a arquitetura MobileNetV2 com Transfer Learning.
A interface gráfica foi construída com PyQt5, e o dataset EMNIST foi utilizado para o treino da CNN.
