"""Prefix / suffix computation helpers for generated aptamer sequences."""
from .config import PREFIX_SOURCE, SUFFIX_SOURCE


def calculate_prefix_suffix_lengths(total_length, variant_length):
    """Calculate the lengths of prefix and suffix based on total and variant lengths"""
    remaining_length = total_length - variant_length

    if remaining_length <= 0:
        # Ensure we have at least some prefix and suffix
        return 1, 1

    if remaining_length % 2 == 0:
        # Even split
        prefix_length = suffix_length = remaining_length // 2
    else:
        # Odd split, give extra character to prefix
        prefix_length = (remaining_length // 2) + 1
        suffix_length = remaining_length // 2

    return prefix_length, suffix_length


def get_prefix_suffix(total_length, variant_length):
    """Get the prefix and suffix strings based on calculated lengths"""
    prefix_length, suffix_length = calculate_prefix_suffix_lengths(total_length, variant_length)

    # Extract prefix and suffix from source strings
    prefix = PREFIX_SOURCE[:prefix_length]
    suffix = SUFFIX_SOURCE[:suffix_length]

    return prefix, suffix
