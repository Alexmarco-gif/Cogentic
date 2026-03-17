import type { Metadata } from 'next'

export const metadata: Metadata = { title: 'Data Processing Addendum' }

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

export default function DataProcessingPage() {
  return (
    <article className="flex flex-col gap-10">
      {/* ── Header ────────────────────────────────────────────────────────── */}
      <div className="border-b border-border pb-8">
        <p className="text-[10px] font-semibold uppercase tracking-wider text-primary mb-2">Legal Document</p>
        <h1 className="text-display text-heading mb-3">Data Processing Addendum</h1>
        <div className="flex flex-wrap gap-4 text-xs text-subtle">
          <span>Effective Date: <strong className="text-body">March 1, 2026</strong></span>
          <span>Last Updated: <strong className="text-body">March 1, 2026</strong></span>
          <span>Version: <strong className="text-body">2.0</strong></span>
        </div>
      </div>

      {/* ── Preamble ──────────────────────────────────────────────────────── */}
      <div className="rounded-2xl border border-border bg-surface p-6 shadow-card">
        <p className="text-xs leading-relaxed text-body">
          This Data Processing Addendum (&ldquo;DPA&rdquo;) forms part of the Terms of Service between
          <strong> Cogent Technologies Ltd.</strong> (&ldquo;Cogent&rdquo; or &ldquo;Processor&rdquo;) and the
          enterprise customer (&ldquo;Client&rdquo; or &ldquo;Controller&rdquo;) and governs the processing of
          personal data by Cogent on behalf of the Client. This DPA applies where and to the extent that Cogent
          processes personal data subject to the Nigeria Data Protection Act (NDPA) 2023, EU General Data
          Protection Regulation (GDPR), or other applicable data protection laws.
        </p>
        <p className="mt-3 text-xs leading-relaxed text-body">
          This DPA turns our &ldquo;Enterprise Safety by Design&rdquo; philosophy into legally binding commitments.
          It establishes clear roles, restrictions, security obligations, and sub-processor transparency requirements.
        </p>
      </div>

      {/* ── 1. Definitions & Roles ────────────────────────────────────────── */}
      <Section id="definitions" number="1" title="Definitions &amp; Roles">
        <SubSection title="1.1 Data Controller (Client)">
          <p>
            The Client is the <strong>Data Controller</strong>. The Client determines the purposes and means of
            processing personal data. The Client owns the input data, intent, queries, and contextual enrichment
            information submitted to the Cogent platform.
          </p>
        </SubSection>
        <SubSection title="1.2 Data Processor (Cogent)">
          <p>
            Cogent is the <strong>Data Processor</strong>. Cogent processes personal data on behalf of the Client
            solely to provide the signal intelligence services described in the Terms of Service and the applicable
            Signal Contracts. Cogent does not independently determine the purposes of processing Client data.
          </p>
        </SubSection>
        <SubSection title="1.3 Dual Role Disclosure">
          <p>
            Cogent additionally acts as a <strong>Data Controller</strong> for the purpose of ingesting public
            and semi-public data (&ldquo;World Activity&rdquo;) to generate market-level signals. This separate
            controller activity is governed by the Cogent Privacy Policy, not this DPA.
          </p>
        </SubSection>
      </Section>

      {/* ── 2. Scope of Processing ────────────────────────────────────────── */}
      <Section id="scope" number="2" title="Scope of Processing">
        <SubSection title="2.1 Subject Matter">
          <p>
            Cogent processes personal data solely to provide the services described in the agreed Signal
            Contracts, including: signal discovery, validation, enrichment, and delivery of decision-ready
            intelligence.
          </p>
        </SubSection>
        <SubSection title="2.2 Categories of Data Subjects">
          <ul className="list-disc pl-5 space-y-1 text-xs text-body">
            <li>Authorised users of the Client&apos;s Cogent account (employees, contractors);</li>
            <li>Individuals whose data may be incidentally included in Client-uploaded content;</li>
            <li>Business contacts referenced in public data sources monitored by the platform.</li>
          </ul>
        </SubSection>
        <SubSection title="2.3 Types of Personal Data">
          <ul className="list-disc pl-5 space-y-1 text-xs text-body">
            <li>Account information (name, email, role, organisation);</li>
            <li>User Content uploaded by the Client for signal enrichment;</li>
            <li>Platform usage data (search queries, dashboard interactions, API calls);</li>
            <li>Technical data (IP addresses, device identifiers, session logs).</li>
          </ul>
        </SubSection>
      </Section>

      {/* ── 3. Restricted Processing ──────────────────────────────────────── */}
      <Section id="restricted" number="3" title="Restricted Processing Obligations">
        <SubSection title="3.1 Purpose Limitation">
          <p>
            Cogent shall process personal data <strong>only</strong> to provide the services described in the
            Signal Contracts and these Terms. Cogent shall not process personal data for any secondary purpose,
            including but not limited to:
          </p>
          <ul className="list-disc pl-5 space-y-1 text-xs text-body">
            <li>Advertising, marketing, or profiling for third-party purposes;</li>
            <li>Selling or licensing personal data to third parties;</li>
            <li>Training machine learning models on identifiable Client data without explicit authorisation;</li>
            <li>Any purpose that is not reasonably necessary to provide the contracted services.</li>
          </ul>
        </SubSection>
        <SubSection title="3.2 Instruction-Based Processing">
          <p>
            Cogent shall process personal data only on documented instructions from the Client (including the
            Terms of Service, DPA, and Signal Contract definitions), unless required to do so by applicable
            law — in which case, Cogent shall inform the Client before processing (unless legally prohibited
            from doing so).
          </p>
        </SubSection>
      </Section>

      {/* ── 4. Sub-Processor Transparency ─────────────────────────────────── */}
      <Section id="sub-processors" number="4" title="Sub-Processor Transparency">
        <SubSection title="4.1 Current Sub-Processors">
          <p>
            Cogent uses the following authorised sub-processors. This list is maintained and updated regularly:
          </p>
          <div className="mt-2 overflow-x-auto rounded-xl border border-border">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-border bg-muted/50">
                  <th className="px-4 py-2 text-left font-medium text-heading">Sub-Processor</th>
                  <th className="px-4 py-2 text-left font-medium text-heading">Service</th>
                  <th className="px-4 py-2 text-left font-medium text-heading">Data Processing</th>
                  <th className="px-4 py-2 text-left font-medium text-heading">Location</th>
                </tr>
              </thead>
              <tbody className="text-body">
                <tr className="border-b border-border">
                  <td className="px-4 py-2">Amazon Web Services</td>
                  <td className="px-4 py-2">Cloud infrastructure</td>
                  <td className="px-4 py-2">Hosting, storage, compute</td>
                  <td className="px-4 py-2">EU (Ireland)</td>
                </tr>
                <tr className="border-b border-border">
                  <td className="px-4 py-2">Auth0 (Okta)</td>
                  <td className="px-4 py-2">Authentication</td>
                  <td className="px-4 py-2">User identity & session management</td>
                  <td className="px-4 py-2">US / EU</td>
                </tr>
                <tr className="border-b border-border">
                  <td className="px-4 py-2">Stripe</td>
                  <td className="px-4 py-2">Payments</td>
                  <td className="px-4 py-2">Billing & payment processing</td>
                  <td className="px-4 py-2">US / EU</td>
                </tr>
                <tr className="border-b border-border">
                  <td className="px-4 py-2">SendGrid / Resend</td>
                  <td className="px-4 py-2">Email delivery</td>
                  <td className="px-4 py-2">Transactional emails</td>
                  <td className="px-4 py-2">US</td>
                </tr>
                <tr className="border-b border-border">
                  <td className="px-4 py-2">PostHog</td>
                  <td className="px-4 py-2">Product analytics</td>
                  <td className="px-4 py-2">Anonymised usage analytics</td>
                  <td className="px-4 py-2">EU</td>
                </tr>
                <tr className="border-b border-border">
                  <td className="px-4 py-2">OpenAI</td>
                  <td className="px-4 py-2">AI/ML</td>
                  <td className="px-4 py-2">LLM-powered signal enrichment</td>
                  <td className="px-4 py-2">US</td>
                </tr>
                <tr>
                  <td className="px-4 py-2">Anthropic</td>
                  <td className="px-4 py-2">AI/ML</td>
                  <td className="px-4 py-2">LLM-powered analysis</td>
                  <td className="px-4 py-2">US</td>
                </tr>
              </tbody>
            </table>
          </div>
        </SubSection>
        <SubSection title="4.2 New Sub-Processor Notification">
          <p>
            Cogent shall notify the Client at least <strong>30 days</strong> in advance before engaging a new
            sub-processor or materially changing the scope of an existing sub-processor&apos;s access. The
            notification will include the sub-processor&apos;s identity, the nature of processing, and the
            data location.
          </p>
        </SubSection>
        <SubSection title="4.3 Client Objection Rights">
          <p>
            The Client may object to a new sub-processor within 14 days of notification by providing written
            reasons. If Cogent cannot reasonably accommodate the objection, the Client may terminate the
            affected service upon written notice without penalty.
          </p>
        </SubSection>
        <SubSection title="4.4 Sub-Processor Obligations">
          <p>
            Cogent ensures that all sub-processors are bound by data processing agreements that impose
            obligations no less protective than those set out in this DPA. Cogent remains fully liable for
            the acts and omissions of its sub-processors.
          </p>
        </SubSection>
      </Section>

      {/* ── 5. Security Measures (Annex II) ───────────────────────────────── */}
      <Section id="security" number="5" title="Security Measures (Annex II)">
        <p className="text-xs leading-relaxed">
          Cogent implements and maintains the following technical and organisational measures to protect
          personal data processed on behalf of the Client:
        </p>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          {[
            {
              title: 'Encryption at Rest',
              description: 'All stored data is encrypted using AES-256 encryption. Database backups and archived data are similarly encrypted.',
            },
            {
              title: 'Encryption in Transit',
              description: 'All data transmissions use TLS 1.3. API communications, inter-service communication, and webhook deliveries are encrypted end-to-end.',
            },
            {
              title: 'Access Controls (RBAC)',
              description: 'Role-based access controls prevent unauthorised internal access to Client signals. Staff access requires multi-factor authentication and is logged.',
            },
            {
              title: 'Audit Logging',
              description: 'Comprehensive, tamper-evident logs of all data access, modifications, and processing activities. Logs are retained for 24 months.',
            },
            {
              title: 'Network Security',
              description: 'Virtual private cloud isolation, network segmentation, intrusion detection systems, and DDoS protection across all environments.',
            },
            {
              title: 'Incident Response',
              description: 'Documented incident response procedures. GDPR-compliant 72-hour breach notification. NDPA-compliant notification to NDPC where applicable.',
            },
            {
              title: 'Data Isolation',
              description: 'Client data is logically isolated at the application and database levels. No cross-client data leakage in signal processing pipelines.',
            },
            {
              title: 'Personnel Security',
              description: 'All Cogent staff with access to Client data undergo background checks, sign confidentiality agreements, and receive annual data protection training.',
            },
          ].map(measure => (
            <div key={measure.title} className="rounded-xl border border-border bg-surface p-4">
              <p className="text-xs font-semibold text-heading mb-1">{measure.title}</p>
              <p className="text-xs leading-relaxed text-subtle">{measure.description}</p>
            </div>
          ))}
        </div>
      </Section>

      {/* ── 6. Data Subject Requests ──────────────────────────────────────── */}
      <Section id="dsr" number="6" title="Data Subject Requests">
        <SubSection title="6.1 Assistance">
          <p>
            Taking into account the nature of the processing, Cogent shall assist the Client by appropriate
            technical and organisational measures in fulfilling the Client&apos;s obligation to respond to
            requests from data subjects exercising their rights under the NDPA, GDPR, or other applicable law.
          </p>
        </SubSection>
        <SubSection title="6.2 Notification">
          <p>
            If Cogent receives a data subject request directly, Cogent shall promptly notify the Client and
            shall not respond to the request without the Client&apos;s prior written authorisation, unless
            required to do so by applicable law.
          </p>
        </SubSection>
        <SubSection title="6.3 Response Timeline">
          <p>
            Cogent shall respond to the Client&apos;s assistance requests within <strong>10 business days</strong>,
            ensuring the Client can meet the 30-day statutory response deadline.
          </p>
        </SubSection>
      </Section>

      {/* ── 7. Cross-Border Transfers ─────────────────────────────────────── */}
      <Section id="transfers" number="7" title="International Data Transfers">
        <SubSection title="7.1 Transfer Mechanisms">
          <p>
            Where personal data is transferred from Nigeria or the EEA to a jurisdiction that does not provide
            an adequate level of data protection, such transfers shall be governed by:
          </p>
          <ul className="list-disc pl-5 space-y-1 text-xs text-body">
            <li><strong>Standard Contractual Clauses (SCCs):</strong> EU-approved SCCs (Commission Decision 2021/914) are incorporated by reference into this DPA;</li>
            <li><strong>NDPA Transfer Mechanisms:</strong> Compliance with Chapter 5 of the NDPA 2023 regarding data transfers from Nigeria;</li>
            <li><strong>Supplementary Measures:</strong> Additional technical measures (encryption, pseudonymisation) applied where required by Schrems II guidance.</li>
          </ul>
        </SubSection>
        <SubSection title="7.2 Data Residency Options">
          <p>
            Enterprise customers may specify data residency preferences. Cogent currently supports:
          </p>
          <ul className="list-disc pl-5 space-y-1 text-xs text-body">
            <li><strong>EU (Ireland):</strong> AWS eu-west-1 region;</li>
            <li><strong>Additional regions:</strong> Available upon request for enterprise agreements.</li>
          </ul>
        </SubSection>
      </Section>

      {/* ── 8. Data Breach Notification ───────────────────────────────────── */}
      <Section id="breach" number="8" title="Data Breach Notification">
        <SubSection title="8.1 Notification Timeline">
          <p>
            In the event of a personal data breach, Cogent shall notify the Client <strong>without undue
            delay</strong> and in any event within <strong>48 hours</strong> of becoming aware of the breach.
            This allows the Client sufficient time to meet the 72-hour GDPR notification requirement to
            supervisory authorities.
          </p>
        </SubSection>
        <SubSection title="8.2 Breach Information">
          <p>Cogent&apos;s breach notification shall include:</p>
          <ul className="list-disc pl-5 space-y-1 text-xs text-body">
            <li>The nature of the breach, including categories and approximate number of data subjects affected;</li>
            <li>The likely consequences of the breach;</li>
            <li>The measures taken or proposed to address the breach and mitigate its effects;</li>
            <li>Contact details of Cogent&apos;s Data Protection Officer.</li>
          </ul>
        </SubSection>
      </Section>

      {/* ── 9. Data Return & Deletion ─────────────────────────────────────── */}
      <Section id="deletion" number="9" title="Data Return &amp; Deletion">
        <SubSection title="9.1 Upon Termination">
          <p>
            Upon termination of the service agreement, Cogent shall — at the Client&apos;s election — either:
          </p>
          <ul className="list-disc pl-5 space-y-1 text-xs text-body">
            <li><strong>Return</strong> all personal data in a machine-readable format (JSON, CSV) within 30 days; or</li>
            <li><strong>Delete</strong> all personal data within 90 days, except where retention is required by applicable law.</li>
          </ul>
        </SubSection>
        <SubSection title="9.2 Certification">
          <p>
            Upon request, Cogent shall provide written certification that personal data has been deleted or
            returned in accordance with this DPA.
          </p>
        </SubSection>
      </Section>

      {/* ── 10. Audit Rights ──────────────────────────────────────────────── */}
      <Section id="audit" number="10" title="Audit Rights">
        <SubSection title="10.1 Right to Audit">
          <p>
            The Client has the right to audit Cogent&apos;s compliance with this DPA. Audits may be conducted
            by the Client or an independent third-party auditor appointed by the Client (subject to reasonable
            confidentiality obligations).
          </p>
        </SubSection>
        <SubSection title="10.2 Audit Process">
          <p>
            The Client shall provide at least <strong>30 days&apos;</strong> written notice of an audit.
            Audits shall be conducted during normal business hours, no more than once per year, and shall
            not unreasonably interfere with Cogent&apos;s operations.
          </p>
        </SubSection>
        <SubSection title="10.3 Compliance Reports">
          <p>
            Cogent shall make available to the Client, upon request, relevant compliance reports including
            SOC 2 reports, penetration test summaries, and DPCO audit findings (for Nigerian operations).
          </p>
        </SubSection>
      </Section>

      {/* ── 11. NDPC-Specific Provisions ──────────────────────────────────── */}
      <Section id="ndpc" number="11" title="NDPA &amp; NDPC-Specific Provisions">
        <SubSection title="11.1 NDPC Registration">
          <p>
            As a Data Processor of Major Importance processing the data of more than 200 Nigerian data subjects
            within six months, Cogent maintains registration with the <strong>Nigeria Data Protection Commission
            (NDPC)</strong> as required by the NDPA 2023.
          </p>
        </SubSection>
        <SubSection title="11.2 DPCO Engagement">
          <p>
            Cogent engages a licensed Data Protection Compliance Organisation (DPCO) to conduct annual compliance
            audits of data processing activities within the Nigerian jurisdiction. Audit summaries are available
            to enterprise clients upon request.
          </p>
        </SubSection>
        <SubSection title="11.3 Local Representation">
          <p>
            For processing activities involving Nigerian data subjects, Cogent maintains a local representative
            contactable at <a href="mailto:nigeria-dpo@cogent.ai" className="text-primary hover:underline">nigeria-dpo@cogent.ai</a>.
          </p>
        </SubSection>
      </Section>

      {/* ── 12. Liability & Indemnification ───────────────────────────────── */}
      <Section id="liability" number="12" title="Liability &amp; Indemnification">
        <p className="text-xs leading-relaxed">
          Each party&apos;s liability under this DPA is subject to the limitations of liability set out in the
          Terms of Service. Cogent shall indemnify the Client against all costs, claims, damages, and expenses
          incurred by the Client arising from any breach of this DPA by Cogent or its sub-processors, subject
          to the liability cap in the Terms of Service.
        </p>
      </Section>

      {/* ── 13. Term ──────────────────────────────────────────────────────── */}
      <Section id="term" number="13" title="Term &amp; Survival">
        <p className="text-xs leading-relaxed">
          This DPA shall remain in effect for the duration of the service agreement between Cogent and the
          Client. Provisions relating to confidentiality, data deletion/return, liability, and audit rights
          shall survive the termination of this DPA.
        </p>
      </Section>

      {/* ── Execution Notice ──────────────────────────────────────────────── */}
      <div className="rounded-2xl border border-primary/20 bg-primary/5 p-6">
        <h3 className="text-sm font-semibold text-heading mb-2">Execution &amp; Incorporation</h3>
        <p className="text-xs text-body leading-relaxed">
          This DPA is automatically incorporated into the Terms of Service for all customers whose data
          processing is subject to the NDPA 2023, GDPR, or other applicable data protection laws. Enterprise
          customers may request a separately executed DPA with custom provisions by contacting
          <a href="mailto:legal@cogent.ai" className="text-primary hover:underline ml-1">legal@cogent.ai</a>.
        </p>
      </div>

      {/* ── Contact ───────────────────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 rounded-xl border border-border bg-surface px-6 py-4">
        <div>
          <p className="text-sm font-medium text-heading">Enterprise DPA Requests</p>
          <p className="text-xs text-subtle">Require a custom DPA or have questions about data processing?</p>
        </div>
        <div className="flex gap-3">
          <a
            href="mailto:dpo@cogent.ai"
            className="rounded-xl border border-border px-4 py-2 text-xs font-medium text-body hover:bg-muted transition-colors"
          >
            DPO Contact
          </a>
          <a
            href="mailto:legal@cogent.ai"
            className="rounded-xl bg-primary px-4 py-2 text-xs font-medium text-white hover:bg-primary-hover transition-colors"
          >
            legal@cogent.ai
          </a>
        </div>
      </div>
    </article>
  )
}
