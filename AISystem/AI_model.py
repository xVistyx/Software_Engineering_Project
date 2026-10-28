from abc import abstractmethod, ABC
from preprocess import preprocess
import torch
import json
import re
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training, PeftModel
from torch.utils.data import DataLoader
from pair_dataset import PairDataset, make_collate_fn
import csv

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
        self.last_raw = raw
        return self.parse(raw)


    def parse(self, raw_text):
        match = re.search(r'"relevant"\s*:\s*(true|false)', raw_text, re.IGNORECASE)
        if match is None:
            print(f"parse failure: {raw_text!r}")   # log it so you can see how often it happens
            return True                             
        return match.group(1).lower() == "true"

    def apply_template(self, prompt_text):
        return self.tokenizer.apply_chat_template(
            [{"role": "user", "content": prompt_text}],
            tokenize=False, add_generation_prompt=True,
            **self.config["tokenizer"]["chat_template_kwargs"],
        )

    def build_training_example(self, query, page, relevant):
        prompt_text = self.apply_template(self.build_prompt(query, page))
        answer = json.dumps({"relevant": bool(relevant)}) + self.tokenizer.eos_token
        prompt_ids = self.tokenizer(prompt_text, add_special_tokens=False)["input_ids"]
        answer_ids = self.tokenizer(answer, add_special_tokens=False)["input_ids"]
        return {
            "input_ids": torch.tensor(prompt_ids + answer_ids),
            "labels": torch.tensor([-100] * len(prompt_ids) + answer_ids),
        }
    
    def train(self, dataset, val_path=None):
        train_rows = [json.loads(l) for l in open(train_path)]
        val_rows = [json.loads(l) for l in open(val_path)] if val_path else None
        #attach LoRA adapters to the model
        self.model = prepare_model_for_kbit_training(self.model)
        self.model = get_peft_model(self.model, LoraConfig(**self.LoRA_config))
        self.model.print_trainable_parameters()

        # dataset = list of {"input_ids", "labels"} from build_training_example
        dataset = PairDataset(train_rows, self)
        loader = DataLoader(dataset, batch_size=self.training_config["per_device_train_batch_size"],
                        shuffle=True, collate_fn=make_collate_fn(self.tokenizer.pad_token_id))

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

    def evaluate(self, rows, save_path="predictions.csv"):
        self.model.eval()
        tp = fp = fn = tn = 0
        by_tier = {}
        records = []
        for r in rows:
            pred_relevant = self.classify(r["query"], r["page"])
            records.append({
                "query": r["query"],
                "title": r["page"]["title"],
                "description": r["page"]["description"],
                "tier": r.get("tier"),
                "truth": r["relevant"],
                "pred": pred_relevant,
                "raw": self.last_raw,
            })
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

        if save_path and records:
            with open(save_path, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=records[0].keys())
                w.writeheader()
                w.writerows(records)

        errors = [r for r in records if r["truth"] != r["pred"]]
        if errors:
            with open("errors.csv", "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=errors[0].keys())
                w.writeheader()
                w.writerows(errors)

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