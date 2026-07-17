// Top navigation bar shown on every page.
// Reads its links from app/content/nav.ts and its title from app/content/site.ts.
// To add a new page: create the route folder, then add it to navLinks in nav.ts.

"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { navLinks } from "../content/nav";
import { site } from "../content/site";

export default function Header() {
  const pathname = usePathname();

  return (
    <header className="border-b border-gray-200 bg-white">
      <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between gap-4">
        <Link href="/" className="font-semibold text-lg text-gray-900 hover:text-blue-600">
          {site.name}
        </Link>
        <nav className="flex flex-wrap gap-x-4 gap-y-1 text-sm">
          {navLinks.map((link) => {
            const active =
              link.href === "/"
                ? pathname === "/"
                : pathname === link.href || pathname.startsWith(link.href + "/");
            return (
              <Link
                key={link.href}
                href={link.href}
                className={
                  active
                    ? "text-blue-600 font-medium"
                    : "text-gray-700 hover:text-blue-600"
                }
              >
                {link.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
