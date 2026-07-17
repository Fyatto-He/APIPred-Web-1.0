// Nested layout for /results/[jobId]. This route renders the same
// Aptamer Designer component as /predict (via `import Home from
// "../../predict/page"`) and therefore needs the same visualization
// libraries. See AptamerVizScripts for the load-order rationale.

import AptamerVizScripts from "../components/AptamerVizScripts";
import { ReactNode } from "react";

export default function ResultsLayout({ children }: { children: ReactNode }) {
  return (
    <>
      <AptamerVizScripts />
      {children}
    </>
  );
}
