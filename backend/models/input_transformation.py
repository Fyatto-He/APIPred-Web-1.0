import repDNA
from repDNA.nac import Kmer

def generate_kmer_vector(apt):
    """
    Generate a k-mer frequency vector for the given aptamer sequence.
    
    Parameters:
        apt (str): The input aptamer sequence.
    
    Returns:
        list: The computed k-mer frequency vector.
    """
    list1 = [apt]  # Convert input string into a list
    kmer = Kmer(k=4, normalize=True, upto=True)  # Initialize Kmer with given parameters
    a = kmer.make_kmer_vec(list1)  # Generate k-mer frequency vector
    # print("Length of the kmer vector is :" + str(len(a[0])))
    # print("the kmer vector :")
    # print(a[0])
    return a[0]


import math

def compute_combined_pseaac(target):
    """
    Compute a combined PseAAC feature vector by processing multiple property sets.
    
    Parameters:
        apt (str): Aptamer sequence (retained for compatibility, not used).
        target (str): Protein sequence. Must contain only the 20 standard amino acids.
        
    Returns:
        list: The final concatenated PseAAC feature vector.
    """
    # Define the 20 native amino acids (in alphabetical order)
    aa_20 = ['A','C','D','E','F','G','H','I','K','L',
             'M','N','P','Q','R','S','T','V','W','Y']
    
    # Validate the target sequence
    for ch in target:
        if ch not in aa_20:
            raise ValueError(f"Invalid amino acid '{ch}' found in target sequence.")
    
    # Count occurrences for each amino acid
    list_aa = [target.count(aa) for aa in aa_20]
    
    # Use a fixed Lambda value as in the original code
    LambdaVal = 30
    if len(target) <= LambdaVal:
        raise ValueError("Target sequence length must be greater than LambdaVal (30).")
    
    # Helper to normalize a property dictionary (to zero mean and unit variance)
    def normalize(prop_dict):
        avg = sum(prop_dict.values()) / 20.0
        sum_sq = sum((v - avg) ** 2 for v in prop_dict.values())
        std = math.sqrt(sum_sq / 20.0)
        return {k: (v - avg) / std for k, v in prop_dict.items()}
    
    # Inner function: given a set of FOUR property dictionaries, compute its PseAAC features.
    def compute_block(H01, H02, M0, H3):
        # Normalize each property scale
        H1_norm = normalize(H01)
        H2_norm = normalize(H02)
        M_norm  = normalize(M0)
        H3_norm = normalize(H3)
        
        # Define the correlation function (modified Eq. 3) -- now average over 4 properties.
        def theta_RiRj(Ri, Rj):
            return ((H1_norm[Rj] - H1_norm[Ri]) ** 2 +
                    (H2_norm[Rj] - H2_norm[Ri]) ** 2 +
                    (M_norm[Rj] - M_norm[Ri]) ** 2 +
                    (H3_norm[Rj] - H3_norm[Ri]) ** 2) / 4.0
        
        # Sequence order effect for lag n (Eq. 2 remains unchanged except for theta_RiRj)
        def sum_theta(n):
            total = 0.0
            count = 0
            for i in range(len(target) - LambdaVal):
                total += theta_RiRj(target[i], target[i + n])
                count += 1
            return total / count if count > 0 else 0
        
        # Compute normalized amino acid frequency sum
        sum_all_aa_freq = sum(round(c / len(target), 3) for c in list_aa)
        
        # Compute theta values for each lag n = 1,...,LambdaVal
        all_theta_vals = []
        sum_all_theta_val = 0.0
        for n in range(1, LambdaVal + 1):
            t_val = sum_theta(n)
            all_theta_vals.append(t_val)
            sum_all_theta_val += t_val
        
        # Denominator as in Eq. 6 (unchanged)
        denominator_val = sum_all_aa_freq + (0.15 * sum_all_theta_val)
        
        # Build the feature vector for this block:
        # First 20 features: normalized composition (each count divided by 20, then scaled by denominator)
        features_block = [round(((c / 20.0) / denominator_val), 3) for c in list_aa]
        # Next LambdaVal features: each theta scaled by 0.15 and denominator
        features_block += [round(((0.15 * t) / denominator_val), 3) for t in all_theta_vals]
        
        return features_block
    
    # ---------------------------------------------------------
    # Re-group the property sets from 7 groups of 3 features (21 features)
    # plus 3 new helix power features (from your provided values)
    # into 6 groups of 4 features (24 features).
    #
    # One possible grouping is as follows:
    #
    # Group 1 (4 features):
    #   - Block 1: Hydrophobicity, Hydrophilicity, Side-chain mass
    #   - New feature: Power of the N-terminal of the α helix
    #
    # Group 2 (4 features):
    #   - Block 2: Polarity, Molecular weight, Melting point
    #   - New feature: Power of the C-terminal of the α helix
    #
    # Group 3 (4 features):
    #   - Block 3: Transfer free energy, Buriability, Bulkiness
    #   - New feature: Power of the middle of the α helix
    #
    # Group 4 (4 features):
    #   - Block 4: Solvation free energy, Relative mutability, Residue volume
    #   - Plus the 1st unfolding property from Block 7 (Unfolding entropy change)
    #
    # Group 5 (4 features):
    #   - Block 5: Volume, Amino acid distribution, Hydration number
    #   - Plus the 2nd unfolding property from Block 7 (Unfolding enthalpy change)
    #
    # Group 6 (4 features):
    #   - Block 6: Isoelectric point, Compressibility, Chromatographic index
    #   - Plus the 3rd unfolding property from Block 7 (Unfolding Gibbs free energy change)
    # ---------------------------------------------------------
    
    property_sets = [
        # Group 1: (Block 1 + helix N-terminal)
        (
            # Block 1: Hydrophobicity, Hydrophilicity, Side-chain mass
            {'A':0.62, 'C':0.29, 'D':-0.90, 'E':-0.74, 'F':1.19,
             'G':0.48, 'H':-0.40, 'I':1.38, 'K':-1.50, 'L':1.06,
             'M':0.64, 'N':-0.78, 'P':0.12, 'Q':-0.85, 'R':-2.53,
             'S':-0.18, 'T':-0.05, 'V':1.08, 'W':0.81, 'Y':0.26},
            {'A':-0.5, 'C':-1.0, 'D':3.0, 'E':3.0, 'F':-2.5,
             'G':0.0, 'H':-0.5, 'I':-1.8, 'K':3.0, 'L':-1.8,
             'M':-1.3, 'N':0.2, 'P':0.0, 'Q':0.2, 'R':3.0,
             'S':0.3, 'T':-0.4, 'V':-1.5, 'W':-3.4, 'Y':-2.3},
            {'A':15.0, 'C':47.0, 'D':59.0, 'E':73.0, 'F':91.0,
             'G':1.0, 'H':82.0, 'I':57.0, 'K':73.0, 'L':57.0,
             'M':75.0, 'N':58.0, 'P':42.0, 'Q':72.0, 'R':101.0,
             'S':31.0, 'T':45.0, 'V':43.0, 'W':130.0, 'Y':107.0},
            # New: Power of N-terminal of the α helix (22nd feature)
            {'A':1.59, 'C':0.33, 'D':0.53, 'E':1.45, 'F':1.14,
             'G':0.53, 'H':0.89, 'I':1.22, 'K':1.13, 'L':1.91,
             'M':1.25, 'N':0.53, 'P':0.00, 'Q':0.98, 'R':0.67,
             'S':0.70, 'T':0.75, 'V':1.42, 'W':1.33, 'Y':0.58}
        ),
        # Group 2: (Block 2 + helix C-terminal)
        (
            # Block 2: Polarity, Molecular weight, Melting point
            {'A':0.5, 'C':2.5, 'D':-1, 'E':2.5, 'F':-2.5,
             'G':0, 'H':-0.5, 'I':1.8, 'K':3, 'L':-1.8,
             'M':-1.3, 'N':0.2, 'P':-1.4, 'Q':0.2, 'R':3,
             'S':0.3, 'T':-0.4, 'V':-1.5, 'W':-3.4, 'Y':-2.3},
            {'A':5.3, 'C':3.6, 'D':1.3, 'E':3.3, 'F':2.3,
             'G':4.8, 'H':1.4, 'I':3.1, 'K':4.1, 'L':4.7,
             'M':1.1, 'N':3, 'P':2.5, 'Q':2.4, 'R':2.6,
             'S':4.5, 'T':3.7, 'V':4.2, 'W':0.8, 'Y':2.3},
            {'A':0.81, 'C':0.71, 'D':1.17, 'E':0.53, 'F':1.2,
             'G':0.88, 'H':0.92, 'I':1.48, 'K':0.77, 'L':1.24,
             'M':1.05, 'N':0.62, 'P':0.61, 'Q':0.98, 'R':0.85,
             'S':0.92, 'T':1.18, 'V':1.66, 'W':1.18, 'Y':1.23},
            # New: Power of C-terminal of the α helix (23rd feature)
            {'A':1.44, 'C':0.76, 'D':2.13, 'E':2.01, 'F':1.01,
             'G':0.62, 'H':0.56, 'I':0.68, 'K':0.59, 'L':0.58,
             'M':0.73, 'N':0.93, 'P':2.19, 'Q':1.20, 'R':0.39,
             'S':0.81, 'T':1.25, 'V':0.63, 'W':1.40, 'Y':0.72}
        ),
        # Group 3: (Block 3 + helix middle)
        (
            # Block 3: Transfer free energy, Buriability, Bulkiness
            {'A':58, 'C':-97, 'D':116, 'E':-131, 'F':92,
             'G':-11, 'H':-73, 'I':107, 'K':-24, 'L':95,
             'M':78, 'N':-93, 'P':-79, 'Q':-139, 'R':-184,
             'S':-34, 'T':-7, 'V':100, 'W':59, 'Y':-11},
            {'A':1.37, 'C':8.93, 'D':-4.47, 'E':4.04, 'F':-7.96,
             'G':3.39, 'H':-1.65, 'I':-7.92, 'K':7.7, 'L':-8.68,
             'M':-7.13, 'N':6.29, 'P':6.25, 'Q':3.88, 'R':1.33,
             'S':4.08, 'T':4.02, 'V':-6.94, 'W':0.79, 'Y':-4.73},
            {'A':6.77, 'C':8.57, 'D':0.31, 'E':12.93, 'F':1.92,
             'G':7.95, 'H':2.8, 'I':2.72, 'K':10.2, 'L':4.43,
             'M':1.87, 'N':5.5, 'P':4.79, 'Q':5.24, 'R':6.87,
             'S':5.41, 'T':5.36, 'V':3.57, 'W':0.54, 'Y':2.26},
            # New: Power of the middle of the α helix (24th feature)
            {'A':1.22, 'C':1.53, 'D':0.56, 'E':1.28, 'F':1.13,
             'G':0.40, 'H':2.23, 'I':0.77, 'K':1.65, 'L':1.05,
             'M':1.47, 'N':0.93, 'P':0.00, 'Q':1.63, 'R':1.59,
             'S':0.87, 'T':0.46, 'V':1.20, 'W':0.46, 'Y':0.52}
        ),
        # Group 4: (Block 4 + first unfolding property)
        (
            # Block 4: Solvation free energy, Relative mutability, Residue volume
            {'A':0.87, 'C':0.66, 'D':1.52, 'E':0.67, 'F':2.87,
             'G':0.1, 'H':0.87, 'I':3.15, 'K':1.64, 'L':2.17,
             'M':1.67, 'N':0.09, 'P':2.77, 'Q':0, 'R':0.85,
             'S':0.07, 'T':0.07, 'V':1.87, 'W':3.77, 'Y':2.67},
            {'A':1.09, 'C':0.77, 'D':0.5, 'E':0.92, 'F':0.5,
             'G':1.25, 'H':0.67, 'I':0.66, 'K':1.25, 'L':0.44,
             'M':0.45, 'N':1.14, 'P':2.96, 'Q':0.83, 'R':0.97,
             'S':1.21, 'T':1.33, 'V':0.56, 'W':0.62, 'Y':0.94},
            {'A':0.91, 'C':1.4, 'D':0.93, 'E':0.97, 'F':0.72,
             'G':1.51, 'H':0.9, 'I':0.65, 'K':0.82, 'L':0.59,
             'M':0.58, 'N':1.64, 'P':1.66, 'Q':0.94, 'R':1,
             'S':1.23, 'T':1.04, 'V':0.6, 'W':0.67, 'Y':0.92},
            # From Block 7: Unfolding entropy change (first unfolding property)
            {'A':0.54, 'C':-4.14, 'D':-0.26, 'E':-0.19, 'F':-4.66,
             'G':-0.31, 'H':-0.23, 'I':-0.27, 'K':1.13, 'L':-0.24,
             'M':-2.36, 'N':1.74, 'P':-0.08, 'Q':1.53, 'R':3.69,
             'S':-0.24, 'T':-0.28, 'V':-0.36, 'W':-2.69, 'Y':-2.82}
        ),
        # Group 5: (Block 5 + second unfolding property)
        (
            # Block 5: Volume, Amino acid distribution, Hydration number
            {'A':0.92, 'C':0.48, 'D':1.16, 'E':0.61, 'F':1.25,
             'G':0.61, 'H':0.93, 'I':1.81, 'K':0.7, 'L':1.3,
             'M':1.19, 'N':0.6, 'P':0.4, 'Q':0.95, 'R':0.93,
             'S':0.82, 'T':1.12, 'V':1.81, 'W':1.54, 'Y':1.53},
            {'A':0.96, 'C':0.9, 'D':1.13, 'E':0.33, 'F':1.37,
             'G':0.9, 'H':0.87, 'I':1.54, 'K':0.81, 'L':1.26,
             'M':1.29, 'N':0.72, 'P':0.75, 'Q':1.18, 'R':0.67,
             'S':0.77, 'T':1.23, 'V':1.41, 'W':1.13, 'Y':1.07},
            {'A':0.9, 'C':0.47, 'D':1.24, 'E':0.62, 'F':1.23,
             'G':0.56, 'H':1.12, 'I':1.54, 'K':0.74, 'L':1.26,
             'M':1.09, 'N':0.62, 'P':0.42, 'Q':1.18, 'R':1.02,
             'S':0.87, 'T':1.3, 'V':1.53, 'W':1.75, 'Y':1.68},
            # From Block 7: Unfolding enthalpy change (second unfolding property)
            {'A':0.51, 'C':5.21, 'D':0.18, 'E':0.05, 'F':6.82,
             'G':-0.23, 'H':0.79, 'I':0.19, 'K':-1.45, 'L':0.17,
             'M':2.89, 'N':-2.03, 'P':0.02, 'Q':-1.76, 'R':-4.4,
             'S':-0.16, 'T':0.04, 'V':0.3, 'W':4.47, 'Y':3.73}
        ),
        # Group 6: (Block 6 + third unfolding property)
        (
            # Block 6: Isoelectric point, Compressibility, Chromatographic index
            {'A':6, 'C':5.05, 'D':2.77, 'E':5.22, 'F':5.48,
             'G':5.97, 'H':7.59, 'I':6.02, 'K':9.74, 'L':5.98,
             'M':5.74, 'N':5.41, 'P':6.3, 'Q':5.65, 'R':10.76,
             'S':5.68, 'T':5.66, 'V':5.96, 'W':5.89, 'Y':5.66},
            {'A':-25.5, 'C':-32.82, 'D':-33.12, 'E':-36.17, 'F':-34.54,
             'G':-27, 'H':-31.84, 'I':-31.78, 'K':-32.4, 'L':-31.78,
             'M':-31.18, 'N':-30.9, 'P':-23.25, 'Q':-32.6, 'R':-26.62,
             'S':-29.88, 'T':-31.23, 'V':-30.62, 'W':-30.24, 'Y':-35.01},
            {'A':9.9, 'C':2.8, 'D':2.8, 'E':3.2, 'F':18.8,
             'G':5.6, 'H':8.2, 'I':17.1, 'K':3.5, 'L':17.6,
             'M':14.7, 'N':5.4, 'P':14.8, 'Q':9, 'R':4.6,
             'S':6.9, 'T':9.5, 'V':14.3, 'W':17, 'Y':15},
            # From Block 7: Unfolding Gibbs free energy change (third unfolding property)
            {'A':-0.02, 'C':1.08, 'D':-0.08, 'E':-0.13, 'F':2.16,
             'G':0.09, 'H':0.56, 'I':-0.08, 'K':-0.32, 'L':-0.08,
             'M':0.53, 'N':-0.3, 'P':-0.06, 'Q':-0.23, 'R':-0.71,
             'S':-0.4, 'T':-0.24, 'V':-0.06, 'W':1.78, 'Y':-0.91}
        )
    ]
    
    # Compute features for each block and concatenate the results
    all_PseAAC = []
    for (prop1, prop2, prop3, prop4) in property_sets:
        block_features = compute_block(prop1, prop2, prop3, prop4)
        all_PseAAC.extend(block_features)
    
    # print("Final combined PseAAC vector:")
    # print(all_PseAAC)
    # print("Length of final vector:", len(all_PseAAC))
    return all_PseAAC

