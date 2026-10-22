import onnxruntime as ort
import logging
from transformers import AutoTokenizer
import numpy as np


try:
    from pipeline import PipelineDTO, DTODecision
except (ImportError, ModuleNotFoundError):
    from engine.pipeline import PipelineDTO, DTODecision

TOKEN_LIMIT = 512

def get_session():
   '''Get the global Classifier model ONNX session'''
   logging.info("get_session Started")
   session_options = ort.SessionOptions()
   
    
   # Cap operations across independent nodes (InterOp)
   session_options.inter_op_num_threads = 1 
    
    # Execution mode
   session_options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
    
    # Load the model ONCE into memory
   logging.info("Loading INT8 model into memory...")
   session = ort.InferenceSession("../models/piguard_onnx/model_int8.onnx", sess_options=session_options)
   tokenizer = AutoTokenizer.from_pretrained("../models/piguard_onnx") 
   
   return session,tokenizer

def softmax(x, axis=-1):
    # Subtract the maximum value along the axis for numerical stability
    e_x = np.exp(x - np.max(x, axis=axis, keepdims=True))
    return e_x / np.sum(e_x, axis=axis, keepdims=True)  

class Classifier_Stage():
   '''Analyze the prompt usnig BERT family model'''
            
   def process(self, prompt: str)->PipelineDTO:
      session,tokenizer= get_session()
      
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
      probs = softmax(outputs[0])
      
      benign_prob = probs[0]
      injection_prob = probs[1]
      
      logging.info(f"{prompt[0:20]} \n---RESULT---\nBENIGN = {benign_prob}\nINJECTION{injection_prob}")
      
      if benign_prob < 0.52 and benign_prob>0.48:
         return PipelineDTO(
            prompt=prompt,
            action=DTODecision.MUTATE,
            is_final=False,
            reason=f"Detection Model(Small) result = {benign_prob}, more checking up required"
            
                           )
      elif benign_prob>0.52:
         return PipelineDTO(prompt=prompt,
                           action=DTODecision.ALLOW , 
                           is_final=True , 
                           reason=f"Detection Model(Small) result = {benign_prob*100}% chance of this is Safe")
      else: 
         return PipelineDTO(prompt=prompt,
                           action=DTODecision.DENY , 
                           is_final=True , 
                           reason=f"Detection Model(Small) result = {benign_prob*100}% chance of this is Safe")
               
