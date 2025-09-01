from transformers import AutoProcessor , AutoModelForCausalLM
from PIL import Image 
import requests , copy 
import torch

import os
os.environ["PYTORCH_USE_SDPA"] = "0"


model_id = "microsoft/Florence-2-large"
#model = AutoModelForCausalLM.from_pretrained(model_id, trust_remote_code=True).eval().cuda()
model = AutoModelForCausalLM.from_pretrained(
    model_id,
    trust_remote_code=True,
    attn_implementation="eager" ,
    torch_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
    device_map="auto" if torch.cuda.is_available() else None,
).eval()

processor = AutoProcessor.from_pretrained(model_id, trust_remote_code=True)