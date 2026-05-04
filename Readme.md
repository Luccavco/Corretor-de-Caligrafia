codigo para detectar as dimensoes das letras:
      
python -c "
from image_pipeline import process
pil_image, characters = process('test_images/Letra_A.jpg')
print(f'Imagem processada: {pil_image.size}')
print(f'Caracteres encontrados: {len(characters)}')
for i, (x, y, w, h, _) in enumerate(characters):
    print(f'  Char {i+1}: x={x}, y={y}, largura={w}, altura={h}')
"

codigo para delimitar as dimensoes da imagem em relacao a letra:

python -c "
from image_pipeline import process
from PIL import Image
import numpy as np

pil_image, characters = process('test_images/Letra_A.jpg')
x, y, w, h, char_img = characters[0]
result = Image.fromarray(char_img)
result.save('test_images/A_segmentado.png')
print('Salvo em test_images/A_segmentado.png')
"