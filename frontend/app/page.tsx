// Home page: hero + grid of module cards.
// Module list lives in app/content/modules.ts — add an entry there to
// show a new card here.
// (touched to force Next dev to re-emit app/page.js chunk)

import ModuleCard from "./components/ModuleCard";
import { modules } from "./content/modules";
import { site } from "./content/site";

export default function HomePage() {
  return (
    <div className="max-w-6xl mx-auto px-4 py-10">
      <section className="text-center mb-10">
        <h1 className="text-3xl font-bold text-gray-900">{site.fullTitle}</h1>
        <p className="mt-2 text-gray-600">
          Tools for predicting and designing DNA aptamers for protein targets.
        </p>
      </section>

      <section>
        <h2 className="text-xl font-semibold text-gray-800 mb-4">Modules</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {modules.map((m) => (
            <ModuleCard key={m.slug} module={m} />
          ))}
        </div>
      </section>
    </div>
  );
}
