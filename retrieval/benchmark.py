import sys
from pathlib import Path
from typing import List, Dict, Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from retrieval.pipeline import RetrievalPipeline


BENCHMARK_DATASET: List[Dict[str, Any]] = [
    # --- Scheme 1: HDFC Mid-Cap Opportunities Fund ---
    {
        "query": "What is the expense ratio (TER) of HDFC Mid Cap Fund Direct Growth?",
        "expected_scheme": "hdfc-mid-cap-fund",
        "expected_section": "expense_ratio",
        "expected_snippet": "0.75%"
    },
    {
        "query": "What is the exit load for HDFC Mid-Cap Opportunities Fund?",
        "expected_scheme": "hdfc-mid-cap-fund",
        "expected_section": "exit_load",
        "expected_snippet": "Exit load of 1%"
    },
    {
        "query": "What is the minimum SIP amount for HDFC Mid Cap Fund?",
        "expected_scheme": "hdfc-mid-cap-fund",
        "expected_section": "minimum_investment",
        "expected_snippet": "SIP"
    },
    {
        "query": "Does HDFC Mid-Cap Opportunities Fund have a lock-in period?",
        "expected_scheme": "hdfc-mid-cap-fund",
        "expected_section": "lock_in_period",
        "expected_snippet": "no lock-in"
    },
    {
        "query": "What is the riskometer rating for HDFC Mid Cap Fund?",
        "expected_scheme": "hdfc-mid-cap-fund",
        "expected_section": "riskometer",
        "expected_snippet": "Riskometer"
    },
    {
        "query": "What is the benchmark index for HDFC Mid Cap Opportunities Fund?",
        "expected_scheme": "hdfc-mid-cap-fund",
        "expected_section": "benchmark_index",
        "expected_snippet": "NIFTY Midcap 150"
    },
    {
        "query": "Who manages HDFC Mid Cap Fund?",
        "expected_scheme": "hdfc-mid-cap-fund",
        "expected_section": "fund_management",
        "expected_snippet": "Chirag Setalvad"
    },
    {
        "query": "How do I download account statements for HDFC Mid Cap Fund on Groww?",
        "expected_scheme": "hdfc-mid-cap-fund",
        "expected_section": "statement_download_process",
        "expected_snippet": "Groww Reports"
    },
    {
        "query": "Give me an overview of HDFC Mid Cap Opportunities Fund.",
        "expected_scheme": "hdfc-mid-cap-fund",
        "expected_section": "fund_overview",
        "expected_snippet": "Mid Cap"
    },

    # --- Scheme 2: HDFC Flexi Cap Fund ---
    {
        "query": "What is the TER of HDFC Flexi Cap Direct Plan?",
        "expected_scheme": "hdfc-equity-fund",
        "expected_section": "expense_ratio",
        "expected_snippet": "0.74%"
    },
    {
        "query": "What is the exit load for HDFC Flexi Cap Fund?",
        "expected_scheme": "hdfc-equity-fund",
        "expected_section": "exit_load",
        "expected_snippet": "Exit load"
    },
    {
        "query": "Minimum lumpsum investment for HDFC Flexi Cap",
        "expected_scheme": "hdfc-equity-fund",
        "expected_section": "minimum_investment",
        "expected_snippet": "lumpsum"
    },
    {
        "query": "What is the risk rating of HDFC Flexi Cap Fund according to SEBI?",
        "expected_scheme": "hdfc-equity-fund",
        "expected_section": "riskometer",
        "expected_snippet": "Riskometer"
    },
    {
        "query": "What benchmark does HDFC Flexi Cap track?",
        "expected_scheme": "hdfc-equity-fund",
        "expected_section": "benchmark_index",
        "expected_snippet": "NIFTY 500"
    },
    {
        "query": "Who is the fund manager of HDFC Flexi Cap Fund?",
        "expected_scheme": "hdfc-equity-fund",
        "expected_section": "fund_management",
        "expected_snippet": "Prashant Jain"
    },

    # --- Scheme 3: HDFC Small Cap Fund ---
    {
        "query": "What is the expense ratio for HDFC Small Cap Fund Direct Growth?",
        "expected_scheme": "hdfc-small-cap-fund",
        "expected_section": "expense_ratio",
        "expected_snippet": "0.76%"
    },
    {
        "query": "What is the exit load period for HDFC Small Cap Fund?",
        "expected_scheme": "hdfc-small-cap-fund",
        "expected_section": "exit_load",
        "expected_snippet": "Exit load"
    },
    {
        "query": "Minimum SIP for HDFC Small Cap Fund",
        "expected_scheme": "hdfc-small-cap-fund",
        "expected_section": "minimum_investment",
        "expected_snippet": "SIP"
    },
    {
        "query": "What is the riskometer classification for HDFC Small Cap Fund?",
        "expected_scheme": "hdfc-small-cap-fund",
        "expected_section": "riskometer",
        "expected_snippet": "Riskometer"
    },
    {
        "query": "What is the benchmark of HDFC Small Cap Fund?",
        "expected_scheme": "hdfc-small-cap-fund",
        "expected_section": "benchmark_index",
        "expected_snippet": "BSE 250 SmallCap"
    },
    {
        "query": "Is there a 3-year lock-in on HDFC Small Cap Fund?",
        "expected_scheme": "hdfc-small-cap-fund",
        "expected_section": "lock_in_period",
        "expected_snippet": "no lock-in"
    },

    # --- Scheme 4: HDFC Nifty 50 Index Fund ---
    {
        "query": "Expense ratio of HDFC Nifty 50 Index Fund Direct Growth",
        "expected_scheme": "hdfc-nifty-50-index-fund",
        "expected_section": "expense_ratio",
        "expected_snippet": "0.3%"
    },
    {
        "query": "Does HDFC Nifty 50 Index Fund have an exit load?",
        "expected_scheme": "hdfc-nifty-50-index-fund",
        "expected_section": "exit_load",
        "expected_snippet": "Exit load"
    },
    {
        "query": "Minimum investment amount in HDFC NIFTY 50 Index Fund",
        "expected_scheme": "hdfc-nifty-50-index-fund",
        "expected_section": "minimum_investment",
        "expected_snippet": "SIP"
    },
    {
        "query": "What is the benchmark for HDFC Nifty 50 Index Fund?",
        "expected_scheme": "hdfc-nifty-50-index-fund",
        "expected_section": "benchmark_index",
        "expected_snippet": "NIFTY 50"
    },

    # --- Scheme 5: HDFC Balanced Advantage Fund ---
    {
        "query": "What is the expense ratio of HDFC Balanced Advantage Fund?",
        "expected_scheme": "hdfc-balanced-advantage-fund",
        "expected_section": "expense_ratio",
        "expected_snippet": "0.77%"
    },
    {
        "query": "Exit load structure for HDFC Balanced Advantage Fund",
        "expected_scheme": "hdfc-balanced-advantage-fund",
        "expected_section": "exit_load",
        "expected_snippet": "Exit load"
    },
    {
        "query": "What is the minimum SIP in HDFC Balanced Advantage Fund?",
        "expected_scheme": "hdfc-balanced-advantage-fund",
        "expected_section": "minimum_investment",
        "expected_snippet": "SIP"
    },
    {
        "query": "What is the riskometer level of HDFC Balanced Advantage Fund?",
        "expected_scheme": "hdfc-balanced-advantage-fund",
        "expected_section": "riskometer",
        "expected_snippet": "Riskometer"
    },
    {
        "query": "Where can I get capital gains statements for HDFC Balanced Advantage Fund?",
        "expected_scheme": "hdfc-balanced-advantage-fund",
        "expected_section": "statement_download_process",
        "expected_snippet": "Groww Reports"
    }
]


