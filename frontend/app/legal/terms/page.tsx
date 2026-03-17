import type { Metadata } from 'next'

export const metadata: Metadata = { title: 'Terms of Service' }

/* ─── Section component ────────────────────────────────────────────────────── */

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

export default function TermsOfServicePage() {
  return (
    <article className="flex flex-col gap-10">
      {/* ── Header ────────────────────────────────────────────────────────── */}
      <div className="border-b border-border pb-8">
        <p className="text-[10px] font-semibold uppercase tracking-wider text-primary mb-2">Legal Document</p>
        <h1 className="text-display text-heading mb-3">Terms of Service</h1>
        <div className="flex flex-wrap gap-4 text-xs text-subtle">
          <span>Effective Date: <strong className="text-body">March 1, 2026</strong></span>
          <span>Last Updated: <strong className="text-body">March 1, 2026</strong></span>
          <span>Version: <strong className="text-body">2.0</strong></span>
        </div>
      </div>

      {/* ── Preamble ──────────────────────────────────────────────────────── */}
      <div className="rounded-2xl border border-border bg-surface p-6 shadow-card">
        <p className="text-xs leading-relaxed text-body">
          These Terms of Service (&ldquo;Terms&rdquo;) constitute a legally binding agreement between you
          (&ldquo;User,&rdquo; &ldquo;Customer,&rdquo; or &ldquo;you&rdquo;) and <strong>Cogent Technologies
          Ltd.</strong> (&ldquo;Cogent,&rdquo; &ldquo;we,&rdquo; &ldquo;us,&rdquo; or &ldquo;our&rdquo;), a company
          registered under the laws of the Federal Republic of Nigeria, governing your access to and use of the Cogent
          platform — an enterprise-grade signal intelligence system that continuously discovers, validates, enriches,
          and explains real-world signals for decision support.
        </p>
        <p className="mt-3 text-xs leading-relaxed text-body">
          By accessing or using the Cogent platform, clicking &ldquo;I Agree,&rdquo; or executing an Order Form
          that references these Terms, you acknowledge that you have read, understood, and agree to be bound by
          these Terms in their entirety. If you are entering into these Terms on behalf of a company or legal entity,
          you represent that you have the authority to bind that entity.
        </p>
      </div>

      {/* ── 1. Nature of the Service ──────────────────────────────────────── */}
      <Section id="nature" number="1" title="Nature of the Service">
        <p className="text-xs leading-relaxed">
          Cogent provides an enterprise-grade system designed to continuously discover, validate, enrich, and
          explain real-world signals. The platform is a <strong>decision support layer</strong>, not a data delivery
          layer. We do not deliver raw data; we deliver decision-ready intelligence with confidence scores,
          provenance lineage, and historical context.
        </p>
        <SubSection title="1.1 Decision Support Disclaimer">
          <p>
            All intelligence, signals, confidence scores, and analytical outputs provided through the Cogent platform
            are for <strong>informational purposes only</strong>. They do not constitute professional, financial, legal,
            or investment advice. Cogent provides distilled, prioritised insights to help users answer complex,
            ambiguous questions — but the User remains solely responsible for any business decisions or actions taken
            based on Cogent&apos;s intelligence.
          </p>
        </SubSection>
        <SubSection title="1.2 Confidence & Lineage">
          <p>
            Every signal provided by the platform includes provenance information and confidence scores. These scores
            represent a <strong>probabilistic assessment</strong> and are not a guarantee of absolute factual certainty.
            Signal accuracy is managed via Signal Contracts with specific confidence thresholds (e.g., 0.75), which
            set clear expectations for enterprise-grade performance.
          </p>
        </SubSection>
        <SubSection title="1.3 Signal Freshness">
          <p>
            Signal freshness and accuracy requirements are defined declaratively via Signal Contracts. We strive to
            meet the specific freshness SLAs (e.g., 2-hour cycles) defined within these contracts but do not guarantee
            real-time delivery. Signal freshness is a best-effort commitment subject to source availability and
            network conditions.
          </p>
        </SubSection>
      </Section>

      {/* ── 2. License Scope & Restrictions ───────────────────────────────── */}
      <Section id="license" number="2" title="License Scope &amp; Restrictions">
        <SubSection title="2.1 Subscription License">
          <p>
            Subject to these Terms and the payment of applicable fees, Cogent grants you a <strong>limited,
            non-exclusive, non-transferable, revocable subscription license</strong> to access and use the
            platform during the subscription term. This is a subscription to a service — not a sale of software,
            data, or intellectual property.
          </p>
        </SubSection>
        <SubSection title="2.2 Restrictions">
          <p>You shall not, and shall not permit any third party to:</p>
          <ul className="list-disc pl-5 space-y-1 text-xs text-body">
            <li>Reverse-engineer, decompile, disassemble, or attempt to derive the source code of any part of the platform, including the signal detection logic, crawling infrastructure, or algorithmic models;</li>
            <li>Use the platform as a &ldquo;crawler-as-a-service,&rdquo; &ldquo;scraper-as-a-service,&rdquo; or URL-centric search engine;</li>
            <li>Redistribute, resell, sublicense, or make the platform available to any third party as a dataset marketplace;</li>
            <li>Use Cogent&apos;s outputs to train, develop, or improve any competing signal intelligence, market monitoring, or competitive analysis tool or product;</li>
            <li>Circumvent, disable, or interfere with any security, rate-limiting, or access-control features of the platform;</li>
            <li>Share a single-seat or team-seat license beyond the authorised users specified in your subscription.</li>
          </ul>
        </SubSection>
        <SubSection title="2.3 Seat Management & Fair Use">
          <p>
            Cogent is licensed on a per-seat basis. Each account login credential is for a single authorised user.
            You may not share credentials across multiple individuals. Enterprise plans with team seats must comply
            with the &ldquo;Fair Use&rdquo; limits defined in the applicable Order Form. Cogent reserves the right
            to audit usage and suspend access for violations.
          </p>
        </SubSection>
      </Section>

      {/* ── 3. Data Ownership & Intellectual Property ─────────────────────── */}
      <Section id="data-ownership" number="3" title="Data Ownership &amp; Intellectual Property">
        <SubSection title="3.1 User Content (Input Data)">
          <p>
            You retain full ownership of all data, content, and materials you upload to or submit through the
            platform (&ldquo;User Content&rdquo;), including proprietary data such as team goals, internal KPIs,
            and contextual enrichment inputs. Cogent claims no ownership over your User Content.
          </p>
        </SubSection>
        <SubSection title="3.2 Derived Intelligence (Output Data)">
          <p>
            While you may access, download, and use the specific signal reports and intelligence outputs generated
            for your account, Cogent retains ownership of:
          </p>
          <ul className="list-disc pl-5 space-y-1 text-xs text-body">
            <li><strong>Signal Contracts:</strong> The schema definitions, detection logic, and business-meaning declarations that power the platform — these are proprietary intellectual property of Cogent;</li>
            <li><strong>Aggregated Data Insights:</strong> Anonymised, aggregated patterns derived from platform-wide signal processing;</li>
            <li><strong>Algorithmic Models:</strong> The vertical vocabularies, machine learning models, and detection algorithms used to interpret signals into intelligence;</li>
            <li><strong>Platform Infrastructure:</strong> The &ldquo;invisible plumbing&rdquo; — crawling, scraping, and search infrastructure — that powers signal ingestion.</li>
          </ul>
        </SubSection>
        <SubSection title="3.3 Signal Persistence">
          <p>
            While data sources are considered volatile, synthesised Signals persist as a system of record for
            longitudinal analysis. The retention and archival policies for persistent signals are governed by
            your subscription tier and applicable data retention settings.
          </p>
        </SubSection>
      </Section>

      {/* ── 4. Service Level Agreement (SLA) ──────────────────────────────── */}
      <Section id="sla" number="4" title="Service Level Agreement (SLA)">
        <SubSection title="4.1 Uptime Commitment">
          <p>
            Cogent commits to a platform availability of <strong>99.9%</strong> uptime per calendar month,
            measured as the percentage of total minutes in the month during which the platform&apos;s core
            services (signal ingestion, dashboard access, API endpoints) are operational.
          </p>
        </SubSection>
        <SubSection title="4.2 Exclusions">
          <p>The following are excluded from uptime calculations:</p>
          <ul className="list-disc pl-5 space-y-1 text-xs text-body">
            <li>Scheduled maintenance windows (communicated at least 48 hours in advance);</li>
            <li>Force majeure events, including natural disasters, government actions, or third-party infrastructure failures;</li>
            <li>Issues caused by the User&apos;s equipment, software, or network connectivity;</li>
            <li>Third-party API or data source outages beyond Cogent&apos;s control.</li>
          </ul>
        </SubSection>
        <SubSection title="4.3 Service Credits">
          <p>
            If Cogent fails to meet the 99.9% uptime commitment, eligible enterprise customers may request
            service credits as follows:
          </p>
          <div className="mt-2 overflow-x-auto rounded-xl border border-border">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-border bg-muted/50">
                  <th className="px-4 py-2 text-left font-medium text-heading">Monthly Uptime</th>
                  <th className="px-4 py-2 text-left font-medium text-heading">Service Credit</th>
                </tr>
              </thead>
              <tbody className="text-body">
                <tr className="border-b border-border"><td className="px-4 py-2">99.0% – 99.9%</td><td className="px-4 py-2">10% of monthly fees</td></tr>
                <tr className="border-b border-border"><td className="px-4 py-2">95.0% – 99.0%</td><td className="px-4 py-2">25% of monthly fees</td></tr>
                <tr><td className="px-4 py-2">Below 95.0%</td><td className="px-4 py-2">50% of monthly fees</td></tr>
              </tbody>
            </table>
          </div>
          <p className="mt-2 text-xs text-subtle">
            Service credits must be requested within 30 days of the applicable month. Credits are applied to
            future invoices and are non-refundable.
          </p>
        </SubSection>
      </Section>

      {/* ── 5. Acceptable Use Policy (AUP) ────────────────────────────────── */}
      <Section id="aup" number="5" title="Acceptable Use Policy">
        <p className="text-xs leading-relaxed">
          Users agree not to use the Cogent platform for any of the following purposes:
        </p>
        <SubSection title="5.1 Prohibited Activities">
          <ul className="list-disc pl-5 space-y-1 text-xs text-body">
            <li><strong>Illegal surveillance:</strong> Using the platform to conduct unlawful monitoring, tracking, or surveillance of individuals or organisations;</li>
            <li><strong>Corporate espionage:</strong> Using Cogent outputs to engage in illegal corporate intelligence gathering or trade secret theft;</li>
            <li><strong>Harassment or intimidation:</strong> Leveraging intelligence outputs to harass, threaten, defame, or intimidate any person or entity;</li>
            <li><strong>Violation of data protection laws:</strong> Using the platform in a manner that violates the NDPA 2023, GDPR, CCPA, or any other applicable data protection regulation;</li>
            <li><strong>Circumvention of access controls:</strong> Using Cogent to bypass paywalls, login walls, or terms of service of third-party platforms;</li>
            <li><strong>Illegal web scraping:</strong> Using the platform to scrape data in violation of other platforms&apos; terms of service or applicable computer fraud laws;</li>
            <li><strong>Generation of misleading intelligence:</strong> Deliberately inputting false data to generate or manipulate signals for fraudulent purposes;</li>
            <li><strong>Competing product development:</strong> Using any Cogent APIs, outputs, or infrastructure to build, train, or enhance a competing intelligence product.</li>
          </ul>
        </SubSection>
        <SubSection title="5.2 Enforcement">
          <p>
            Cogent reserves the right to suspend or terminate any account found in violation of this Acceptable
            Use Policy, with or without prior notice. In the case of severe violations, Cogent may report the
            activity to relevant authorities and pursue legal remedies.
          </p>
        </SubSection>
      </Section>

      {/* ── 6. AI Transparency & Automated Decision-Making ────────────────── */}
      <Section id="ai-transparency" number="6" title="AI Transparency &amp; Automated Decision-Making">
        <SubSection title="6.1 Disclosure">
          <p>
            The Cogent platform uses machine learning models, natural language processing, and automated detection
            logic to discover, validate, and synthesise signals. These automated systems:
          </p>
          <ul className="list-disc pl-5 space-y-1 text-xs text-body">
            <li>Analyse public and semi-public data sources to detect emerging patterns and trends;</li>
            <li>Generate confidence scores representing probabilistic signal quality;</li>
            <li>Autonomously propose new signals based on coverage gap analysis;</li>
            <li>Enrich signals using vertical-specific vocabularies and contextual models.</li>
          </ul>
        </SubSection>
        <SubSection title="6.2 Human-in-the-Loop Safeguards">
          <p>
            Where automated processing may have a significant impact on decision-making, Cogent maintains
            human-in-the-loop oversight. Analysts may label, curate, or validate signals in a secure,
            audited environment to improve model accuracy and ensure enterprise safety by design.
          </p>
        </SubSection>
        <SubSection title="6.3 Opt-Out">
          <p>
            Users may request an opt-out from AI-generated signal recommendations for significant decisions
            by contacting <a href="mailto:privacy@cogent.ai" className="text-primary hover:underline">privacy@cogent.ai</a>.
            Enterprise accounts may configure this preference via the platform settings.
          </p>
        </SubSection>
      </Section>

      {/* ── 7. Limitation of Liability ────────────────────────────────────── */}
      <Section id="liability" number="7" title="Limitation of Liability">
        <SubSection title="7.1 Cap on Liability">
          <p>
            To the maximum extent permitted by law, Cogent&apos;s total aggregate liability to you for any and all
            claims arising out of or relating to these Terms or the use of the platform shall not exceed the
            <strong> total amount paid by you to Cogent during the twelve (12) months</strong> immediately preceding
            the event giving rise to the claim.
          </p>
        </SubSection>
        <SubSection title="7.2 Exclusion of Consequential Damages">
          <p>
            In no event shall Cogent be liable for any indirect, incidental, special, consequential, or punitive
            damages, including but not limited to: loss of profits, revenue, business opportunities, data, or
            goodwill; business interruption; or the cost of procuring substitute services — whether arising from
            contract, tort (including negligence), strict liability, or otherwise, even if Cogent has been advised
            of the possibility of such damages.
          </p>
        </SubSection>
        <SubSection title="7.3 Signal Accuracy">
          <p>
            Cogent does not warrant that signals will be error-free, complete, or meet any specific accuracy
            threshold beyond those explicitly defined in the applicable Signal Contract. The User acknowledges
            that signal intelligence is inherently probabilistic and dependent on external data sources.
          </p>
        </SubSection>
      </Section>

      {/* ── 8. Switching Rights & Data Portability (EU Data Act) ──────────── */}
      <Section id="switching" number="8" title="Switching Rights &amp; Data Portability">
        <p className="text-xs leading-relaxed">
          In compliance with the EU Data Act (2025/2026) and evolving global interoperability standards:
        </p>
        <SubSection title="8.1 Data Export">
          <p>
            Users may export their User Content and signal reports in machine-readable formats (JSON, CSV) at any
            time through the platform&apos;s Data &amp; Privacy settings. Enterprise customers may request bulk
            data exports via the API.
          </p>
        </SubSection>
        <SubSection title="8.2 No Lock-In">
          <p>
            Cogent shall not impose any switching fees, data lock-in charges, or artificial barriers to prevent
            customers from migrating their User Content to a competing service. You are free to terminate your
            subscription and retrieve your data within 90 days of account closure.
          </p>
        </SubSection>
      </Section>

      {/* ── 9. Termination ────────────────────────────────────────────────── */}
      <Section id="termination" number="9" title="Termination">
        <SubSection title="9.1 By the User">
          <p>
            You may terminate your subscription at any time through the platform settings or by contacting
            support. Upon termination, your access will continue until the end of the current billing period.
          </p>
        </SubSection>
        <SubSection title="9.2 By Cogent">
          <p>
            Cogent may suspend or terminate your access — with or without prior notice — if you materially
            breach these Terms, violate the Acceptable Use Policy, or fail to pay applicable fees.
          </p>
        </SubSection>
        <SubSection title="9.3 Effect of Termination">
          <p>
            Upon termination, you retain ownership of your User Content and may export it within 90 days.
            After this period, Cogent may delete your data in accordance with our retention policies. Provisions
            that by their nature should survive termination (including Sections 3, 7, and 10) shall continue
            in full force.
          </p>
        </SubSection>
      </Section>

      {/* ── 10. Governing Law & Jurisdiction ──────────────────────────────── */}
      <Section id="governing-law" number="10" title="Governing Law &amp; Jurisdiction">
        <p className="text-xs leading-relaxed">
          These Terms shall be governed by and construed in accordance with the laws of the
          <strong> Federal Republic of Nigeria</strong>. Any dispute arising from or relating to these Terms
          shall be subject to the exclusive jurisdiction of the <strong>Federal High Court of Nigeria</strong>,
          unless a separate enterprise agreement specifies alternative jurisdiction. For EU-based customers,
          GDPR provisions apply concurrently, and disputes may also be brought before the competent courts
          of the Customer&apos;s EU Member State.
        </p>
      </Section>

      {/* ── 11. Modifications ─────────────────────────────────────────────── */}
      <Section id="modifications" number="11" title="Modifications to These Terms">
        <p className="text-xs leading-relaxed">
          Cogent reserves the right to modify these Terms at any time. Material changes will be communicated
          via email and/or in-platform notification at least <strong>30 days</strong> prior to taking effect.
          Continued use of the platform after the effective date constitutes acceptance of the revised Terms.
          Enterprise customers with executed agreements will be governed by the terms of their specific contract
          until renewal.
        </p>
      </Section>

      {/* ── Click-Wrap Notice ─────────────────────────────────────────────── */}
      <div className="rounded-2xl border border-primary/20 bg-primary/5 p-6">
        <h3 className="text-sm font-semibold text-heading mb-2">Click-Wrap Agreement</h3>
        <p className="text-xs text-body leading-relaxed">
          By clicking &ldquo;I Agree&rdquo; or &ldquo;Create Account&rdquo; during the signup process, you
          acknowledge that you have read, understood, and agree to be bound by these Terms of Service and the
          accompanying Privacy Policy. This click-wrap mechanism constitutes a legally binding agreement. If you
          do not agree to these Terms, do not create an account or use the platform.
        </p>
      </div>

      {/* ── Contact ───────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between rounded-xl border border-border bg-surface px-6 py-4">
        <div>
          <p className="text-sm font-medium text-heading">Questions about these Terms?</p>
          <p className="text-xs text-subtle">Contact our legal team for enterprise contract inquiries.</p>
        </div>
        <a
          href="mailto:legal@cogent.ai"
          className="flex-shrink-0 rounded-xl bg-primary px-5 py-2 text-xs font-medium text-white hover:bg-primary-hover transition-colors"
        >
          legal@cogent.ai
        </a>
      </div>
    </article>
  )
}
