"""Ultra-fast sequence constraint checking helpers.

Pure functions: no shared state, no I/O. Used to pre-filter candidate
aptamer sequences by GC content and consecutive-base repeats before
running expensive ML prediction and RNA folding.
"""
import re
import numpy as np

# Pre-compiled regex patterns for ultra-fast constraint checking
CONSECUTIVE_IDENTICAL = re.compile(r'(.)\1{4,}')  # 5 or more consecutive identical bases
CONSECUTIVE_GC = re.compile(r'[GC]{5,}')  # 5 or more consecutive G or C bases


def ultra_fast_gc_content_check(sequence):
    """
    Ultra-fast GC content calculation using numpy.
    """
    # Convert sequence to numpy array for vectorized operations
    seq_array = np.frombuffer(sequence.encode('ascii'), dtype=np.uint8)
    gc_count = np.sum((seq_array == ord('G')) | (seq_array == ord('C')))
    gc_percentage = (gc_count / len(sequence)) * 100
    return 47 <= gc_percentage <= 55


def ultra_fast_sequence_constraints_check(sequence):
    """
    Ultra-fast constraint checking using pre-compiled regex and numpy.
    Returns True if sequence meets all constraints.
    """
    # Fast GC content check using numpy
    if not ultra_fast_gc_content_check(sequence):
        return False

    # Fast consecutive checks using pre-compiled regex
    if CONSECUTIVE_IDENTICAL.search(sequence):  # 5 or more consecutive identical
        return False

    # if CONSECUTIVE_GC.search(sequence):  # 5 or more consecutive G/C
    #     return False

    return True


def batch_constraint_checking(sequences):
    """
    Vectorized constraint checking for multiple sequences.
    Returns list of sequences that pass all constraints.
    """
    valid_sequences = []

    for seq in sequences:
        if ultra_fast_sequence_constraints_check(seq):
            valid_sequences.append(seq)

    return valid_sequences


# Legacy constraint functions (kept for compatibility, but now optimized)
def has_too_many_consecutive_identical(seq):
    """Legacy function - now uses optimized regex."""
    return CONSECUTIVE_IDENTICAL.search(seq) is not None


def has_too_many_consecutive_gc(seq):
    """Legacy function - now uses optimized regex."""
    return CONSECUTIVE_GC.search(seq) is not None


def has_acceptable_gc_content(seq):
    """Legacy function - now uses optimized numpy calculation."""
    return ultra_fast_gc_content_check(seq)


def sequence_meets_constraints(full_seq):
    """
    Legacy constraint checking function - now uses ultra-fast implementation.
    """
    return ultra_fast_sequence_constraints_check(full_seq)
