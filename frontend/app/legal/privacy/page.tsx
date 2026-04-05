import type { Metadata } from 'next'

export const metadata: Metadata = { title: 'Privacy Notice' }

function Section({
  id,
  number,
  title,
  children,
}: {
  id: string
  number: string
  title: string
  children: React.ReactNode
}) {
  return (
    <section id={id} className="scroll-mt-24">
      <h2 className="mb-4 flex items-baseline gap-3 text-heading text-heading">
        <span className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-lg bg-primary/10 text-xs font-bold text-primary">
          {number}
        </span>
        {title}
      </h2>
      <div className="prose prose-sm max-w-none space-y-3 text-body">{children}</div>
    </section>
  )
}

function SubSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mt-4">
      <h3 className="mb-2 text-sm font-semibold text-heading">{title}</h3>
      <div className="space-y-2 text-xs leading-relaxed text-body">{children}</div>
    </div>
  )
}

const OVERVIEW = [
  {
    label: 'Controller',
    text: 'Stem Systems Ltd. operates Cogent and acts as controller for account, service, security, and product administration data.',
  },
  {
    label: 'Enterprise data',
    text: 'Where we process customer content solely on a business customer’s instructions, we act as processor under the applicable enterprise arrangement.',
  },
  {
    label: 'Core vendors',
    text: 'Cogent currently relies on Auth0 for authentication, OpenAI for certain model features, Resend for transactional email, and PostHog if analytics is enabled.',
  },
  {
    label: 'Your rights',
    text: 'You may request access, correction, deletion, restriction, portability, or object to certain processing, subject to applicable law.',
  },
]

