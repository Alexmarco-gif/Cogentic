import type { Metadata } from 'next'

export const metadata: Metadata = { title: 'Privacy Policy' }

/* ─── Section helpers ──────────────────────────────────────────────────────── */

function Section({ id, number, title, children }: { id: string; number: string; title: string; children: React.ReactNode }) {
  return (
    <section id={id} className="scroll-mt-24">
      <h2 className="flex items-baseline gap-3 text-heading text-heading mb-4">
        <span className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-lg bg-primary/10 text-xs font-bold text-primary">
          {number}
        </span>
        {title}
      </h2>
      <div className="prose prose-sm max-w-none text-body space-y-3">{children}</div>
    </section>
  )
}

function SubSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mt-4">
      <h3 className="text-sm font-semibold text-heading mb-2">{title}</h3>
      <div className="text-xs leading-relaxed text-body space-y-2">{children}</div>
    </div>
  )
}

/* ─── Page ─────────────────────────────────────────────────────────────────── */

export default function PrivacyPolicyPage() {
  return (
    <article className="flex flex-col gap-10">
      {/* ── Header ────────────────────────────────────────────────────────── */}
      <div className="border-b border-border pb-8">
        <p className="text-[10px] font-semibold uppercase tracking-wider text-primary mb-2">Legal Document</p>
        <h1 className="text-display text-heading mb-3">Privacy Policy</h1>
        <div className="flex flex-wrap gap-4 text-xs text-subtle">
          <span>Effective Date: <strong className="text-body">March 1, 2026</strong></span>
          <span>Last Updated: <strong className="text-body">March 1, 2026</strong></span>
          <span>Version: <strong className="text-body">2.0</strong></span>
        </div>
      </div>

      {/* ── Preamble ──────────────────────────────────────────────────────── */}
      <div className="rounded-2xl border border-border bg-surface p-6 shadow-card">
        <p className="text-xs leading-relaxed text-body">
          This Privacy Policy explains how <strong>Cogent Technologies Ltd.</strong> (&ldquo;Cogent,&rdquo;
          &ldquo;we,&rdquo; &ldquo;us,&rdquo; or &ldquo;our&rdquo;) collects, uses, stores, shares, and
          protects information in connection with the Cogent platform. We are committed to transparency and
          comply with the <strong>Nigeria Data Protection Act (NDPA) 2023</strong>, the <strong>EU General
          Data Protection Regulation (GDPR)</strong>, the <strong>EU Data Act (2025/2026)</strong>, and other
          applicable data protection laws.
        </p>
        <p className="mt-3 text-xs leading-relaxed text-body">
          Cogent operates as both a <strong>Data Controller</strong> (when gathering market and public data
          for signal synthesis) and a <strong>Data Processor</strong> (when handling user-provided data on
          behalf of enterprise customers). This dual role is reflected throughout this policy.
        </p>
      </div>

      {/* ── Quick Overview Cards ──────────────────────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {[
          { label: 'Data collected', text: 'Account information, usage patterns, search queries, contract definitions, and platform interaction data — strictly minimised.' },
          { label: 'Lawful basis', text: 'Contractual Necessity (to run the platform) and Legitimate Interest (to improve signal quality and platform performance).' },
          { label: 'Data retention', text: 'Active data retained while your account is active. User Content deleted 90 days after account closure. Anonymised aggregates retained indefinitely.' },
          { label: 'Your rights', text: 'Access, rectification, portability (JSON/CSV export), erasure, restriction, and the right to object to automated processing.' },
          { label: 'Third parties', text: 'We do not sell your data. Sub-processors are listed below with 30-day advance notice of changes.' },
          { label: 'International transfers', text: 'Data may be processed in Nigeria and the EU. Transfers safeguarded by Standard Contractual Clauses (SCCs).' },
        ].map(item => (
          <div key={item.label} className="rounded-xl border border-border bg-muted/40 p-4">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-subtle mb-1">{item.label}</p>
            <p className="text-xs leading-relaxed text-body">{item.text}</p>
          </div>
        ))}
      </div>

      {/* ── 1. Information We Collect ─────────────────────────────────────── */}
      <Section id="collection" number="1" title="Information We Collect">
        <SubSection title="1.1 Account Information">
          <p>
            When you create an account, we collect your name, email address, organisation name, role, and
            authentication credentials. For enterprise accounts, we may also collect billing contact details
            and team member information.
          </p>
        </SubSection>
        <SubSection title="1.2 Platform Usage Data">
          <p>
            We collect data about how you interact with the platform, including search queries, signal
            contract configurations, dashboard views, API calls, feature usage, and session duration. This
            data is used to improve platform functionality and user experience.
          </p>
        </SubSection>
        <SubSection title="1.3 User Content (Input Data)">
          <p>
            You may upload or input proprietary data — such as team goals, internal KPIs, and contextual
            enrichment data — to enhance signal relevance. You retain full ownership of this User Content.
            We process it solely to provide the services you requested.
          </p>
        </SubSection>
        <SubSection title="1.4 Signal Ingestion Data (World Activity)">
          <p>
            Cogent ingests structured and unstructured signals from the <strong>public web, semi-public PDFs,
            APIs, and partner-accessible data</strong>. This is &ldquo;World Activity&rdquo; data used to
            generate market-level signals. We do not track individual users across the web. Every signal
            synthesised by the platform links back to source snippets to ensure auditability and policy control.
          </p>
        </SubSection>
        <SubSection title="1.5 Technical Data">
          <p>
            We automatically collect IP addresses, browser type, device information, operating system, and
            referral URLs for security, fraud prevention, and platform optimisation.
          </p>
        </SubSection>
      </Section>

      {/* ── 2. Lawful Basis for Processing ────────────────────────────────── */}
      <Section id="lawful-basis" number="2" title="Lawful Basis for Processing">
        <p className="text-xs leading-relaxed">
          Under the NDPA 2023 and GDPR, we process personal data only when we have a valid legal basis:
        </p>
        <div className="mt-3 overflow-x-auto rounded-xl border border-border">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-border bg-muted/50">
                <th className="px-4 py-2 text-left font-medium text-heading">Purpose</th>
                <th className="px-4 py-2 text-left font-medium text-heading">Legal Basis</th>
              </tr>
            </thead>
            <tbody className="text-body">
              <tr className="border-b border-border">
                <td className="px-4 py-2">Providing the Cogent platform and services</td>
                <td className="px-4 py-2">Contractual Necessity</td>
              </tr>
              <tr className="border-b border-border">
                <td className="px-4 py-2">Processing User Content per Signal Contracts</td>
                <td className="px-4 py-2">Contractual Necessity</td>
              </tr>
              <tr className="border-b border-border">
                <td className="px-4 py-2">Ingesting public market data for signal synthesis</td>
                <td className="px-4 py-2">Legitimate Interest</td>
              </tr>
              <tr className="border-b border-border">
                <td className="px-4 py-2">Improving signal quality and platform features</td>
                <td className="px-4 py-2">Legitimate Interest</td>
              </tr>
              <tr className="border-b border-border">
                <td className="px-4 py-2">Security monitoring and fraud prevention</td>
                <td className="px-4 py-2">Legitimate Interest</td>
              </tr>
              <tr className="border-b border-border">
                <td className="px-4 py-2">Sending product updates and service notices</td>
                <td className="px-4 py-2">Contractual Necessity</td>
              </tr>
              <tr>
                <td className="px-4 py-2">Marketing communications (opt-in only)</td>
                <td className="px-4 py-2">Consent</td>
              </tr>
            </tbody>
          </table>
        </div>
      </Section>

      {/* ── 3. Data Minimisation ──────────────────────────────────────────── */}
      <Section id="minimisation" number="3" title="Data Minimisation">
        <p className="text-xs leading-relaxed">
          We adhere to the principle of data minimisation. We collect only the information that is
          <strong> strictly necessary</strong> for the platform&apos;s functionality and the specific services
          you have subscribed to. Our crawling and search infrastructure is focused on &ldquo;World Activity&rdquo;
          to generate market-level signals — we do not perform mass personal data collection or individual
          user tracking across the web.
        </p>
      </Section>

      {/* ── 4. Data Provenance & Signal Transparency ──────────────────────── */}
      <Section id="provenance" number="4" title="Data Provenance &amp; Signal Transparency">
        <SubSection title="4.1 Explainability">
          <p>
            In alignment with our core principle of &ldquo;Confidence &amp; Lineage Everywhere,&rdquo; every
            signal synthesised by the platform includes provenance information — linking back to source snippets,
            timestamp, and confidence scoring methodology. This allows users and their legal teams to audit
            how a signal was generated.
          </p>
        </SubSection>
        <SubSection title="4.2 Third-Party Data Sources">
          <p>
            Cogent monitors and processes data from the following categories of sources:
          </p>
          <ul className="list-disc pl-5 space-y-1 text-xs text-body">
            <li>Social media APIs (public posts and trends);</li>
            <li>News aggregators and media outlets;</li>
            <li>Public government records and regulatory filings;</li>
            <li>Industry reports and semi-public research publications;</li>
            <li>Company websites and publicly available corporate disclosures.</li>
          </ul>
          <p className="mt-2">
            Cogent acts as a conduit for public information. We do not scrape private profiles, protected
            content behind authentication walls, or content prohibited by the source platform&apos;s terms.
          </p>
        </SubSection>
      </Section>

      {/* ── 5. International Transfers ────────────────────────────────────── */}
      <Section id="transfers" number="5" title="International Data Transfers">
        <SubSection title="5.1 Transfer Mechanisms">
          <p>
            Cogent&apos;s infrastructure operates across multiple jurisdictions. Data may be processed in
            Nigeria (our primary operational jurisdiction) and stored on cloud infrastructure in the EU
            (e.g., AWS Ireland). All cross-border transfers are safeguarded by:
          </p>
          <ul className="list-disc pl-5 space-y-1 text-xs text-body">
            <li><strong>Standard Contractual Clauses (SCCs):</strong> As approved by the European Commission for EU-to-third-country transfers;</li>
            <li><strong>Adequacy Findings:</strong> Where applicable, transfers are based on adequacy decisions;</li>
            <li><strong>NDPA-compliant safeguards:</strong> Cross-border transfers from Nigeria comply with NDPA 2023 requirements, including data residency transparency.</li>
          </ul>
        </SubSection>
        <SubSection title="5.2 Data Residency">
          <p>
            Enterprise customers may request specific data residency configurations through their account
            settings or enterprise agreement. The physical storage location of your data will be disclosed
            in your Data Processing Addendum (DPA).
          </p>
        </SubSection>
      </Section>

      {/* ── 6. Sub-Processors ─────────────────────────────────────────────── */}
      <Section id="sub-processors" number="6" title="Sub-Processors">
        <p className="text-xs leading-relaxed">
          Cogent uses the following categories of third-party sub-processors to deliver the platform:
        </p>
        <div className="mt-3 overflow-x-auto rounded-xl border border-border">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-border bg-muted/50">
                <th className="px-4 py-2 text-left font-medium text-heading">Category</th>
                <th className="px-4 py-2 text-left font-medium text-heading">Provider</th>
                <th className="px-4 py-2 text-left font-medium text-heading">Purpose</th>
                <th className="px-4 py-2 text-left font-medium text-heading">Location</th>
              </tr>
            </thead>
            <tbody className="text-body">
              <tr className="border-b border-border">
                <td className="px-4 py-2">Cloud Infrastructure</td>
                <td className="px-4 py-2">Amazon Web Services</td>
                <td className="px-4 py-2">Hosting, compute, storage</td>
                <td className="px-4 py-2">EU (Ireland)</td>
              </tr>
              <tr className="border-b border-border">
                <td className="px-4 py-2">Authentication</td>
                <td className="px-4 py-2">Auth0 (Okta)</td>
                <td className="px-4 py-2">User authentication & SSO</td>
                <td className="px-4 py-2">US / EU</td>
              </tr>
              <tr className="border-b border-border">
                <td className="px-4 py-2">Payments</td>
                <td className="px-4 py-2">Stripe</td>
                <td className="px-4 py-2">Billing & payment processing</td>
                <td className="px-4 py-2">US / EU</td>
              </tr>
              <tr className="border-b border-border">
                <td className="px-4 py-2">Email</td>
                <td className="px-4 py-2">SendGrid / Resend</td>
                <td className="px-4 py-2">Transactional & notification emails</td>
                <td className="px-4 py-2">US</td>
              </tr>
              <tr className="border-b border-border">
                <td className="px-4 py-2">Analytics</td>
                <td className="px-4 py-2">PostHog</td>
                <td className="px-4 py-2">Product analytics (anonymised)</td>
                <td className="px-4 py-2">EU</td>
              </tr>
              <tr>
                <td className="px-4 py-2">AI/ML</td>
                <td className="px-4 py-2">OpenAI / Anthropic</td>
                <td className="px-4 py-2">LLM-powered signal enrichment</td>
                <td className="px-4 py-2">US</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p className="mt-3 text-xs text-subtle">
          We maintain an up-to-date sub-processor list and will notify customers at least <strong>30 days</strong> before
          adding a new sub-processor. Enterprise customers may object to new sub-processors per the terms of their DPA.
        </p>
      </Section>

      {/* ── 7. Your Rights ────────────────────────────────────────────────── */}
      <Section id="rights" number="7" title="Your Data Rights">
        <p className="text-xs leading-relaxed">
          Under the NDPA 2023 and GDPR, you have the following rights regarding your personal data:
        </p>
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          {[
            { title: 'Right to Access', description: 'Request a copy of the personal data we hold about you and how it is processed.' },
            { title: 'Right to Rectification', description: 'Correct inaccurate or incomplete personal data at any time through your account settings or by contacting us.' },
            { title: 'Right to Erasure', description: 'Request deletion of your personal data ("Right to be Forgotten"). We will comply within 30 days, subject to legal retention obligations.' },
            { title: 'Right to Portability', description: 'Export your User Content and signal reports in machine-readable formats (JSON, CSV) through the platform\'s Data & Privacy settings.' },
            { title: 'Right to Restrict Processing', description: 'Request that we limit the processing of your data while a complaint or accuracy concern is being investigated.' },
            { title: 'Right to Object', description: 'Object to the processing of your data based on Legitimate Interest, including AI-driven automated decision-making.' },
          ].map(right => (
            <div key={right.title} className="rounded-xl border border-border bg-surface p-4">
              <p className="text-xs font-semibold text-heading mb-1">{right.title}</p>
              <p className="text-xs leading-relaxed text-subtle">{right.description}</p>
            </div>
          ))}
        </div>
        <p className="mt-4 text-xs text-body">
          To exercise any of these rights, contact <a href="mailto:privacy@cogent.ai" className="text-primary hover:underline">privacy@cogent.ai</a> or
          use the Data &amp; Privacy controls in your account settings. We will respond within <strong>30 days</strong>.
        </p>
      </Section>

      {/* ── 8. Automated Decision-Making & AI Transparency ────────────────── */}
      <Section id="ai" number="8" title="Automated Decision-Making &amp; AI Transparency">
        <SubSection title="8.1 How We Use AI">
          <p>
            Cogent uses machine learning models and automated detection logic to:
          </p>
          <ul className="list-disc pl-5 space-y-1 text-xs text-body">
            <li>Discover and validate signals from public data sources;</li>
            <li>Generate confidence scores and quality assessments;</li>
            <li>Autonomously propose new signals based on coverage gap analysis;</li>
            <li>Enrich signals using vertical-specific vocabularies.</li>
          </ul>
        </SubSection>
        <SubSection title="8.2 The &ldquo;Double-Blind&rdquo; Guarantee">
          <p>
            If we use data patterns from one enterprise to improve signal quality for the entire platform,
            this data is fully <strong>anonymised and aggregated</strong> before being incorporated. Your
            specific competitive secrets, proprietary queries, or strategic inputs are never shared with
            other users or fed to rivals.
          </p>
        </SubSection>
        <SubSection title="8.3 Opt-Out">
          <p>
            You have the right to opt out of AI-generated signal recommendations that may significantly
            affect your decision-making. Enterprise accounts can configure this via platform settings.
            Individual requests can be directed to <a href="mailto:privacy@cogent.ai" className="text-primary hover:underline">privacy@cogent.ai</a>.
          </p>
        </SubSection>
      </Section>

      {/* ── 9. Nigeria-Specific Compliance (NDPA 2023) ────────────────────── */}
      <Section id="nigeria" number="9" title="Nigeria-Specific Compliance (NDPA 2023)">
        <SubSection title="9.1 NDPC Registration">
          <p>
            As Cogent processes the data of more than 200 data subjects in Nigeria within a six-month period,
            we are classified as a &ldquo;Data Controller of Major Importance&rdquo; (Ordinary-High Level) and
            are registered with the <strong>Nigeria Data Protection Commission (NDPC)</strong>.
          </p>
        </SubSection>
        <SubSection title="9.2 Data Protection Compliance Organisation (DPCO)">
          <p>
            In compliance with the NDPA, Cogent engages a licensed Data Protection Compliance Organisation to
            conduct annual audits of our data processing activities within Nigeria.
          </p>
        </SubSection>
        <SubSection title="9.3 Regional Intelligence Realism">
          <p>
            As Nigeria is our initial high-depth region, we ensure that our data processing reflects local market
            realities and infrastructure conditions rather than relying on generic global assumptions. Signal depth
            and accuracy may vary by region based on data source availability.
          </p>
        </SubSection>
        <SubSection title="9.4 Cross-Border Transfers from Nigeria">
          <p>
            Where data originating from Nigerian data subjects is transferred outside Nigeria (e.g., to our
            EU-based cloud infrastructure), we ensure compliance with NDPA cross-border transfer requirements,
            including the use of Standard Contractual Clauses and adequacy assessments.
          </p>
        </SubSection>
      </Section>

      {/* ── 10. Data Security ─────────────────────────────────────────────── */}
      <Section id="security" number="10" title="Data Security">
        <p className="text-xs leading-relaxed">
          Cogent implements comprehensive security measures to protect your data:
        </p>
        <ul className="list-disc pl-5 space-y-1 text-xs text-body mt-2">
          <li><strong>Encryption at rest:</strong> AES-256 encryption for all stored data;</li>
          <li><strong>Encryption in transit:</strong> TLS 1.3 for all data transmissions;</li>
          <li><strong>Access controls:</strong> Role-based access control (RBAC) preventing unauthorised internal access to client signals;</li>
          <li><strong>Audit logging:</strong> Comprehensive logs of all data access and processing activities;</li>
          <li><strong>Infrastructure security:</strong> SOC 2-aligned controls across our cloud infrastructure;</li>
          <li><strong>Incident response:</strong> Documented incident response procedures with 72-hour GDPR breach notification compliance.</li>
        </ul>
      </Section>

      {/* ── 11. Data Retention ────────────────────────────────────────────── */}
      <Section id="retention" number="11" title="Data Retention">
        <div className="mt-2 overflow-x-auto rounded-xl border border-border">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-border bg-muted/50">
                <th className="px-4 py-2 text-left font-medium text-heading">Data Type</th>
                <th className="px-4 py-2 text-left font-medium text-heading">Retention Period</th>
              </tr>
            </thead>
            <tbody className="text-body">
              <tr className="border-b border-border">
                <td className="px-4 py-2">Account information</td>
                <td className="px-4 py-2">Duration of account + 90 days</td>
              </tr>
              <tr className="border-b border-border">
                <td className="px-4 py-2">User Content</td>
                <td className="px-4 py-2">Duration of account + 90 days (exportable)</td>
              </tr>
              <tr className="border-b border-border">
                <td className="px-4 py-2">Signal reports</td>
                <td className="px-4 py-2">Per subscription tier retention settings</td>
              </tr>
              <tr className="border-b border-border">
                <td className="px-4 py-2">Usage/analytics data</td>
                <td className="px-4 py-2">24 months (anonymised)</td>
              </tr>
              <tr className="border-b border-border">
                <td className="px-4 py-2">Billing records</td>
                <td className="px-4 py-2">7 years (legal obligation)</td>
              </tr>
              <tr>
                <td className="px-4 py-2">Aggregated signal data</td>
                <td className="px-4 py-2">Retained indefinitely (fully anonymised)</td>
              </tr>
            </tbody>
          </table>
        </div>
      </Section>

      {/* ── 12. Cookies & Tracking ────────────────────────────────────────── */}
      <Section id="cookies" number="12" title="Cookies &amp; Tracking Technologies">
        <p className="text-xs leading-relaxed">
          Cogent uses strictly necessary cookies for authentication, session management, and preference
          storage. We do not use third-party advertising cookies or cross-site tracking pixels. Analytics
          cookies (PostHog) are configured with anonymised identifiers and can be disabled through your
          browser settings or platform preferences.
        </p>
      </Section>

      {/* ── 13. Children's Privacy ────────────────────────────────────────── */}
      <Section id="children" number="13" title="Children&rsquo;s Privacy">
        <p className="text-xs leading-relaxed">
          The Cogent platform is designed for business professionals and enterprise users. We do not knowingly
          collect personal data from individuals under the age of 18. If we become aware that we have collected
          data from a minor, we will delete it promptly.
        </p>
      </Section>

      {/* ── 14. Changes to This Policy ────────────────────────────────────── */}
      <Section id="changes" number="14" title="Changes to This Policy">
        <p className="text-xs leading-relaxed">
          We may update this Privacy Policy from time to time. Material changes will be communicated via email
          notification and/or an in-platform banner at least <strong>30 days</strong> prior to taking effect.
          The &ldquo;Last Updated&rdquo; date at the top of this page reflects the most recent revision.
        </p>
      </Section>

      {/* ── Data Ethics Charter ───────────────────────────────────────────── */}
      <div className="rounded-2xl border border-primary/20 bg-primary/5 p-6">
        <h3 className="text-sm font-semibold text-heading mb-2">Data Ethics Charter</h3>
        <p className="text-xs text-body leading-relaxed mb-3">
          Beyond our legal obligations, Cogent commits to the following ethical principles:
        </p>
        <ul className="list-disc pl-5 space-y-1 text-xs text-body">
          <li><strong>Data Sovereignty:</strong> Your data is yours. We will never &ldquo;weaponise&rdquo; your data, sell your search trends, or monetise your strategy to third-party advertisers.</li>
          <li><strong>No Competitive Leakage:</strong> Enterprise-specific signals, queries, and strategic context are never shared between customers, even in anonymised form beyond aggregated market-level patterns.</li>
          <li><strong>Transparency by Default:</strong> Every signal includes provenance. Every AI decision is explainable. Every data flow is auditable.</li>
          <li><strong>Human Oversight:</strong> Automated decisions that may significantly affect users are always subject to human review and override capabilities.</li>
        </ul>
      </div>

      {/* ── Contact ───────────────────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 rounded-xl border border-border bg-surface px-6 py-4">
        <div>
          <p className="text-sm font-medium text-heading">Data Protection Officer</p>
          <p className="text-xs text-subtle">For privacy inquiries, data subject requests, or DPO contact.</p>
        </div>
        <div className="flex gap-3">
          <a
            href="mailto:dpo@cogent.ai"
            className="rounded-xl border border-border px-4 py-2 text-xs font-medium text-body hover:bg-muted transition-colors"
          >
            dpo@cogent.ai
          </a>
          <a
            href="mailto:privacy@cogent.ai"
            className="rounded-xl bg-primary px-4 py-2 text-xs font-medium text-white hover:bg-primary-hover transition-colors"
          >
            privacy@cogent.ai
          </a>
        </div>
      </div>
    </article>
  )
}
