// Clickable card used on the home page to list modules.
// The list of modules lives in app/content/modules.ts.

import Link from "next/link";
import type { Module } from "../content/modules";

export default function ModuleCard({ module: m }: { module: Module }) {
  const isLive = m.status === "live";

  const cardBody = (
    <div
      className={
        "block p-6 rounded-lg border transition " +
        (isLive
          ? "border-gray-200 bg-white hover:border-blue-500 hover:shadow-md"
          : "border-dashed border-gray-300 bg-gray-50 opacity-70 cursor-not-allowed")
      }
    >
      <div className="flex items-start justify-between mb-2">
        <h3 className="text-lg font-semibold text-gray-900">{m.title}</h3>
        {!isLive && (
          <span className="text-xs px-2 py-0.5 rounded bg-gray-200 text-gray-600">
            Coming soon
          </span>
        )}
      </div>
      <p className="text-sm text-gray-600">{m.description}</p>
    </div>
  );

  if (!isLive) return cardBody;
  return <Link href={m.href}>{cardBody}</Link>;
}
