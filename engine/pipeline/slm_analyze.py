import onnxruntime as ort
import json
import logging
import os
from pathlib import Path
from transformers import AutoTokenizer
import numpy as np
from functools import lru_cache


try:
    from pipeline import PipelineDTO, DTODecision
except (ImportError, ModuleNotFoundError):
    from engine.pipeline import PipelineDTO, DTODecision

TOKEN_LIMIT = int(os.getenv("JANUS_SLM_TOKEN_LIMIT", "512"))
# Pass 2 only decides when confident; the gray area in between goes to the LLM judge.
DENY_INJECTION_PROB = float(os.getenv("JANUS_SLM_DENY_PROB", "0.95"))
ALLOW_INJECTION_PROB = float(os.getenv("JANUS_SLM_ALLOW_PROB", "0.05"))
# Default is anchored to the repo root so it works from any working directory.
DEFAULT_MODEL_DIR = Path(__file__).resolve().parents[2] / "models" / "piguard_onnx"
MODEL_DIR = os.getenv("JANUS_SLM_MODEL_DIR", str(DEFAULT_MODEL_DIR))

@lru_cache(maxsize=1)
def get_session():
   '''Get the global Classifier model ONNX session'''
   logging.info("get_session Started")
   session_options = ort.SessionOptions()
   
    
   # cap operations across independent nodes (InterOp)
   session_options.inter_op_num_threads = 1 
    
    # Execution mode
   session_options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
    
    # Load the model ONCE into memory
   logging.info("Loading FP32 model into memory...")
   session = ort.InferenceSession(f"{MODEL_DIR}/model.onnx", sess_options=session_options)
   tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)

   # Resolve class indices from the model config instead of assuming an order
   with open(f"{MODEL_DIR}/config.json", encoding="utf-8") as f:
      id2label = json.load(f)["id2label"]
   label2id = {v.lower(): int(k) for k, v in id2label.items()}
   return session, tokenizer, label2id["benign"], label2id["injection"]

def softmax(x, axis=-1):
    # Subtract the maximum value along the axis for numerical stability
    e_x = np.exp(x - np.max(x, axis=axis, keepdims=True))
    return e_x / np.sum(e_x, axis=axis, keepdims=True)  

class Classifier_Stage():
   '''Analyze the prompt usnig BERT family model'''
            
   def process(self, prompt: str)->PipelineDTO:
      session, tokenizer, benign_idx, injection_idx = get_session()
      
      input = tokenizer(
         text=prompt,
         padding=True,
         truncation=True,
         max_length=TOKEN_LIMIT,
         return_tensors="np"
      )
    
      input_feed = {
            "input_ids": input["input_ids"].astype(np.int64),
            "attention_mask": input["attention_mask"].astype(np.int64)
        }

        # Run inference through the ONNX graph
        # Passing None as the first argument fetches all output nodes (logits)
      outputs = session.run(None, input_feed)
      probs = softmax(outputs[0])[0]
      
      benign_prob = float(probs[benign_idx])
      injection_prob = float(probs[injection_idx])
      
      logging.info(f"SLM result: benign={benign_prob:.4f} injection={injection_prob:.4f}")
      
      if injection_prob >= DENY_INJECTION_PROB:
         return PipelineDTO(prompt=prompt, score=injection_prob,
                           action=DTODecision.DENY ,
                           is_final=True ,
                           reason=f"Detection Model(Small) result = {injection_prob*100}% chance of this is an injection")
      elif injection_prob <= ALLOW_INJECTION_PROB:
         return PipelineDTO(prompt=prompt, score=injection_prob,
                           action=DTODecision.ALLOW ,
                           is_final=True ,
                           reason=f"Detection Model(Small) result = {benign_prob*100}% chance of this is Safe")
      else:
         # Gray area: not final, escalate to the LLM judge (Pass 3)
         return PipelineDTO(prompt=prompt, score=injection_prob,
                           action=DTODecision.MUTATE,
                           is_final=False,
                           reason=f"Detection Model(Small) result = {injection_prob*100}% injection, more checking up required")

@lru_cache(maxsize=1)
def get_classifier() -> Classifier_Stage:
   '''Get the global Classifier_Stage instance (model is loaded on first call)'''
   get_session()
   return Classifier_Stage()
