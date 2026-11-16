import numpy as np
from scipy.stats import wilcoxon

class UnlearningSignificanceTester:
    def __init__(self, alpha=0.05):
        self.alpha = alpha

    def run_signed_rank_test(self, baseline_metrics, target_metrics, hypothesis_name="RQ"):
        """
        Performs a two-sided Wilcoxon signed-rank test between paired metrics across random seeds.
        """
        baseline_arr = np.array(baseline_metrics)
        target_arr = np.array(target_metrics)
        
        if len(baseline_arr) != len(target_arr):
            raise ValueError("Metrics lists must have the exact same length (equal number of paired seeds).")
            
        # Compute the paired differences
        diff = target_arr - baseline_arr
        if np.all(diff == 0):
            return {
                "hypothesis": hypothesis_name,
                "p_value": 1.0,
                "significant": False,
                "message": "No difference observed between runs."
            }
            
        statistic, p_val = wilcoxon(baseline_arr, target_arr, alternative='two-sided')
        significant = p_val < self.alpha
        
        return {
            "hypothesis": hypothesis_name,
            "statistic": float(statistic),
            "p_value": float(p_val),
            "significant": bool(significant),
            "message": f"Reject H0: Significant difference detected (p={p_val:.4f})" if significant else f"Fail to reject H0: No statistical significance (p={p_val:.4f})"
        }
