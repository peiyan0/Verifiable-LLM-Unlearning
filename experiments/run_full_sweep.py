import time
import json
from src.unlearning_engine import UnlearningEngine
from src.utility_evaluator import UtilityEvaluator
from src.audit_logger import CryptographicAuditLogger
from src.statistical_tests import UnlearningSignificanceTester

def execute_matrix_sweep(model, tokenizer, ds_forget, ds_retain):
    logger = CryptographicAuditLogger()
    tester = UnlearningSignificanceTester()
    
    # Sweep Parameters
    seeds = [42, 101, 2023, 7, 88, 999]
    privacy_budgets = [2.0, 4.0, 8.0]
    methods = ["DP2Unlearning", "Gradient_Ascent", "PGU"]
    
    print(f"Starting Full Sweep Matrix: {len(seeds)} Seeds x {len(privacy_budgets)} Budgets x {len(methods)} Methods\n")
    
    for seed in seeds:
        for epsilon in privacy_budgets:
            for method in methods:
                start_time = time.time()
                
                # Simulate engine run depending on parameter state
                engine = UnlearningEngine(model, tokenizer, ds_forget, ds_retain)
                if method == "DP2Unlearning":
                    model_eval = engine.run_dp2unlearning(epsilon=epsilon)
                elif method == "Gradient_Ascent":
                    model_eval = engine.run_gradient_ascent()
                else:
                    model_eval = engine.run_projected_gradient_unlearning()
                
                elapsed = time.time() - start_time
                
                # Logging state and verifying cryptographic ledger chaining
                payload = {
                    "seed": seed,
                    "epsilon": epsilon,
                    "method": method,
                    "duration_seconds": elapsed
                }
                logger.log_event("EXPERIMENT_RUN", payload)
                
    # Run final health check on ledger
    verified, msg = logger.verify_ledger_integrity()
    print(f"\nSweep completed successfully. Integrity status: {msg}")

if __name__ == "__main__":
    print("Full Sweep script constructed and ready for invocation.")
