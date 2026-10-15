import { LegalPage, type LegalSection } from "./legal-page"
import { ISSUES_URL } from "./terms-page"

const sections: LegalSection[] = [
  {
    heading: "Who runs this",
    body: [
      "Pro-Goal is a personal learning project run by one person. It is not a company, and it has no support team or service guarantees.",
    ],
  },
  {
    heading: "What we store",
    body: [
      "Account details: your name, email address, password (stored as a hash, never in plain text), and an avatar if you add one. If you sign in with Google, we also store your Google account ID and the profile picture and name Google shares.",
      "Your content: the projects, tasks, notes, comments, and attachments you create, and who you give access to them.",
      "Security and activity records: sign-in events with an IP address and device name, and a log of changes inside projects you belong to.",
    ],
  },
  {
    heading: "Cookies",
    body: [
      "We use a session cookie to keep you signed in and a CSRF cookie to protect your requests. We do not use advertising or tracking cookies.",
    ],
  },
  {
    heading: "How it is used",
    body: [
      "Only to run the app: to sign you in, show your projects, and send the emails the app needs, such as email verification and join requests. We do not sell your data and we do not use it for advertising.",
    ],
  },
  {
    heading: "Who can see what",
    body: [
      "Members of a project can see its content. Owners see members' names and emails. Strangers on Explore see only a listed project's name, description, tags, owner's first name, size, and dates.",
      "Demo projects are shared by everyone with an account. Do not put anything private in them.",
    ],
  },
  {
    heading: "Third parties",
    body: [
      "We rely on services that process data for us, such as hosting, file storage, email delivery, and Google sign-in. If you connect an integration like Slack, the project data you choose to share goes to that service.",
    ],
  },
  {
    heading: "Keeping and deleting data",
    body: [
      "You can delete your account from your account settings. Your account is removed after a short grace period, and signing in during that time cancels it. Projects you own must be deleted or handed over first.",
      "Because this is a learning project, data may also be reset or lost without notice. Do not rely on it as a record.",
    ],
  },
  {
    heading: "Contact",
    body: [
      <>For questions about your data, open an issue on the project's <a className="underline underline-offset-2" href={ISSUES_URL} target="_blank" rel="noreferrer">GitHub issue tracker</a>. Do not post private information there.</>,
    ],
  },
]

export function PrivacyPage() {
  return <LegalPage sheet="LEGAL-02" title="Privacy policy" updated="11 October 2026" sections={sections} />
}
