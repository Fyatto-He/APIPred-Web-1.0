// Contact page.

export const metadata = { title: "Contact" };

export default function ContactPage() {
  return (
    <div className="max-w-3xl mx-auto px-4 py-10">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Contact</h1>
      <div className="bg-white border border-gray-200 rounded-md p-6 text-sm text-gray-700 space-y-3">
        <p>
          For regular inquiries, please contact Xing, Abhisek, or Saurabh.
          See the{" "}
          <a href="/members" className="text-blue-600 hover:underline">
            Members
          </a>{" "}
          page for email addresses.
        </p>
      </div>
    </div>
  );
}
