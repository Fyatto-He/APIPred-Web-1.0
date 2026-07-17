from xgboost import XGBClassifier
import xgboost as xgb
import numpy as np
import pickle
import threading
import hashlib
from collections import OrderedDict
from sklearn.preprocessing import StandardScaler
from .input_transformation import generate_kmer_vector, compute_combined_pseaac


class KmerCache:
    """
    Thread-safe LRU cache for k-mer features to avoid recomputation.
    """
    
    def __init__(self, max_size=50000):
        self.max_size = max_size
        self.cache = OrderedDict()
        self.lock = threading.RLock()  # Thread-safe access
        self.hit_count = 0
        self.miss_count = 0
    
    def _get_sequence_hash(self, sequence):
        """Generate a hash for the sequence for efficient lookup."""
        return hashlib.md5(sequence.encode('utf-8')).hexdigest()
    
    def get_kmer_features(self, sequence):
        """
        Get k-mer features with caching.
        Returns cached features if available, otherwise computes and caches them.
        """
        seq_hash = self._get_sequence_hash(sequence)
        
        with self.lock:
            # Check if features are in cache
            if seq_hash in self.cache:
                # Move to end (most recently used)
                features = self.cache.pop(seq_hash)
                self.cache[seq_hash] = features
                self.hit_count += 1
                return features.copy()  # Return copy to prevent modification
            
            # Cache miss - compute features
            self.miss_count += 1
            features = generate_kmer_vector(sequence)
            
            # Add to cache
            if len(self.cache) >= self.max_size:
                # Remove least recently used item
                self.cache.popitem(last=False)
            
            self.cache[seq_hash] = features.copy()
            return features
    
    def get_batch_kmer_features(self, sequences):
        """
        Get k-mer features for multiple sequences with caching.
        Returns numpy array of k-mer features.
        """
        batch_features = []
        
        for sequence in sequences:
            features = self.get_kmer_features(sequence)
            batch_features.append(features)
        
        return np.array(batch_features)
    
    def get_cache_stats(self):
        """Get cache performance statistics."""
        total_requests = self.hit_count + self.miss_count
        hit_rate = (self.hit_count / total_requests * 100) if total_requests > 0 else 0
        
        with self.lock:
            cache_size = len(self.cache)
        
        return {
            "cache_size": cache_size,
            "max_size": self.max_size,
            "hit_count": self.hit_count,
            "miss_count": self.miss_count,
            "hit_rate": f"{hit_rate:.2f}%",
            "total_requests": total_requests
        }
    
    def clear_cache(self):
        """Clear the entire cache."""
        with self.lock:
            self.cache.clear()
            self.hit_count = 0
            self.miss_count = 0