def evaluate_retrieval(
    pipeline: RetrievalPipeline,
    top_k: int = 3,
    verbose: bool = False
) -> Dict[str, Any]:
    """
    Evaluates retrieval pipeline across all benchmark questions.
    Returns metrics dictionary with top_1_accuracy and top_k_accuracy.
    """
    total = len(BENCHMARK_DATASET)
    top_1_hits = 0
    top_k_hits = 0
    scheme_hits = 0

    results: List[Dict[str, Any]] = []

    for item in BENCHMARK_DATASET:
        query = item["query"]
        expected_scheme = item["expected_scheme"]
        expected_section = item["expected_section"]
        expected_snippet = item["expected_snippet"]

        ret = pipeline.retrieve(query, top_k=top_k)
        chunks = ret["chunks"]

        scheme_match = ret["detected_scheme"] == expected_scheme
        if scheme_match:
            scheme_hits += 1

        top_1_match = False
        top_k_match = False

        if chunks:
            # Top-1 check
            top_rec = chunks[0]
            if (
                top_rec.section_label == expected_section and
                expected_scheme in top_rec.chunk_id
            ):
                top_1_match = True

            # Top-K check
            for rec in chunks[:top_k]:
                if (
                    rec.section_label == expected_section and
                    expected_scheme in rec.chunk_id
                ):
                    top_k_match = True
                    break

        if top_1_match:
            top_1_hits += 1
        if top_k_match:
            top_k_hits += 1

        if verbose:
            status = "PASS" if top_k_match else "FAIL"
            print(f"[{status}] Query: {query}")
            if not top_k_match:
                top_labels = [f"{r.chunk_id}:{r.section_label}" for r in chunks]
                print(f"       Expected: {expected_scheme}:{expected_section} | Got: {top_labels}")

        results.append({
            "query": query,
            "expected_scheme": expected_scheme,
            "expected_section": expected_section,
            "top_1_match": top_1_match,
            "top_k_match": top_k_match,
            "detected_scheme": ret["detected_scheme"],
            "retrieved_chunk_ids": [c.chunk_id for c in chunks]
        })

    top_1_acc = (top_1_hits / total) * 100
    top_k_acc = (top_k_hits / total) * 100
    scheme_acc = (scheme_hits / total) * 100

    return {
        "total_queries": total,
        "top_1_hits": top_1_hits,
        "top_1_accuracy": top_1_acc,
        "top_k": top_k,
        "top_k_hits": top_k_hits,
        "top_k_accuracy": top_k_acc,
        "scheme_accuracy": scheme_acc,
        "target_met": top_k_acc >= 90.0,
        "details": results
    }


if __name__ == "__main__":
    pipeline = RetrievalPipeline()
    metrics = evaluate_retrieval(pipeline, top_k=3, verbose=True)
    print("\n--- Retrieval Benchmark Results ---")
    print(f"Total Queries Tested: {metrics['total_queries']}")
    print(f"Scheme Detection Accuracy: {metrics['scheme_accuracy']:.1f}%")
    print(f"Top-1 Accuracy: {metrics['top_1_accuracy']:.1f}%")
    print(f"Top-3 Accuracy: {metrics['top_k_accuracy']:.1f}%")
    print(f"Exit Criteria (>= 90%): {'PASSED' if metrics['target_met'] else 'FAILED'}")
