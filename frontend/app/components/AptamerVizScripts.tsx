// Shared visualization script loader used by any route that renders
// the Aptamer Designer UI (which needs the D3 + Fornac libraries to
// draw RNA secondary structures).
//
// Currently wrapped around /predict (app/predict/layout.tsx) and
// /results/[jobId] (app/results/layout.tsx). Add it to any future
// layout that mounts the prediction component.
//
// Ordering matters: fornac.js is a UMD bundle that captures window.d3
// at load time (`t.fornac = e(t.d3)`). If fornac loads before d3, its
// internal d3 reference is undefined and every rendering call fails
// with "Cannot read properties of undefined (reading 'select')".
// Nested layouts can't use strategy="beforeInteractive" (Next silently
// ignores it outside the root layout), so we chain the loads: fornac's
// <Script> only mounts after d3's onLoad fires.

"use client";

import Script from "next/script";
import { useState } from "react";

export default function AptamerVizScripts() {
  const [d3Ready, setD3Ready] = useState(false);

  return (
    <>
      <Script
        src="https://cdnjs.cloudflare.com/ajax/libs/d3/3.5.17/d3.min.js"
        strategy="afterInteractive"
        onLoad={() => setD3Ready(true)}
        onReady={() => setD3Ready(true)}
      />
      {d3Ready && (
        <Script
          src="/fornac.js?v=1.1.16"
          strategy="afterInteractive"
        />
      )}
    </>
  );
}
