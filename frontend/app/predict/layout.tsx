// Nested layout for /predict. Loads the RNA visualization libraries
// (D3 v3 + Fornac) scoped to this route only, so they don't ship on
// pages that don't need them (Home, FAQ, etc.).
//
// The actual script-loading logic lives in AptamerVizScripts so it can
// be reused by /results/[jobId], which also renders the prediction UI.

import AptamerVizScripts from "../components/AptamerVizScripts";
import { ReactNode } from "react";

export default function PredictLayout({ children }: { children: ReactNode }) {
  return (
    <>
      <AptamerVizScripts />
      {children}
    </>
  );
}
