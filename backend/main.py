import uuid
import time
import logging
import json
import os
import random
import signal
import sys
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
from fastapi import FastAPI, HTTPException, BackgroundTasks, Query, APIRouter
from fastapi.middleware.cors import CORSMiddleware
import RNA  # ViennaRNA library
from models.predictor import APIPred
import sqlite3
from itertools import product
import numpy as np
import threading

from utils.config import (
    RESULTS_DB_PATH,
    RESULTS_RETENTION_DAYS,
    EMAIL_ENABLED,
    EMAIL_SERVER,
    EMAIL_PORT,
    EMAIL_USER,
    EMAIL_PASSWORD,
    EMAIL_FROM,
    DEFAULT_VARIANT_LENGTH,
    DEFAULT_TOTAL_LENGTH,
    DEFAULT_MAX_SEQUENCES,
    MAX_TOTAL_LENGTH,
    MAX_RNA_WORKERS,
    RNA_FOLDING_BATCH_SIZE,
    PREFIX_SOURCE,
    SUFFIX_SOURCE,
)
from utils.constraints import (
    CONSECUTIVE_IDENTICAL,
    CONSECUTIVE_GC,
    ultra_fast_gc_content_check,
    ultra_fast_sequence_constraints_check,
    batch_constraint_checking,
    has_too_many_consecutive_identical,
    has_too_many_consecutive_gc,
    has_acceptable_gc_content,
    sequence_meets_constraints,
)
from utils.sequence_utils import calculate_prefix_suffix_lengths, get_prefix_suffix
from utils.schemas import InputData
from utils.results_queue import BoundedResultsQueue

# Configure logging
logger = logging.getLogger("uvicorn")
logger.setLevel(logging.INFO)

# Load DNA folding parameters (Mathews 2004) so RNA.fold() uses DNA thermodynamics.
# The model is trained on DNA folding, so structures must match that.
DNA_PARAMS_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "ViennaRNA-master", "ViennaRNA-master", "misc", "dna_mathews2004.par"
)
try:
    RNA.params_load(DNA_PARAMS_PATH)
    logger.info(f"Loaded DNA folding parameters from {DNA_PARAMS_PATH}")
except Exception as _dna_param_err:
    logger.error(f"Failed to load DNA parameters from {DNA_PARAMS_PATH}: {_dna_param_err}. "
                 f"Folding will fall back to default RNA parameters.")

# GLOBAL THREAD POOL - Create once, reuse forever
GLOBAL_RNA_EXECUTOR = ThreadPoolExecutor(max_workers=MAX_RNA_WORKERS, thread_name_prefix="RNA_")

app = FastAPI(title="Aptamer Prediction API", version="2.0")
origins = [
    "http://localhost",         # your console says origin is "http://localhost"
    "http://localhost:3000",    # if you ever run on :3000
    "http://141.142.220.151",   # your VM's HTTP
    "https://141.142.220.151",  # if you use TLS
    "https://apipred.ncsa.illinois.edu",  # production hostname (HTTPS)
    "http://apipred.ncsa.illinois.edu",   # redirected to HTTPS, but allow for safety
    # …or just "*" for quick testing (not recommended long‑term)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize predictor
predictor = APIPred()

# Initialize database
def init_db():
    conn = sqlite3.connect(RESULTS_DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS jobs (
        job_id TEXT PRIMARY KEY,
        status TEXT,
        progress REAL,
        created_at TEXT,
        completed_at TEXT,
        user_email TEXT,
        query TEXT,
        result TEXT
    )
    ''')
    conn.commit()
    conn.close()
    logger.info("Database initialized")

# Call init_db on startup
init_db()

# In-memory jobs dictionary for tracking active jobs
active_jobs = {}

# Throttle for per-batch / per-tick progress logs. Suppresses log lines whose
# (job_id, key) was emitted less than `interval` seconds ago — so per-batch logs
# emit at most once per second per category instead of multiple times per batch.
def _should_log_now(job_id, key, interval=1.0):
    if not job_id or job_id not in active_jobs:
        return True
    last = active_jobs[job_id].setdefault("_log_ts", {})
    now = time.time()
    if now - last.get(key, 0.0) >= interval:
        last[key] = now
        return True
    return False

def save_job_to_db(job_id, status, progress, query, user_email=None, result=None):
    try:
        conn = sqlite3.connect(RESULTS_DB_PATH)
        cursor = conn.cursor()
        
        # Check if job exists
        cursor.execute("SELECT job_id FROM jobs WHERE job_id = ?", (job_id,))
        job = cursor.fetchone()
        
        now = datetime.now().isoformat()
        completed_at = now if status in ["Completed", "Failed", "Terminated"] else None
        
        if job:
            # Update existing job
            cursor.execute('''
            UPDATE jobs SET 
                status = ?,
                progress = ?,
                completed_at = ?,
                result = ?
            WHERE job_id = ?
            ''', (status, progress, completed_at, json.dumps(result) if result else None, job_id))
        else:
            # Create new job
            cursor.execute('''
            INSERT INTO jobs (job_id, status, progress, created_at, completed_at, user_email, query, result)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                job_id, 
                status, 
                progress, 
                now, 
                completed_at,
                user_email,
                query,
                json.dumps(result) if result else None
            ))
            
        conn.commit()
        conn.close()
        # Throttle mid-run "Processing" saves; always log terminal states.
        if status != "Processing" or _should_log_now(job_id, "db_save"):
            logger.info(f"Saved job {job_id} to database with status {status}")
    except Exception as e:
        logger.error(f"Error saving job to database: {e}")

