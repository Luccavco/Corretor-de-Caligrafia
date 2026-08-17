# Arquivos otimizados do Calligraphos

Estes sao os arquivos revisados nas 4 partes da otimizacao. Para aplicar,
copie todos eles para a raiz do projeto, substituindo os antigos:

```fish
cp *.py *.md *.txt ~/tcc-caligrafia/
```

(Rode este comando de DENTRO da pasta extraida deste zip.)

## O que mudou

ARQUIVO NOVO (precisa existir):
- ui_helpers.py  -> utilitarios de interface compartilhados

DESDUPLICACAO E LIMPEZA:
- praticar_widget.py  -> usa ui_helpers, imports mortos removidos,
                         limpeza de PNGs temporarios, correcao de bugs
- analise_widget.py   -> import pesado morto removido (abre mais rapido)
- 11 outros arquivos  -> imports nao usados removidos

CORRECAO DE BUGS:
- praticar_widget.py  -> fases nao desbloqueiam mais com 0 acertos
- progresso.py        -> nao sobrescreve progresso real em falha de rede;
                         streak exibida corretamente (0 se sequencia quebrou)
- handwriting_evaluator.py, htr_google.py, firebase_config.py,
  auth_service.py     -> caminhos de arquivo robustos (funcionam de
                         qualquer diretorio)
- firebase_config.py  -> config do Pyrebase corrigida (projeto certo)
- htr_engine.py       -> flag de progress bar corrigida

DOCUMENTACAO:
- Readme.md           -> reescrito e atualizado
- requirements.txt    -> so dependencias diretas, com versoes fixadas

## Importante

Este zip NAO inclui os arquivos que nao mudaram (image_pipeline.py,
detalhe_letra_dialog.py, ui_theme.py, anel_progresso.py, test_pipeline.py)
nem o calligraphos-web/, o instalar-app/ nem as credenciais. So os
arquivos que foram de fato otimizados.
