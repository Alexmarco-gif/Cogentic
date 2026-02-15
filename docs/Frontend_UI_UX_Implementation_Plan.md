# Frontend Implementation Master Plan: The Cognitive Interface (ESIP)

**Version:** 1.0
**Status:** Approved for Execution
**Theme:** "Clean Intelligence" (Light Mode / Tactical Professional)
**Target Audience:** Enterprise Analysts, Strategy Executives, Decision Makers.

---

## 1. Design Philosophy & System

We are building a **Cognitive Interface**, not a passive dashboard. The UI must feel like a high-end Saas Platform, Not too dashboard centric, analytical and financial terminal met a modern AI assistant—dense with value, but calm in execution.

**Core Tenet:** "Silence until Signal." We do not clutter the screen with decorative charts. We show intelligence only when it matters.

### 1.1 Visual Language (Light Mode)

*   **Backgrounds:**
    *   **Canvas:** `#F8FAFC` (Slate 50) - The base layer.
    *   **Surface:** `#FFFFFF` (Pure White) - Cards, sidebars, panels.
    *   **Active/Highlight:** `#F1F5F9` (Slate 100) - Hover states.
*   **Typography:**
    *   **Headings:** `Inter` (or `Geist Sans`). Weights: 400 (Regular), 500 (Medium). *No bold shouting.* Color: `#0F172A` (Slate 900).
    *   **Body:** `Inter`. Color: `#334155` (Slate 700).
    *   **Data / Signals / IDs:** `JetBrains Mono` or `Geist Mono`. Color: `#475569` (Slate 600).
*   **Borders & Dividers:**
    *   Subtle, crisp lines: `#E2E8F0` (Slate 200).
    *   *Rule:** No muddy greys. Crisp definition.
*   **Shadows (Depth):**
    *   **Layer 1 (Cards):** `0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)` (Subtle lift).
    *   **Layer 2 (Dropdowns/Modals):** `0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)` (Distinct separation).
*   **Color Palette (Semantic):**
    *   **Primary (Action):** `#4F46E5` (Indigo 600) - Buttons, active tabs.
    *   **Success (High Confidence):** `#059669` (Emerald 600) - Backgrounds: `#ECFDF5`.
    *   **Warning (Volatility):** `#D97706` (Amber 600) - Backgrounds: `#FFFBEB`.
    *   **Critical (Risk):** `#E11D48` (Rose 600) - Backgrounds: `#FFF1F2`.
    *   **Neutral (Info):** `#64748B` (Slate 500).

---

## 2. Global App Shell (The "Cockpit")

The shell provides stability while content changes. It must be responsive Saas Platform in a modernic way and "app-like" (PWA), not "website-like".

### 2.1 Navigation Rail (Left)
*   **State:** Collapsed by default (64px width) to maximize data visibility. Expands on hover/click to 240px.
*   **Styling:** Pure White (`#FFFFFF`), Border-Right (`#E2E8F0`).
*   **Content:**
    1.  **Logo:** Minimalist abstract symbol (Indigo).
    2.  **Primary Nav:**
        *   **Home** (Icon: `LayoutGrid`) - The Feed.
        *   **Investigate** (Icon: `Search` or `Sparkles`) - Deep Search & Chat.
        *   **Signals** (Icon: `Activity`) - Watchlist/Data Grid.
        *   **Domains** (Icon: `Globe` or `Map`) - Geospatial/Sector Maps.
        *   **Library** (Icon: `BookOpen`) - Saved Briefs.
    3.  **Footer:** Settings, User Profile (Avatar/User Image), Notification, Dark and White theme icon and Log out
*   **Interaction:**
    *   *Hover:* Item background becomes `#F1F5F9`. Text turns Indigo.
    *   *Active:** Indigo vertical bar on the left edge. Icon becomes Indigo.

### 2.2 Omni-Command Bar (Top)
*   **Height:** 64px. Sticky.
*   **Styling:** Transparent/Glassmorphic (backdrop-blur) over the page content. Border-Bottom (`#E2E8F0`).
*   **Components:**
    *   **Center:** The "Command Input".
        *   *Visual:* A wide input field (max-width 600px). Background `#F1F5F9`. No border. Rounded `8px`.
        *   *Placeholder:* "Ask about market trends, specific entities, or press '/' for commands..."
        *   *Behavior:* Typing triggers a Spotlight-style dropdown.
    *   **Right:**
        *   **System Status:** "Data Freshness: Live" (Green dot).
        *   **Notification Bell:** For critical alerts.

