import json
import os
import re
import pandas as pd
from transformers import AutoModelForCausalLM, AutoTokenizer

script_dir = os.path.dirname(os.path.abspath(__file__))

model_name = "Qwen/Qwen3-4B"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name, torch_dtype="auto", device_map="auto")

TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)

def extract_title(html):
    match = TITLE_RE.search(html)
    if not match:
        return ""
    raw = match.group(1)
    raw = re.sub(r"<[^>]+>", "", raw)
    raw = re.sub(r"\s+", " ", raw).strip()
    return raw

def classify(query, title):
    prompt = f"""Study session goal: {query}

Page title: {title}

Is this page relevant to the study session goal above? Answer with just JSON: {{"relevant": true or false, "reason": "short reason"}}"""

    messages = [{"role": "user", "content": prompt}]
    text = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True, enable_thinking=False
    )
    inputs = tokenizer(text, return_tensors="pt").to(model.device)
    outputs = model.generate(**inputs, max_new_tokens=100)
    response = tokenizer.decode(outputs[0][inputs.input_ids.shape[-1]:], skip_special_tokens=True)
    return response

def parse_model_response(response_text):
    """Extract {relevant: bool} from the model's raw text output, tolerating minor formatting noise."""
    try:
        # find the first {...} block in case the model adds extra text
        match = re.search(r"\{.*\}", response_text, re.DOTALL)
        if match:
            parsed = json.loads(match.group(0))
            return parsed.get("relevant"), parsed.get("reason", "")
    except (json.JSONDecodeError, AttributeError):
        pass
    return None, "PARSE_FAILED"

# --- load queries ---
with open(os.path.join(script_dir, "queries.json"), "r") as f:
    queries_data = json.load(f)
topic_to_query = {entry["topic"]: entry["query"] for entry in queries_data["queries"]}

# --- load candidates (tier labels — NOT shown to the model, only used for scoring afterward) ---
candidates_df = pd.read_csv(os.path.join(script_dir, "eval_set_candidates.csv"))

# --- load html content, build uid -> title lookup ---
uid_to_title = {}
with open(os.path.join(script_dir, "eval_set_html.jsonl"), "r") as f:
    for line in f:
        record = json.loads(line)
        uid_to_title[record["uid"]] = extract_title(record["html"])

# expected label per tier: easy_yes -> True, hard_no/easy_no/ambiguous -> False
TIER_EXPECTED = {
    "easy_yes": True,
    "hard_no": False,
    "easy_no": False,
    "ambiguous": False,
}

results = []
for _, row in candidates_df.iterrows():
    uid = row["uid"]
    topic = row["topic"]
    tier = row["tier"]

    if pd.isna(uid) or uid not in uid_to_title:
        print(f"Skipping {topic} / {tier} — no matching HTML found")
        continue

    title = uid_to_title[uid]
    query = topic_to_query.get(topic)
    if not query:
        print(f"Skipping {topic} — no query found in queries.json")
        continue

    raw_response = classify(query, title)
    predicted, reason = parse_model_response(raw_response)
    expected = TIER_EXPECTED.get(tier)

    correct = (predicted == expected) if predicted is not None else False

    results.append({
        "topic": topic,
        "tier": tier,
        "title": title,
        "query": query,
        "expected": expected,
        "predicted": predicted,
        "correct": correct,
        "reason": reason,
        "raw_response": raw_response,
    })

    print(f"[{topic} / {tier}] expected={expected} predicted={predicted} {'✓' if correct else '✗'} — {title[:60]}")

results_df = pd.DataFrame(results)
results_df.to_csv(os.path.join(script_dir, "eval_results.csv"), index=False)

# --- summary ---
print("\n" + "=" * 60)
print(f"Overall accuracy: {results_df['correct'].mean():.2%} ({results_df['correct'].sum()}/{len(results_df)})")
print("\nPer-tier accuracy:")
print(results_df.groupby("tier")["correct"].agg(["mean", "count"]))