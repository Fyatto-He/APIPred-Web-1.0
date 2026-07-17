// app/results/[jobId]/page.tsx
// Persistent bookmark URL for a completed job. Renders the same
// Aptamer Designer component as /predict — that component reads the
// job id from the URL pathname (see the /\/results\/([a-zA-Z0-9-]+)/
// match in predict/page.tsx) and fetches the stored result.
"use client";

import { useParams } from "next/navigation";
import Home from "../../predict/page";

export default function JobPage() {
  const params = useParams();

  // Convert params.jobId to string if it's an array
  const jobId = Array.isArray(params.jobId)
    ? params.jobId[0]
    : params.jobId as string;

  return <Home key={jobId} />;
}