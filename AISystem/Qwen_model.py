from AI_model import Model
from transformers import Tokenizer
from transformers import AutoModelForCausalLM, AutoTokenizer
import json 

class Qwen_3B(AI_model):
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
    
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModelForCausalLM.from_pretrained(self.model_name, torch_dtype=self.torch_dtype, device_map=self.device_map)

