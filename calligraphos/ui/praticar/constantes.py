"""Constantes do modo Praticar: fases de palavras, alfabeto, fonte da letra-guia
e notas minimas do exercicio (lidas de config.json)."""

from calligraphos.config import CONFIG


FASES = [
    {
        "nome": "Iniciante",
        "descricao": "Palavras curtas de 3 a 4 letras, úteis para se acostumar com o traço básico.",
        "palavras": ["CASA", "GATO", "PAO", "SOL", "MAR"],
    },
    {
        "nome": "Intermediário",
        "descricao": "Palavras médias de 5 a 6 letras, com combinações mais desafiadoras.",
        "palavras": ["LIVRO", "PORTA", "MESA", "FLOR", "PRAIA"],
    },
    {
        "nome": "Avançado",
        "descricao": "Palavras mais longas e menos comuns, para consolidar a fluência da escrita.",
        "palavras": ["ESCOLA", "ARVORE", "JANELA", "CADERNO", "MENINO"],
    },
]

LETRAS = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")

FONTE_FORMA = "'Cambria', 'Georgia', serif"

# Ajustaveis em config.json (secao "exercicio")
NOTA_MINIMA_LETRA = CONFIG["exercicio"]["nota_minima_letra"]              # acerto no exercicio

NOTA_MINIMA_PIOR = CONFIG["exercicio"]["nota_minima_pior_letra_palavra"]  # numa palavra, piso por letra
