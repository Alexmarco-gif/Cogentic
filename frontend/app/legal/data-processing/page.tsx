import type { Metadata } from 'next'

export const metadata: Metadata = { title: 'Enterprise Data Processing Addendum' }

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

export default function DataProcessingPage() {
  return (
    <article className="flex flex-col gap-10">
      <div className="border-b border-border pb-8">
        <p className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-primary">Legal Document</p>
        <h1 className="mb-3 max-w-[18ch] text-[1.95rem] font-semibold leading-[1.08] tracking-[-0.04em] text-heading sm:text-[2.1rem]">Enterprise Data Processing Addendum</h1>
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
          This Enterprise Data Processing Addendum (&ldquo;DPA&rdquo;) applies only where it is incorporated into an
          order form, master services agreement, or other written agreement between <strong>Stem Systems Ltd.</strong> and
          an enterprise customer using <strong>Cogent</strong>.
        </p>
        <p className="mt-3 text-xs leading-relaxed text-body">
          This page is a public summary of our standard DPA position. Enterprise customers may request an executed version
          or negotiated schedule by contacting{' '}
          <a href="mailto:legal@cogent.ai" className="text-primary hover:underline">
            legal@cogent.ai
          </a>
          .
        </p>
      </div>

      <Section id="roles" number="1" title="Roles and Scope">
        <SubSection title="1.1 Controller and Processor Roles">
          <p>
            For customer content processed solely on behalf of an enterprise customer, the customer acts as controller and
            Stem Systems Ltd. acts as processor, except where Stem Systems independently determines the purpose and means
            of processing for its own business operations.
          </p>
        </SubSection>
        <SubSection title="1.2 Scope of Processing">
          <p>
            Processing may include hosting, storage, retrieval, search, enrichment, summarisation, workspace management,
            authentication support, logging, and security operations required to provide Cogent.
          </p>
        </SubSection>
      </Section>

      <Section id="categories" number="2" title="Categories of Data">
        <SubSection title="2.1 Typical Data Subjects">
          <ul className="list-disc space-y-1 pl-5 text-xs text-body">
            <li>authorised customer users and workspace members;</li>
            <li>individuals referenced in customer-provided content;</li>
            <li>individuals whose professional or public-facing information is incidentally processed through product use.</li>
          </ul>
        </SubSection>
        <SubSection title="2.2 Typical Data Types">
          <ul className="list-disc space-y-1 pl-5 text-xs text-body">
            <li>name, email, role, workspace and organisation metadata;</li>
            <li>search and investigation inputs, saved items, and customer-uploaded content;</li>
            <li>technical, session, and audit data associated with service access and security;</li>
            <li>other data the customer intentionally instructs us to process through the service.</li>
          </ul>
        </SubSection>
      </Section>

      <Section id="instructions" number="3" title="Processing Instructions and Restrictions">
        <SubSection title="3.1 Customer Instructions">
          <p>
            Stem Systems Ltd. will process customer personal data only on documented customer instructions, as reflected in
            the agreement, product configuration, and lawful customer use of the service, unless otherwise required by law.
          </p>
        </SubSection>
        <SubSection title="3.2 Restricted Uses">
          <p>
            We will not sell customer personal data or use identifiable customer content to train general-purpose models
            for unrelated purposes without an appropriate permission, instruction, or another lawful basis.
          </p>
        </SubSection>
      </Section>

      <Section id="security" number="4" title="Security Measures">
        <p className="text-xs leading-relaxed">
          Stem Systems Ltd. maintains technical and organisational measures designed to protect customer data, including
          access controls, audit logging, environment security, credential management, and incident handling processes
          appropriate to the nature of the service.
        </p>
        <SubSection title="4.1 Access Controls">
          <p>
            Access to systems and data is limited to personnel or service components that need it for authorised support,
            operations, or security purposes.
          </p>
        </SubSection>
        <SubSection title="4.2 Incident Response">
          <p>
            We maintain incident handling procedures and will notify enterprise customers of a confirmed personal data
            breach affecting customer data without undue delay, in line with applicable law and the enterprise agreement.
          </p>
        </SubSection>
      </Section>

      <Section id="subprocessors" number="5" title="Subprocessors and Service Providers">
        <p className="text-xs leading-relaxed">
          The following providers are used to support Cogent features or operations, depending on the customer&apos;s plan
          and enabled functionality:
        </p>
        <div className="mt-3 overflow-x-auto rounded-xl border border-border">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-border bg-muted/50">
                <th className="px-4 py-2 text-left font-medium text-heading">Provider</th>
                <th className="px-4 py-2 text-left font-medium text-heading">Role</th>
              </tr>
            </thead>
            <tbody className="text-body">
              <tr className="border-b border-border">
                <td className="px-4 py-2">Auth0</td>
                <td className="px-4 py-2">Authentication and identity-related services</td>
              </tr>
              <tr className="border-b border-border">
                <td className="px-4 py-2">OpenAI</td>
                <td className="px-4 py-2">Model inference and AI-assisted features</td>
              </tr>
              <tr className="border-b border-border">
                <td className="px-4 py-2">Resend</td>
                <td className="px-4 py-2">Transactional and notification email delivery</td>
              </tr>
              <tr>
                <td className="px-4 py-2">PostHog (if enabled)</td>
                <td className="px-4 py-2">Product analytics and measurement</td>
              </tr>
            </tbody>
          </table>
        </div>
        <SubSection title="5.1 Changes to Subprocessors">
          <p>
            Enterprise customers may request the current subprocessor schedule and applicable notice mechanics under their
            contract. Additional subprocessors may be used where reasonably required to operate the service.
          </p>
        </SubSection>
      </Section>

      <Section id="transfers" number="6" title="Cross-Border Transfers">
        <p className="text-xs leading-relaxed">
          Where customer personal data is transferred outside Nigeria or another originating jurisdiction, Stem Systems
          Ltd. will rely on a lawful transfer mechanism and appropriate safeguards required by applicable law and the
          enterprise agreement.
        </p>
      </Section>

      <Section id="assistance" number="7" title="Assistance With Data Subject Rights and Incidents">
        <SubSection title="7.1 Rights Requests">
          <p>
            Where we act as processor, we will provide reasonable assistance to help the customer respond to access,
            rectification, deletion, portability, objection, or restriction requests, taking into account the nature of the
            processing and the information available to us.
          </p>
        </SubSection>
        <SubSection title="7.2 Direct Requests">
          <p>
            If we receive a request directly from a data subject relating to customer-controlled data, we may direct the
            requester to the customer or notify the customer, unless law requires otherwise.
          </p>
        </SubSection>
      </Section>

      <Section id="return-delete" number="8" title="Return and Deletion">
        <p className="text-xs leading-relaxed">
          At the end of the relevant service relationship, we will return or delete customer personal data in accordance
          with the agreement, the customer&apos;s documented instructions, and any applicable retention obligations.
        </p>
      </Section>

      <Section id="compliance" number="9" title="Regulatory Compliance Position">
        <p className="text-xs leading-relaxed">
          Stem Systems Ltd. intends for Cogent&apos;s enterprise processing arrangements to align with the NDPA and other
          applicable data protection laws that may govern a customer relationship. Where Stem Systems Ltd. qualifies as a
          controller or processor of major importance under Nigerian law, it will address the legal obligations that apply
          to that status, including any registration, governance, or contact requirements imposed by law.
        </p>
      </Section>

      <Section id="contact" number="10" title="Contact and Execution">
        <p className="text-xs leading-relaxed">
          To request an executed DPA, security questionnaire, or enterprise privacy review, contact{' '}
          <a href="mailto:legal@cogent.ai" className="text-primary hover:underline">
            legal@cogent.ai
          </a>
          .
        </p>
      </Section>

      <div className="rounded-2xl border border-primary/20 bg-primary/5 p-6">
        <h3 className="mb-2 text-sm font-semibold text-heading">Enterprise note</h3>
        <p className="text-xs leading-relaxed text-body">
          This page is not a substitute for a signed DPA. If your team needs controller-to-processor terms,
          international transfer clauses, or procurement review documents, request the enterprise package from our legal
          team.
        </p>
      </div>

      <div className="flex flex-col items-start justify-between gap-4 rounded-xl border border-border bg-surface px-6 py-4 sm:flex-row sm:items-center">
        <div>
          <p className="text-sm font-medium text-heading">Enterprise privacy and DPA requests</p>
          <p className="text-xs text-subtle">We can share the current enterprise paperwork through legal review.</p>
        </div>
        <a
          href="mailto:legal@cogent.ai"
          className="rounded-xl bg-primary px-4 py-2 text-xs font-medium text-white transition-colors hover:bg-primary-hover"
        >
          legal@cogent.ai
        </a>
      </div>
    </article>
  )
}
