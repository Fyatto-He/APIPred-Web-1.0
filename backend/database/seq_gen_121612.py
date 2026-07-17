from itertools import product
from tqdm import tqdm
import time
def generate_gene_sequences(file_name="gene_sequences20.txt", front="", end=""):
    bases = ['A', 'G', 'C', 'T']
    sequence_length = 16
    total_sequences = 4 ** sequence_length
    batch_size = 10000
    with open(file_name, "w") as file:
        buffer = []
        start_time = time.time()
        for i, sequence in enumerate(tqdm(product(bases, repeat=sequence_length), total=total_sequences, desc="Generating sequences")):
            formatted_sequence = f"{front}{''.join(sequence)}{end}\n"
            buffer.append(formatted_sequence)
            if (i + 1) % batch_size == 0:
                file.writelines(buffer)
                buffer = []
        if buffer:
            file.writelines(buffer)
    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"All possible {sequence_length}-base gene sequences saved to {file_name}.")
    print(f"Elapsed time: {elapsed_time:.2f} seconds")
generate_gene_sequences(file_name="gene_sequences12-16-12.txt", front="TTTCGCACCAAC", end="AAGCGCCAAGTA")