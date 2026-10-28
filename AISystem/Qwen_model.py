import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import PeftModel

from AI_model import Model


class Qwen3Model(Model):
    def load(self):
        m, q = self.config["model"], self.config["quantization"]
        self.tokenizer = AutoTokenizer.from_pretrained(m["tokenizer_name"])
        self.tokenizer.padding_side = self.config["tokenizer"]["padding_side"]

        bnb = None
        if q["enabled"]:
            bnb = BitsAndBytesConfig(
                load_in_4bit=q["load_in_4bit"],
                bnb_4bit_quant_type=q["bnb_4bit_quant_type"],
                bnb_4bit_compute_dtype=getattr(torch, q["bnb_4bit_compute_dtype"]),
                bnb_4bit_use_double_quant=q["bnb_4bit_use_double_quant"],
            )
        self.model = AutoModelForCausalLM.from_pretrained(
            m["name"],
            torch_dtype=getattr(torch, m["torch_dtype"]),
            device_map=m["device_map"],
            quantization_config=bnb,
        )
        if m["adapter_path"]:
            self.model = PeftModel.from_pretrained(self.model, m["adapter_path"])
        self.model.eval()

    def tokenise(self, prompt_text):
        text = self.apply_template(prompt_text)        
        return self.tokenizer(
            text, return_tensors="pt", add_special_tokens=False,
            truncation=self.config["tokenizer"]["truncation"],
            max_length=self.config["tokenizer"]["max_input_length"],
        ).to(self.model.device)

    def generate(self, inputs):
        g = self.config["generation"]
        with torch.no_grad():
            output = self.model.generate(
                **inputs, max_new_tokens=g["max_new_tokens"], do_sample=g["do_sample"],
            )
        new_tokens = output[0][inputs["input_ids"].shape[1]:]
        return self.tokenizer.decode(new_tokens, skip_special_tokens=True)