---

## 3. Page Specifications

### 3.1 HOME: The "Intelligence Feed"
**Goal:** Situation Awareness. Answer "What do I need to know right now?" in 30 seconds.
**Layout:** Single Central Feed (max-width 800px) + Right Sidebar (Context).

*   **A. The "Morning Brief" (Hero Section)**
    *   **Visual:** Clean typography block. No boxes.
    *   **Content:** "Good Morning, (User Name). There are **3 Critical Impact** affecting The **Domain** portfolio today. The CBN rate hike is projected to impact fertilizer costs by +12%."(this will always update every 2 hrs or 1hrs to different domains that are high impact and freshness that has effect)
    *   **Typography:** `H1` equivalent. Light weight (300). Large (24px+). Important entities are highlighted in Indigo text.
    *   **Interaction:** Clicking "CBN rate hike" deep-links to that specific signal's Dossier.

*   **B. The Signal Stream (Feed)**
    *   **Component: `SignalCard`**
        *   **Container:** White card. `border: 1px solid #E2E8F0`. Shadow-sm. Rounded-lg.
        *   **Header:**
            *   Left: Entity Icon + Name ("Dangote Cement") + Domain Tag ("FMCG").
            *   Right: "2h ago" + Confidence Badge (Green pill "89%").
        *   **Body:**
            *   **Headline:** Bold, 16px. "Price deviation > 15% detected in Kano market."
            *   **Summary:** 2 lines of grey text explaining *why*.
            *   **Sparkline:** A subtle SVG line chart *behind* the text or at the bottom, showing the trend.
        *   **Footer Actions:** (Visible on Hover)
            *   "Synthesize" (Magic Wand icon), "Share", "Dismiss".
    *   **Interaction:** Clicking the card opens the **Signal Dossier Drawer** (Slide-over from right).

*   **C. The "Moat" Widget (Right Sidebar)**
    *   **Visual:** Sticky card.
    *   **Content:** "Proprietary Data Ingest." A live counter. "15,420 unique data points processed today."
    *   **Purpose:** Reinforce value proposition, knowledge, and must know value.

*   **Brief Structure:**
      • Title + BLUF
      • Argument + Evidence (structured, sourced)
      • Outlook & Implications(What is likely next), (and what this means to read)
      • Decision Lens: "What this means for you" panel
---

### 3.2 INVESTIGATE: The "War Room"
**Goal:** Active Analysis. Deep Dive.
**Layout:** Split Screen (Left: Chat/Input, Right: Dynamic Context).

*   **A. Left Pane: The Conversation (Chat)**
    *   **Width:** 40-50%.
    *   **Design:** Clean message list.
        *   **User:** Right aligned. Indigo background (`#4F46E5`), White text. Rounded corners (standard chat bubble).
        *   **System:** Left aligned. Grey background (`#F1F5F9`), Dark text. Markdown support (tables, lists).
    *   **Input Area:** Sticky at bottom. Large text area. "Send" button.

*   **B. Right Pane: The "Evidence Board" (Dynamic)**
    *   **Behavior:** This panel morphs based on the conversation context.
    *   **State 1: "Thinking" (Process Visualization)**
        *   *Visual:* A checklist appearing in real-time.
        *   "Searching 12 sources..." (Spinner -> Checkmark).
        *   "Reading 'CBN Monetary Policy PDF, web, search'..." (Spinner -> Checkmark).
        *   "Synthesizing answer..."
        *   *Purpose:* Radical transparency. Shows work.
    *   **State 2: "Citations" (Document View)**
        *   *Visual:** When the AI cites a source `[1]`, this pane shows the source document snippet.
        *   *Feature:** Highlight the exact paragraph used.
    *   **State 3: "Graph" (Relationship View)**
        *   *Visual:** Interactive Node Graph (React Flow).
        *   *Content:** Shows connections between entities discussed (e.g., "Dangote" <-> "Supplier X").
    *   **State 4: Visualizations (Turn data signal or information into visual)**
        *   *This turn the user query if query visulization and chart it gives simple and clean chart with nice color
        *   * Uses charts to give and explain meaningful and important information to users with the visual
        *   * Visuals are not always compulsory they are optional support
        *   * Only when a user query really need cahrt to convey informations (Finances, comparison, analytics etc)

