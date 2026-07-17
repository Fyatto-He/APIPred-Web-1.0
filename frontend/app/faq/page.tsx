// FAQ page. Content lives in app/content/faq.ts — edit that file to add items.

import { faq } from "../content/faq";

export const metadata = { title: "FAQ" };

export default function FAQPage() {
  return (
    <div className="max-w-3xl mx-auto px-4 py-10">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">
        Frequently Asked Questions
      </h1>
      <div className="space-y-6">
        {faq.map((item, i) => (
          <div key={i} className="bg-white border border-gray-200 rounded-md p-4">
            <h2 className="font-semibold text-gray-900 mb-2">{item.question}</h2>
            <p className="text-sm text-gray-700 leading-relaxed">{item.answer}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
