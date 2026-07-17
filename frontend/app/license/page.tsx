// License page — CC BY-NC-SA 4.0, plus citation info.
// Update the citation refs in the CITATIONS array below when a new
// paper is published or the preprint is updated.

export const metadata = { title: "License" };

const CITATIONS: string[] = [
  "Fang Z, Wu Z, Wu X, Chen S, Wang X, Umrao S, Dwivedy A. APIPred: An XGBoost-Based Method for Predicting Aptamer-Protein Interactions. J Chem Inf Model. 2024 Apr 8;64(7):2290-2301. doi: 10.1021/acs.jcim.3c00713. Epub 2023 Dec 21. PMID: 38127053; PMCID: PMC11001522.",
  "Catherine Zhang, Juncheng He, Dhanush Gandavadi, Chau Nguyen Minh Hoang, Hyeongjun Cho, Minjun Son, Xing Wang, Abhisek Dwivedy, Saurabh Umrao. bioRxiv 2025.12.31.697194; doi: https://doi.org/10.64898/2025.12.31.697194",
];

export default function LicensePage() {
  return (
    <div className="max-w-3xl mx-auto px-4 py-10 space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">License</h1>

      <section className="bg-white border border-gray-200 rounded-md p-6 text-sm text-gray-700 leading-relaxed space-y-4">
        <p>
          <strong>
            APIPred Web is released under the Creative Commons
            Attribution-NonCommercial-ShareAlike 4.0 International License
            (CC&nbsp;BY-NC-SA&nbsp;4.0).
          </strong>
        </p>

        <p>Under this license you are free to:</p>
        <ul className="list-disc pl-6 space-y-1">
          <li>
            <strong>Share</strong> — copy and redistribute the material in any
            medium or format.
          </li>
          <li>
            <strong>Adapt</strong> — remix, transform, and build upon the
            material.
          </li>
        </ul>

        <p>Under the following terms:</p>
        <ul className="list-disc pl-6 space-y-1">
          <li>
            <strong>Attribution</strong> — you must give appropriate credit,
            provide a link to the license, and indicate if changes were made.
          </li>
          <li>
            <strong>NonCommercial</strong> — you may not use the material for
            commercial purposes.
          </li>
          <li>
            <strong>ShareAlike</strong> — if you remix, transform, or build
            upon the material, you must distribute your contributions under
            the same license as the original.
          </li>
        </ul>

        <p className="text-xs text-gray-500 pt-2">
          Full license text:{" "}
          <a
            href="https://creativecommons.org/licenses/by-nc-sa/4.0/"
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-600 hover:underline"
          >
            creativecommons.org/licenses/by-nc-sa/4.0
          </a>
        </p>
      </section>

      <section className="bg-white border border-gray-200 rounded-md p-6 text-sm text-gray-700 leading-relaxed space-y-3">
        <h2 className="text-lg font-semibold text-gray-900">Citation</h2>
        <p>
          If you used APIPred Web 1.0 for your research, please cite:
        </p>
        <ol className="list-decimal pl-6 space-y-3">
          {CITATIONS.map((c, i) => (
            <li key={i} className="leading-relaxed">
              {c}
            </li>
          ))}
        </ol>
      </section>
    </div>
  );
}