class APIPred:
    def __init__(self):
        # File paths
        MODEL_PATH = "models/apipred_model.model"
        FEATURE_INDICES_PATH = "models/selected_feature_indices.npy"
        POLY_TRANSFORMER_PATH = "models/poly_transformer.pkl"
        

        # Load trained model
        self.model = XGBClassifier()
        self.model.load_model(MODEL_PATH)

        # Load feature selection indices
        self.selected_indices = np.load(FEATURE_INDICES_PATH)

        # Load polynomial transformer
        with open(POLY_TRANSFORMER_PATH, "rb") as f:
            self.poly = pickle.load(f)
        
        # Optimization flags
        self._use_dmatrix = True  # Enable XGBoost DMatrix optimization
        self._use_kmer_cache = True  # Enable k-mer caching
        
        # Initialize k-mer cache
        self.kmer_cache = KmerCache(max_size=50000)


    def fast_preprocess_input(self, X_input):
        """Apply precomputed feature selection, scaling, and polynomial transformation."""
        X_selected = X_input[:, self.selected_indices]  # Select relevant features
        X_poly = self.poly.transform(X_selected)  # Apply polynomial transformation
        return X_poly

    def precompute_aa_features(self, aa_sequence):
        """
        Precompute amino acid sequence features once for reuse across multiple predictions.
        
        Args:
            aa_sequence: The amino acid sequence string
            
        Returns:
            numpy array of protein features (300 dimensions)
        """
        return compute_combined_pseaac(aa_sequence)

    def encode_gene_aas_batch(self, gene_sequences, precomputed_aa_features):
        """
        Convert multiple gene sequences into numerical features using precomputed AA features
        and cached k-mer generation.
        
        Args:
            gene_sequences: List of gene sequence strings
            precomputed_aa_features: Precomputed amino acid features (300 dimensions)
            
        Returns:
            Preprocessed feature matrix ready for prediction
        """
        batch_size = len(gene_sequences)
        
        # OPTIMIZATION: Use cached k-mer features for faster batch processing
        if self._use_kmer_cache:
            try:
                batch_kmer_features = self.kmer_cache.get_batch_kmer_features(gene_sequences)
            except Exception as cache_error:
                print(f"K-mer cache failed, falling back to direct computation: {cache_error}")
                # Fallback to direct computation
                batch_kmer_features = np.array([generate_kmer_vector(gene) for gene in gene_sequences])
                self._use_kmer_cache = False  # Disable caching if it fails
        else:
            # Direct k-mer computation without caching
            batch_kmer_features = np.array([generate_kmer_vector(gene) for gene in gene_sequences])
        
        # Broadcast precomputed protein features to match batch size
        batch_protein_features = np.tile(precomputed_aa_features, (batch_size, 1))
        
        # Combine k-mer and protein features to get batch of 640-dimensional vectors
        batch_features = np.hstack((batch_kmer_features, batch_protein_features))
        
        # Apply feature selection and transformation to entire batch
        return self.fast_preprocess_input(batch_features)

    def predict_batch(self, gene_sequences, precomputed_aa_features):
        """
        Predict aptamer interactions for multiple gene sequences at once using optimized XGBoost DMatrix API
        and cached k-mer features.
        
        Args:
            gene_sequences: List of gene sequence strings
            precomputed_aa_features: Precomputed amino acid features
            
        Returns:
            List of prediction dictionaries with interaction probabilities
        """
        if not gene_sequences:
            return []
            
        # Transform all sequences at once (now with k-mer caching)
        features_transformed = self.encode_gene_aas_batch(gene_sequences, precomputed_aa_features)
        
        # OPTIMIZATION: Use XGBoost DMatrix API for faster prediction
        if self._use_dmatrix:
            try:
                # Create DMatrix for optimized prediction
                dmatrix = xgb.DMatrix(features_transformed)
                probabilities = self.model.predict(dmatrix)
                
                # Handle different XGBoost output formats
                if len(probabilities.shape) == 1:
                    # Binary classification with single probability output
                    probabilities = np.column_stack([1 - probabilities, probabilities])
                elif probabilities.shape[1] == 1:
                    # Single column output, convert to two-column format
                    probabilities = np.column_stack([1 - probabilities.flatten(), probabilities.flatten()])
                
            except Exception as e:
                # Fallback to standard predict_proba if DMatrix fails
                print(f"DMatrix prediction failed, falling back to predict_proba: {e}")
                probabilities = self.model.predict_proba(features_transformed)
                self._use_dmatrix = False  # Disable for future calls
        else:
            # Standard prediction method
            probabilities = self.model.predict_proba(features_transformed)
        
        # Return list of results matching input format
        return [{"interaction_probability": float(prob)} for prob in probabilities[:, 1]]

    def predict_batch_with_dmatrix(self, gene_sequences, precomputed_aa_features):
        """
        Alternative method explicitly using DMatrix API for maximum performance.
        """
        if not gene_sequences:
            return []
            
        # Transform all sequences at once (with k-mer caching)
        features_transformed = self.encode_gene_aas_batch(gene_sequences, precomputed_aa_features)
        
        # Use DMatrix for optimal XGBoost performance
        dmatrix = xgb.DMatrix(features_transformed)
        probabilities = self.model.predict(dmatrix)
        
        # Handle XGBoost output format
        if len(probabilities.shape) == 1:
            # Binary classification - convert to probability format
            probabilities = np.column_stack([1 - probabilities, probabilities])
        elif probabilities.shape[1] == 1:
            # Single column - convert to two-column format
            probabilities = np.column_stack([1 - probabilities.flatten(), probabilities.flatten()])
        
        # Return list of results
        return [{"interaction_probability": float(prob)} for prob in probabilities[:, 1]]

    def encode_gene_aas(self, gene, aa_sequence):
        """
        Convert amino acid sequence into numerical features (legacy single prediction).
        Now uses k-mer caching for consistency.
        """
        # Use cached k-mer features if available
        if self._use_kmer_cache:
            try:
                kmer_features = self.kmer_cache.get_kmer_features(gene)
            except:
                kmer_features = generate_kmer_vector(gene)
        else:
            kmer_features = generate_kmer_vector(gene)  # 340 features
            
        protein_features = compute_combined_pseaac(aa_sequence)  # 300 features
        
        # Combine k-mer and protein features to get a 640-dimensional vector
        feature_vector = np.hstack((kmer_features, protein_features))

        # Apply feature selection and transformation
        return self.fast_preprocess_input(feature_vector.reshape(1, -1))

    def predict(self, gene, aa_sequence):
        """
        Predict aptamer interaction with a given amino acid sequence (legacy single prediction).
        """
        features_transformed = self.encode_gene_aas(gene, aa_sequence)
        
        # Use DMatrix for consistency if available
        if self._use_dmatrix:
            try:
                dmatrix = xgb.DMatrix(features_transformed)
                probabilities = self.model.predict(dmatrix)
                
                if len(probabilities.shape) == 1:
                    return {"interaction_probability": float(probabilities[0])}
                else:
                    return {"interaction_probability": float(probabilities[0, 1])}
            except:
                # Fallback to predict_proba
                probabilities = self.model.predict_proba(features_transformed)
                return {"interaction_probability": float(probabilities[:, 1][0])}
        else:
            probabilities = self.model.predict_proba(features_transformed)
            return {"interaction_probability": float(probabilities[:, 1][0])}

    def get_cache_statistics(self):
        """
        Get comprehensive cache performance statistics.
        """
        if not self._use_kmer_cache:
            return {"kmer_cache": "disabled"}
        
        cache_stats = self.kmer_cache.get_cache_stats()
        return {
            "kmer_cache": cache_stats,
            "optimizations": {
                "dmatrix_enabled": self._use_dmatrix,
                "kmer_cache_enabled": self._use_kmer_cache
            }
        }

    def clear_cache(self):
        """
        Clear all caches to free memory.
        """
        if self._use_kmer_cache:
            self.kmer_cache.clear_cache()
        
        return {"message": "All caches cleared successfully"}

    def benchmark_prediction_methods(self, gene_sequences, precomputed_aa_features):
        """
        Benchmark different prediction methods to verify performance gains,
        including k-mer caching performance.
        """
        import time
        
        if len(gene_sequences) < 10:
            print("Need at least 10 sequences for meaningful benchmark")
            return
        
        print(f"\n🔥 Benchmarking prediction methods with {len(gene_sequences)} sequences:")
        print("=" * 70)
        
        # Clear cache for fair comparison
        if self._use_kmer_cache:
            self.kmer_cache.clear_cache()
        
        # Test 1: Standard predict_proba without caching
        start_time = time.time()
        old_use_dmatrix = self._use_dmatrix
        old_use_cache = self._use_kmer_cache
        self._use_dmatrix = False
        self._use_kmer_cache = False
        results_standard = self.predict_batch(gene_sequences, precomputed_aa_features)
        time_standard = time.time() - start_time
        
        # Test 2: DMatrix API without caching
        start_time = time.time()
        self._use_dmatrix = True
        self._use_kmer_cache = False
        self.kmer_cache.clear_cache()  # Ensure clean start
        results_dmatrix = self.predict_batch(gene_sequences, precomputed_aa_features)
        time_dmatrix = time.time() - start_time
        
        # Test 3: DMatrix API with k-mer caching (first run - cache misses)
        start_time = time.time()
        self._use_dmatrix = True
        self._use_kmer_cache = True
        self.kmer_cache.clear_cache()  # Start with empty cache
        results_cached_cold = self.predict_batch(gene_sequences, precomputed_aa_features)
        time_cached_cold = time.time() - start_time
        
        # Test 4: DMatrix API with k-mer caching (second run - cache hits)
        start_time = time.time()
        results_cached_warm = self.predict_batch(gene_sequences, precomputed_aa_features)
        time_cached_warm = time.time() - start_time
        
        # Restore original settings
        self._use_dmatrix = old_use_dmatrix
        self._use_kmer_cache = old_use_cache
        
        # Get cache statistics
        cache_stats = self.kmer_cache.get_cache_stats()
        
        # Compare results
        results_match_dmatrix = all(
            abs(r1["interaction_probability"] - r2["interaction_probability"]) < 1e-6
            for r1, r2 in zip(results_standard, results_dmatrix)
        )
        
        results_match_cached = all(
            abs(r1["interaction_probability"] - r2["interaction_probability"]) < 1e-6
            for r1, r2 in zip(results_standard, results_cached_warm)
        )
        
        # Calculate speedups
        dmatrix_speedup = time_standard / time_dmatrix if time_dmatrix > 0 else 1.0
        cache_cold_speedup = time_standard / time_cached_cold if time_cached_cold > 0 else 1.0
        cache_warm_speedup = time_standard / time_cached_warm if time_cached_warm > 0 else 1.0
        cache_improvement = time_cached_cold / time_cached_warm if time_cached_warm > 0 else 1.0
        
        print(f"Standard predict_proba:     {time_standard:.4f} seconds")
        print(f"DMatrix API:                {time_dmatrix:.4f} seconds ({dmatrix_speedup:.2f}x speedup)")
        print(f"DMatrix + Cache (cold):     {time_cached_cold:.4f} seconds ({cache_cold_speedup:.2f}x speedup)")
        print(f"DMatrix + Cache (warm):     {time_cached_warm:.4f} seconds ({cache_warm_speedup:.2f}x speedup)")
        print(f"Cache improvement:          {cache_improvement:.2f}x faster when warm")
        print(f"Results identical (DMatrix): {results_match_dmatrix}")
        print(f"Results identical (Cached): {results_match_cached}")
        print(f"Cache hit rate:             {cache_stats['hit_rate']}")
        print(f"Cache efficiency:           {cache_stats['hit_count']}/{cache_stats['total_requests']} hits")
        print("=" * 70)
        
        return {
            "dmatrix_speedup": dmatrix_speedup,
            "cache_warm_speedup": cache_warm_speedup,
            "cache_improvement": cache_improvement,
            "cache_stats": cache_stats
        }

    def benchmark_kmer_caching_only(self, gene_sequences, iterations=3):
        """
        Benchmark specifically k-mer caching performance.
        """
        import time
        
        if len(gene_sequences) < 5:
            print("Need at least 5 sequences for k-mer benchmark")
            return
        
        print(f"\n🧬 K-mer Caching Benchmark with {len(gene_sequences)} sequences:")
        print("=" * 60)
        
        # Test without caching
        times_no_cache = []
        for i in range(iterations):
            start_time = time.time()
            batch_features = np.array([generate_kmer_vector(gene) for gene in gene_sequences])
            times_no_cache.append(time.time() - start_time)
        
        avg_no_cache = sum(times_no_cache) / len(times_no_cache)
        
        # Test with caching (cold start)
        self.kmer_cache.clear_cache()
        start_time = time.time()
        batch_features_cached = self.kmer_cache.get_batch_kmer_features(gene_sequences)
        time_cache_cold = time.time() - start_time
        
        # Test with caching (warm - multiple iterations)
        times_cache_warm = []
        for i in range(iterations):
            start_time = time.time()
            batch_features_cached = self.kmer_cache.get_batch_kmer_features(gene_sequences)
            times_cache_warm.append(time.time() - start_time)
        
        avg_cache_warm = sum(times_cache_warm) / len(times_cache_warm)
        
        # Calculate improvements
        cold_vs_no_cache = avg_no_cache / time_cache_cold if time_cache_cold > 0 else 1.0
        warm_speedup = avg_no_cache / avg_cache_warm if avg_cache_warm > 0 else 1.0
        
        cache_stats = self.kmer_cache.get_cache_stats()
        
        print(f"No caching (avg):           {avg_no_cache:.4f} seconds")
        print(f"With caching (cold):        {time_cache_cold:.4f} seconds ({cold_vs_no_cache:.2f}x)")
        print(f"With caching (warm avg):    {avg_cache_warm:.4f} seconds ({warm_speedup:.2f}x speedup)")
        print(f"Cache hit rate:             {cache_stats['hit_rate']}")
        print(f"Memory efficiency:          {cache_stats['cache_size']}/{cache_stats['max_size']} slots used")
        print("=" * 60)
        
        return {
            "no_cache_time": avg_no_cache,
            "cache_warm_time": avg_cache_warm,
            "speedup": warm_speedup,
            "cache_stats": cache_stats
        }