# Frontend Implementation Master Plan: The Cognitive Interface (ESIP)

**Version:** 2.0  
**Status:** Production Ready  
**Design Theme:** "Clean Intelligence" (Light Mode / Tactical Professional)  
**Target Audience:** Enterprise Analysts, Strategy Executives, Decision Makers

---

## Table of Contents
1. [Design Philosophy](#1-design-philosophy)
2. [Design System](#2-design-system)
3. [Application Architecture](#3-application-architecture)
4. [Page Specifications](#4-page-specifications)
5. [Component Library](#5-component-library)
6. [Interaction Patterns](#6-interaction-patterns)
7. [Visual Reference Guide](#7-visual-reference-guide)
8. [Implementation Priority](#8-implementation-priority)

---

## 1. Design Philosophy

### 1.1 Core Principles
**Cognitive Interface, Not Dashboard**
- We build an intelligent assistant that feels like a high-end SaaS platform
- Think: Report,Financial terminal meets modern AI assistant
- **Golden Rule:** "Silence until Signal" — show intelligence only when it matters

**User Experience Goals**
- Answer "What do I need to know?" in 30 seconds
- Dense with value, calm in execution
- Responsive, app-like (PWA), not website-like

---

## 2. Design System

### 2.1 Color Palette

#### Background Colors
```css
Canvas (Base Layer):     #F8FAFC  /* Slate 50 */
Surface (Cards/Panels):  #FFFFFF  /* Pure White */
Active/Hover State:      #F1F5F9  /* Slate 100 */
```

#### Semantic Colors
```css
Primary Action:          #4F46E5  /* Indigo 600 - Buttons, Active Tabs */
Success/High Confidence: #059669  /* Emerald 600 - Background: #ECFDF5 */
Warning/Volatility:      #D97706  /* Amber 600 - Background: #FFFBEB */
Critical/Risk:           #E11D48  /* Rose 600 - Background: #FFF1F2 */
Neutral/Info:            #64748B  /* Slate 500 */
```

#### Text Colors
```css
Headings:                #0F172A  /* Slate 900 */
Body Text:               #334155  /* Slate 700 */
Data/Code/IDs:           #475569  /* Slate 600 */
```

#### Borders & Dividers
```css
Border Color:            #E2E8F0  /* Slate 200 - Crisp, no muddy greys */
```

### 2.2 Typography

#### Font Families
```css
Headings & UI:           'Inter' or 'Geist Sans'
Body Text:               'Inter'
Code/Data/Monospace:     'JetBrains Mono' or 'Geist Mono'
Reading Mode:            'Merriweather' (Serif for reports)
```

#### Font Weights
```css
Light (Headings):        300
Regular:                 400
Medium (Emphasis):       500
/* Avoid bold (700+) for cleaner aesthetic */
```

### 2.3 Shadows & Depth

```css
/* Layer 1: Cards - Subtle Lift */
box-shadow: 0 1px 3px 0 rgb(0 0 0 / 0.1), 
            0 1px 2px -1px rgb(0 0 0 / 0.1);

/* Layer 2: Dropdowns/Modals - Distinct Separation */
box-shadow: 0 10px 15px -3px rgb(0 0 0 / 0.1), 
            0 4px 6px -4px rgb(0 0 0 / 0.1);
```

### 2.4 Spatial System

```css
Border Radius:           8px   /* Rounded-lg for cards */
Spacing Scale:           4px base (Tailwind standard)
Max Content Width:       800px (Feed), 600px (Command Bar)
```

---

## 3. Application Architecture

### 3.1 Tech Stack

```
Framework:        Next.js 14 (App Router)
Styling:          Tailwind CSS
UI Components:    Shadcn/UI (Headless, heavily customized)
Icons:            Lucide React (Thin stroke, consistent)
Data Viz:         Recharts (Charts/Sparklines)
Graphs:           React Flow (Entity Relationships)
Maps:             Mapbox GL / Leaflet (Lightweight)
State:            React Context / Zustand (for global state)
```

### 3.2 Component Architecture

```
src/
├── components/
│   ├── ui/                    # Base Shadcn components
│   │   ├── Shell.tsx          # Global layout wrapper
│   │   ├── NavigationRail.tsx
│   │   ├── OmniBar.tsx
│   │   └── ...
│   ├── signals/
│   │   ├── SignalCard.tsx     # Feed item component
│   │   ├── SignalDrawer.tsx   # Detail slide-over
│   │   └── SignalGrid.tsx     # Data table
│   ├── investigate/
│   │   ├── ChatInterface.tsx  # Split-screen chat
│   │   ├── EvidenceBoard.tsx  # Dynamic right panel
│   │   └── ProcessTracker.tsx # "Thinking" visualization
│   ├── visualizations/
│   │   ├── TrendLine.tsx      # Micro-sparkline
│   │   ├── EntityGraph.tsx    # Node relationship graph
│   │   └── Chart.tsx          # Reusable chart wrapper
│   └── contracts/
│       ├── ContractStudio.tsx # Custom contract builder
│       └── FeasibilityPanel.tsx
├── app/
│   ├── (dashboard)/
│   │   ├── layout.tsx         # Shell wrapper
│   │   ├── home/
│   │   ├── investigate/
│   │   ├── signals/
│   │   ├── domains/
│   │   ├── library/
│   │   └── settings/
│   └── ...
```

---

## 4. Page Specifications

### 4.1 Global Shell (The "Cockpit")

The shell provides stability while content changes dynamically.

#### Navigation Rail (Left Sidebar)

**Default State:** Collapsed (64px width)  
**Expanded State:** 240px on hover/click  
**Styling:** White background, right border `#E2E8F0`

**Structure:**
```
┌─────────────────┐
│ [Logo]          │  ← Minimalist abstract symbol (Indigo)
├─────────────────┤
│ ⊞ Home          │  ← Icon: Home icon
│ ✨ Investigate  │  ← Icon: The Keyhole icon
│ ⚡ Signals      │  ← Icon: Activity
│ 🌍 Domains      │  ← Icon: Globe/Map
│ 📖 Library      │  ← Icon: BookOpen
├─────────────────┤
│ ⚙️ Settings     │  ← Footer section ←
│ 🔔 Notifications│
│ 🌓 Theme        │
│ 🚪 Logout       │
└─────────────────┘
```

**Interactions:**
- **Hover:** Background → `#F1F5F9`, Text → Indigo
- **Active:** Indigo vertical bar (4px) on left edge, Icon → Indigo
- **Click (Collapsed):** Expand sidebar
- **Click Outside:** Collapse sidebar

#### Omni-Command Bar (Top)

**Height:** 64px (Sticky)  
**Styling:** Glassmorphic (`backdrop-blur-sm`), bottom border `#E2E8F0`

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│ [Nav Toggle]  [Command Input ..................]  [Status]  │
│                                                   [🔔 Bell]  │
└─────────────────────────────────────────────────────────────┘
```

**Command Input:**
- **Width:** max-width 600px (centered)
- **Background:** `#F1F5F9`
- **Border:** None
- **Radius:** 8px
- **Placeholder:** "Ask about market trends, entities, or press '/' for commands..."
- **Behavior:** Triggers Spotlight-style dropdown on typing

**Right Section:**
- **System Status:** "Data Freshness: Live" with green dot
- **Notification Bell:** Badge count for critical alerts

---

### 4.2 HOME Page: Intelligence Feed

**Goal:** Situation awareness in 30 seconds  
**Layout:** Single-column feed (max 800px) + Right sidebar

#### A. Morning Brief (Hero Section)

**Visual:** Clean typography, no container box

**Content Structure:**
```
Good Morning, [User Name].

There are 3 Critical Impact events affecting the [Domain] portfolio today.
The CBN rate hike is projected to impact fertilizer costs by +12%.

[Auto-updates every 1-2 hours with high-impact domain changes]
```

**Typography:**
- **Font Size:** 24px+
- **Weight:** 300 (Light)
- **Color:** `#0F172A`
- **Highlighted Entities:** Indigo color `#4F46E5`

**Interaction:** Clicking highlighted entities (e.g., "CBN rate hike") deep-links to Signal Dossier

#### B. Signal Stream (Feed)

**Component:** `<SignalCard />`

**Card Structure:**
```
┌───────────────────────────────────────────────┐
│ [Icon] Dangote Cement · FMCG    2h ago · 89% │ ← Header
├───────────────────────────────────────────────┤
│ Price deviation >15% detected in Kano market  │ ← Headline (Bold, 16px)
│ Regional supply chain disruption from fuel... │ ← Summary (2 lines, grey)
│ [Subtle sparkline showing trend ───╱──]       │ ← SVG trend line
├───────────────────────────────────────────────┤
│ [✨ Synthesize] [Share] [Dismiss]             │ ← Actions (Hover visible)
└───────────────────────────────────────────────┘
```

**Styling:**
- **Container:** White, `border: 1px solid #E2E8F0`, shadow-sm, rounded-lg
- **Header Left:** Entity icon + name + domain tag
- **Header Right:** Timestamp + confidence badge (Green pill "89%")
- **Footer:** Actions visible on hover

**Interaction:** Click card → Opens Signal Dossier Drawer (slide from right)

#### C. The "Moat" Widget (Right Sidebar)

**Position:** Sticky  
**Content:**
```
┌─────────────────────────┐
│ Proprietary Data Ingest │
│                         │
│      15,420             │ ← Live counter
│ unique data points      │
│ processed today         │
└─────────────────────────┘
```

**Purpose:** Reinforce platform value proposition

#### Signal Dossier Structure

When user clicks a Signal Card or Grid row:

```
┌─────────────────────────────────────┐
│ [X] Title + BLUF                    │
├─────────────────────────────────────┤
│ Argument + Evidence                 │
│ • Point 1 [Source Link]             │
│ • Point 2 [Source Link]             │
│ • Point 3 [Source Link]             │
├─────────────────────────────────────┤
│ Outlook & Implications              │
│ • What is likely next               │
│ • What this means for stakeholders  │
├─────────────────────────────────────┤
│ Decision Lens                       │
│ "What this means for you" panel     │
└─────────────────────────────────────┘
```

---

### 4.3 INVESTIGATE Page: The War Room

**Goal:** Active deep-dive analysis  
**Layout:** 40/60 Split Screen

#### Left Pane: Chat Interface (40%)

**Message Structure:**
```
┌────────────────────────────────────┐
│          System Message            │ ← Left aligned
│ [Grey background #F1F5F9]          │   Dark text
│ Markdown support enabled           │   Tables, lists, and minimal charts
└────────────────────────────────────┘

                ┌───────────────────┐
                │   User Message    │ ← Right aligned
                │ [Indigo #4F46E5]  │   White text
                │ Standard bubble   │
                └───────────────────┘
```

**Input Area:**
- **Position:** Sticky bottom
- **Component:** Large textarea + Send button
- **Features:** Multi-line support, Shift+Enter for new line

#### Right Pane: Evidence Board (60%)

**Dynamic States:**

**State 1: "Thinking" (Process Visualization)**
```
Searching 12 sources...        [⟳ → ✓]
Reading CBN Monetary Policy... [⟳ → ✓]
Analyzing market trends...     [⟳ → ✓]
Synthesizing answer...         [⟳]
```

**State 2: "Citations" (Document View)**
- Shows source document snippets
- Highlights exact paragraph used when AI cites `[1]`

**State 3: "Graph" (Relationship View)**
- Interactive Node Graph (React Flow)
- Shows entity connections discussed (e.g., "Dangote" ↔ "Supplier X")

**State 4: "Visualizations"**
- Charts appear only when query needs visual explanation
- Clean charts with semantic colors
- Use cases: Finances, comparisons, analytics
- **Rule:** Visuals are optional support, not mandatory

**Behavior:** Panel morphs automatically based on conversation context

---

### 4.4 SIGNALS Page: The Data Grid

**Goal:** Monitoring, sorting, filtering high-density data  
**Layout:** Full-width table

#### Grid Specifications

**Container:** White surface, no outer borders

**Headers:**
- **Position:** Sticky top
- **Style:** Uppercase, text-xs, `#64748B`, sortable indicators

**Columns:**
```
┌──────────┬───────────┬─────────┬─────────┬────────────┬────────┐
│ Entity   │ Signal    │ Trend   │ Driver  │ Confidence │ Action │
├──────────┼───────────┼─────────┼─────────┼────────────┼────────┤
│ [Icon]   │ Price     │ ╱──     │ 🌧️→💰  │ ◉ 89%      │ View   │
│ Dangote  │ Surge     │ (Red)   │         │ (Green)    │        │
└──────────┴───────────┴─────────┴─────────┴────────────┴────────┘
```

**Row Styling:**
- **Height:** 48px (compact)
- **Hover:** Background → `#F8FAFC`
- **Border:** Bottom border `#E2E8F0`

**Column Details:**
1. **Entity:** Logo + Name
2. **Signal:** Description text
3. **Trend:** Micro-sparkline (Red/Green SVG)
4. **Driver:** Icon showing causality (e.g., Rain Cloud → Dollar)
5. **Confidence:** Circular progress ring (color-coded)
6. **Action:** "View" button

**Interaction:** Click row → Opens Signal Dossier Drawer (same structure as Home feed)

---

### 4.5 DOMAINS Page: The God View

**Goal:** Spatial & sector intelligence  
**Layout:** Full-screen map with floating controls

#### Map Canvas

**Technology:** Mapbox GL or Leaflet  
**Style:** Custom light mode (desaturated land, crisp borders)

**Map Layers:**
- **Heatmaps:** Risk intensity (Red), Opportunity (Green)
- **Pins:** Specific assets (Factories, Ports, Markets)
- **Regions:** Clickable polygons

#### Floating Control Panel (Top Right)

**Visual:** Glassmorphic card (`backdrop-blur`)

**Structure:**
```
┌─────────────────────┐
│ Domain | Title      │ ← Tabs
├─────────────────────┤
│ ☐ Show Drought Risk │ ← Toggle switches
│ ☐ Show Price Spreads│
│ ☐ Show Supply Chain │
└─────────────────────┘
```

#### Region Interaction

**Click Region (e.g., "Kano State"):**
```
┌─────────────────────────────┐
│ Kano State                  │
│ [Related Image]             │ ← Image from web related to that region
│ Regional Risk: High         │
│ Driver: Fuel Costs          │
│                             │
│ Latest Discovery:           │
│ Fertilizer shortage...      │
└─────────────────────────────┘
```

**Popover Features:**
- Summary card with risk level
- Relevant image (context-specific from web)
- Latest regional discovery/news

---

### 4.6 LIBRARY Page: Institutional Memory

**Goal:** Retrieval & synthesis of past reports and also a weekly report
**Layout:** Masonry grid (Pinterest-style)

#### Brief Card (Horizontal in Grid)

**Card Structure:**
```
┌──────────────────────────────────────┐
│ [Generative Abstract Pattern]       │ ← Pastel colors based on topic
│                                      │
│ Impact of Fuel Subsidy Removal      │ ← Serif font (Merriweather)
│ on Q3 Agri-Yields                   │
│                                      │
│ Dec 15, 2024 · AI Generated         │ ← Meta
│ #Agriculture #Policy #Q3            │ ← Tags
└──────────────────────────────────────┘
```

**Interaction:** Click → Opens Reader View Modal

#### Reader View (Centered Modal)

**Style:**
- Minimalist layout
- Wide margins (max 65ch)
- Serif font (`Merriweather`)
- Clean like Medium article
- Distraction-free reading

#### Weekly Report Format

**Structure:** Consultant-style (McKinsey format) that can be exported in pdf format and presentation format (PowerPoint/Google Slides)

```

**Components:**
- Social media / news network ready format
- Charts, icons, typography
- Semantic color palette
- Clear visual hierarchy

---

### 4.7 CONTRACT STUDIO Page

**Goal:** Define institutional truth (custom contracts)  
**Access Points:**

#### Entry Points

1. **Primary:** `Signals > Studio` (Dedicated full-screen page)
2. **From Investigate:** "Promote to Contract" button during chat
3. **From Library:** "View Definition" on entity/signal (read-only mode)

#### Layout System

```
┌─────────────────────────────────────────────────────────────┐
│ Draft → AI Validation → Simulation → Active                │ ← Lifecycle Tracker
├──────────────────────────┬──────────────────────────────────┤
│ Left Pane (40%)          │ Right Pane (60%)                 │
│ ──────────────           │ ──────────────                   │
│ Definition Area          │ Intelligence Area                │
│ • Natural language input │ • Feasibility charts             │
│ • Schema builder forms   │ • Credit costs                   │
│ • Contract parameters    │ • Synthetic preview              │
│                          │ • Real-time validation           │
├──────────────────────────┴──────────────────────────────────┤
│ Bottom Tray: Source Documents (PDFs/URLs AI is reading)     │
└─────────────────────────────────────────────────────────────┘
```

**Purpose:** Build custom data contracts with AI assistance and validation

---

### 4.8 SETTINGS Page

**Reference:** `Wire/1 (1).jpeg`  
**Layout:** horizontal tab layout structure with sidebar navigation on the top content and the content in the down panel

**Sections:**
| Sidebar | Content Panel |
|---|---|
| Profile | Active section: Billing settings & invoices · Contact information · Account settings · Plan management |
| Preferences & Permissions | Form fields for user preferences, roles, and permission controls |
| Notifications | Toggle switches and delivery settings |
| Security | Security settings (password, 2FA) · Save / Apply buttons |
| Integrations | Integration management (connect/disconnect services, API keys) |
| Dashboard | Billing overview: credit & billing usage dashboard · Usage charts |

**Visual Style:**
- Clean form inputs
- Clear section headers
- Toggle switches for boolean options
- Save confirmation toasts
- Consistent use of semantic colors for warnings, errors, and success states
- Clean chart and layout for the dashboard section
- Responsive layout for mobile and desktop

---

## 5. Component Library

### 5.1 Core UI Components

#### SignalCard Component

```tsx
<SignalCard
  entity={{
    name: "Dangote Cement",
    icon: "...",
    domain: "FMCG"
  }}
  signal={{
    headline: "Price deviation >15% detected",
    summary: "Regional supply chain disruption...",
    confidence: 89,
    timestamp: "2h ago"
  }}
  trend={[...trendData]}
  onSynthesize={() => {}}
  onShare={() => {}}
  onDismiss={() => {}}
/>
```

#### ChatInterface Component

```tsx
<ChatInterface
  messages={messages}
  onSendMessage={(msg) => {}}
  renderEvidence={<EvidenceBoard state={currentState} />}
/>
```

#### SignalDrawer Component

```tsx
<SignalDrawer
  open={isOpen}
  onClose={() => {}}
  signal={{
    title: "...",
    bluf: "...",
    evidence: [...],
    outlook: "...",
    decisionLens: "..."
  }}
/>
```

### 5.2 Visualization Components

#### TrendLine (Sparkline)

```tsx
<TrendLine
  data={[1, 3, 2, 5, 4, 6]}
  width={100}
  height={24}
  color="emerald" // or "rose" or "amber"
/>
```

#### EntityGraph (Node Graph)

```tsx
<EntityGraph
  nodes={[
    { id: '1', label: 'Dangote', type: 'company' },
    { id: '2', label: 'Supplier X', type: 'supplier' }
  ]}
  edges={[
    { source: '1', target: '2', label: 'supplies' }
  ]}
/>
```

#### ConfidenceBadge

```tsx
<ConfidenceBadge
  score={89}
  breakdown={{
    source: "high",
    freshness: "medium",
    corroboration: "high"
  }}
/>
```

### 5.3 Layout Components

#### Shell Component

```tsx
<Shell>
  <NavigationRail />
  <OmniBar />
  <main>{children}</main>
</Shell>
```

---

## 6. Interaction Patterns

### 6.1 Motion & Transitions

**Page Transitions:**
```css
/* Subtle fade-in + slide-up */
animation: fadeInUp 200ms ease-out;
transform: translateY(10px) → translateY(0);
opacity: 0 → 1;
```

**Drawer Animation:**
```css
/* Slide from right */
transform: translateX(100%) → translateX(0);
transition: transform 300ms cubic-bezier(0.16, 1, 0.3, 1);
```

### 6.2 Loading States

**Never use generic full-screen spinners.**

**Skeleton Loaders:**
- Match exact content shape
- Shimmer effect animation
- Card skeletons, table row skeletons

**AI Text Streaming:**
```tsx
// Typewriter effect for AI responses
<StreamingText text={aiResponse} speed={30} />
```

### 6.3 Micro-interactions

**Button States:**
```css
/* Hover: Subtle lift */
button:hover {
  transform: translateY(-1px);
  transition: transform 150ms ease;
}

/* Active: Press down */
button:active {
  transform: scale(0.98);
}
```

**Confidence Badge Hover:**
- Shows breakdown tooltip
- "Source: High, Freshness: Medium, Corroboration: High"

### 6.4 Advanced UX Features

#### Freshness Pulse (Live Data)

```css
/* Soft pulsing glow for real-time data */
.live-indicator {
  animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
```

#### Indigo for Intelligence

**Rule:** Indigo color (`#4F46E5`) is **reserved exclusively** for AI-generated insights.  
**Purpose:** User instantly knows if content is Cogent intelligence vs. raw data.

---

## 7. Visual Reference Guide

**CRITICAL:** These reference images guide spatial arrangement, component scale, and styling. Do NOT copy literally—use as design direction.

### 7.1 Global Shell

| Reference | Purpose |
|-----------|---------|
| `Wire/1 (7).JPG` | Minimal sidebar, active states, settings popover |
| `Wire/1 (36).webp` | Active state styling, clean settings UI |

### 7.2 Home Page

| Reference | Purpose |
|-----------|---------|
| `Wire/1 (1).jpg` | "Morning Brief" typography, card shadows, badge styling |
| `Wire/1 (1).webp` | Activity tracker density for Signal Stream |
| `Wire/1 (2).webp` | **GOLD STANDARD for SignalCard design** |

### 7.3 Investigation / War Room

| Reference | Purpose |
|-----------|---------|
| `Wire/1 (18).webp` | **GOLD STANDARD for split-view layout** (Terminal + Copilot) |
| `Wire/1 (1).webp` | Chat bubble styling |

### 7.4 Signals Data Grid

| Reference | Purpose |
|-----------|---------|
| `Wire/1 (13).webp` | Table layout, row density, status pills |
| `Wire/1 (17).webp` | Drawer content structure with charts/colors |

### 7.5 Domain Maps

| Reference | Purpose |
|-----------|---------|
| `Wire/11 (2).webp` | Geo-Traffic map style (desaturated tiles, bright data points) |
| `Wire/11 (1).webp` | Map hover effect with image card + description |

### 7.6 Library

| Reference | Purpose |
|-----------|---------|
| `Wire/1 (25).webp` | Grid card layout, metadata display |

### 7.7 Settings

| Reference | Purpose |
|-----------|---------|
| `Wire/1 (1).jpeg` | Layout structure and styling pattern |

---

## 8. Implementation Priority

### Phase 1: Foundation (Week 1-2)
```
1. ✓ Set up Next.js 14 + Tailwind + Shadcn/UI
2. ✓ Build Shell component (NavigationRail + OmniBar)
3. ✓ Implement design system tokens
4. ✓ Create base UI components (Button, Card, Badge, etc.)
```

### Phase 2: Core Pages (Week 3-4)
```
5. ✓ HOME: Build Feed + SignalCard + Morning Brief
6. ✓ HOME: Implement Signal Dossier Drawer
7. ✓ INVESTIGATE: Build Chat Interface
8. ✓ INVESTIGATE: Build Evidence Board (all 4 states)
```

### Phase 3: Data Views (Week 5-6)
```
9. ✓ SIGNALS: Build data grid + filtering
10. ✓ DOMAINS: Integrate map (Mapbox/Leaflet)
11. ✓ DOMAINS: Build region popover system
12. ✓ LIBRARY: Build masonry grid + Reader View
```

### Phase 4: Advanced Features (Week 7-8)
```
13. ✓ CONTRACT STUDIO: Build full workspace
14. ✓ SETTINGS: Build settings page
15. ✓ Add all micro-interactions and animations
16. ✓ Implement skeleton loaders everywhere
17. ✓ Polish + Performance optimization
```

### Phase 5: Testing & Launch (Week 9-10)
```
18. ✓ Cross-browser testing
19. ✓ Accessibility audit (WCAG 2.1 AA)
20. ✓ Performance testing (Lighthouse)
21. ✓ User acceptance testing
22. ✓ Production deployment
```

---

## Engineering Notes

### State Management Strategy
- **Global:** User auth, theme, notifications (Zustand)
- **Server:** Next.js Server Components + Server Actions
- **Client:** React Context for page-specific state

### Data Fetching Pattern
```tsx
// Server Component (default)
async function HomePage() {
  const signals = await fetchSignals();
  return <SignalFeed signals={signals} />;
}

// Client Component (when interactivity needed)
'use client';
function SignalCard({ signal }) {
  const [expanded, setExpanded] = useState(false);
  // ...
}
```

### Performance Targets
- **First Contentful Paint:** < 1.5s
- **Time to Interactive:** < 3.5s
- **Lighthouse Score:** > 90

### Accessibility Checklist
- [ ] Keyboard navigation for all interactions
- [ ] ARIA labels on all interactive elements
- [ ] Focus visible states
- [ ] Screen reader tested
- [ ] Color contrast ratio > 4.5:1

---

**Document Version:** 2.0  
**Last Updated:** 2024  
**Next Review:** After Phase 2 completion

