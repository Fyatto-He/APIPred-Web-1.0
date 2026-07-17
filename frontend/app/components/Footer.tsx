// Small footer shown on every page.
// Edit footerText in app/content/site.ts to change the copyright line.

import { site } from "../content/site";

export default function Footer() {
  return (
    <footer className="mt-12 border-t border-gray-200 bg-white">
      <div className="max-w-6xl mx-auto px-4 py-4 text-xs text-gray-500 flex justify-between">
        <span>{site.footerText}</span>
        <span>v{site.version}</span>
      </div>
    </footer>
  );
}
