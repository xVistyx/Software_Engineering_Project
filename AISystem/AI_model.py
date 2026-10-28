from abc import abstractmethod, ABC
from preprocess import preprocess
import torch
import json
import re
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training, PeftModel
from torch.utils.data import DataLoader
from transformers import DataCollatorForSeq2Seq

class Model(ABC):
    def __init__(self, config_path, model_name=None):
        with open(config_path) as f:
            all_config = json.load(f)
        name = model_name or all_config["default_model"]
        self.config = all_config["models"][name]       # this model's settings
        self.LoRA_config = self.config["lora"]
        self.training_config = self.config["training"]
        self.model = None
        self.tokenizer = None

    @abstractmethod
    def load(self):
        pass

    @abstractmethod
    def tokenise(self, prompt_text):
        pass

    @abstractmethod
    def generate(self, inputs):
        pass


    def build_prompt(self, query, page_data):
        prompt = (
            f"Study session goal: {query}\n\n"
            f"{preprocess(page_data)}\n\n"
            "Is this page relevant to the study session goal? "
            'Answer with just JSON: {"relevant": true or false}'
        )
        return prompt
    
    def classify(self, query, page_data):
        prompt = self.build_prompt(query, page_data)
        inputs = self.tokenise(prompt)
        raw = self.generate(inputs)
        return self.parse(raw)


    def parse(self, raw_text):
        match = re.search(r'"relevant"\s*:\s*(true|false)', raw_text, re.IGNORECASE)
        if match is None:
            print(f"parse failure: {raw_text!r}")   # log it so you can see how often it happens
            return True                             
        return match.group(1).lower() == "true"

    def train(self, dataset, val_rows=None):
        #attach LoRA adapters to the model
        self.model = prepare_model_for_kbit_training(self.model)
        self.model = get_peft_model(self.model, LoraConfig(**self.LoRA_config))
        self.model.print_trainable_parameters()

        # dataset = list of {"input_ids", "labels"} from build_training_example
        collator = DataCollatorForSeq2Seq(self.tokenizer, padding=True, label_pad_token_id=-100)
        loader = DataLoader(dataset, batch_size=self.training_config["per_device_train_batch_size"],
                            shuffle=True, collate_fn=collator)

        # 3. optimiser over the LoRA parameters only
        optimizer = torch.optim.AdamW(
            [p for p in self.model.parameters() if p.requires_grad],
            lr=self.training_config["learning_rate"], weight_decay=self.training_config["weight_decay"])
        accum = self.training_config["gradient_accumulation_steps"]

        self.model.train()
        for epoch in range(self.training_config["num_train_epochs"]):
            epoch_loss = 0.0
            for step, batch in enumerate(loader):
                batch = {k: v.to(self.model.device) for k, v in batch.items()}
                loss = self.model(**batch).loss / accum
                loss.backward()
                epoch_loss += loss.item()
                if (step + 1) % accum == 0 or step + 1 == len(loader):
                    optimizer.step()
                    optimizer.zero_grad()
            print(f"epoch {epoch + 1}: loss {epoch_loss / len(loader) * accum:.4f}")
            if val_rows:
                metrics = self.evaluate(val_rows)
                print(f"epoch {epoch + 1}: precision {metrics['precision']:.3f} "
                    f"recall {metrics['recall']:.3f} f1 {metrics['f1']:.3f}")
                self.model.train()   # evaluate() switched to eval mode, so switch back

        self.save_adapter(self.training_config["output_dir"])

    def save_adapter(self, path):
        self.model.save_pretrained(path)      #save LoRA weights
        self.tokenizer.save_pretrained(path)

    def load_adapter(self, path):
        self.model = PeftModel.from_pretrained(self.model, path)

    def evaluate(self, rows):
        self.model.eval()
        tp = 0
        fp = 0
        fn = 0
        tn = 0 
        by_tier = {}
        for r in rows:
            pred_relevant = self.classify(r["query"], r["page"])
            correct = pred_relevant == r["relevant"]
            if "tier" in r:
                by_tier.setdefault(r["tier"], []).append(correct)
            # positive class = "block"
            if not pred_relevant and not r["relevant"]: 
                tp += 1
            elif not pred_relevant and r["relevant"]:   
                fp += 1   # wrongly blocked
            elif pred_relevant and not r["relevant"]:   
                fn += 1   # distraction let through
            else:                                       
                tn += 1
        precision = tp / max(tp + fp, 1)
        recall = tp / max(tp + fn, 1)
        return {
            "precision": precision,
            "recall": recall,
            "f1": 2 * precision * recall / max(precision + recall, 1e-9),
            "accuracy": (tp + tn) / max(len(rows), 1),
            "confusion": {"tp": tp, "fp": fp, "fn": fn, "tn": tn},
            "per_tier": {k: sum(v) / len(v) for k, v in by_tier.items()},
        }






    