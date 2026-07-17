// FAQ entries rendered on /faq. Add or edit items here.

export type FAQItem = { question: string; answer: string };

export const faq: FAQItem[] = [
  {
    question: "What does the Aptamer Designer actually do?",
    answer:
      "Given a target amino-acid sequence, the service iterates over candidate DNA aptamer variants " +
      "(a variable region flanked by fixed prefix and suffix), scores each with a machine-learning " +
      "interaction model, folds it with ViennaRNA using DNA thermodynamics, and returns the top 25 " +
      "highest-scoring candidates.",
  },
  {
    question: "What does the interaction probability score mean?",
    answer:
      "It is the output of an XGBoost classifier trained on known aptamer–protein pairs. Values are in " +
      "[0, 1]; higher values indicate a candidate the model considers more likely to bind the target.",
  },
  {
    question: "What is MFE and why can it be positive?",
    answer:
      "MFE is the Minimum Free Energy of the predicted secondary structure in kcal/mol. More-negative " +
      "values mean a more stable fold. Values near zero (or positive) mean the sequence is unlikely " +
      "to fold into a stable structure under the DNA thermodynamic model.",
  },
  {
    question: "Why does my job take a while?",
    answer:
      "Each candidate sequence is filtered by GC content and repeat rules, then scored by the ML model, " +
      "then folded. For large search spaces (e.g. variant length 12+ with many target sequences) this " +
      "adds up. Progress and estimated remaining time update while the job runs.",
  },
  {
    question: "How long are results kept?",
    answer:
      "Result URLs stay valid for 90 days from job submission. Bookmark the result URL if you need to " +
      "return to a specific job.",
  },
  {
    question: "Can I submit a custom prefix and suffix?",
    answer:
      "Yes. Toggle the custom-sequences option in the Aptamer Designer form and enter DNA prefix / " +
      "suffix strings (A, T, G, C only). The variant region is generated between them.",
  },
];
