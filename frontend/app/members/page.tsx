// Members page. Content lives in app/content/members.ts — edit that file
// to add / update people, roles, emails, personal websites, or images.

import { members, type Member } from "../content/members";

export const metadata = { title: "Members" };

// Two initials from the name — shown when a member has no image on file.
function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase() ?? "")
    .join("");
}

function Avatar({ member }: { member: Member }) {
  const size = "w-20 h-20"; // 80px — matches typical bio-page thumbnails
  if (member.image) {
    return (
      <img
        src={member.image}
        alt={member.name}
        className={`${size} rounded-full object-cover border border-gray-200`}
      />
    );
  }
  // Fallback: light-purple circle with initials (matches site accent).
  return (
    <div
      className={`${size} rounded-full flex items-center justify-center text-lg font-semibold text-white`}
      style={{ backgroundColor: "rgb(160, 120, 200)" }}
      aria-hidden="true"
    >
      {initials(member.name)}
    </div>
  );
}

export default function MembersPage() {
  return (
    <div className="max-w-3xl mx-auto px-4 py-10">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Project Members</h1>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {members.map((m, i) => (
          <div
            key={i}
            className="bg-white border border-gray-200 rounded-md p-4 flex gap-4 items-start"
          >
            <Avatar member={m} />
            <div className="min-w-0">
              <div className="font-semibold text-gray-900">
                {m.website ? (
                  <a
                    href={m.website}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 hover:underline"
                  >
                    {m.name}
                  </a>
                ) : (
                  m.name
                )}
              </div>
              <div className="text-sm text-gray-700">{m.role}</div>
              {m.affiliation && (
                <div className="text-xs text-gray-500 mt-1">{m.affiliation}</div>
              )}
              {m.email && (
                <div className="text-xs text-gray-500 mt-1 truncate">
                  <a href={`mailto:${m.email}`} className="text-blue-600 hover:underline">
                    {m.email}
                  </a>
                </div>
              )}
              {m.github && (
                <div className="text-xs text-gray-500 mt-1 truncate">
                  GitHub:{" "}
                  <a
                    href={m.github}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 hover:underline"
                  >
                    {m.github.replace(/^https?:\/\//, "")}
                  </a>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
