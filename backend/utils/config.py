"""Configuration constants shared across the backend."""

# Path for results database
RESULTS_DB_PATH = "database/results.db"

# Results retention period (in days)
RESULTS_RETENTION_DAYS = 90

# Email settings (update these with your actual email server details)
EMAIL_ENABLED = False  # Set to True when you've configured your email settings
EMAIL_SERVER = "smtp.example.com"
EMAIL_PORT = 587
EMAIL_USER = "your-email@example.com"
EMAIL_PASSWORD = "your-email-password"
EMAIL_FROM = "no-reply@example.com"

# Sequence generation parameters
DEFAULT_VARIANT_LENGTH = 10
DEFAULT_TOTAL_LENGTH = 30
DEFAULT_MAX_SEQUENCES = 1e16  # Limit for testing purposes
MAX_TOTAL_LENGTH = 50  # Cap for total sequence length

# Parallel processing configuration
MAX_RNA_WORKERS = 8  # Number of parallel threads for RNA folding
RNA_FOLDING_BATCH_SIZE = 50  # Batch size for parallel RNA folding

# Standard sequences for prefix and suffix
PREFIX_SOURCE = "ATAACTGGTCTTGTTACAGGTCTG"
SUFFIX_SOURCE = "TCCTTACGTATAATACTACCGAAC"
