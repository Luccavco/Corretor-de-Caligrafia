"""Consulta de definicoes de palavras em portugues.

Estrategia em cascata (a primeira que funcionar e usada):
1. Dicio.com.br (HTTPS, mais completo, traz classe gramatical) - extraido
   do HTML da pagina, que tem formato estavel.
2. Dicionario Aberto (https://api.dicionario-aberto.net/word/<palavra>) -
   API JSON publica, sem chave; usada como reserva.

Ambas sao publicas e nao exigem chave. Se as duas falharem (sem conexao,
palavra inexistente), devolve None e a interface mostra um aviso amigavel.
"""

import re
import json
import html as _html
import urllib.parse
import urllib.request

TIMEOUT = 10
_UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko)"

# Classes gramaticais reconhecidas (para separar do corpo da definicao)
_CLASSES = (
    "substantivo feminino", "substantivo masculino", "substantivo",
    "adjetivo e substantivo", "adjetivo",
    "verbo transitivo direto e indireto",
    "verbo transitivo direto e pronominal",
    "verbo transitivo indireto e pronominal",
    "verbo transitivo direto", "verbo transitivo indireto",
    "verbo transitivo e pronominal", "verbo transitivo",
    "verbo intransitivo e pronominal", "verbo intransitivo",
    "verbo pronominal", "verbo",
    "adverbio", "numeral", "preposicao", "conjuncao", "interjeicao",
    "pronome", "artigo", "locucao",
)


def _fetch(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": _UA,
        "Accept": "text/html,application/json",
    })
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read().decode("utf-8", errors="replace")


# --- FONTE 1: DICIO.COM.BR ---

def _buscar_dicio(palavra):
    url = "https://www.dicio.com.br/" + urllib.parse.quote(palavra.lower())
    try:
        pagina = _fetch(url)
    except Exception:
        return None

    m = re.search(
        r'<p class="significado[^"]*"[^>]*>(.*?)</p>', pagina, re.DOTALL
    )
    if not m:
        return None

    bruto = m.group(1)
    # Cada acepcao costuma vir em <span>...</span>; viram quebras de linha
    bruto = re.sub(r"</span>", "\n", bruto)
    texto = re.sub(r"<[^>]+>", " ", bruto)
    texto = _html.unescape(texto)
    linhas = [re.sub(r"\s+", " ", ln).strip() for ln in texto.split("\n")]
    linhas = [ln for ln in linhas if ln]
    if not linhas:
        return None

    # A classe gramatical costuma abrir a definicao
    classe = ""
    primeira_norm = _sem_acento(linhas[0].lower())
    for c in _CLASSES:
        if primeira_norm.startswith(c):
            classe = linhas[0][:len(c)]
            linhas[0] = linhas[0][len(c):].strip()
            break

    # Limpa cada linha: remove classes gramaticais soltas, fragmentos que
    # comecam com virgula, e marcadores entre colchetes tipo [Por Extensao]
    linhas_limpas = []
    for ln in linhas:
        # descarta linha que e so uma classe gramatical solta
        if _eh_classe_solta(ln):
            continue
        # remove marcador inicial entre colchetes: "[Por Extensao] Texto" -> "Texto"
        ln = re.sub(r"^\s*\[[^\]]*\]\s*", "", ln)
        # remove virgula/pontuacao residual no inicio
        ln = ln.lstrip(" ,;.").strip()
        if ln and len(ln) > 2:
            linhas_limpas.append(ln)

    linhas_limpas = [ln for ln in linhas_limpas if ln]
    if not linhas_limpas:
        return None

    definicao = "\n".join(linhas_limpas)
    return {
        "palavra": palavra.upper(),
        "classe": classe,
        "definicao": definicao,
        "exemplos": [],
        "fonte": "Dicio",
    }


def _eh_classe_solta(linha):
    """True se a linha e apenas uma classe gramatical (ou fragmento dela),
    que nao deve virar um 'significado'."""
    ln = linha.strip()
    if ln.startswith(","):
        return True
    norm = _sem_acento(ln.lower()).strip(" ,.;")
    if norm in _CLASSES:
        return True
    # se a linha e so combinacao de marcadores de transitividade +
    # conectivos (ex: "transitivo indireto e pronominal"), descarta
    palavras = norm.replace(" e ", " ").replace(",", " ").split()
    resto = [p for p in palavras if p not in (
        "transitivo", "indireto", "direto", "intransitivo", "pronominal"
    )]
    if palavras and not resto:
        return True
    return False


def _sem_acento(s):
    import unicodedata
    return "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )


# --- FONTE 2: DICIONARIO ABERTO (reserva) ---

def _limpar_tei(texto_xml):
    if not texto_xml:
        return "", []
    exemplos = re.findall(r"<quote>(.*?)</quote>", texto_xml, re.DOTALL)
    exemplos = [re.sub(r"<[^>]+>", "", e).strip() for e in exemplos]
    exemplos = [e for e in exemplos if e]

    corpo = texto_xml
    corpo = re.sub(r"<form>.*?</form>", " ", corpo, flags=re.DOTALL)
    corpo = re.sub(r"<orth>.*?</orth>", " ", corpo, flags=re.DOTALL)
    corpo = re.sub(r"<cit[^>]*>.*?</cit>", " ", corpo, flags=re.DOTALL)
    corpo = re.sub(r"<quote>.*?</quote>", " ", corpo, flags=re.DOTALL)
    corpo = re.sub(r"<[^>]+>", " ", corpo)
    corpo = _html.unescape(corpo)
    corpo = re.sub(r"\s+", " ", corpo).strip()
    return corpo, exemplos


def _buscar_aberto(palavra):
    url = "https://api.dicionario-aberto.net/word/" + urllib.parse.quote(
        palavra.lower()
    )
    try:
        bruto = _fetch(url)
        dados = json.loads(bruto)
    except Exception:
        return None

    entradas = dados if isinstance(dados, list) else [dados]
    for entrada in entradas:
        if not isinstance(entrada, dict):
            continue
        definicao, exemplos = _limpar_tei(entrada.get("xml", ""))
        if definicao:
            return {
                "palavra": entrada.get("word", palavra).upper(),
                "classe": "",
                "definicao": definicao,
                "exemplos": exemplos[:3],
                "fonte": "Dicionario Aberto",
            }
    return None


# --- PUBLICO ---

def buscar(palavra):
    """Busca a definicao de uma palavra. Devolve dict com:
    palavra, classe, definicao, exemplos, fonte - ou None se nao achar."""
    palavra = (palavra or "").strip()
    if len(palavra) < 2:
        return None

    resultado = _buscar_dicio(palavra)
    if resultado:
        return resultado

    return _buscar_aberto(palavra)
