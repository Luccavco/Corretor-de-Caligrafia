"""Serviço HTTP que expõe o avaliador do Calligraphos para outros clientes
(site/PWA no celular, futuro app nativo), sem duplicar a implementação.

    venv/bin/python -m calligraphos.api          # http://localhost:8000
    docs interativas em http://localhost:8000/docs

Endpoints:
    GET  /saude                 estado do serviço e do modelo
    POST /avaliar               imagem (multipart) + alvo opcional -> notas
                                por letra, texto, imagem anotada e mapa
                                de diferenças (PNG em base64)
"""

import base64
import logging
import os
import tempfile

import cv2
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from calligraphos import __version__
from calligraphos.log_config import configurar
from calligraphos.nucleo import handwriting_evaluator as he
from calligraphos.nucleo.feedback_visual import mapa_diferencas
from calligraphos.nucleo.image_pipeline import annotate_image, load_image, process

configurar()
log = logging.getLogger(__name__)

app = FastAPI(title="Calligraphos API", version=__version__,
              description="Reconhecimento e avaliação de caligrafia em letra de forma.")
# O site (PWA) roda em outra origem; libera o acesso a partir do navegador.
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

TAMANHO_MAXIMO = 8 * 1024 * 1024   # 8 MB por imagem


def _png_base64(bgr):
    ok, buf = cv2.imencode(".png", bgr)
    return base64.b64encode(buf.tobytes()).decode("ascii") if ok else None


def _transcrever(caminho, characters, avaliacao):
    """Google Vision quando disponível; senão a própria CNN (letras) ou o TrOCR."""
    try:
        from calligraphos.nucleo.htr_google import predict_from_path
        return predict_from_path(caminho), "google"
    except Exception as e:
        log.info("Google Vision indisponível (%s); usando reconhecimento local", e)
    if avaliacao and avaliacao["total"] <= 1:
        return "".join(r["letra_prevista"] for r in avaliacao["caracteres"]), "cnn"
    try:
        from calligraphos.nucleo.htr_engine import predict
        _, _, linhas = process(caminho)
        return " ".join(predict(l).strip() for l in linhas), "trocr"
    except Exception as e:
        log.warning("TrOCR indisponível: %s", e)
        return "".join(r["letra_prevista"] for r in avaliacao["caracteres"]), "cnn"


@app.get("/saude")
def saude():
    return {"ok": True, "versao": __version__, "modelo": os.path.basename(he.MODELO_PATH),
            "modelo_presente": os.path.exists(he.MODELO_PATH), "dispositivo": str(he.device)}


@app.post("/avaliar")
async def avaliar(imagem: UploadFile = File(..., description="PNG ou JPEG do texto manuscrito"),
                  alvo: str = Form("", description="Letra ou palavra esperada (A-Z), opcional"),
                  incluir_imagens: bool = Form(True)):
    dados = await imagem.read()
    if not dados:
        raise HTTPException(400, "imagem vazia")
    if len(dados) > TAMANHO_MAXIMO:
        raise HTTPException(413, "imagem maior que 8 MB")
    sufixo = ".png" if (imagem.content_type or "").endswith("png") else ".jpg"
    with tempfile.NamedTemporaryFile(suffix=sufixo, delete=False) as f:
        f.write(dados)
        caminho = f.name
    try:
        try:
            _, characters, _ = process(caminho)
        except Exception as e:
            raise HTTPException(400, f"não foi possível ler a imagem: {e}")
        if not characters:
            return {"texto": "", "motor": None, "pontuacao_geral": None, "letras": [],
                    "aviso": "nenhuma letra detectada"}
        alvo_limpo = "".join(c for c in alvo.upper() if "A" <= c <= "Z")
        alvos = list(alvo_limpo) if len(alvo_limpo) == len(characters) else None
        avaliacao = he.avaliar_texto(characters, alvos=alvos)
        texto, motor = _transcrever(caminho, characters, avaliacao)
        resposta = {
            "texto": texto, "motor": motor,
            "pontuacao_geral": avaliacao["pontuacao_geral"],
            "boas": avaliacao["boas"], "aceitaveis": avaliacao["aceitaveis"], "ruins": avaliacao["ruins"],
            "letras": [{
                "indice": r["indice"], "posicao": r["posicao"], "alvo": r["letra_alvo"],
                "prevista": r["letra_prevista"], "nota": r["nota"], "categoria": r["categoria"],
                "legibilidade": r["legibilidade"], "formacao": r["formacao"],
                "medidas": r["medidas"], "explicacao": he.explicar_letra(r),
            } for r in avaliacao["caracteres"]],
        }
        if incluir_imagens:
            resposta["imagem_anotada_png"] = _png_base64(annotate_image(caminho, avaliacao))
            resposta["mapa_diferencas_png"] = _png_base64(
                mapa_diferencas(characters, avaliacao, load_image(caminho).shape[:2]))
        return resposta
    finally:
        try:
            os.remove(caminho)
        except OSError:
            pass


def main():
    import uvicorn
    uvicorn.run("calligraphos.api:app", host="0.0.0.0", port=int(os.environ.get("PORTA", "8000")))


if __name__ == "__main__":
    main()
