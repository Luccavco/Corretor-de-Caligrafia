import warnings
import logging
import os

os.environ["TRANSFORMERS_VERBOSITY"] = "error"
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "0"
logging.getLogger("transformers").setLevel(logging.ERROR)

from transformers import TrOCRProcessor, VisionEncoderDecoderModel
from PIL import Image

processor = None
model = None


def load_model():
    global processor, model
    print("Carregando modelo TrOCR...")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        processor = TrOCRProcessor.from_pretrained("microsoft/trocr-base-printed")
        model = VisionEncoderDecoderModel.from_pretrained("microsoft/trocr-base-printed")
    model.config.max_new_tokens = 50
    print("Modelo carregado!")


def predict(pil_image):
    if processor is None or model is None:
        load_model()
    pixel_values = processor(images=pil_image, return_tensors="pt").pixel_values
    generated_ids = model.generate(pixel_values, max_new_tokens=50)
    text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
    return text