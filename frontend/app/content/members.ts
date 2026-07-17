// Team / project members shown on /members.
// Add / edit people by editing this array. Optional fields (affiliation,
// email, website, image) are simply omitted when not applicable.
// - `website`  → member's name renders as a clickable link
// - `image`    → path under /public (e.g. "/images/members/xing.jpg").
//               Drop the file in frontend/public/images/members/ and set
//               the path here. If omitted, an initials avatar is shown.

export type Member = {
  name: string;
  role: string;
  affiliation?: string;
  email?: string;
  website?: string;  // linked from the member's name
  github?: string;   // shown as a separate "GitHub" line
  image?: string;
};

export const members: Member[] = [
  {
    name: "Xing Wang",
    role: "Principal Investigator",
    email: "xingw@illinois.edu",
    image: "/images/members/xing.jpg",
  },
  {
    name: "Abhisek Dwivedy",
    role: "Principal Investigator",
    email: "abhisekdwivedyillinois@gmail.com",
    website: "https://abhisekdwivedy.wixsite.com/abhisekdwivedy",
    image: "/images/members/abhisek.jpg",
  },
  {
    name: "Saurabh Umrao",
    role: "Principal Investigator",
    email: "usaurabh@illinois.edu",
    website: "https://sites.google.com/view/saurabhumrao/",
    github: "https://github.com/saurabhumrao",
    image: "/images/members/saurabh.jpg",
  },
  {
    name: "Catherine Zhang",
    role: "Main Developer",
    email: "catherinezhang1717@gmail.com",
    // image: "/images/members/catherine.jpg",
  },
  {
    name: "Henry He",
    role: "Main Developer",
    email: "fyattohe12@gmail.com",
    // image: "/images/members/henry.jpg",
  },
];
