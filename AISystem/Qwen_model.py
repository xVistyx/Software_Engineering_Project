from AI_model import Model
from transformers import Tokenizer
from transformers import AutoModelForCausalLM, AutoTokenizer
import json 
import torch

class Qwen_3B(Model):
    def __init__(self, config):
        self.config = config
        with open(self.config) as f:
            self.config_loaded = json.load(f)

        self.model_choice = self.config_loaded["default_model"] #qwen3_4b
        cfg = config["models"][self.model_choice]

        self.model_name = cfg["name"]
        self.torch_dtype = cfg["model"]["torch_dtype"]
        self.device_map = cfg["model"]["device_map"]
        self.adapter_pth = cfg["model"]["adapter_path"]  

        self.quantization = cfg["quantization"]["load_in_4bit"]       # True  (JSON true -> Python True)
        self.tokenizer_cfg = cfg["tokenizer"]["max_input_length"]      # 1024
        self.lora_target_modules = cfg["lora"]["target_modules"]             # ["q_proj", "k_proj", "v_proj", "o_proj"]

        self.tokenizer = None
        self.model = None
    
    def load(self):
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModelForCausalLM.from_pretrained(self.model_name, torch_dtype=self.torch_dtype, device_map=self.device_map)
        
    def tokenise(self, prompt_text):
        text = self.tokenizer.apply_chat_template(
                [{"role": "user", "content": prompt_text}],
                tokenize=False, add_generation_prompt=True, enable_thinking=False,
            )
        inputs = self.tokenizer(text, return_tensors = "pt").to(self.model.device)
        return inputs
        
    def generate(self, inputs):
        with torch.no_grad():
            output = self.model.generate(
                **inputs,
                max_new_tokens=32,
                do_sample=False,
            )
        new_tokens = output[0][inputs["input_ids"].shape[1]:]
        return self.tokenizer.decode(new_tokens, skip_special_tokens=True)


    