export default function PrivacyPolicyPage() {
  return (
    <article className="flex flex-col gap-10">
      <div className="border-b border-border pb-8">
        <p className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-primary">Legal Document</p>
        <h1 className="mb-3 text-display text-heading">Privacy Notice</h1>
        <div className="flex flex-wrap gap-4 text-xs text-subtle">
          <span>
            Effective Date: <strong className="text-body">March 29, 2026</strong>
          </span>
          <span>
            Last Updated: <strong className="text-body">March 29, 2026</strong>
          </span>
          <span>
            Version: <strong className="text-body">3.0</strong>
          </span>
        </div>
      </div>

      <div className="rounded-2xl border border-border bg-surface p-6 shadow-card">
        <p className="text-xs leading-relaxed text-body">
          This Privacy Notice explains how <strong>Stem Systems Ltd.</strong> collects, uses, stores, shares, and
          protects personal data when you use <strong>Cogent</strong>. It is written primarily for compliance with the
          Nigeria Data Protection Act, 2023 (&ldquo;NDPA&rdquo;) and related guidance from the Nigeria Data Protection
          Commission (&ldquo;NDPC&rdquo;), while also supporting contractual commitments we may make to enterprise
          customers in other jurisdictions.
        </p>
        <p className="mt-3 text-xs leading-relaxed text-body">
          For privacy questions or rights requests, contact{' '}
          <a href="mailto:privacy@cogent.ai" className="text-primary hover:underline">
            privacy@cogent.ai
          </a>
          .
        </p>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {OVERVIEW.map(item => (
          <div key={item.label} className="rounded-xl border border-border bg-muted/40 p-4">
            <p className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-subtle">{item.label}</p>
            <p className="text-xs leading-relaxed text-body">{item.text}</p>
          </div>
        ))}
      </div>

      <Section id="who-we-are" number="1" title="Who We Are">
        <SubSection title="1.1 Identity">
          <p>
            Stem Systems Ltd. is the company responsible for operating Cogent. In this notice, references to
            &ldquo;Stem Systems,&rdquo; &ldquo;we,&rdquo; &ldquo;us,&rdquo; or &ldquo;our&rdquo; mean Stem Systems Ltd.
          </p>
        </SubSection>
        <SubSection title="1.2 Our Role">
          <p>
            In most cases, we act as the data controller for account creation, authentication orchestration, workspace
            administration, service security, audit logging, and product communications. For some enterprise customer
            content processed solely under customer instructions, we act as a processor and the customer remains the
            controller.
          </p>
        </SubSection>
      </Section>

      <Section id="collection" number="2" title="Information We Collect">
        <SubSection title="2.1 Account and Workspace Data">
          <p>
            We collect information such as your name, email address, organisation or workspace name, role, account
            status, and related profile details when you sign up or are invited to a workspace.
          </p>
        </SubSection>
        <SubSection title="2.2 Product Usage Data">
          <p>
            We collect information about how you use Cogent, including search queries, prompt and investigation activity,
            contract definitions, saved items, filters, settings, audit events, and similar workspace actions.
          </p>
        </SubSection>
        <SubSection title="2.3 Technical and Security Data">
          <p>
            We collect IP address, browser and device details, session data, timestamps, and system logs to secure the
            service, troubleshoot issues, and investigate abuse.
          </p>
        </SubSection>
        <SubSection title="2.4 Customer Content">
          <p>
            If you upload documents, enter strategic context, save investigations, or create workflow instructions, we
            process that content to deliver the service you requested.
          </p>
        </SubSection>
      </Section>

      <Section id="lawful-basis" number="3" title="Why We Process Personal Data">
        <p className="text-xs leading-relaxed">
          Under the NDPA, we process personal data only where there is a valid lawful basis. The main bases we rely on are
          contractual necessity, legal obligation, legitimate interests, and consent where required.
        </p>
        <div className="mt-3 overflow-x-auto rounded-xl border border-border">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-border bg-muted/50">
                <th className="px-4 py-2 text-left font-medium text-heading">Purpose</th>
                <th className="px-4 py-2 text-left font-medium text-heading">Primary basis</th>
              </tr>
            </thead>
            <tbody className="text-body">
              <tr className="border-b border-border">
                <td className="px-4 py-2">Create and manage your account or workspace</td>
                <td className="px-4 py-2">Contractual necessity</td>
              </tr>
              <tr className="border-b border-border">
                <td className="px-4 py-2">Provide search, signals, investigations, and saved outputs</td>
                <td className="px-4 py-2">Contractual necessity</td>
              </tr>
              <tr className="border-b border-border">
                <td className="px-4 py-2">Secure the service, detect abuse, and maintain logs</td>
                <td className="px-4 py-2">Legitimate interests / legal obligation</td>
              </tr>
              <tr className="border-b border-border">
                <td className="px-4 py-2">Improve product quality and feature performance</td>
                <td className="px-4 py-2">Legitimate interests</td>
              </tr>
              <tr className="border-b border-border">
                <td className="px-4 py-2">Analytics and optional product measurement</td>
                <td className="px-4 py-2">Consent or legitimate interests, depending on configuration and law</td>
              </tr>
              <tr>
                <td className="px-4 py-2">Marketing communications</td>
                <td className="px-4 py-2">Consent or another lawful basis permitted by law</td>
              </tr>
            </tbody>
          </table>
        </div>
      </Section>

      <Section id="product-processing" number="4" title="How Cogent Uses Source Material and AI">
        <SubSection title="4.1 Public and Lawfully Accessible Sources">
          <p>
            Cogent is designed to analyse and organise information from public or otherwise lawfully accessible sources,
            together with information users choose to provide inside the product. We do not position Cogent as a tool for
            bypassing authentication walls, protected systems, or private accounts.
          </p>
        </SubSection>
        <SubSection title="4.2 AI-Assisted Processing">
          <p>
            Cogent uses automated systems and model providers to support retrieval, summarisation, classification,
            enrichment, and explanation. These systems may process prompts, snippets, and related metadata needed to return
            the feature you asked for.
          </p>
        </SubSection>
        <SubSection title="4.3 Training Position">
          <p>
            We do not use identifiable customer content to train our own general-purpose models or a third party&apos;s
            general-purpose models without an appropriate permission, instruction, or another lawful basis.
          </p>
        </SubSection>
      </Section>

      <Section id="sharing" number="5" title="Sharing and Processors">
        <SubSection title="5.1 When We Share Personal Data">
          <p>
            We share personal data only where necessary to operate Cogent, meet legal obligations, protect rights and
            security, or deliver services requested by the customer.
          </p>
        </SubSection>
        <SubSection title="5.2 Current Service Providers">
          <div className="mt-2 overflow-x-auto rounded-xl border border-border">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-border bg-muted/50">
                  <th className="px-4 py-2 text-left font-medium text-heading">Provider</th>
                  <th className="px-4 py-2 text-left font-medium text-heading">Purpose</th>
                </tr>
              </thead>
              <tbody className="text-body">
                <tr className="border-b border-border">
                  <td className="px-4 py-2">Auth0</td>
                  <td className="px-4 py-2">Authentication, login flow, and identity-related account services</td>
                </tr>
                <tr className="border-b border-border">
                  <td className="px-4 py-2">OpenAI</td>
                  <td className="px-4 py-2">Model inference, embeddings, and AI-assisted product features</td>
                </tr>
                <tr className="border-b border-border">
                  <td className="px-4 py-2">Resend</td>
                  <td className="px-4 py-2">Transactional and notification email delivery</td>
                </tr>
                <tr>
                  <td className="px-4 py-2">PostHog (if enabled)</td>
                  <td className="px-4 py-2">Product analytics and service improvement</td>
                </tr>
              </tbody>
            </table>
          </div>
        </SubSection>
      </Section>

      <Section id="transfers" number="6" title="International Transfers">
        <p className="text-xs leading-relaxed">
          Some service providers or processing operations may involve data transfers outside Nigeria. Where that happens,
          we will use a lawful transfer mechanism and appropriate safeguards required by the NDPA or another applicable law.
        </p>
        <SubSection title="6.1 Enterprise Arrangements">
          <p>
            Where an enterprise customer requires more detailed transfer terms, those terms may be set out in a separate
            data processing addendum or order form.
          </p>
        </SubSection>
      </Section>

      <Section id="retention" number="7" title="Retention">
        <SubSection title="7.1 General Rule">
          <p>
            We keep personal data for as long as needed to provide the service, maintain security and audit records, meet
            legal obligations, resolve disputes, and enforce agreements.
          </p>
        </SubSection>
        <SubSection title="7.2 Typical Retention Approach">
          <ul className="list-disc space-y-1 pl-5 text-xs text-body">
            <li>account and workspace records are retained while the account remains active and for a limited period afterward;</li>
            <li>logs and security records are retained for operational, security, and compliance purposes;</li>
            <li>customer content may remain available until deleted by the customer, removed under retention settings, or deleted after account closure;</li>
            <li>some records may be retained longer where required by law, litigation hold, or fraud-prevention needs.</li>
          </ul>
        </SubSection>
      </Section>

      <Section id="rights" number="8" title="Your Rights">
        <p className="text-xs leading-relaxed">
          Depending on the circumstances and applicable law, you may have rights to access, correct, delete, restrict,
          object to, or receive a copy of your personal data.
        </p>
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          {[
            'request access to personal data we hold about you;',
            'correct inaccurate or incomplete information;',
            'request deletion where there is no valid reason to keep the data;',
            'object to certain processing based on legitimate interests;',
            'request restriction of processing in some cases;',
            'request data portability where applicable.',
          ].map(item => (
            <div key={item} className="rounded-xl border border-border bg-surface p-4 text-xs leading-relaxed text-body">
              {item}
            </div>
          ))}
        </div>
        <SubSection title="8.1 Complaints">
          <p>
            You may contact us first at{' '}
            <a href="mailto:privacy@cogent.ai" className="text-primary hover:underline">
              privacy@cogent.ai
            </a>
            . If you believe your concern has not been resolved, you may also complain to the Nigeria Data Protection
            Commission or another competent authority where applicable.
          </p>
        </SubSection>
      </Section>

      <Section id="cookies" number="9" title="Cookies and Analytics">
        <p className="text-xs leading-relaxed">
          Cogent uses cookies and similar technologies for login, security, session continuity, and product preferences.
          Where analytics is enabled, we may also use analytics technologies to understand feature performance and product
          usage. Where consent is required, we will rely on it before enabling non-essential analytics processing.
        </p>
      </Section>

      <Section id="security" number="10" title="Security">
        <p className="text-xs leading-relaxed">
          We use technical and organisational measures designed to protect personal data against unauthorised access, loss,
          misuse, disclosure, or alteration. No system can be guaranteed to be completely secure, so we encourage users to
          protect their credentials and use strong access controls.
        </p>
      </Section>

      <Section id="children" number="11" title="Children">
        <p className="text-xs leading-relaxed">
          Cogent is intended for business and professional use. It is not designed for children, and we do not knowingly
          offer the service directly to children.
        </p>
      </Section>

      <Section id="changes" number="12" title="Changes to This Notice">
        <p className="text-xs leading-relaxed">
          We may update this Privacy Notice from time to time. When the change is material, we will provide a reasonable
          notice by email, in-product message, or by updating the date at the top of this page.
        </p>
      </Section>

      <div className="rounded-2xl border border-primary/20 bg-primary/5 p-6">
        <h3 className="mb-2 text-sm font-semibold text-heading">Need to contact us about privacy?</h3>
        <p className="text-xs leading-relaxed text-body">
          Email{' '}
          <a href="mailto:privacy@cogent.ai" className="text-primary hover:underline">
            privacy@cogent.ai
          </a>{' '}
          for data requests, privacy questions, or enterprise privacy documentation.
        </p>
      </div>

      <div className="flex flex-col items-start justify-between gap-4 rounded-xl border border-border bg-surface px-6 py-4 sm:flex-row sm:items-center">
        <div>
          <p className="text-sm font-medium text-heading">Privacy contact</p>
          <p className="text-xs text-subtle">For rights requests, privacy questions, or enterprise privacy review.</p>
        </div>
        <a
          href="mailto:privacy@cogent.ai"
          className="rounded-xl bg-primary px-4 py-2 text-xs font-medium text-white transition-colors hover:bg-primary-hover"
        >
          privacy@cogent.ai
        </a>
      </div>
    </article>
  )
}
