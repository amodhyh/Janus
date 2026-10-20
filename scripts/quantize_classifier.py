from onnxruntime import quantization
from huggingface_hub import snapshot_download
import logging
from pathlib import Path
from onnxruntime.quantization import quantize_dynamic
from transformers import AutoTokenizer
from optimum.onnxruntime import ORTModelForSequenceClassification 

MODEL_ID = "leolee99/PIGuard"
RAW_DIR = Path("./models/piguard_raw")
ONNX_DIR = Path("./models/piguard_onnx")
FP32_ONNX_PATH = ONNX_DIR / "model.onnx"
INT8_ONNX_PATH = ONNX_DIR / "model_int8.onnx"
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# download the model

def model_get():
    # path check
    if (not RAW_DIR.exists) or (not ONNX_DIR.exists):
        logging.info("ONNX and RAW_DIR not found! Creating new directories")
        RAW_DIR.mkdir(parents=True,exist_ok=True)
        ONNX_DIR.mkdir(parents=True,exist_ok=True)
        
    model = snapshot_download(
        repo_id=MODEL_ID,
        local_dir=RAW_DIR,
        local_dir_use_symlinks=False)
# run the quantizatio script
# export the pytorch weights into ONNX
def quantize2int8():
    tokenizer=AutoTokenizer.from_pretrained(RAW_DIR)
    
    # export with opset version
    model = ORTModelForSequenceClassification.from_pretrained(
            model_id=RAW_DIR, #as the model is downloaded we will use the RAW_DIR instead of the model id
            export=True,
            trust_remote_code=True,
            provider="CPUExecutionProvider"
        )

    # generate the model_int8.onnx
    model.save_pretrained(ONNX_DIR)
    tokenizer.save_pretrained(ONNX_DIR)

    # Apply Dynamic Quantization (INT8)
    logging.info("Quantizing ONNX model to INT8...")
    quantize_dynamic()
    
    
# benchmarks


