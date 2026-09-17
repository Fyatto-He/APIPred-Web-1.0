#!/usr/bin/env python
"""Golden-file determinism check for the prediction pipeline.

Runs `process_genes` in-process (no HTTP server needed) and compares the
full ordered top-25 — sequence, probability, structure and MFE — against a
committed golden file. Any change that shifts a prediction or its rank
fails loudly instead of silently.

Why the *ordered* list and not just the set: for a typical query most of
the top 25 share an identical probability (the default case below has only
two distinct values across all 25), so ranks are decided by insertion
order into BoundedResultsQueue while 8 threads fold concurrently. The
reordering step in parallel_rna_folding_global is what keeps that stable.
A set comparison would not notice it breaking.

Usage (from the backend/ directory, with the venv active):

    python tests/check_determinism.py                 # fast case
    python tests/check_determinism.py --case full     # the UI's defaults, ~6 min
    python tests/check_determinism.py --case all
    python tests/check_determinism.py --twice         # also check run-to-run within one process
    python tests/check_determinism.py --update        # regenerate goldens (review the diff!)

Exit status is 0 when every selected case matches, 1 otherwise.
"""
import argparse
import json
import logging
import os
import sys
import tempfile
import time
import uuid

# Model and database paths in the backend are relative to backend/, so run
# from there regardless of where this script was invoked.
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLDEN_DIR = os.path.join(BACKEND_DIR, "tests", "golden")
os.chdir(BACKEND_DIR)
sys.path.insert(0, BACKEND_DIR)

# Point the job database at a throwaway file *before* importing main, which
# binds RESULTS_DB_PATH at import time and calls init_db(). Keeps the check
# from writing rows into the real results.db.
import utils.config as config  # noqa: E402

_TMP_DB = tempfile.NamedTemporaryFile(prefix="apipred_determinism_", suffix=".db", delete=False)
_TMP_DB.close()
config.RESULTS_DB_PATH = _TMP_DB.name

import main  # noqa: E402

# The pipeline logs per-batch progress through the uvicorn logger; quiet it
# so the check's own output is readable.
logging.getLogger("uvicorn").setLevel(logging.WARNING)


# Each case pins one set of job parameters. The amino acid query is the
# 40-residue sequence used throughout the repo's examples; it must be
# longer than LambdaVal (30) for compute_combined_pseaac to accept it.
QUERY = "ACDEFGHIKLMNPQRSTVWYACDEFGHIKLMNPQRSTVWY"

CASES = {
    # 4^8 = 65,536 variants, ~2,100 of them scored across 5 batches in
    # about 2 seconds. Deliberately sized past the 500-per-batch boundary
    # and the 25-slot result heap, and its top 25 contains a 20-way
    # probability tie — so it exercises batch handoff, heap eviction and
    # insertion-order tie-breaking, which is where ordering would break.
    "fast": {"variant_length": 8, "total_length": 30},
    # What the frontend submits by default: 4^10 = 1,048,576 variants,
    # 161,280 of them scored. ~2.5 min, so it's opt-in — run before a release.
    "full": {"variant_length": 10, "total_length": 30},
}


def run_case(params):
    """Execute one prediction job and return its comparable result."""
    job_id = str(uuid.uuid4())

    # Mirror what the /predict endpoint seeds, so the error paths inside
    # process_genes have the dict entry they expect.
    main.active_jobs[job_id] = {
        "progress": 0.0,
        "result": None,
        "start_time": None,
        "remaining_time": None,
    }

    main.process_genes(
        job_id,
        QUERY,
        config.DEFAULT_MAX_SEQUENCES,
        params["variant_length"],
        params["total_length"],
        None,  # user_email
        None,  # custom_prefix
        None,  # custom_suffix
    )

    result = main.active_jobs[job_id].get("result")
    if not result or "error" in result:
        raise RuntimeError(f"job failed: {result}")
    return normalize(result)


