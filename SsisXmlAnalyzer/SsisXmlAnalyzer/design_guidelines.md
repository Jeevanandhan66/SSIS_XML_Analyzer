# SSIS DTSX Workflow Analyzer - Design Guidelines

## Design Approach

**Selected System:** Carbon Design System
**Rationale:** Enterprise-grade design system optimized for data-heavy applications with complex information hierarchies. Carbon excels at technical tools requiring clear data visualization, structured content display, and professional aesthetics suitable for data engineering workflows.

**Core Principles:**
- Clarity over decoration - every element serves the data
- Structured information hierarchy for complex technical details
- Scannable layouts optimizing for information density
- Professional, no-nonsense aesthetic for technical users

---

## Typography System

**Font Family:** IBM Plex Sans (via Google Fonts CDN)
- Primary: IBM Plex Sans (body text, UI elements)
- Monospace: IBM Plex Mono (code, technical identifiers, XML paths)

**Type Scale:**
- Page Title: text-3xl font-semibold (activity flow viewer)
- Section Headers: text-xl font-semibold (workflow stages, connection managers)
- Card/Panel Titles: text-lg font-medium (individual activities)
- Body Text: text-sm (descriptions, properties)
- Technical Details: text-xs font-mono (XML paths, IDs, connection strings)
- Labels: text-xs font-medium uppercase tracking-wide (metadata labels)

---

## Layout System

**Spacing Primitives:** Tailwind units of **2, 4, 6, 8** (p-2, p-4, p-6, p-8, gap-4, space-y-6, etc.)

**Grid Structure:**
- Main layout: Two-panel split (30% sidebar / 70% main content) on desktop
- Mobile: Single column stack
- Activity cards grid: grid-cols-1 on mobile, stays single column on desktop for timeline clarity
- Property details: 2-column grid (label/value pairs) using grid-cols-2 gap-4

**Container Widths:**
- Full app container: w-full h-screen (fixed viewport app)
- Content max-width: No max-width constraints (use full available space)
- Property panels: Full width of parent container

---

## Component Library

### Navigation & Structure
**Top Header Bar:**
- Height: h-14
- Contains: App logo/title, upload button (primary action), settings icon
- Fixed position with subtle border-bottom
- Layout: flex justify-between items-center px-6

**Left Sidebar Panel:**
- File upload dropzone area at top (h-32)
- List of parsed workflow activities below
- Scrollable content area
- Each activity item shows: icon, activity name, activity type badge
- Active selection state for currently viewed activity

### File Upload Component
**Upload Dropzone:**
- Dashed border, rounded-lg
- Center-aligned icon (upload cloud) and instructional text
- "Browse files" button below
- Accepts .xml and .dtsx file extensions
- Shows file name and size after upload with remove option

### Workflow Visualization
**Activity Timeline/Flow:**
- Vertical timeline layout (not horizontal flowchart)
- Each activity as card with connector lines between them
- Card structure: Icon (left) | Activity Name & Type | Expand arrow (right)
- Padding: p-4
- Spacing between cards: space-y-4
- Execution order numbers displayed prominently (01, 02, 03...)

**Activity Type Indicators:**
- Small badge chips showing: "Data Flow Task", "Execute SQL", "Script Task", etc.
- Rounded-full px-3 py-1 text-xs

### Information Display
**Activity Detail Panel:**
- Expandable/collapsible accordion sections
- Sections: Overview, Properties, Connections, Components (for data flows), Column Mappings
- Each section header: text-sm font-semibold with chevron icon
- Section content padding: p-4
- Property rows in 2-column grid format

**Data Tables:**
- Compact tables for column mappings, component details
- Header: bg-muted with font-medium text-xs
- Rows: hover states, text-sm
- Cell padding: px-4 py-2
- Borders between rows

**Property Display Pattern:**
```
Label (uppercase, text-xs, font-medium, text-muted-foreground)
Value (text-sm, font-mono for technical values)
Vertical spacing: space-y-1 per property pair
```

### Interactive Elements
**Search/Filter Bar:**
- Input field with search icon prefix
- Placeholder: "Search activities..."
- Width: w-full in sidebar
- Padding: px-3 py-2
- Margin: mb-4

**Buttons:**
- Primary (Upload file): px-4 py-2 rounded-md font-medium
- Secondary (Clear, Reset): px-3 py-1.5 text-sm
- Icon buttons (expand/collapse): p-2 rounded

**Icons:** Use Heroicons via CDN
- Essential icons: DocumentArrowUpIcon, ChevronDownIcon, ChevronRightIcon, MagnifyingGlassIcon, XMarkIcon
- Activity type icons: CircleStackIcon (database), CodeBracketIcon (script), ArrowPathIcon (data flow)

---

## Layout Patterns

### Main Application Layout
```
Fixed Header (h-14)
├── Logo/Title (left)
└── Upload Button (right)

Body (flex h-[calc(100vh-3.5rem)])
├── Sidebar (w-80, border-right, scrollable)
│   ├── Upload Dropzone (sticky top)
│   ├── Search Bar
│   └── Activity List (scrollable)
└── Main Content (flex-1, scrollable)
    ├── Workflow Overview Header
    ├── Activity Timeline (if overview mode)
    └── Activity Detail View (if activity selected)
```

### Activity Card Pattern
- Border rounded-lg with subtle shadow
- Hover: slight shadow increase
- Selected state: border accent
- Internal padding: p-4
- Icon container: w-10 h-10 rounded bg-muted flex items-center justify-center

### Empty States
- Center-aligned icon, heading, description
- "Upload DTSX file to begin" when no file loaded
- "No activities found" if parse returns empty

---

## Responsive Behavior

**Desktop (lg+):** Two-panel layout as described
**Tablet (md):** Sidebar collapses to drawer, toggle button in header
**Mobile (base):** Full-width stack, upload at top, activities list below, detail view in modal/drawer

**Spacing Adjustments:**
- Desktop: p-6 for main containers, p-4 for cards
- Mobile: p-4 for main containers, p-3 for cards

---

## Information Hierarchy

**Priority 1 (Immediately Visible):**
- Activity execution sequence
- Activity names and types
- Number of activities in workflow

**Priority 2 (One Click Away):**
- Activity properties and configurations
- Connection details
- Component information

**Priority 3 (Expandable Details):**
- Column mappings
- Transformation logic
- Technical identifiers and paths

---

## Key UX Patterns

- **Progressive Disclosure:** Collapsed by default, expand for details
- **Persistent Context:** Show workflow overview while viewing individual activities
- **Technical Precision:** Use monospace fonts for all technical identifiers, paths, SQL snippets
- **Scanability:** Clear visual separation between different data types using typography and spacing
- **Status Communication:** Loading states during parse, success/error messages for file upload