import os
import time
import json
import requests
import pandas as pd
from urllib.error import URLError

def generate_datasets():
    os.makedirs("test_data", exist_ok=True)
    ground_truth = []
    
    # 8 Clean
    for i in range(8):
        df = pd.DataFrame({"Item": ["Revenue", "EBITDA", "Total Assets", "Total Liabilities", "Equity"], "Value": [1000, 200, 500, 200, 300]})
        df.to_excel(f"test_data/clean_{i}.xlsx", index=False)
        ground_truth.append({"file": f"clean_{i}.xlsx", "type": "clean", "Revenue": 1000, "EBITDA": 200, "Total Assets": 500, "Total Liabilities": 200, "Equity": 300})
        
    # 4 Broken Balance Sheet (Assets != Liab + Eq)
    for i in range(4):
        df = pd.DataFrame({"Item": ["Revenue", "EBITDA", "Total Assets", "Total Liabilities", "Equity"], "Value": [1000, 200, 1500, 200, 300]})
        df.to_excel(f"test_data/broken_bs_{i}.xlsx", index=False)
        ground_truth.append({"file": f"broken_bs_{i}.xlsx", "type": "broken_bs", "Revenue": 1000, "EBITDA": 200, "Total Assets": 1500, "Total Liabilities": 200, "Equity": 300})
        
    # 3 Unit-scale errors (Crore vs Lakh)
    for i in range(3):
        df = pd.DataFrame({"Item": ["Revenue (in Crore)", "EBITDA", "Total Assets", "Total Liabilities", "Equity"], "Value": [10, 2000, 500, 200, 300]})
        df.to_excel(f"test_data/unit_error_{i}.xlsx", index=False)
        ground_truth.append({"file": f"unit_error_{i}.xlsx", "type": "unit_error", "Revenue": 100000, "EBITDA": 2000, "Total Assets": 500, "Total Liabilities": 200, "Equity": 300})

    # 3 Missing fields
    for i in range(3):
        df = pd.DataFrame({"Item": ["Revenue", "Total Assets", "Total Liabilities"], "Value": [1000, 500, 200]})
        df.to_excel(f"test_data/missing_{i}.xlsx", index=False)
        ground_truth.append({"file": f"missing_{i}.xlsx", "type": "missing", "Revenue": 1000, "EBITDA": None, "Total Assets": 500, "Total Liabilities": 200, "Equity": None})

    # 2 EBITDA > Revenue
    for i in range(2):
        df = pd.DataFrame({"Item": ["Revenue", "EBITDA", "Total Assets", "Total Liabilities", "Equity"], "Value": [1000, 1200, 500, 200, 300]})
        df.to_excel(f"test_data/ebitda_error_{i}.xlsx", index=False)
        ground_truth.append({"file": f"ebitda_error_{i}.xlsx", "type": "ebitda_error", "Revenue": 1000, "EBITDA": 1200, "Total Assets": 500, "Total Liabilities": 200, "Equity": 300})

    with open("test_data/ground_truth.json", "w") as f:
        json.dump(ground_truth, f, indent=4)
    return ground_truth

def run_eval():
    print("Generating datasets...")
    ground_truth = generate_datasets()
    
    metrics = {
        "Gemini Extraction Accuracy": "N/A (Missing API Key)",
        "Regex Fallback Accuracy": "Failed to run",
        "Guardrail Precision": "N/A",
        "Guardrail Recall": "N/A",
        "Confidence Calibration": "N/A",
        "Hallucination Catch Rate": "N/A",
        "Idempotency Latency": "N/A",
        "Circuit Breaker Open": "N/A",
        "Scanned PDF failure point": "N/A",
    }
    
    print("Testing API...")
    try:
        # Test latency
        start = time.time()
        res = requests.post("http://127.0.0.1:5000/api/jobs", files={"file": open("test_data/clean_0.xlsx", "rb")})
        job1 = res.json()
        first_latency = time.time() - start
        
        start = time.time()
        res = requests.post("http://127.0.0.1:5000/api/jobs", files={"file": open("test_data/clean_0.xlsx", "rb")})
        second_latency = time.time() - start
        
        metrics["Idempotency Latency"] = f"First: {first_latency:.2f}s, Duplicate: {second_latency:.2f}s"
    except Exception as e:
        metrics["Idempotency Latency"] = f"Error: {e}"

    print(metrics)

if __name__ == '__main__':
    run_eval()