def cleanup_old_jobs():
    try:
        cutoff_date = (datetime.now() - timedelta(days=RESULTS_RETENTION_DAYS)).isoformat()
        
        conn = sqlite3.connect(RESULTS_DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM jobs WHERE created_at < ?", (cutoff_date,))
        deleted_count = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        logger.info(f"Cleaned up {deleted_count} old jobs")
    except Exception as e:
        logger.error(f"Error cleaning up old jobs: {e}")

def update_time_estimate(job_id: str, current_progress: float, elapsed_time: float, batch_size: int = 100, total_sequences: int = None):
    """
    Update the estimated remaining time with improved initial handling.
    """
    if job_id not in active_jobs:
        return
        
    # Get previous estimates
    previous_estimate = active_jobs[job_id].get("remaining_time")
    previous_speed = active_jobs[job_id].get("processing_speed")
    
    current_time = time.time()
    
    # Improved batch tracking - handle first batch case
    if "batch_count" not in active_jobs[job_id]:
        active_jobs[job_id]["batch_count"] = 0
        active_jobs[job_id]["first_batch_time"] = current_time
    
    active_jobs[job_id]["batch_count"] += 1
    batch_count = active_jobs[job_id]["batch_count"]
    
    # Calculate speed differently for first few batches
    if batch_count == 1:
        # First batch - no speed calculation yet
        active_jobs[job_id]["last_batch_time"] = current_time
        active_jobs[job_id]["last_batch_count"] = batch_size
        return
    elif batch_count == 2:
        # Second batch - use time since first batch
        if "first_batch_time" in active_jobs[job_id]:
            batch_elapsed = current_time - active_jobs[job_id]["first_batch_time"]
            if batch_elapsed > 0:
                # Speed based on processing 2 batches
                current_speed = (batch_size * 2) / batch_elapsed
                active_jobs[job_id]["processing_speed"] = current_speed
                logger.info(f"Job {job_id}: Initial speed estimate: {current_speed:.2f} sequences/sec")
    else:
        # Subsequent batches - use previous batch timing
        if "last_batch_time" in active_jobs[job_id]:
            batch_elapsed = current_time - active_jobs[job_id]["last_batch_time"]
            if batch_elapsed > 0:
                current_speed = batch_size / batch_elapsed
                
                # Apply EMA smoothing
                if previous_speed is not None:
                    new_speed = previous_speed * 0.7 + current_speed * 0.3  # More responsive
                else:
                    new_speed = current_speed
                    
                active_jobs[job_id]["processing_speed"] = new_speed
    
    # Calculate remaining time with more lenient conditions
    current_speed = active_jobs[job_id].get("processing_speed")
    if current_speed and current_speed > 0 and total_sequences and current_progress > 0 and current_progress < 98:
        remaining_work = 100 - current_progress
        new_estimate = (remaining_work / 100) * (total_sequences / current_speed)
        
        # Apply reasonable bounds (between 10 seconds and 24 hours)
        new_estimate = max(10, min(60000000, new_estimate))
        
        # Smooth with previous estimate if available
        if previous_estimate is not None and previous_estimate > 0:
            # More aggressive smoothing for more stable estimates
            new_estimate = previous_estimate * 0.6 + new_estimate * 0.4
        
        active_jobs[job_id]["remaining_time"] = new_estimate
        if _should_log_now(job_id, "eta"):
            logger.info(f"Job {job_id}: Updated time estimate: {new_estimate:.1f}s at {current_progress:.1f}% progress")
    elif current_progress > 0 and not current_speed:
        # Fallback: rough estimate based on elapsed time and progress
        if elapsed_time > 5:  # Only after 5 seconds of processing
            estimated_total_time = elapsed_time / (current_progress / 100)
            remaining_estimate = estimated_total_time - elapsed_time
            remaining_estimate = max(10, min(60000000, remaining_estimate))
            active_jobs[job_id]["remaining_time"] = remaining_estimate
            if _should_log_now(job_id, "eta"):
                logger.info(f"Job {job_id}: Fallback time estimate: {remaining_estimate:.1f}s")
    
    # Update batch tracking
    active_jobs[job_id]["last_batch_time"] = current_time
    active_jobs[job_id]["last_batch_count"] = batch_size

def calculate_weighted_progress(processed, total, phase):
    """
    Calculate weighted progress that accounts for sequence processing complexity.
    
    Parameters:
    - processed: Number of items processed
    - total: Total items to process
    - phase: 0 for early phase, 1 for middle phase, 2 for final phase
    """
    raw_progress = (processed / total) * 100
    
    # Apply phase-based weighting to account for increasing complexity
    if phase == 0:  # Early phase (first 20%)
        # Early progress moves faster than reality
        return min(20, raw_progress * 1.5)
    elif phase == 1:  # Middle phase (20-80%)
        # Middle progress slows down
        middle_portion = min(60, max(0, raw_progress - 13.33))
        return 20 + (middle_portion * 0.8)
    else:  # Final phase (last 20%)
        # Final progress is even slower
        return min(99, 80 + (max(0, (raw_progress - 80)) * 0.95))

# RNA folding functions with global thread pool
def fold_single_rna(sequence):
    """
    Fold a single RNA sequence with improved error handling.
    """
    try:
        # Add basic validation
        if not sequence or not isinstance(sequence, str):
            logger.error(f"Invalid sequence provided to fold_single_rna: {sequence}")
            return sequence or "", "", 0.0
            
        # Fold DNA directly using DNA thermodynamic parameters (loaded at module init)
        structure, mfe = RNA.fold(sequence)
        return sequence, structure, mfe
    except Exception as e:
        logger.error(f"Error folding RNA sequence {sequence[:20] if sequence else 'None'}...: {e}")
        return sequence or "", "", 0.0

def parallel_rna_folding_global(sequences, job_id=None):
    """
    FIXED: Parallel RNA folding using global thread pool.
    Processes multiple sequences concurrently for 3-4x speedup.
    
    Args:
        sequences: List of DNA sequences to fold
        job_id: Optional job ID for termination checking
        
    Returns:
        List of tuples (sequence, structure, mfe), and success flag
    """
    if not sequences:
        return [], True
    
    if len(sequences) == 1:
        # For single sequence, no need for parallel processing
        return [fold_single_rna(sequences[0])], True
    
    # Helper function to check for termination
    def should_terminate():
        if job_id and job_id in active_jobs:
            return active_jobs[job_id].get("terminated", False)
        return False
    
    # Check for termination before starting
    if should_terminate():
        logger.info(f"Job {job_id}: Termination detected before parallel RNA folding")
        return [fold_single_rna(seq) for seq in sequences], False  # Fallback to sequential
    
    results = []
    
    try:
        # Use global thread pool - no more resource exhaustion!
        future_to_sequence = {}
        submitted_count = 0
        
        for seq in sequences:
            # Check for termination before each submission
            if should_terminate():
                logger.info(f"Job {job_id}: Termination detected during task submission after {submitted_count} tasks")
                break
            
            try:
                future = GLOBAL_RNA_EXECUTOR.submit(fold_single_rna, seq)
                future_to_sequence[future] = seq
                submitted_count += 1
            except Exception as e:
                logger.error(f"Job {job_id}: Error submitting RNA folding task: {e}")
                break
        
        # If no futures were submitted (due to early termination), fallback to sequential
        if not future_to_sequence:
            logger.info(f"Job {job_id}: No futures submitted, using sequential processing")
            return [fold_single_rna(seq) for seq in sequences if not should_terminate()], False
        
        # Collect results as they complete with timeout and termination checking
        completed_count = 0
        total_futures = len(future_to_sequence)
        
        try:
            # Use as_completed with timeout to avoid hanging
            for future in as_completed(future_to_sequence, timeout=60):  # 60 second timeout for the entire batch
                # Check for termination periodically
                if should_terminate():
                    logger.info(f"Job {job_id}: Termination detected during result collection ({completed_count}/{total_futures} completed)")
                    break
                
                seq = future_to_sequence[future]
                try:
                    result = future.result(timeout=15)  # 15 second timeout per individual task
                    results.append(result)
                    completed_count += 1
                except TimeoutError:
                    logger.warning(f"Job {job_id}: Timeout folding sequence {seq[:20]}..., using fallback")
                    results.append((seq, "", 0.0))
                    completed_count += 1
                except Exception as e:
                    logger.error(f"Job {job_id}: Error in parallel RNA folding for sequence {seq[:20]}...: {e}")
                    # Add fallback result
                    results.append((seq, "", 0.0))
                    completed_count += 1
                    
        except TimeoutError:
            logger.warning(f"Job {job_id}: Timeout in as_completed after {completed_count}/{total_futures} completed")
            # Process any remaining sequences sequentially
            remaining_sequences = [seq for future, seq in future_to_sequence.items() 
                                 if not future.done()]
            if remaining_sequences and not should_terminate():
                logger.info(f"Job {job_id}: Processing {len(remaining_sequences)} remaining sequences sequentially")
                for seq in remaining_sequences[:10]:  # Limit to first 10 to avoid long delays
                    if should_terminate():
                        break
                    try:
                        results.append(fold_single_rna(seq))
                    except Exception as e:
                        logger.error(f"Job {job_id}: Error in sequential fallback for {seq[:20]}...: {e}")
                        results.append((seq, "", 0.0))
        except Exception as collection_error:
            logger.error(f"Job {job_id}: Error in result collection: {collection_error}")
            # Process remaining sequences sequentially as fallback
            unprocessed_sequences = [seq for seq in sequences if not any(r[0] == seq for r in results)]
            if unprocessed_sequences and not should_terminate():
                logger.info(f"Job {job_id}: Processing {len(unprocessed_sequences)} unprocessed sequences sequentially")
                for seq in unprocessed_sequences[:10]:  # Limit to avoid delays
                    if should_terminate():
                        break
                    try:
                        results.append(fold_single_rna(seq))
                    except Exception as e:
                        logger.error(f"Job {job_id}: Error in fallback processing for {seq[:20]}...: {e}")
                        results.append((seq, "", 0.0))
        
        # Sort results to maintain original order if possible
        if results and not should_terminate():
            try:
                sequence_to_result = {result[0]: result for result in results}
                ordered_results = []
                for seq in sequences:
                    if seq in sequence_to_result:
                        ordered_results.append(sequence_to_result[seq])
                    elif not should_terminate():
                        # Fill in missing sequences with empty results
                        ordered_results.append((seq, "", 0.0))
                return ordered_results, True
            except Exception as ordering_error:
                logger.warning(f"Job {job_id}: Error ordering results, returning as-is: {ordering_error}")
                return results, True
        else:
            return results, True
        
    except Exception as e:
        logger.error(f"Job {job_id}: Critical error in parallel RNA folding setup: {e}")
        # Fallback to sequential processing
        logger.info(f"Job {job_id}: Falling back to sequential RNA folding")
        try:
            sequential_results = []
            for seq in sequences:
                if should_terminate():
                    break
                try:
                    sequential_results.append(fold_single_rna(seq))
                except Exception as seq_error:
                    logger.error(f"Job {job_id}: Error in sequential fallback for {seq[:20]}...: {seq_error}")
                    sequential_results.append((seq, "", 0.0))
            return sequential_results, False
        except Exception as fallback_error:
            logger.error(f"Job {job_id}: Even sequential fallback failed: {fallback_error}")
            # Return empty structures for all sequences
            return [(seq, "", 0.0) for seq in sequences], False

def benchmark_rna_folding_performance(sequences, max_workers=MAX_RNA_WORKERS):
    """
    Benchmark parallel vs sequential RNA folding performance.
    """
    import time
    
    if len(sequences) < 10:
        return {"error": "Need at least 10 sequences for meaningful benchmark"}
    
    # Test sequential folding
    start_time = time.time()
    sequential_results = [fold_single_rna(seq) for seq in sequences]
    sequential_time = time.time() - start_time
    
    # Test parallel folding
    start_time = time.time()
    parallel_results, success = parallel_rna_folding_global(sequences)
    parallel_time = time.time() - start_time
    
    # Verify results match
    results_match = len(sequential_results) == len(parallel_results)
    if results_match:
        for seq_res, par_res in zip(sequential_results, parallel_results):
            if seq_res[0] != par_res[0]:  # Check sequence matches
                results_match = False
                break
    
    speedup = sequential_time / parallel_time if parallel_time > 0 else 1.0
    
    return {
        "sequences_tested": len(sequences),
        "sequential_time": f"{sequential_time:.4f}s",
        "parallel_time": f"{parallel_time:.4f}s",
        "speedup": f"{speedup:.2f}x",
        "results_match": results_match,
        "workers_used": max_workers,
        "parallel_success": success
    }

# FIXED: Updated batch processing function with global thread pool
def process_sequence_batch(batch_sequences, batch_variants, precomputed_aa_features, job_id=None):
    """
    Process a batch of sequences with optimized constraint checking and global thread pool RNA folding.
    """
    if not batch_sequences:
        return []
        
    batch_results = []
    
    # Helper function to check for termination
    def should_terminate():
        if job_id and job_id in active_jobs:
            return active_jobs[job_id].get("terminated", False)
        return False
    
    # Early termination check
    if should_terminate():
        logger.info(f"Job {job_id}: Termination detected at start of batch processing")
        return []
    
    try:
        # OPTIMIZATION 1: Ultra-fast constraint pre-filtering
        valid_indices = []
        valid_sequences = []
        valid_variants = []
        
        constraint_start = time.time()
        for i, sequence in enumerate(batch_sequences):
            if should_terminate():
                logger.info(f"Job {job_id}: Termination detected during constraint checking")
                break
            if ultra_fast_sequence_constraints_check(sequence):
                valid_indices.append(i)
                valid_sequences.append(sequence)
                valid_variants.append(batch_variants[i])
        constraint_time = time.time() - constraint_start
        
        if not valid_sequences or should_terminate():
            if not valid_sequences and _should_log_now(job_id, "batch_summary"):
                logger.info(f"Job {job_id}: No sequences passed constraints in this batch (checked in {constraint_time:.3f}s)")
            return []

        # OPTIMIZATION 2: Get batch predictions using optimized batch processing
        if should_terminate():
            logger.info(f"Job {job_id}: Termination detected before ML predictions")
            return []

        prediction_start = time.time()
        batch_scores = predictor.predict_batch(valid_sequences, precomputed_aa_features)
        prediction_time = time.time() - prediction_start

        # OPTIMIZATION 3: Global thread pool RNA folding with termination checking
        if should_terminate():
            logger.info(f"Job {job_id}: Termination detected before RNA folding")
            return []

        rna_start = time.time()
        if len(valid_sequences) >= 5:  # Use parallel folding for 5+ sequences
            rna_results, parallel_success = parallel_rna_folding_global(valid_sequences, job_id=job_id)
            parallel_used = parallel_success
        else:
            # Sequential for small batches
            rna_results = []
            for seq in valid_sequences:
                if should_terminate():
                    break
                rna_results.append(fold_single_rna(seq))
            parallel_used = False
        rna_time = time.time() - rna_start

        # Throttled: combine constraint / ML / RNA-folding stats into one line per second
        if _should_log_now(job_id, "batch_summary"):
            logger.info(
                f"Job {job_id}: batch — constraints {len(valid_sequences)}/{len(batch_sequences)} "
                f"({constraint_time:.3f}s) | ML {prediction_time:.3f}s | RNA {rna_time:.3f}s "
                f"({'parallel' if parallel_used else 'sequential'})"
            )
        
        # Final termination check before combining results
        if should_terminate():
            logger.info(f"Job {job_id}: Termination detected before combining results")
            return []
        
        # Combine results
        for i, (sequence, variant, score) in enumerate(zip(valid_sequences, valid_variants, batch_scores)):
            if should_terminate():
                logger.info(f"Job {job_id}: Termination detected during result combination")
                break
                
            try:
                # Get RNA folding result
                if i < len(rna_results):
                    _, structure, mfe = rna_results[i]
                else:
                    # Fallback
                    try:
                        structure, mfe = RNA.fold(sequence)
                    except Exception as rna_error:
                        logger.error(f"Job {job_id}: RNA folding fallback failed for {sequence[:20]}...: {rna_error}")
                        structure, mfe = "", 0.0
                
                batch_results.append({
                    "gene_sequence": sequence,
                    "score": score,
                    "structure": structure,
                    "mfe": mfe,
                    "variant_part": variant
                })
            except Exception as struct_error:
                logger.error(f"Error processing structure for sequence in job {job_id}: {struct_error}")
                continue
                
    except Exception as batch_error:
        logger.error(f"Error processing optimized batch in job {job_id}: {batch_error}")
        # Fallback to individual processing
        for sequence, variant in zip(batch_sequences, batch_variants):
            if should_terminate():
                break
                
            try:
                # Check constraints first
                if not ultra_fast_sequence_constraints_check(sequence):
                    continue
                    
                score = predictor.predict(sequence, precomputed_aa_features.get('amino_acid_sequence', ''))
                try:
                    structure, mfe = RNA.fold(sequence)
                except Exception as rna_error:
                    logger.error(f"Job {job_id}: Individual RNA folding failed for {sequence[:20]}...: {rna_error}")
                    structure, mfe = "", 0.0
                    
                batch_results.append({
                    "gene_sequence": sequence,
                    "score": score,
                    "structure": structure,
                    "mfe": mfe,
                    "variant_part": variant
                })
            except Exception as individual_error:
                logger.error(f"Error processing individual sequence in job {job_id}: {individual_error}")
                continue
                
    return batch_results

def process_genes(job_id: str, aa_sequence: str, max_sequences: int, variant_length: int, total_length: int, user_email: str = None, custom_prefix: str = None, custom_suffix: str = None):
    # FIXED: Enhanced termination checking function
    def check_if_terminated():
        # First check in-memory flag
        if job_id in active_jobs and active_jobs[job_id].get("terminated", False):
            return True
            
        # Then check database (in case terminated through another process)
        try:
            conn = sqlite3.connect(RESULTS_DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT status FROM jobs WHERE job_id = ?", (job_id,))
            db_status = cursor.fetchone()
            conn.close()
            
            if db_status and db_status[0] == "Terminated":
                # Update in-memory flag
                if job_id in active_jobs:
                    active_jobs[job_id]["terminated"] = True
                    active_jobs[job_id]["progress"] = 100.0
                logger.info(f"Job {job_id}: Detected termination status from database")
                return True
        except Exception as e:
            logger.error(f"Error checking termination status for job {job_id}: {e}")
            
        return False

    # FIXED: Improved signal handling
    def signal_handler(signum, frame):
        """Handle termination signals gracefully"""
        logger.info(f"Job {job_id}: Received termination signal {signum}")
        if job_id in active_jobs:
            active_jobs[job_id]["terminated"] = True
        # Don't call sys.exit() as it can cause the executor error
        
    # Register signal handlers
    try:
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
    except Exception as signal_error:
        logger.warning(f"Job {job_id}: Could not register signal handlers: {signal_error}")

    # Helper function to handle termination
    def handle_termination(processed_count, valid_count, current_results, is_exhaustive=True):
        logger.info(f"Job {job_id}: Processing terminated at {processed_count} sequences processed")
        
        # FIX 1: Use bounded results queue for termination handling
        if current_results.size() > 0:
            top_results = current_results.get_top_results()
            
            result_data = {
                "query": aa_sequence,
                "predictions": top_results,
                "sequences_processed": processed_count, 
                "valid_sequences_found": valid_count,
                "exhaustive_search": is_exhaustive,
                "prefix": prefix,
                "suffix": suffix,
                "variant_length": variant_length,
                "total_length": total_length,
                "status": "Terminated",
                "message": "Job was terminated before completion. Showing partial results."
            }
            
            # IMMEDIATELY store in memory
            active_jobs[job_id]["result"] = result_data
            
            # IMMEDIATELY save to database
            save_job_to_db(job_id, "Terminated", 100.0, aa_sequence, user_email, result_data)
            
            logger.info(f"Job {job_id}: Termination complete with {len(top_results)} results stored")
        else:
            # Even if no results, store the termination status
            result_data = {
                "query": aa_sequence,
                "predictions": [],
                "sequences_processed": processed_count, 
                "valid_sequences_found": valid_count,
                "exhaustive_search": is_exhaustive,
                "status": "Terminated",
                "message": "Job was terminated before any results could be generated."
            }
            active_jobs[job_id]["result"] = result_data
            save_job_to_db(job_id, "Terminated", 100.0, aa_sequence, user_email, result_data)
            logger.info(f"Job {job_id}: Termination complete with no results")

    try:
        # Update job status in database
        save_job_to_db(job_id, "Processing", 0.0, aa_sequence, user_email)
        
        # Generate prefix and suffix based on the lengths
        if custom_prefix is not None and custom_suffix is not None:
            prefix = custom_prefix.upper()
            suffix = custom_suffix.upper()
            actual_variant_length = variant_length
            actual_total_length = len(prefix) + actual_variant_length + len(suffix)
            logger.info(f"Job {job_id}: Using custom prefix '{prefix}' and suffix '{suffix}'")
        else:
            prefix, suffix = get_prefix_suffix(total_length, variant_length)
            actual_variant_length = variant_length
            actual_total_length = total_length
            logger.info(f"Job {job_id}: Using default prefix '{prefix}' and suffix '{suffix}'")
        
        # OPTIMIZATION 1: Precompute AA sequence features once
        logger.info(f"Job {job_id}: Precomputing amino acid features...")
        aa_sequence_clean = aa_sequence.replace(" ", "").upper()
        precomputed_aa_features = predictor.precompute_aa_features(aa_sequence_clean)
        logger.info(f"Job {job_id}: AA features precomputed successfully")
        
        # Use dynamic sequence generation
        bases = ['A', 'G', 'C', 'T']
        total_possible = 4 ** variant_length
        total_sequences = min(max_sequences, total_possible)
        
        logger.info(f"Job {job_id}: Processing {total_sequences} sequences with optimizations - "
                   f"DMatrix: enabled, "
                   f"Global RNA Pool: {MAX_RNA_WORKERS} workers")
        
        # Initialize enhanced job tracking parameters
        active_jobs[job_id] = {
            "progress": 0.0, 
            "result": None, 
            "start_time": time.time(),
            "remaining_time": None,
            "processing_speed": None,
            "last_batch_time": time.time(),
            "last_batch_count": 0,
            "batch_sizes": [],
            "sample_times": [],
            "sample_counts": [],
            "terminated": False,
            "optimizations_used": {
                "vectorized_constraints": True,
                "dmatrix_api": True,
                "global_rna_pool": True
            }
        }
        
        # OPTIMIZATION 2: Enhanced batch processing configuration
        batch_size = 500  # Process 500 sequences at once - experiment with this value
        progress_batch_size = 100  # Update progress every 100 sequences
        batch_count = 0
        adaptive_sampling = True
        
    except Exception as e:
        error_msg = f"Error initializing sequence generation: {e}"
        active_jobs[job_id]["result"] = {"error": error_msg}
        save_job_to_db(job_id, "Failed", 100.0, aa_sequence, user_email, {"error": error_msg})
        logger.error(f"Error initializing sequence generation for job {job_id}: {e}")
        return

    # FIX 1: Replace unbounded results list with bounded queue
    results = BoundedResultsQueue(max_size=25)
    start_time = time.time()
    active_jobs[job_id]["start_time"] = start_time

    # Calculate fixed GC content from prefix and suffix for filtering
    fixed_gc = sum(1 for base in prefix + suffix if base in ['G', 'C'])
    fixed_length = len(prefix) + len(suffix)
    total_bases = fixed_length + actual_variant_length
    min_gc_total = int(0.47 * total_bases)
    max_gc_total = int(0.55 * total_bases)
    min_gc_variant = max(0, min_gc_total - fixed_gc)
    max_gc_variant = min(actual_variant_length, max_gc_total - fixed_gc)
    
    logger.info(f"Job {job_id}: Target GC content in variant region: {min_gc_variant}-{max_gc_variant} "
                f"out of {actual_variant_length} bases")
    
    try:
        # Initial termination check
        if check_if_terminated():
            logger.info(f"Job {job_id}: Terminated before processing began")
            handle_termination(0, 0, results, True)
            return
            
        # Determine if exhaustive search is feasible
        use_exhaustive = variant_length <= 16
        
        # OPTIMIZATION 2: Batch processing variables
        current_batch_sequences = []
        current_batch_variants = []
        
        if use_exhaustive:
            # EXHAUSTIVE APPROACH WITH ALL OPTIMIZATIONS
            sequence_generator = product(bases, repeat=variant_length)
            valid_sequence_count = 0
            
            for idx, seq_tuple in enumerate(sequence_generator):
                # Check for termination MORE FREQUENTLY (every 10 iterations)
                if idx % 10 == 0 and check_if_terminated():
                    # Process remaining batch before terminating
                    if current_batch_sequences:
                        batch_results = process_sequence_batch(current_batch_sequences, current_batch_variants, precomputed_aa_features, job_id)
                        # FIX 1: Use bounded queue instead of extend
                        results.add_results(batch_results)
                        valid_sequence_count += len(batch_results)
                    handle_termination(idx, valid_sequence_count, results, True)
                    return
                
                # Form the variant part
                variant_part = ''.join(seq_tuple)
                
                # Quick GC content check before full validation
                variant_gc = sum(1 for base in variant_part if base in ['G', 'C'])
                if not (min_gc_variant <= variant_gc <= max_gc_variant):
                    continue
                
                # Form the complete sequence
                complete_sequence = f"{prefix}{variant_part}{suffix}"
                
                # OPTIMIZATION: Use ultra-fast constraint checking
                if not ultra_fast_sequence_constraints_check(complete_sequence):
                    continue
                
                # Add to current batch
                current_batch_sequences.append(complete_sequence)
                current_batch_variants.append(variant_part)
                
                # Process batch when it reaches batch_size
                if len(current_batch_sequences) >= batch_size:
                    batch_results = process_sequence_batch(current_batch_sequences, current_batch_variants, precomputed_aa_features, job_id)
                    # FIX 1: Use bounded queue instead of extend
                    results.add_results(batch_results)
                    valid_sequence_count += len(batch_results)
                    
                    # Clear batch
                    current_batch_sequences = []
                    current_batch_variants = []

                # Break if we've reached the maximum number of sequences
                if valid_sequence_count >= total_sequences:
                    break

                # Update progress periodically
                if idx % progress_batch_size == 0:
                    # Determine phase based on progress
                    linear_progress = min(100.0 * idx / max(total_sequences, 1), 100.0)

                    # Optional: keep your fancy curve ONLY for display
                    phase = 0 if linear_progress < 20 else (1 if linear_progress < 80 else 2)
                    display_progress = calculate_weighted_progress(idx, total_sequences, phase)

                    # Store display progress
                    active_jobs[job_id]["progress"] = display_progress

                    # Use LINEAR progress for ETA
                    update_time_estimate(
                        job_id,
                        linear_progress,
                        time.time() - start_time,
                        progress_batch_size,
                        total_sequences,
                    )
                    
                    # Store partial results in memory
                    if results.size() > 0:
                        # FIX 1: Use bounded queue's get_top_results instead of sorting
                        top_partial = results.get_top_results()
                        partial_result = {
                            "query": aa_sequence_clean,
                            "predictions": top_partial,
                            "sequences_processed": idx,
                            "valid_sequences_found": valid_sequence_count,
                            "exhaustive_search": True,
                            "prefix": prefix,
                            "suffix": suffix,
                            "variant_length": variant_length,
                            "total_length": total_length,
                            "status": "Processing"
                        }
                        active_jobs[job_id]["partial_result"] = partial_result
                    
                    # Update progress in database periodically
                    if (idx // progress_batch_size) % 5 == 0:
                        save_job_to_db(job_id, "Processing", display_progress, aa_sequence_clean, user_email)
                    
                    # Throttled progress logging (~1s cadence)
                    if _should_log_now(job_id, "progress"):
                        logger.info(f"Job {job_id}: Progress update - idx={idx}, progress={display_progress:.2f}%, "
                                   f"valid_sequences={valid_sequence_count}")
            
            # Process any remaining sequences in the final batch
            if current_batch_sequences and not check_if_terminated():
                batch_results = process_sequence_batch(current_batch_sequences, current_batch_variants, precomputed_aa_features, job_id)
                # FIX 1: Use bounded queue instead of extend
                results.add_results(batch_results)
                valid_sequence_count += len(batch_results)
                
        else:
            # OPTIMIZED APPROACH WITH ALL OPTIMIZATIONS
            total_possible = 4 ** variant_length
            total_sequences = min(max_sequences, total_possible)
            processed_count = 0
            valid_sequence_count = 0
            sequence_count = 0
            
            # Generate all possible GC compositions that meet our content constraint
            valid_gc_counts = list(range(min_gc_variant, max_gc_variant + 1))
            tried_variants = set()
            
            # Keep trying until we reach our limit
            while sequence_count < total_sequences:
                # Check for termination MORE FREQUENTLY
                if processed_count % 10 == 0 and check_if_terminated():
                    # Process remaining batch before terminating
                    if current_batch_sequences:
                        batch_results = process_sequence_batch(current_batch_sequences, current_batch_variants, precomputed_aa_features, job_id)
                        # FIX 1: Use bounded queue instead of extend
                        results.add_results(batch_results)
                        valid_sequence_count += len(batch_results)
                    handle_termination(processed_count, valid_sequence_count, results, False)
                    return
                    
                processed_count += 1
                
                # Pick a random valid GC count
                if not valid_gc_counts:
                    valid_gc_counts = list(range(min_gc_variant, max_gc_variant + 1))
                    
                gc_count = random.choice(valid_gc_counts)
                
                # Create a sequence with this GC content
                g_count = random.randint(0, gc_count)
                c_count = gc_count - g_count
                a_count = random.randint(0, variant_length - gc_count)
                t_count = variant_length - gc_count - a_count
                
                # Create a list of bases with this composition
                bases_list = ['G'] * g_count + ['C'] * c_count + ['A'] * a_count + ['T'] * t_count
                
                # Try shuffling to find a valid sequence
                for _ in range(5):  # Limit shuffle attempts
                    if check_if_terminated():
                        if current_batch_sequences:
                            batch_results = process_sequence_batch(current_batch_sequences, current_batch_variants, precomputed_aa_features, job_id)
                            # FIX 1: Use bounded queue instead of extend
                            results.add_results(batch_results)
                            valid_sequence_count += len(batch_results)
                        handle_termination(processed_count, valid_sequence_count, results, False)
                        return
                        
                    random.shuffle(bases_list)
                    variant_part = ''.join(bases_list)
                    
                    # Skip if we've already tried this exact variant
                    if variant_part in tried_variants:
                        continue
                        
                    tried_variants.add(variant_part)
                    complete_sequence = f"{prefix}{variant_part}{suffix}"
                    
                    # OPTIMIZATION: Use ultra-fast constraint checking
                    if not ultra_fast_sequence_constraints_check(complete_sequence):
                        continue
                    
                    # Add to current batch
                    current_batch_sequences.append(complete_sequence)
                    current_batch_variants.append(variant_part)
                    sequence_count += 1
                    
                    # Process batch when it reaches batch_size
                    if len(current_batch_sequences) >= batch_size:
                        batch_results = process_sequence_batch(current_batch_sequences, current_batch_variants, precomputed_aa_features, job_id)
                        # FIX 1: Use bounded queue instead of extend
                        results.add_results(batch_results)
                        valid_sequence_count += len(batch_results)
                        
                        # Clear batch
                        current_batch_sequences = []
                        current_batch_variants = []
                    
                    break  # Found a valid sequence, move to next

                # Update progress periodically
                if processed_count % progress_batch_size == 0:
                    # Determine phase based on current progress relative to target number of sequences
                    phase = 0 if sequence_count < total_sequences * 0.2 else (1 if sequence_count < total_sequences * 0.8 else 2)
                    
                    # Calculate weighted progress
                    current_progress = calculate_weighted_progress(sequence_count, total_sequences, phase)
                    active_jobs[job_id]["progress"] = current_progress
                    
                    # Update time estimate
                    update_time_estimate(job_id, current_progress, time.time() - start_time, progress_batch_size, total_sequences)
                    
                    # Store partial results
                    if results.size() > 0:
                        # FIX 1: Use bounded queue's get_top_results instead of sorting
                        top_partial = results.get_top_results()
                        partial_result = {
                            "query": aa_sequence_clean,
                            "predictions": top_partial,
                            "sequences_processed": processed_count,
                            "valid_sequences_found": valid_sequence_count,
                            "exhaustive_search": False,
                            "prefix": prefix,
                            "suffix": suffix,
                            "variant_length": variant_length,
                            "total_length": total_length,
                            "status": "Processing"
                        }
                        active_jobs[job_id]["partial_result"] = partial_result
                    
                    # Update progress in database periodically
                    if (processed_count // progress_batch_size) % 5 == 0:
                        save_job_to_db(job_id, "Processing", current_progress, aa_sequence_clean, user_email)
                    
                    # Throttled progress logging (~1s cadence)
                    if _should_log_now(job_id, "progress"):
                        logger.info(f"Job {job_id}: Progress update - processed={processed_count}, progress={current_progress:.2f}%, "
                                   f"sequences={sequence_count}")
                
                # Check if we should break
                if sequence_count >= total_sequences:
                    break
            
            # Process any remaining sequences in the final batch
            if current_batch_sequences and not check_if_terminated():
                batch_results = process_sequence_batch(current_batch_sequences, current_batch_variants, precomputed_aa_features, job_id)
                # FIX 1: Use bounded queue instead of extend
                results.add_results(batch_results)
                valid_sequence_count += len(batch_results)

        # Sort results by interaction probability
        # FIX 1: Use bounded queue's get_top_results instead of sorting large list
        if results.size() > 0:
            top_results = results.get_top_results()
        else:
            top_results = []
            logger.warning(f"Job {job_id}: No valid sequences found that meet all constraints.")

        result_data = {
            "query": aa_sequence_clean,
            "predictions": top_results,
            "sequences_processed": processed_count if 'processed_count' in locals() else valid_sequence_count, 
            "valid_sequences_found": valid_sequence_count if 'valid_sequence_count' in locals() else 0,
            "exhaustive_search": use_exhaustive if 'use_exhaustive' in locals() else False,
            "prefix": prefix,
            "suffix": suffix,
            "variant_length": variant_length,
            "total_length": total_length
        }
        
        # One final termination check before completing
        if check_if_terminated():
            result_data["status"] = "Terminated"
            result_data["message"] = "Job was terminated before completion. Showing partial results."
            active_jobs[job_id]["result"] = result_data
            save_job_to_db(job_id, "Terminated", 100.0, aa_sequence_clean, user_email, result_data)
            return
        
        # Set final progress to 100.0%
        active_jobs[job_id]["progress"] = 100.0
        active_jobs[job_id]["result"] = result_data
        
        # Log completion
        logger.info(f"Job {job_id}: Completed with optimizations")
        
        # Save completed job to database with exactly 100.0% progress
        logger.info(f"Job {job_id}: Setting final status to Completed with 100.0% progress")
        save_job_to_db(job_id, "Completed", 100.0, aa_sequence_clean, user_email, result_data)
        
        # Send email notification if enabled and email was provided
        if EMAIL_ENABLED and user_email:
            try:
                import smtplib
                from email.mime.text import MIMEText
                from email.mime.multipart import MIMEMultipart
                
                msg = MIMEMultipart()
                msg['From'] = EMAIL_FROM
                msg['To'] = user_email
                msg['Subject'] = "Your Aptamer Prediction Results Are Ready"
                
                body = f"""
                Hello,
                
                Your aptamer prediction job has completed successfully!
                
                You can view your results at: /api/results/{job_id}
                
                This link will be available for {RESULTS_RETENTION_DAYS} days.
                
                Thank you for using our service.
                """
                
                msg.attach(MIMEText(body, 'plain'))
                
                server = smtplib.SMTP(EMAIL_SERVER, EMAIL_PORT)
                server.starttls()
                server.login(EMAIL_USER, EMAIL_PASSWORD)
                server.send_message(msg)
                server.quit()
                
                logger.info(f"Email notification sent to {user_email} for job {job_id}")
            except Exception as e:
                logger.error(f"Failed to send email notification: {e}")
        
    except Exception as e:
        # Catch any unexpected errors
        error_msg = f"Unexpected error in sequence processing: {str(e)}"
        logger.error(f"Job {job_id} failed with error: {error_msg}")
        active_jobs[job_id]["result"] = {"error": error_msg}
        active_jobs[job_id]["progress"] = 100.0
        
        # Make sure to update the job status to failed
        save_job_to_db(job_id, "Failed", 100.0, aa_sequence_clean, user_email, {"error": error_msg})
    
    # Force a final check and update to ensure 100% is set
    try:
        # Double-check that we've set the progress to 100%
        if job_id in active_jobs and active_jobs[job_id]["progress"] < 100.0:
            logger.warning(f"Job {job_id}: Progress was not set to 100%, fixing now")
            active_jobs[job_id]["progress"] = 100.0
            save_job_to_db(job_id, "Completed", 100.0, aa_sequence_clean, user_email, 
                          active_jobs[job_id].get("result", {"status": "completed"}))
    except Exception as e:
        logger.error(f"Error in final progress update for job {job_id}: {e}")
        
    # Clean up old jobs
    cleanup_old_jobs()


# Create a router
router = APIRouter()

@router.post("/predict")
def predict_sequence(input_data: InputData, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    # Immediately create a job entry in memory
    active_jobs[job_id] = {"progress": 0.0, "result": None, "start_time": None, "remaining_time": None}
    
    # Start the background task with the updated parameters
    background_tasks.add_task(
        process_genes, 
        job_id, 
        input_data.amino_acid_sequence, 
        input_data.max_sequences,
        input_data.variant_length,
        input_data.total_length,
        input_data.email,
        input_data.prefix,  # Add these new parameters
        input_data.suffix
    )
    
    logger.info(f"Created job {job_id} for sequence: {input_data.amino_acid_sequence} "
               f"(max sequences: {input_data.max_sequences}, variant length: {input_data.variant_length}, "
               f"total length: {input_data.total_length}, "
               f"custom prefix: {input_data.prefix}, custom suffix: {input_data.suffix})")
    
    return {
        "job_id": job_id,
        "result_url": f"/api/results/{job_id}",
        "message": "Your job has been submitted. You can bookmark the result_url to check the status and retrieve results later."
    }

# Keep original progress endpoint with query parameter for compatibility
@router.get("/progress")
def get_progress(job_id: str):
    # First check active jobs
    if job_id in active_jobs:
        result = {
            "progress": active_jobs[job_id]["progress"], 
            "remaining_time": active_jobs[job_id]["remaining_time"]
        }
        logger.info(f"Progress request for {job_id}: {result}")  # Add logging
        return result
    
    # If not in active jobs, check database
    try:
        conn = sqlite3.connect(RESULTS_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT status, progress FROM jobs WHERE job_id = ?", (job_id,))
        job = cursor.fetchone()
        conn.close()
        
        if not job:
            logger.error(f"Job {job_id} not found when checking progress")
            raise HTTPException(status_code=404, detail="Job not found")
            
        return {"status": job[0], "progress": job[1]}
    except Exception as e:
        logger.error(f"Database error when checking progress for job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

# Keep original result endpoint with query parameter for compatibility
@router.get("/result")
def get_result(job_id: str):
    # First check active jobs
    if job_id in active_jobs:
        if active_jobs[job_id]["result"] is None:
            return {
                "status": "Processing", 
                "progress": active_jobs[job_id]["progress"], 
                "remaining_time": active_jobs[job_id]["remaining_time"]
            }
        return active_jobs[job_id]["result"]
    
    # If not in active jobs, check database
    try:
        conn = sqlite3.connect(RESULTS_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT status, progress, result FROM jobs WHERE job_id = ?", (job_id,))
        job = cursor.fetchone()
        conn.close()
        
        if not job:
            logger.error(f"Job {job_id} not found when checking result")
            raise HTTPException(status_code=404, detail="Job not found")
            
        if job[0] != "Completed":
            return {"status": job[0], "progress": job[1]}
            
        return json.loads(job[2])
    except Exception as e:
        logger.error(f"Database error when checking result for job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

# New endpoint for retrieving results by link - this is the persistent URL
@router.get("/results/{job_id}")
def view_results(job_id: str):
    try:
        conn = sqlite3.connect(RESULTS_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT status, progress, result FROM jobs WHERE job_id = ?", (job_id,))
        job = cursor.fetchone()
        conn.close()
        
        if not job:
            logger.error(f"Job {job_id} not found when viewing results page")
            raise HTTPException(status_code=404, detail="Results not found")
            
        if job[0] not in ["Completed", "Terminated"]:
            return {
                "status": job[0], 
                "progress": job[1], 
                "message": "Your job is still processing. Please check back later."
            }
            
        return json.loads(job[2])
    except Exception as e:
        logger.error(f"Database error when viewing results for job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

@router.post("/kill/{job_id}")
def kill_job(job_id: str):
    """Terminates a running job and returns the latest available results."""
    
    logger.info(f"=== KILL REQUEST START for {job_id} ===")
    logger.info(f"Active jobs keys: {list(active_jobs.keys())}")
    
    if job_id in active_jobs:
        logger.info(f"Job {job_id} state: progress={active_jobs[job_id].get('progress')}, "
                   f"result_available={active_jobs[job_id].get('result') is not None}, "
                   f"partial_result_available={active_jobs[job_id].get('partial_result') is not None}")
    
    # Check if job exists in active jobs
    if job_id not in active_jobs:
        logger.info(f"Job {job_id} not found in active jobs, checking database")
        # Check if job exists in database
        try:
            conn = sqlite3.connect(RESULTS_DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT status, result FROM jobs WHERE job_id = ?", (job_id,))
            job = cursor.fetchone()
            conn.close()
            
            if not job:
                logger.warning(f"Job {job_id} not found in database when attempting to kill")
                raise HTTPException(status_code=404, detail="Job not found")
                
            # If job is already completed, just return success
            if job[0] in ["Completed", "Failed", "Terminated"]:
                logger.info(f"Job {job_id} is already in {job[0]} state, no need to kill")
                
                # Get the full result to return
                result_data = None
                if job[1]:  # If there's a result stored
                    try:
                        result_data = json.loads(job[1])
                    except:
                        logger.error(f"Could not parse result data for job {job_id}")
                        
                return {
                    "status": "success", 
                    "message": f"Job was already {job[0].lower()}",
                    "result": result_data
                }
        except Exception as e:
            logger.error(f"Database error when killing job {job_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Database error: {e}")
    
    # First, aggressively set termination flags
    if job_id in active_jobs:
        active_jobs[job_id]["terminated"] = True
        active_jobs[job_id]["progress"] = 100.0
        logger.info(f"Set termination flags for active job {job_id}")
    
    # Update database immediately
    try:
        conn = sqlite3.connect(RESULTS_DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
        UPDATE jobs SET 
            status = 'Terminated',
            progress = 100.0,
            completed_at = ?
        WHERE job_id = ?
        ''', (datetime.now().isoformat(), job_id))
        conn.commit()
        conn.close()
        logger.info(f"Database updated with termination status for job {job_id}")
    except Exception as e:
        logger.error(f"Error updating database for job {job_id}: {e}")
    
    # Wait a moment for the background task to detect termination and save results
    import time
    time.sleep(3)  # Give background task more time to save partial results
    
    # Now try to get results from multiple sources
    current_result = None
    
    # 1. Check in-memory results first
    if job_id in active_jobs and active_jobs[job_id].get("result"):
        current_result = active_jobs[job_id]["result"]
        logger.info(f"Found in-memory results for job {job_id}")
    
    # 2. Check for partial results if no full results
    elif job_id in active_jobs and active_jobs[job_id].get("partial_result"):
        current_result = active_jobs[job_id]["partial_result"]
        current_result["status"] = "Terminated"
        current_result["message"] = "Job was terminated before completion. Showing partial results."
        logger.info(f"Found in-memory partial results for job {job_id}")
    
    # 3. If no in-memory results, check database
    if not current_result:
        try:
            conn = sqlite3.connect(RESULTS_DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT result FROM jobs WHERE job_id = ?", (job_id,))
            job_result = cursor.fetchone()
            conn.close()
            
            if job_result and job_result[0]:
                try:
                    current_result = json.loads(job_result[0])
                    logger.info(f"Found database results for job {job_id}")
                except Exception as parse_err:
                    logger.error(f"Could not parse database result for job {job_id}: {parse_err}")
        except Exception as db_err:
            logger.error(f"Database error when fetching results for job {job_id}: {db_err}")
    
    # 4. If still no results, return a meaningful message
    if not current_result:
        current_result = {
            "query": "Unknown",
            "predictions": [],
            "status": "Terminated",
            "message": "Job was terminated too early - no partial results available."
        }
        logger.warning(f"No results found for terminated job {job_id}")
    
    # Ensure the result is marked as terminated
    if isinstance(current_result, dict):
        current_result["status"] = "Terminated"
        if "message" not in current_result:
            current_result["message"] = "Job was terminated before completion. Showing partial results."
    
    logger.info(f"Returning termination response for job {job_id} with result: {current_result is not None}")
    
    return {
        "status": "success", 
        "message": "Job terminated successfully",
        "result": current_result
    }

# Enhanced performance benchmark endpoints
@router.get("/benchmark/{job_id}")
def benchmark_prediction_performance(job_id: str):
    """
    Benchmark the prediction performance optimizations for a completed job.
    """
    # Check if job exists and get a sample of sequences for benchmarking
    try:
        conn = sqlite3.connect(RESULTS_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT result FROM jobs WHERE job_id = ?", (job_id,))
        job_result = cursor.fetchone()
        conn.close()
        
        if not job_result or not job_result[0]:
            raise HTTPException(status_code=404, detail="Job not found or has no results")
        
        result_data = json.loads(job_result[0])
        predictions = result_data.get("predictions", [])
        
        if len(predictions) < 10:
            return {"message": "Need at least 10 predictions for meaningful benchmark"}
        
        # Extract sequences for benchmarking
        sequences = [pred["gene_sequence"] for pred in predictions[:50]]  # Use top 50 for comprehensive benchmark
        
        # Get the original query to precompute AA features
        aa_sequence = result_data.get("query", "")
        if not aa_sequence:
            return {"error": "Could not find original amino acid sequence"}
        
        # Precompute AA features
        precomputed_aa_features = predictor.precompute_aa_features(aa_sequence)
        
        # Run comprehensive benchmark
        benchmark_results = predictor.benchmark_prediction_methods(sequences, precomputed_aa_features)
        
        # Benchmark RNA folding performance
        rna_benchmark = benchmark_rna_folding_performance(sequences[:20], max_workers=MAX_RNA_WORKERS)
        
        return {
            "job_id": job_id,
            "sequences_tested": len(sequences),
            "ml_prediction_benchmark": benchmark_results,
            "rna_folding_benchmark": rna_benchmark,
            "overall_optimizations": {
                "vectorized_constraints": "enabled",
                "dmatrix_api": "enabled",
                "global_rna_pool": f"enabled ({MAX_RNA_WORKERS} workers)"
            }
        }
        
    except Exception as e:
        logger.error(f"Error benchmarking job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Benchmark error: {e}")

# Include the router with the /api prefix
app.include_router(router, prefix="/api")

# Cleanup function for graceful shutdown
def cleanup_global_resources():
    """Clean up global resources on shutdown"""
    try:
        GLOBAL_RNA_EXECUTOR.shutdown(wait=True)
        logger.info("Global RNA executor shut down successfully")
    except Exception as e:
        logger.error(f"Error shutting down global RNA executor: {e}")

# Register cleanup function
import atexit
atexit.register(cleanup_global_resources)

#On mac:
# cd to APIPred
#source env/bin/activate


#On windows powershell
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
# .\env\Scripts\Activate.ps1


#cd to backend


#uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1

# in frontend do
# export PORT=3000
# npm run dev
# or to use product mode:
# npm run build 
# npm start
# https://141.142.220.151



# curl -X POST "http://127.0.0.1:8000/api/predict" \
#      -H "Content-Type: application/json" \ 
#      -d '{"amino_acid_sequence": "ACDEFGHIKLMNPQRSTVWYACDEFGHIKLMNPQRSTVWY"}'




#to activate frontend: in git bash and cd to frontend
# npm run dev


# Using Screen:
# bash# Install screen
# sudo apt install screen

# # Start a new screen session
# screen -S backend

# # Run your backend
# cd ~/APIPred/backend
# uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1

# # Detach from screen (press Ctrl+A, then D)


# For your frontend:
# bash# New screen session
# screen -S frontend

# # Run your frontend
# cd ~/APIPred/frontend
# export PORT=3000
# npm run dev

# # Detach from screen (press Ctrl+A, then D)
# To reconnect later:
# bash# List running screen sessions
# screen -ls

# # Reconnect to a session
# screen -r backend  # or screen -r frontend