def normalize(result):
    """Reduce a job result to the fields whose stability we care about.

    Drops timing, job ids and progress — anything that legitimately varies
    between runs — and keeps the scientific output plus the search
    bookkeeping that explains it.
    """
    return {
        "query": result["query"],
        "prefix": result["prefix"],
        "suffix": result["suffix"],
        "variant_length": result["variant_length"],
        "total_length": result["total_length"],
        "exhaustive_search": result["exhaustive_search"],
        "valid_sequences_found": result["valid_sequences_found"],
        "predictions": [
            {
                "gene_sequence": p["gene_sequence"],
                "variant_part": p["variant_part"],
                "interaction_probability": p["score"]["interaction_probability"],
                "structure": p["structure"],
                "mfe": p["mfe"],
            }
            for p in result["predictions"]
        ],
    }


def describe_mismatch(expected, actual):
    """Return human-readable lines explaining the first differences found."""
    lines = []

    for field in ("prefix", "suffix", "exhaustive_search", "valid_sequences_found"):
        if expected.get(field) != actual.get(field):
            lines.append(f"  {field}: expected {expected.get(field)!r}, got {actual.get(field)!r}")

    exp_preds, act_preds = expected["predictions"], actual["predictions"]
    if len(exp_preds) != len(act_preds):
        lines.append(f"  prediction count: expected {len(exp_preds)}, got {len(act_preds)}")

    for rank, (e, a) in enumerate(zip(exp_preds, act_preds), start=1):
        if e != a:
            lines.append(f"  rank {rank}:")
            for key in ("gene_sequence", "interaction_probability", "structure", "mfe"):
                if e[key] != a[key]:
                    lines.append(f"    {key}: expected {e[key]!r}, got {a[key]!r}")
    return lines


def golden_path(name):
    return os.path.join(GOLDEN_DIR, f"determinism_{name}.json")


def main_cli():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--case", choices=list(CASES) + ["all"], default="fast",
                        help="which case to run (default: fast)")
    parser.add_argument("--update", action="store_true",
                        help="overwrite the golden files with this run's output")
    parser.add_argument("--twice", action="store_true",
                        help="run each case twice in one process and require identical output")
    args = parser.parse_args()

    names = list(CASES) if args.case == "all" else [args.case]
    failures = []

    for name in names:
        params = CASES[name]
        print(f"[{name}] variant_length={params['variant_length']} "
              f"total_length={params['total_length']} ...", flush=True)

        started = time.time()
        actual = run_case(params)
        elapsed = time.time() - started
        print(f"[{name}] {actual['valid_sequences_found']} sequences scored, "
              f"{len(actual['predictions'])} returned in {elapsed:.1f}s")

        if args.twice:
            if run_case(params) == actual:
                print(f"[{name}] repeat run identical: PASS")
            else:
                print(f"[{name}] repeat run DIFFERS — output is not stable within a single process")
                failures.append(name)
                continue

        path = golden_path(name)

        if args.update:
            os.makedirs(GOLDEN_DIR, exist_ok=True)
            with open(path, "w") as fh:
                json.dump(actual, fh, indent=2)
                fh.write("\n")
            print(f"[{name}] wrote {os.path.relpath(path, BACKEND_DIR)}")
            continue

        if not os.path.exists(path):
            print(f"[{name}] no golden file at {os.path.relpath(path, BACKEND_DIR)} "
                  f"— create it with --update")
            failures.append(name)
            continue

        with open(path) as fh:
            expected = json.load(fh)

        if expected == actual:
            print(f"[{name}] matches golden file: PASS")
        else:
            print(f"[{name}] DIFFERS from golden file:")
            for line in describe_mismatch(expected, actual):
                print(line)
            failures.append(name)

    if failures:
        print(f"\nFAILED: {', '.join(failures)}")
        return 1

    print("\nOK" if not args.update else "\nGolden files updated — review the diff before committing.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main_cli())
    finally:
        os.unlink(_TMP_DB.name)
