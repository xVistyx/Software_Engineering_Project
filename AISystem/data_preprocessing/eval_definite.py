"""
Definite-case eval: easy_yes (query + site of same topic) and easy_no (query + site of another topic).
Put next to study_sites_candidates.csv (data_preprocessing/). Run on the GPU node.
"""
import json, re, random
from pathlib import Path
import pandas as pd
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

script_dir = Path(__file__).resolve().parent
random.seed(42)

QUERIES = {
    "Mathematics":      "I will study mathematical analysis",
    "Physics":          "I will study classical mechanics and thermodynamics",
    "Chemistry":        "I will study organic chemistry",
    "Biology":          "I will study cell biology and genetics",
    "Computer_Science": "I will study algorithms and data structures",
    "History":          "I will study European history",
    "Economics":        "I will study microeconomics",
    "Philosophy":       "I will study ethics and epistemology",
    "Law":              "I will study contract law",
}

df = pd.read_csv(script_dir / "study_sites_candidates.csv")
df = df[df["keep"] == 1]
df = df[df["topic"].isin(QUERIES)]
print(df.groupby("topic").size())

# build pairs
pairs = []
for _, r in df.iterrows():
    pairs.append(dict(tier="easy_yes", query=QUERIES[r.topic], uid=r.uid, topic=r.topic,
                      title=r.title, truth=True))
    other = df[df.topic != r.topic].sample(1, random_state=random.randint(0, 10**6)).iloc[0]
    pairs.append(dict(tier="easy_no", query=QUERIES[r.topic], uid=other.uid, topic=other.topic,
                      title=other.title, truth=False))

MODEL = "Qwen/Qwen3-4B"
tok = AutoTokenizer.from_pretrained(MODEL)
model = AutoModelForCausalLM.from_pretrained(MODEL, torch_dtype=torch.bfloat16, device_map="auto")

def classify(query, title):
    prompt = f"""Study session goal: {query}

Page title: {title}

Is this page relevant to the study session goal above? Answer with just JSON: {{"relevant": true or false, "reason": "short reason"}}"""
    text = tok.apply_chat_template([{"role": "user", "content": prompt}], tokenize=False,
                                   add_generation_prompt=True, enable_thinking=False)
    inputs = tok(text, return_tensors="pt").to(model.device)
    out = model.generate(**inputs, max_new_tokens=60, do_sample=False)
    return tok.decode(out[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)

rows = []
for p in pairs:
    raw = classify(p["query"], p["title"])
    m = re.search(r'"relevant"\s*:\s*(true|false)', raw, re.I)
    pred = (m.group(1).lower() == "true") if m else None
    rows.append({**p, "pred": pred, "correct": pred == p["truth"], "raw": raw})

res = pd.DataFrame(rows)
res.to_csv(script_dir / "eval_definite_results.csv", index=False)
print("parse failures:", res["pred"].isna().sum())
print(res.groupby("tier")["correct"].agg(["mean", "sum", "count"]))
print(res.groupby(["tier", "topic"])["correct"].mean().unstack(0))