---

### 3.3 SIGNALS: The "Data Grid"
**Goal:** Monitoring, Sorting, Filtering.
**Layout:** High-density Table.

*   **The Grid:**
    *   **Container:** White surface. No outer borders.
    *   **Headers:** Sticky top. Uppercase. Text-xs. Slate-500. Sortable indicators.
    *   **Rows:**
        *   **Height:** Compact (48px).
        *   **Hover:** `#F8FAFC`.
        *   **Columns:**
            1.  **Entity:** Name + Logo, Icons.
            2.  **Signal:** Description ("Price Surge").
            3.  **Trend:** Micro-sparkline (Red/Green).
            4.  **Driver:** Icon showing causality (e.g., Rain Cloud -> Dollar Sign).
            5.  **Confidence:** Circular progress ring (Green/Yellow/Red).
            6.  **Action:** "View" button.
*   **Interaction:**
    *   Clicking a row opens the **Signal Dossier Drawer** (same as Home feed).
*   **Layout:**
    * For the Information in the Signal card when click it should be in this format:
*    **Brief Structure:**
      • Title + BLUF
      • Argument + Evidence (structured, sourced)
      • Outlook & Implications(What is likely next), (and what this means to read)
      • Decision Lens: "What this means for you" panel
---

### 3.4 DOMAINS: The "God View"
**Goal:** Spatial & Sector Intelligence.
**Layout:** Full-screen Map with Floating Controls.

*   **The Map Canvas:**
    *   **Tech:** Mapbox GL or Leaflet.
    *   **Style:** Custom Light Mode style (Desaturated land, crisp borders).
    *   **Layers:**
        *   **Heatmaps:** Risk intensity (Red), Opportunity (Green).
        *   **Pins:** Specific assets (Factories, Ports, Markets).
*   **Floating Control Panel (Top Right):**
    *   **Visual:** Glassmorphic card.
    *   **Tabs:** "Domain", "Title".
    *   **Filters:** Toggle switches for specific layers ("Show Drought Risk", "Show Price Spreads").
*   **Interaction:**
    *   Clicking a region (e.g., "Kano State") opens a Popover Summary card: "Regional Risk: High. Driver: Fuel Costs."
    *   Clicking a region shows not just a summary card only also image related to that summary gotten from the search or online
    *   Clicking the region gives the latest discovery in that region

---

### 3.5 LIBRARY: The "Institutional Memory"
**Goal:** Retrieval & Synthesis of past reports.
**Layout:** Masonry Grid.

*   **The Brief Card:**
    *   **Visual:** Vertical card Horinzontal in a masonry grid form(Paper aspect ratio).
    *   **Top Section:** Generative abstract pattern (pastel colors) based on the topic.
    *   **Title:** Serif font (`Merriweather` or similar). "Impact of Fuel Subsidy Removal on Q3 Agri-Yields."
    *   **Meta:** Date, Author (AI/User), Tags.
*   **Interaction:**
    *   **Reading Mode:** Clicking a card opens a Centered Modal (Reader View).
    *   **Reader View:** Minimalist. Wide margins. Serif font. Like a Medium article or PDF report. Distraction-free.
*   **The weekly report:**
    *   **Struture weekly report:** in a format that can be posted or share on social media, New Networks
    *   **The struture:** This should be in a consultant explantory format in micskinsey style format
    *   **Visuals:** with the use of chart, icons, typography, nice color pallate
    *

---

## 4. Component Architecture (Technical)

*   **Framework:** Next.js 14 (App Router).
*   **Styling:** Tailwind CSS.
*   **UI Library:** Shadcn/UI (Headless components, heavily styled).
*   **Icons:** Lucide React (Thin stroke, consistent).
*   **Data Viz:** Recharts (Sparklines), React Flow (Node Graphs).
*   **Maps:** Pigeon Maps or Leaflet (Lightweight).

### Key Reusable Components
1.  `@/components/ui/Shell.tsx`: The layout wrapper (Sidebar + Header).
2.  `@/components/signals/SignalCard.tsx`: The feed item.
3.  `@/components/investigate/ChatInterface.tsx`: The split-screen chat.
4.  `@/components/visualizations/TrendLine.tsx`: The micro-sparkline.
5.  `@/components/visualizations/EntityGraph.tsx`: The node graph.

