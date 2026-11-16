import torch
import numpy as np
from evaluate import load

class UtilityEvaluator:
    def __init__(self, model, tokenizer, retain_dataset):
        self.model = model
        self.tokenizer = tokenizer
        self.retain_dataset = retain_dataset
        try:
            self.rouge_metric = load("rouge")
        except Exception:
            self.rouge_metric = None
            print("ROUGE evaluation metric not found or offline. Falling back to exact match indicators.")
            
    def evaluate_exact_match(self, limit=30):
        """
        Computes standard Exact Match (EM) over a subset of the Retain Dataset.
        """
        print(f"Evaluating Exact Match on {limit} retain samples...")
        em_scores = []
        for i in range(min(limit, len(self.retain_dataset))):
            row = self.retain_dataset[i]
            prompt = f"Question: {row['question']}\nAnswer: "
            inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
            
            with torch.no_grad():
                outputs = self.model.generate(**inputs, max_new_tokens=32, pad_token_id=self.tokenizer.eos_token_id)
            
            generated_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            generated_answer = generated_text.replace(prompt, "").strip()
            
            em = 1.0 if generated_answer.lower() == row["answer"].lower() else 0.0
            em_scores.append(em)
            
        return np.mean(em_scores)

    def evaluate_perplexity(self, limit=30):
        """
        Computes word/token entropy and sequence-level perplexity over retained concepts
        to ensure the model's core language generation capabilities have not collapsed.
        """
        print(f"Evaluating Perplexity on {limit} retain samples...")
        losses = []
        for i in range(min(limit, len(self.retain_dataset))):
            row = self.retain_dataset[i]
            full_text = f"Question: {row['question']}\nAnswer: {row['answer']}"
            inputs = self.tokenizer(full_text, return_tensors="pt").to(self.model.device)
            
            with torch.no_grad():
                outputs = self.model(**inputs, labels=inputs["input_ids"])
                loss = outputs.loss.item()
            losses.append(loss)
            
        avg_loss = np.mean(losses)
        perplexity = np.exp(avg_loss)
        return {"loss": avg_loss, "perplexity": perplexity}
