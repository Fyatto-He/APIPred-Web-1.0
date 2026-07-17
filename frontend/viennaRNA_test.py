import RNA
import subprocess

sequence = "GCGGAUUUAGCUCAGUUGGAGAGCGCCAGACUGAUGGGUUUC"
(ss, mfe) = RNA.fold(sequence)
print(f"RNA: {sequence}, Structure: {ss}, MFE: {mfe}")

# Save sequence and structure to a file
with open("rna_input.txt", "w") as f:
    f.write(sequence + "\n")
    f.write(ss + "\n")

# Run RNAfold + RNAplot to generate a 2D structure plot
subprocess.run("RNAfold < rna_input.txt | RNAplot", shell=True)

print("Structure Plot Generated: Check output files")