---

## 5. Interaction Design & Motion

We use motion to convey **state**, not just for decoration.

*   **Transitions:**
    *   Page transitions: Subtle fade-in + slide-up (10px).
    *   Drawer open: Smooth slide from right (`ease-out-expo`).
*   **Loading States:**
    *   Never use a generic full-screen spinner.
    *   Use **Skeleton Loaders** (shimmer effect) to match the exact shape of the content (Card skeleton, Table row skeleton).
    *   For AI actions, use **Text Streaming** (typewriter effect) to reduce perceived latency.
*   **Micro-interactions:**
    *   *Hover:* Buttons lift slightly (transform: translateY(-1px)).
    *   *Click:* Buttons press down slightly (transform: scale(0.98)).
    *   *Confidence Reveal:* Hovering a confidence badge breaks down the score ("Source: High, Freshness: Low").

---

## 6. Design Reference Guide (Visual Direction)

**CRITICAL INSTRUCTION FOR AI AGENTS:**
The following local images (located in the `Wire` folder) are the **primary visual truth** for the ESIP platform.
- **Do NOT copy these images literally.**
- **DO use them as a guide** for spatial arrangement, component scaling, border radius, shadow depth, and the "Clean Intelligence" styling.
- Ensure the final implementation adheres to the Light Mode theme and the technical constraints defined in this document.

### 6.1 Global Shell (Sidebar & Nav)
*   **Primary Ref:** `Wire/1 (7).JPG` - *Note the minimal sidebar, active state styling, and clean "Settings" popover.*
*   **Secondary Ref:** `Wire/1 (36).webp` - *Good reference for active state styling, and clean "Settings" popover in the sidebar.*

### 6.2 Home Page (The Intelligence Feed)
*   **Primary Ref:** `Wire/1 (1).jpg` - *Use the "Hello Moni" section as inspiration for the "Morning Brief". Note the clean card shadows and badge styling.*
*   **Feed Layout Ref:** `1 (1).webp` - *The "Activity Tracker" on the right is the exact density we want for the Signal Stream.*
*   **Signal card Ref:** `Wire/1 (2).webp` - *This is the ideal design for the SignalCard component: clean, with a subtle sparkline and clear metadata, and the card layout and design and struture.*

### 6.3 Investigation / War Room
*   **GOLD STANDARD Ref:** `Wire/1 (18).webp` - *This "Terminal + Copilot" split view is exactly how the Investigate page should function. Data on left, Chat on right.*
*   **Chat Ref:** `Wire/1 (1).webp` - *Use the left-side chat bubbles for the message styling.*

### 6.4 Signals Data Grid
*   **Primary Ref:** `Wire/1 (13).webpp` - *Clean table layout. Note how status pills (Green/Red) are used. Copy this row density, filtering style.*
*   **Detail View Ref:** `Wire/1 (17).webp` - *When a user clicks a row, the drawer content should look like this (structured data, clearly labeled) with the use of colors and chats, and strutures.*

### 6.5 Domain Maps
*   **Primary Ref:** `Wire/11 (2).webp` - *Look at the "Geo-Traffic Overview" map. Use this style: desaturated map tiles, bright data points, floating overlay cards.*
*   **Secondary Ref:** `Wire/11 (1).webp` - *when a users hover over a map it should look like this (image card hover effect with short paragraph then an ellipsis) the image should relate to what is been viewed "If it about marketing showing marketing image, if it about cooperate organization show related image gotten from the web" this is another good reference for the map styling and visualization approach.*

### 6.6 Library / Briefs
*   **Primary Ref:** `Wire/1 (25).webp` - *Grid of cards. Replace progress bars with "Relevance Score" or similar metadata.*

### 6.7 Setting
*   **Primary Ref:** `Wire/1 (1).jpeg` - Use the layout struture and style


---

**Execution Priority:**
1.  **Shell:** Build the Sidebar and Header layouts.
2.  **Home:** Implement the Feed and Signal Card.
3.  **Investigate:** Build the Chat UI and Split pane.
4.  **Signals/Domains/Library:** Build remaining specialized views.
5.  **Setting/Profile/Notification:** Build the setting page and profile page with the use of the reference image for the setting page and profile page.


custom contract find it in the pricing document, tell gemini that how do we go about the ui for that
