// Header nav links, in display order.
// Edit this array to add / remove / rename entries in the top nav bar.

export type NavLink = { href: string; label: string };

export const navLinks: NavLink[] = [
  { href: "/",             label: "Home" },
  { href: "/predict",      label: "Aptamer Designer" },
  { href: "/instructions", label: "Instructions" },
  { href: "/faq",          label: "FAQ" },
  { href: "/members",      label: "Members" },
  { href: "/license",      label: "License" },
  { href: "/contact",      label: "Contact" },
];
