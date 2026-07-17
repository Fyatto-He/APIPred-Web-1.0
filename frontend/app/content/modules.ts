// Modules displayed on the home page as clickable cards.
// Add a new object here to register a new module on the home page.
// Set `status: "coming-soon"` for stubs.

export type Module = {
  slug: string;
  title: string;
  description: string;
  href: string;
  status: "live" | "coming-soon";
};

export const modules: Module[] = [
  {
    slug: "predict",
    title: "Aptamer Designer",
    description:
      "Generate and rank candidate DNA aptamers for a target amino-acid sequence. " +
      "Uses an XGBoost interaction model plus DNA-parameter ViennaRNA folding.",
    href: "/predict",
    status: "live",
  },
  {
    slug: "future-module",
    title: "Coming Soon",
    description:
      "A future analysis module will live here.",
    href: "#",
    status: "coming-soon",
  },
];
