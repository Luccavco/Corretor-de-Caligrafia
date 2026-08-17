# Instalar o Calligraphos como um app no KDE (CachyOS)

Estes 3 arquivos fazem o programa aparecer no menu do KDE (Kickoff) com
icone proprio, podendo ser fixado na barra de tarefas.

## Passo 1 - Copiar o icone e o launcher para a pasta do projeto

Os arquivos calligraphos.png e calligraphos.sh devem ficar na RAIZ do
projeto (a mesma pasta onde esta o main_ui.py):

```fish
cp calligraphos.png calligraphos.sh /home/luccavco/tcc-caligrafia/
cd /home/luccavco/tcc-caligrafia
chmod +x calligraphos.sh
```

## Passo 2 - Testar o launcher direto (antes de integrar ao KDE)

```fish
./calligraphos.sh
```

Se o programa abrir normalmente, o launcher esta funcionando. Feche e
continue para o proximo passo.

## Passo 3 - Instalar o arquivo .desktop

O arquivo calligraphos.desktop ja aponta para os caminhos corretos
(/home/luccavco/tcc-caligrafia/calligraphos.sh e .png). Copie ele para
a pasta de aplicativos do seu usuario (nao precisa de sudo):

```fish
mkdir -p ~/.local/share/applications
cp calligraphos.desktop ~/.local/share/applications/
chmod +x ~/.local/share/applications/calligraphos.desktop
```

## Passo 4 - Atualizar o cache do KDE (se nao aparecer sozinho)

Normalmente o KDE detecta o novo app sozinho em alguns segundos. Se nao
aparecer no menu, forca a atualizacao:

```fish
kbuildsycoca6
```

(Em versoes mais antigas do Plasma pode ser `kbuildsycoca5` - tenta os
dois se um nao existir.)

## Passo 5 - Usar

Abre o menu do KDE (Kickoff) e procura por "Calligraphos". Deve aparecer
com o icone azul "Ca". Voce pode:
- Arrastar para a barra de tarefas para fixar
- Botao direito > "Adicionar aos favoritos"
- Criar um atalho na area de trabalho (botao direito no item do menu)

## Se algo der errado

Se o icone nao aparecer mas o app abrir: o caminho do Icon= no .desktop
pode estar diferente do seu. Confirma que calligraphos.png esta
realmente em /home/luccavco/tcc-caligrafia/calligraphos.png.

Se o app nao abrir a partir do menu (mas abre via ./calligraphos.sh no
terminal): abre um terminal e roda o comando do Exec= manualmente para
ver o erro:

```fish
/home/luccavco/tcc-caligrafia/calligraphos.sh
```

Se voce moveu a pasta do projeto para outro lugar, edita o
calligraphos.desktop e troca os dois caminhos (Exec= e Icon=) para o
novo local.
