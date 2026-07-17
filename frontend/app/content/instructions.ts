// Instructions rendered on /instructions. Grouped into sections.

export type InstructionSection = { title: string; body: string[] };

export const instructions: InstructionSection[] = [
  {
    title: "1. What you need",
    body: [
      "A target amino-acid sequence (the protein you want an aptamer to bind).",
      "Optionally, custom DNA prefix and suffix strings if you want to override the built-in primers.",
    ],
  },
  {
    title: "2. Choose parameters",
    body: [
      "Variant length: length (in bases) of the variable region generated between the prefix and suffix. Larger values mean a much larger search space.",
      "Total length: the full aptamer length (prefix + variant + suffix). Must be at least variant length + 2.",
      "Max sequences: upper bound on how many candidates the search will consider.",
    ],
  },
  {
    title: "3. Submit and wait",
    body: [
      "Click Submit. The job is queued in the background and you are redirected to a live progress view.",
      "The progress bar and remaining-time estimate update every second or so.",
      "You can bookmark the result URL — it stays valid for 90 days.",
    ],
  },
  {
    title: "4. Read the results",
    body: [
      "The top 25 candidates are shown, ranked by interaction probability (higher = more likely to bind the target).",
      "Each row shows the candidate sequence, its predicted secondary structure (fornac visualization), and its MFE in kcal/mol.",
      "Use the Start New Task button to reset the form and submit a different query.",
    ],
  },
];
