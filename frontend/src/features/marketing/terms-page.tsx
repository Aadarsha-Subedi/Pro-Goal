import { LegalPage, type LegalSection } from "./legal-page"

export const ISSUES_URL = "https://github.com/Aadarsha-Subedi/Pro-Goal-Frontend/issues"

const sections: LegalSection[] = [
  {
    heading: "What Pro-Goal is",
    body: [
      "Pro-Goal is a personal learning project built to practise building a project tracker. It is not a commercial product, and nobody is paid to run it.",
      "By creating an account or using the site you agree to these terms. If you do not agree, please do not use it.",
    ],
  },
  {
    heading: "Not for real work",
    body: [
      "Do not use Pro-Goal to run a business, manage client work, or keep anything you cannot afford to lose. Do not store passwords, financial details, health information, or other sensitive or confidential data in it.",
      "Use it to try ideas, learn, and explore.",
    ],
  },
  {
    heading: "No promises",
    body: [
      "The service is provided as is, with no warranty of any kind. It may be slow, change, break, or go offline at any time, without notice.",
      "Your data may be lost, reset, or deleted at any time. Keep your own copy of anything you care about.",
    ],
  },
  {
    heading: "Shared demo projects",
    body: [
      "Demo projects are shared, read-only, and owned by a system account. Everyone with an account can see them. Do not expect privacy there, and do not add real information to a copy you plan to keep secret.",
      "A copy you make from a demo is yours. It is still subject to every other term here.",
    ],
  },
  {
    heading: "Your conduct",
    body: [
      "Do not break the law, harass others, upload harmful files, probe or attack the service, or try to read other people's data. Accounts or content that do may be removed without warning.",
      "You are responsible for what you add to your own projects and for who you let join them.",
    ],
  },
  {
    heading: "Your account",
    body: [
      "Keep your sign-in details to yourself. You can delete your account from your account settings. Deletion takes effect after a short grace period, during which signing in cancels it.",
    ],
  },
  {
    heading: "Liability",
    body: [
      "To the fullest extent the law allows, the maker of Pro-Goal is not liable for any loss or damage that comes from using it, including lost data, lost time, or lost income.",
    ],
  },
  {
    heading: "Changes and contact",
    body: [
      <>These terms may change as the project does. Continuing to use Pro-Goal after a change means you accept it. Questions or concerns can go to the project's <a className="underline underline-offset-2" href={ISSUES_URL} target="_blank" rel="noreferrer">issue tracker on GitHub</a>.</>,
    ],
  },
]

export function TermsPage() {
  return <LegalPage sheet="LEGAL-01" title="Terms of service" updated="11 October 2026" sections={sections} />
}
