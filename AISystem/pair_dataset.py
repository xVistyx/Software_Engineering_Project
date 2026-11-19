"""PyTorch Dataset + collate function for the (query, page, relevant) rows in train.jsonl / val.jsonl."""
import torch
from torch.utils.data import Dataset
from torch.nn.utils.rnn import pad_sequence


class PairDataset(Dataset):
    """Tokenises every row once, up front. Rows look like {"query", "page", "relevant", ...}."""
    def __init__(self, rows, model):
        max_len = model.training_config["max_seq_length"]
        self.examples, dropped = [], 0
        for r in rows:
            ex = model.build_training_example(r["query"], r["page"], r["relevant"])
            if len(ex["input_ids"]) > max_len:      # cutting the end would cut the answer, so skip instead
                dropped += 1
                continue
            self.examples.append(ex)
        if dropped:
            print(f"dropped {dropped} examples longer than {max_len} tokens")

    def __len__(self):
        return len(self.examples)

    def __getitem__(self, i):
        return self.examples[i]


def make_collate_fn(pad_token_id):
    """Pads a batch to its longest example. Padding in `labels` is -100 so the loss ignores it."""
    def collate(batch):
        lengths = torch.tensor([len(b["input_ids"]) for b in batch])
        input_ids = pad_sequence([b["input_ids"] for b in batch], batch_first=True, padding_value=pad_token_id)
        labels = pad_sequence([b["labels"] for b in batch], batch_first=True, padding_value=-100)
        attention_mask = (torch.arange(input_ids.size(1))[None, :] < lengths[:, None]).long()
        return {"input_ids": input_ids, "attention_mask": attention_mask, "labels": labels}
    return collate