def extract_kmers(sequence, k=3):
    """
    Extract all k-mers from a sequence.
    
    Args:
        sequence: DNA sequence string
        k: k-mer length (default 3)
    
    Returns:
        List of k-mer strings
    """
    kmers = []
    for i in range(len(sequence) - k + 1):
        kmer = sequence[i:i+k]
        kmers.append(kmer)
    return kmers


def generate_single_kmer_features(kmer):
    """
    Generate features for a SINGLE k-mer (not a whole sequence).
    
    This extracts the relevant portion of what generate_kmer_vector does
    for one k-mer.
    
    Args:
        kmer: A single k-mer string (e.g., "ATG")
    
    Returns:
        Feature array for this k-mer
    """
    # TODO: You need to extract the single k-mer feature computation
    # from your existing generate_kmer_vector function
    
    # Example implementation (adjust based on your actual feature computation):
    # If you use one-hot encoding:
    base_to_index = {'A': 0, 'T': 1, 'G': 2, 'C': 3}
    features = np.zeros(4 * len(kmer))  # 4 bases × k positions
    
    for i, base in enumerate(kmer):
        if base in base_to_index:
            features[i * 4 + base_to_index[base]] = 1
    
    return features


def combine_kmer_features(kmer_features_list):
    """
    Combine individual k-mer features into a sequence feature vector.
    
    This depends on how your original generate_kmer_vector combines k-mers.
    Common approaches:
    - Average pooling
    - Max pooling
    - Concatenation (if fixed length)
    - Frequency counts
    
    Args:
        kmer_features_list: List of feature arrays for individual k-mers
    
    Returns:
        Combined feature vector for the sequence
    """
    # TODO: Implement based on your actual combination method
    
    # Example: Simple averaging (adjust based on your actual method)
    if not kmer_features_list:
        return np.zeros(340)  # Your k-mer feature dimension
    
    # Stack and average
    stacked = np.array(kmer_features_list)
    combined = np.mean(stacked, axis=0)
    
    return combined


# Example usage:
if __name__ == "__main__":
    apt_seq = "CAGACCCTCGATATCAAAAAAGCTAGCTTTGAACGTGCAT"  # Example aptamer sequence (not used in the calculation)
    # Example target protein sequence (must be longer than LambdaVal = 30)
    target_seq = "ACDEFGHIKLMNPQRSTVWYACDEFGHIKLMNPQRSTVWY"
    kmer = generate_kmer_vector(apt_seq)
    final_vector = compute_combined_pseaac(target_seq)
