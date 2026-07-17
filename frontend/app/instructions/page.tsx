// Instructions page. Content lives in app/content/instructions.ts.

import { instructions } from "../content/instructions";

export const metadata = { title: "Instructions" };

export default function InstructionsPage() {
  return (
    <div className="max-w-3xl mx-auto px-4 py-10">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Instructions</h1>
      <div className="space-y-6">
        {instructions.map((section, i) => (
          <section key={i} className="bg-white border border-gray-200 rounded-md p-4">
            <h2 className="font-semibold text-gray-900 mb-2">{section.title}</h2>
            <ul className="list-disc pl-6 text-sm text-gray-700 space-y-1">
              {section.body.map((line, j) => (
                <li key={j}>{line}</li>
              ))}
            </ul>
          </section>
        ))}
      </div>
    </div>
  );
}
