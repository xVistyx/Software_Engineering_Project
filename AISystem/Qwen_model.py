import math
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
        text = self.apply_template(prompt_text)          # same helper the training examples use
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

    #probability probe 
    PREFIX = '{"relevant":'     

    def _answer_setup(self):
        if not hasattr(self, "_ans"):
            tok = self.tokenizer
            enc = lambda t: tok.encode(t, add_special_tokens=False)
            prefix = enc(self.PREFIX)
            true_ids, false_ids = set(), set()
            for word, bucket in (("true", true_ids), ("false", false_ids)):
                for variant in (" " + word, word, " " + word.capitalize(), word.capitalize()):
                    full = enc(self.PREFIX + variant)
                    # keep a spelling only if the prefix tokens come out the same and exactly one token follows
                    if full[:len(prefix)] == prefix and len(full) == len(prefix) + 1:
                        bucket.add(full[-1])
            assert true_ids and false_ids and not (true_ids & false_ids), "could not find separate true/false tokens"
            self._ans = {"prefix": prefix, "true": sorted(true_ids), "false": sorted(false_ids)}
        return self._ans

    def score(self, prompt_text):
        a = self._answer_setup()
        inputs = self.tokenise(prompt_text)
        prefix = torch.tensor([a["prefix"]], device=inputs["input_ids"].device)
        input_ids = torch.cat([inputs["input_ids"], prefix], dim=1)
        attention_mask = torch.ones_like(input_ids)
        with torch.no_grad():
            logits = self.model(input_ids=input_ids, attention_mask=attention_mask).logits[0, -1].float()
        lt = torch.logsumexp(logits[a["true"]], dim=0)
        lf = torch.logsumexp(logits[a["false"]], dim=0)
        margin = (lt - lf).item()
        p = 1.0 / (1.0 + math.exp(-margin))
        mass = torch.softmax(logits, dim=0)[a["true"] + a["false"]].sum().item()
        return {"p_relevant": p, "logit_margin": margin, "answer_mass": mass}