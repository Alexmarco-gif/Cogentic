import type { Metadata } from 'next'

export const metadata: Metadata = { title: 'Terms of Service' }

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

export default function TermsOfServicePage() {
  return (
    <article className="flex flex-col gap-10">
      <div className="border-b border-border pb-8">
        <p className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-primary">Legal Document</p>
        <h1 className="mb-3 text-display text-heading">Terms of Service</h1>
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
          These Terms of Service (&ldquo;Terms&rdquo;) form a legally binding agreement between you and
          <strong> Stem Systems Ltd.</strong> (&ldquo;Stem Systems,&rdquo; &ldquo;we,&rdquo; &ldquo;us,&rdquo; or
          &ldquo;our&rdquo;) for your access to and use of <strong>Cogent</strong>, our market and signal intelligence
          platform.
        </p>
        <p className="mt-3 text-xs leading-relaxed text-body">
          By creating an account, clicking to accept these Terms, or using Cogent, you agree to these Terms. If you are
          using Cogent for a company, you confirm that you have authority to bind that company.
        </p>
      </div>

      <Section id="service" number="1" title="The Service">
        <p className="text-xs leading-relaxed">
          Cogent helps users monitor markets, sources, and operating environments, review synthesised signals, run
          investigations, and generate decision-support outputs. Cogent is designed to support professional judgment, not
          replace it.
        </p>
        <SubSection title="1.1 Decision Support Only">
          <p>
            Cogent provides research tools, signal summaries, search, and AI-assisted analysis for informational and
            operational support purposes only. It does not provide legal, financial, investment, tax, or regulatory
            advice.
          </p>
        </SubSection>
        <SubSection title="1.2 Product Evolution">
          <p>
            We may improve, change, add, or retire features from time to time. Where a change materially reduces the core
            paid service, we will give reasonable notice in-app, by email, or under your enterprise agreement.
          </p>
        </SubSection>
      </Section>

      <Section id="accounts" number="2" title="Accounts, Workspaces, and Access">
        <SubSection title="2.1 Eligibility">
          <p>
            You must be legally capable of entering into a binding agreement and may use Cogent only in compliance with
            applicable law and these Terms.
          </p>
        </SubSection>
        <SubSection title="2.2 Accounts and Team Access">
          <p>
            Each login is personal to the authorised user assigned to it. Team collaboration should happen through
            workspace membership, seats, and roles made available in the product, not by sharing one person&apos;s login
            credentials.
          </p>
        </SubSection>
        <SubSection title="2.3 Security of Your Account">
          <p>
            You are responsible for maintaining the confidentiality of your account credentials and for activities that
            occur under your account. Notify us promptly if you believe your account has been compromised.
          </p>
        </SubSection>
      </Section>

      <Section id="billing" number="3" title="Subscriptions, Fees, and Billing">
        <SubSection title="3.1 Paid Plans">
          <p>
            Some parts of Cogent may require a paid subscription, paid seat allocation, usage allowance, or a separately
            signed order form. Pricing, billing frequency, seat limits, and any usage thresholds will be shown in the
            product or in the relevant commercial agreement.
          </p>
        </SubSection>
        <SubSection title="3.2 Renewals and Cancellation">
          <p>
            Unless your order form says otherwise, paid plans renew at the end of the billing cycle. You may cancel before
            renewal to avoid the next charge. Unless required by law or stated in a commercial agreement, fees already paid
            are non-refundable.
          </p>
        </SubSection>
        <SubSection title="3.3 Taxes">
          <p>
            Fees may be exclusive of applicable taxes, levies, duties, or government charges. You are responsible for
            taxes associated with your purchase except for taxes based on our net income.
          </p>
        </SubSection>
      </Section>

      <Section id="use" number="4" title="Acceptable Use">
        <p className="text-xs leading-relaxed">You may not use Cogent to do or facilitate any of the following:</p>
        <ul className="list-disc space-y-1 pl-5 text-xs text-body">
          <li>unlawful surveillance, harassment, intimidation, discrimination, or fraud;</li>
          <li>unauthorised access, credential abuse, scraping behind login walls, or bypassing technical restrictions;</li>
          <li>infringing third-party intellectual property, privacy, confidentiality, or database rights;</li>
          <li>uploading malicious code, attempting to disrupt the platform, or interfering with other users;</li>
          <li>using Cogent outputs as a substitute for professional advice where human review is required;</li>
          <li>building a competing product by reverse engineering the service or extracting protected system logic at scale.</li>
        </ul>
        <SubSection title="4.1 Public Source Material">
          <p>
            Cogent may reference or summarise public or lawfully accessible source material. Rights in third-party source
            material remain with their respective owners, and your use of outputs must still respect applicable rights and
            restrictions.
          </p>
        </SubSection>
      </Section>

      <Section id="data-ip" number="5" title="Customer Data, Outputs, and Intellectual Property">
        <SubSection title="5.1 Your Content">
          <p>
            You retain your rights in the content, prompts, documents, contract definitions, and other material you submit
            to Cogent. You grant us the rights reasonably necessary to host, process, secure, and display that material in
            order to provide the service.
          </p>
        </SubSection>
        <SubSection title="5.2 Our Service and Technology">
          <p>
            Stem Systems Ltd. owns the Cogent service, including its software, interface design, workflows, model
            orchestration, taxonomies, and related intellectual property. These Terms do not transfer ownership of the
            service to you.
          </p>
        </SubSection>
        <SubSection title="5.3 Outputs">
          <p>
            You may use outputs generated for your workspace for your internal business purposes, subject to these Terms,
            your plan, and any order form. Outputs may contain summaries of third-party content and should be reviewed
            before onward publication or high-impact use.
          </p>
        </SubSection>
      </Section>

      <Section id="ai" number="6" title="AI-Assisted Features">
        <SubSection title="6.1 How AI Is Used">
          <p>
            Cogent uses automated systems and language models to help classify, enrich, summarise, retrieve, and explain
            information. These systems can produce incomplete, outdated, or incorrect results.
          </p>
        </SubSection>
        <SubSection title="6.2 Human Review">
          <p>
            You remain responsible for reviewing important outputs before acting on them, especially where a result may
            affect legal, financial, strategic, reputational, or regulatory decisions.
          </p>
        </SubSection>
      </Section>

      <Section id="availability" number="7" title="Availability, Support, and Changes">
        <SubSection title="7.1 Availability">
          <p>
            We aim to keep Cogent available and secure, but we do not promise uninterrupted or error-free operation unless
            a separately executed enterprise agreement states a specific service level commitment.
          </p>
        </SubSection>
        <SubSection title="7.2 Support">
          <p>
            Support channels and response expectations may vary by plan. Enterprise support commitments, if any, are
            governed by the applicable commercial agreement.
          </p>
        </SubSection>
      </Section>

      <Section id="termination" number="8" title="Suspension and Termination">
        <SubSection title="8.1 By You">
          <p>You may stop using the service at any time and may cancel your subscription in accordance with your plan.</p>
        </SubSection>
        <SubSection title="8.2 By Us">
          <p>
            We may suspend or terminate access where necessary to prevent harm, investigate abuse, protect the service, or
            respond to non-payment or material breach. Where practical, we will provide notice and an opportunity to cure.
          </p>
        </SubSection>
        <SubSection title="8.3 After Termination">
          <p>
            After termination, your access may end immediately or at the end of the current billing period, depending on
            the reason for termination and your plan. Data retention and deletion will be handled under our Privacy Notice
            and any enterprise agreement.
          </p>
        </SubSection>
      </Section>

      <Section id="liability" number="9" title="Disclaimers and Limitation of Liability">
        <SubSection title="9.1 Warranty Disclaimer">
          <p>
            To the maximum extent permitted by law, Cogent is provided on an &ldquo;as is&rdquo; and &ldquo;as
            available&rdquo; basis. We do not guarantee that outputs will always be accurate, complete, or fit for every
            purpose.
          </p>
        </SubSection>
        <SubSection title="9.2 Limitation of Liability">
          <p>
            To the maximum extent permitted by law, Stem Systems Ltd. will not be liable for indirect, incidental,
            special, consequential, exemplary, or punitive damages, or for loss of profits, revenue, goodwill, or data.
            Our aggregate liability for claims arising out of these Terms or the service will not exceed the amount paid by
            you for Cogent during the twelve months preceding the event giving rise to the claim.
          </p>
        </SubSection>
      </Section>

      <Section id="law" number="10" title="Governing Law and Contact">
        <p className="text-xs leading-relaxed">
          These Terms are governed by the laws of the Federal Republic of Nigeria. Any dispute arising out of or in
          connection with these Terms will be brought before a court of competent jurisdiction in Nigeria, unless a
          separate enterprise agreement states otherwise.
        </p>
        <SubSection title="10.1 Contact">
          <p>
            Legal questions about these Terms may be sent to{' '}
            <a href="mailto:legal@cogent.ai" className="text-primary hover:underline">
              legal@cogent.ai
            </a>
            .
          </p>
        </SubSection>
      </Section>

      <div className="rounded-2xl border border-primary/20 bg-primary/5 p-6">
        <h3 className="mb-2 text-sm font-semibold text-heading">Acceptance of Terms</h3>
        <p className="text-xs leading-relaxed text-body">
          By clicking &ldquo;Create Account,&rdquo; accepting these Terms in the product, or continuing to use Cogent,
          you acknowledge that you have read and agreed to these Terms of Service and the accompanying Privacy Notice.
        </p>
      </div>

      <div className="flex items-center justify-between rounded-xl border border-border bg-surface px-6 py-4">
        <div>
          <p className="text-sm font-medium text-heading">Questions about these Terms?</p>
          <p className="text-xs text-subtle">Contact our legal team for commercial or contract questions.</p>
        </div>
        <a
          href="mailto:legal@cogent.ai"
          className="flex-shrink-0 rounded-xl bg-primary px-5 py-2 text-xs font-medium text-white transition-colors hover:bg-primary-hover"
        >
          legal@cogent.ai
        </a>
      </div>
    </article>
  )
}
