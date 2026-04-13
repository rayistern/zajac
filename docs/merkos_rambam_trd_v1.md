# Technical Requirements Document

## Merkos Rambam Learning Platform

| | |
|---|---|
| **Owner** | Rayi Stern |
| **Department** | Merkos 302 / ChabadAI |
| **Status** | Pre-Development |
| **Date** | February 2026 |
| **Version** | 1.0 |
| **Related PRD** | merkos_rambam_prd_v3.md |

---

## 1. Executive Summary

This TRD defines the technical architecture, tooling selections, and implementation approach for the Merkos Rambam Learning Platform. The architecture prioritizes:

- **Open source and reusable components** where quality and support are comparable
- **Hosted/managed services** to minimize operational overhead for a solo developer
- **Glue code architecture** — connecting best-in-class services rather than building custom infrastructure
- **Maintainability and updateability** through industry-standard patterns and documentation

The system is designed to be built and maintained by a single developer leveraging AI-assisted development, with the flexibility to scale if the project succeeds.

---

## 2. Architecture Overview

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLIENT LAYER                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│  PWA (Next.js)  │  WhatsApp  │  Social Share Cards  │  Future: Native Apps  │
└────────┬────────┴─────┬──────┴──────────┬───────────┴──────────────────────-┘
         │              │                 │
         ▼              ▼                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              API LAYER                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│  Next.js API Routes  │  Edge Functions  │  Webhook Handlers                 │
└────────┬─────────────┴────────┬─────────┴────────┬──────────────────────────┘
         │                      │                  │
         ▼                      ▼                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SERVICE LAYER                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│  Sefaria API   │  PortKey/LLM  │  Image Gen  │  WhatsApp API  │  Analytics  │
│  (Rambam text) │  (via Anthropic)│  (Replicate) │  (Twilio)    │  (PostHog)  │
└────────┬───────┴───────┬───────┴──────┬───────┴───────┬───────┴──────┬──────┘
         │               │              │               │              │
         ▼               ▼              ▼               ▼              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            DATA LAYER                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│  Supabase (PostgreSQL)  │  Cloudflare R2 (Assets)  │  Upstash Redis (Cache) │
└─────────────────────────┴──────────────────────────┴────────────────────────┘
```

### 2.2 Design Principles Applied

| Principle | Implementation |
|-----------|----------------|
| **Open source preference** | Next.js, PostgreSQL, PostHog, Sentry — all open source with managed hosting options |
| **Hosted services** | Vercel, Supabase, Cloudflare, Upstash — all managed, no servers to maintain |
| **Glue code architecture** | <50% custom code; majority is configuration and integration |
| **Maintainability** | TypeScript throughout, conventional patterns, comprehensive documentation |

---

## 3. Technology Stack

### 3.1 Core Stack Selection

| Layer | Technology | Rationale | Alternative Considered |
|-------|------------|-----------|------------------------|
| **Frontend Framework** | Next.js 14+ (App Router) | Industry standard, excellent PWA support, built-in SSR/SSG for SEO, RTL support | Remix, Nuxt |
| **Language** | TypeScript | Type safety, better tooling, maintainability | JavaScript |
| **Styling** | Tailwind CSS + Radix UI | Utility-first, RTL support via `rtl:` variants, accessible primitives | CSS Modules, Chakra |
| **Database** | Supabase (PostgreSQL) | Open source core, managed hosting, real-time, auth built-in, generous free tier | PlanetScale, Neon |
| **File Storage** | Cloudflare R2 | S3-compatible, no egress fees, global CDN | AWS S3, Supabase Storage |
| **Cache** | Upstash Redis | Serverless Redis, pay-per-request, global replication | Vercel KV |
| **Hosting** | Vercel | Optimal Next.js support, edge functions, preview deployments | Netlify, Railway |
| **Domain/DNS** | Cloudflare | Free tier adequate, excellent DDoS protection, analytics | Vercel DNS |

### 3.2 External Services

| Service | Provider | Purpose | Pricing Model |
|---------|----------|---------|---------------|
| **Rambam Text** | Sefaria API | Canonical text source with halacha indexing | Free / Open source |
| **LLM Routing** | PortKey | Model flexibility, fallbacks, cost tracking | Usage-based |
| **Primary LLM** | Anthropic Claude | Text generation, content creation | Usage-based |
| **Image Generation** | Replicate (SDXL/Flux) | Open source models, pay-per-image | ~$0.003/image |
| **WhatsApp** | Twilio WhatsApp API | Business API wrapper, reliable delivery | ~$0.005/message + Meta fees |
| **Analytics** | PostHog Cloud | Open source, self-hostable option, privacy-focused | Free <1M events/mo |
| **Error Tracking** | Sentry | Industry standard, excellent Next.js integration | Free tier adequate |
| **Uptime Monitoring** | Better Uptime | Simple, affordable, good Slack integration | Free tier adequate |

### 3.3 Development Tools

| Tool | Purpose | Cost |
|------|---------|------|
| **GitHub** | Repository, CI/CD via Actions, Issues for tracking | Free |
| **Linear** | Issue tracking (if GitHub Issues insufficient) | Free for small teams |
| **Notion** | Editorial workflow, documentation, volunteer coordination | Free |
| **Figma** | Design mockups, component library | Free tier |
| **Claude Code** | AI-assisted development | Included with Anthropic subscription |

---

## 4. Data Architecture

### 4.1 Database Schema (Supabase/PostgreSQL)

```sql
-- Core content tables
CREATE TABLE tracks (
  id TEXT PRIMARY KEY,  -- '1-perek', '3-perek'
  name TEXT NOT NULL,
  description TEXT
);

CREATE TABLE learning_days (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  date DATE NOT NULL UNIQUE,
  hebrew_date TEXT,
  track_1_perakim JSONB NOT NULL,  -- [{sefer, perek, halachos: [start, end]}]
  track_3_perakim JSONB NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE content_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  learning_day_id UUID REFERENCES learning_days(id),
  content_type TEXT NOT NULL,  -- 'conceptual_image', 'infographic', 'perek_overview', 'did_you_know', 'sichos_highlight', 'daily_chart'
  sefer TEXT NOT NULL,
  perek INTEGER NOT NULL,
  halacha_start INTEGER,
  halacha_end INTEGER,
  
  -- Content payload
  title TEXT,
  content JSONB NOT NULL,  -- Flexible structure per content_type
  image_url TEXT,
  thumbnail_url TEXT,
  
  -- Editorial
  status TEXT DEFAULT 'draft',  -- 'draft', 'pending_review', 'approved', 'published', 'rejected'
  reviewed_by TEXT[],
  review_notes TEXT,
  published_at TIMESTAMPTZ,
  
  -- Metadata
  generation_model TEXT,
  generation_prompt_hash TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Sichos mapping (structured data, not AI-generated)
CREATE TABLE sichos_references (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  sefer TEXT NOT NULL,
  perek INTEGER NOT NULL,
  halacha INTEGER NOT NULL,
  source_volume TEXT NOT NULL,  -- e.g., 'Likkutei Sichos Vol. 19'
  source_page TEXT,
  source_url TEXT,
  excerpt TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- User preferences (minimal, privacy-respecting)
CREATE TABLE user_preferences (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  device_id TEXT UNIQUE,  -- Anonymous device identifier
  track TEXT DEFAULT '3-perek',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Analytics events supplement (PostHog is primary)
CREATE TABLE share_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  content_item_id UUID REFERENCES content_items(id),
  platform TEXT,  -- 'whatsapp', 'twitter', 'copy_link'
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- WhatsApp subscribers
CREATE TABLE whatsapp_subscribers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  phone_hash TEXT UNIQUE NOT NULL,  -- Hashed for privacy
  track TEXT DEFAULT '3-perek',
  subscribed_at TIMESTAMPTZ DEFAULT NOW(),
  unsubscribed_at TIMESTAMPTZ,
  status TEXT DEFAULT 'active'
);

-- Indexes
CREATE INDEX idx_content_items_day ON content_items(learning_day_id);
CREATE INDEX idx_content_items_status ON content_items(status);
CREATE INDEX idx_content_items_type ON content_items(content_type);
CREATE INDEX idx_sichos_refs ON sichos_references(sefer, perek, halacha);
CREATE INDEX idx_learning_days_date ON learning_days(date);
```

### 4.2 Content Storage Strategy

| Content Type | Storage Location | Caching Strategy |
|--------------|------------------|------------------|
| **Rambam text** | Fetched from Sefaria, cached in Redis (24h TTL) | Edge cache + Redis |
| **Generated images** | Cloudflare R2 with CDN | Immutable, infinite cache |
| **Thumbnails** | Cloudflare R2 (auto-generated via Image Resizing) | Same as images |
| **Watermarked shares** | Generated on-demand, cached 1h | Edge function + R2 |
| **Content metadata** | Supabase PostgreSQL | 5-minute TTL at edge |

### 4.3 Data Flow

```
1. INGESTION (Daily, Automated)
   Sefaria API → Parse perakim → Identify halachos → Store in learning_days

2. GENERATION (Daily, Automated)
   learning_days → Content pipelines → Draft content_items
   
3. REVIEW (Daily, Human)
   Draft items → Notion review queue → Approved/Rejected → Update status
   
4. PUBLICATION (Daily, Automated)
   Approved items → Apply watermarks → Upload to R2 → Update status → Trigger WhatsApp
   
5. DELIVERY
   Web: Next.js SSG → Vercel Edge → User
   WhatsApp: Twilio API → WhatsApp servers → User
```

---

## 5. Frontend Architecture

### 5.1 Application Structure

```
/app
├── (marketing)
│   ├── page.tsx              # Landing page
│   └── about/page.tsx        # About page
├── (app)
│   ├── layout.tsx            # App shell with track selector
│   ├── page.tsx              # Today's learning (redirect to /day/today)
│   ├── day/
│   │   └── [date]/page.tsx   # Daily content view
│   ├── perek/
│   │   └── [sefer]/[perek]/page.tsx  # Individual perek deep-dive
│   └── share/
│       └── [contentId]/page.tsx      # Share card generator
├── api/
│   ├── content/route.ts      # Content API
│   ├── share/route.ts        # Share image generation
│   ├── webhook/
│   │   └── whatsapp/route.ts # WhatsApp webhook handler
│   └── cron/
│       ├── generate/route.ts # Trigger content generation
│       └── publish/route.ts  # Trigger publication
├── globals.css
└── layout.tsx                # Root layout with providers

/components
├── ui/                       # Radix-based primitives
├── content/
│   ├── RambamText.tsx        # Halacha-indexed text display
│   ├── ConceptualImage.tsx   # Image with caption
│   ├── Infographic.tsx       # Structured visual
│   ├── SichosHighlight.tsx   # Sichos reference card
│   ├── PerekOverview.tsx     # Summary component
│   └── ShareCard.tsx         # Branded share card
├── navigation/
│   ├── TrackSelector.tsx     # 1-perek / 3-perek toggle
│   ├── DayNavigator.tsx      # Previous/Next day
│   └── Header.tsx
└── share/
    └── ShareButton.tsx       # Multi-platform share

/lib
├── sefaria.ts               # Sefaria API client
├── content.ts               # Content fetching/caching
├── share.ts                 # Share URL generation
├── analytics.ts             # PostHog wrapper
└── utils.ts                 # Shared utilities

/hooks
├── useTrack.ts              # Track preference (localStorage + cookie)
├── useHebrewDate.ts         # Hebrew date utilities
└── useLearningDay.ts        # Current day content
```

### 5.2 PWA Configuration

```typescript
// next.config.js
const withPWA = require('next-pwa')({
  dest: 'public',
  register: true,
  skipWaiting: true,
  disable: process.env.NODE_ENV === 'development'
});

module.exports = withPWA({
  // ... other config
});

// public/manifest.json
{
  "name": "Merkos Rambam",
  "short_name": "Rambam",
  "description": "Daily Rambam learning with AI-generated visual content",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#ffffff",
  "theme_color": "#1a365d",
  "dir": "auto",
  "icons": [
    { "src": "/icons/icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/icons/icon-512.png", "sizes": "512x512", "type": "image/png" }
  ]
}
```

### 5.3 RTL Support Strategy

```typescript
// app/layout.tsx
import { IBM_Plex_Sans_Hebrew } from 'next/font/google';

const hebrewFont = IBM_Plex_Sans_Hebrew({
  subsets: ['hebrew'],
  weight: ['400', '500', '600', '700'],
  variable: '--font-hebrew'
});

export default function RootLayout({ children }) {
  return (
    <html lang="he" dir="rtl" className={hebrewFont.variable}>
      <body>{children}</body>
    </html>
  );
}

// Tailwind RTL utilities (tailwind.config.js)
module.exports = {
  plugins: [
    require('tailwindcss-rtl'),  // Adds rtl: and ltr: variants
  ],
};

// Usage in components
<div className="mr-4 rtl:mr-0 rtl:ml-4">
  {/* Automatic margin flip for RTL */}
</div>
```

### 5.4 Offline Support

```typescript
// Service worker strategy
// - Cache static assets (immutable)
// - Cache today's content on first load
// - Cache previous 7 days for offline access
// - Network-first for fresh content, fallback to cache

// lib/offline.ts
export async function precacheDay(date: string) {
  const cache = await caches.open('rambam-content-v1');
  const contentUrls = await getContentUrlsForDay(date);
  await cache.addAll(contentUrls);
}
```

---

## 6. Content Generation Pipeline

### 6.1 Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CONTENT GENERATION PIPELINE                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌───────────┐  │
│  │   INGEST     │───►│   ANALYZE    │───►│   GENERATE   │───►│   STORE   │  │
│  │              │    │              │    │              │    │           │  │
│  │ Sefaria API  │    │ LLM: Claude  │    │ Visual: SDXL │    │ Supabase  │  │
│  │ Hebrew Date  │    │ Complexity   │    │ Text: Claude │    │ R2 (imgs) │  │
│  │ Schedule     │    │ Detection    │    │ via PortKey  │    │           │  │
│  └──────────────┘    └──────────────┘    └──────────────┘    └───────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           EDITORIAL WORKFLOW                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌───────────┐  │
│  │  QUEUE IN    │───►│   REVIEW     │───►│   APPROVE/   │───►│  PUBLISH  │  │
│  │   NOTION     │    │   (Human)    │    │   REJECT     │    │           │  │
│  │              │    │              │    │              │    │ Watermark │  │
│  │ Webhook      │    │ 3 reviewers  │    │ Notion form  │    │ CDN push  │  │
│  │ Automation   │    │ per item     │    │ → Supabase   │    │ WhatsApp  │  │
│  └──────────────┘    └──────────────┘    └──────────────┘    └───────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 6.2 Generation Scripts

```typescript
// scripts/generate-daily-content.ts
import { SefariaClient } from '@/lib/sefaria';
import { PortKeyClient } from '@/lib/portkey';
import { ReplicateClient } from '@/lib/replicate';
import { supabase } from '@/lib/supabase';

interface GenerationJob {
  date: string;
  track: '1-perek' | '3-perek';
  perakim: PerekReference[];
}

export async function generateDailyContent(job: GenerationJob) {
  const results = [];
  
  for (const perek of job.perakim) {
    // 1. Fetch Rambam text
    const text = await SefariaClient.getPerek(perek.sefer, perek.number);
    
    // 2. Analyze for visual opportunities
    const analysis = await PortKeyClient.analyze({
      model: 'claude-sonnet-4-5-20250929',
      prompt: ANALYSIS_PROMPT,
      content: text,
    });
    
    // 3. Generate content items
    if (analysis.needsVisual) {
      // Generate conceptual image
      const imagePrompt = await PortKeyClient.generateImagePrompt({
        model: 'claude-sonnet-4-5-20250929',
        halacha: analysis.visualHalacha,
        styleGuide: STYLE_GUIDE,
      });
      
      const image = await ReplicateClient.generate({
        model: 'stability-ai/sdxl',
        prompt: imagePrompt,
        negativePrompt: NEGATIVE_PROMPT,
        width: 1024,
        height: 1024,
      });
      
      results.push({
        type: 'conceptual_image',
        content: { prompt: imagePrompt, analysis: analysis.visualRationale },
        imageUrl: await uploadToR2(image),
      });
    }
    
    // 4. Generate text content
    const overview = await PortKeyClient.generate({
      model: 'claude-sonnet-4-5-20250929',
      prompt: OVERVIEW_PROMPT,
      content: text,
    });
    
    results.push({
      type: 'perek_overview',
      content: { text: overview, perek: perek },
    });
    
    // 5. Generate "did you know"
    const didYouKnow = await PortKeyClient.generate({
      model: 'claude-sonnet-4-5-20250929',
      prompt: DID_YOU_KNOW_PROMPT,
      content: text,
    });
    
    results.push({
      type: 'did_you_know',
      content: { text: didYouKnow },
    });
  }
  
  // 6. Store all items as drafts
  await supabase.from('content_items').insert(
    results.map(r => ({
      ...r,
      learning_day_id: job.learningDayId,
      status: 'pending_review',
    }))
  );
  
  // 7. Trigger Notion workflow
  await notifyNotionReviewQueue(job.date, results.length);
}
```

### 6.3 Image Generation Prompts

```typescript
// lib/prompts/image-generation.ts

export const STYLE_GUIDE = `
You are creating educational illustrations for a Torah learning platform.

STYLE REQUIREMENTS:
- Clean, professional illustration style
- Muted, dignified color palette (no garish colors)
- No depictions of faces or human figures (Jewish artistic tradition)
- Architectural and object-focused compositions
- Clear visual hierarchy
- Suitable for both digital and print

CONTENT REQUIREMENTS:
- Historically accurate where depicting Temple/ancient items
- Clearly labeled measurements when relevant
- Respectful of subject matter (holy objects, mitzvos)
- Educational purpose evident

AVOID:
- Cartoon or comic styles
- Photorealistic rendering
- Any AI artifacts or distortions
- Modern items anachronistically placed
- Faces, human figures, or anthropomorphization
`;

export const NEGATIVE_PROMPT = `
faces, people, human figures, hands, cartoon, anime, 3d render, 
photorealistic, modern elements, text, watermark, signature, 
distorted, blurry, low quality, nsfw
`;

export const CONCEPTUAL_IMAGE_PROMPT = (halacha: string, context: string) => `
Create an educational illustration for the following Torah concept:

HALACHA: ${halacha}
CONTEXT: ${context}

Generate a detailed image generation prompt that:
1. Captures the key visual elements described in the halacha
2. Uses appropriate scale and perspective for understanding
3. Includes relevant labels or measurements if applicable
4. Follows the style guide provided

Return only the image generation prompt, nothing else.
`;
```

### 6.4 Editorial Workflow (Notion Integration)

```typescript
// lib/notion-workflow.ts
import { Client } from '@notionhq/client';

const notion = new Client({ auth: process.env.NOTION_API_KEY });

const REVIEW_DB_ID = process.env.NOTION_REVIEW_DB_ID;

export async function createReviewTask(item: ContentItem) {
  await notion.pages.create({
    parent: { database_id: REVIEW_DB_ID },
    properties: {
      'Title': { title: [{ text: { content: `${item.type}: ${item.date}` } }] },
      'Content Type': { select: { name: item.type } },
      'Date': { date: { start: item.date } },
      'Status': { status: { name: 'Pending Review' } },
      'Content ID': { rich_text: [{ text: { content: item.id } }] },
      'Preview URL': { url: `${process.env.APP_URL}/preview/${item.id}` },
      'Reviewers': { people: [] },  // Assigned via Notion automation
    },
    children: [
      {
        type: 'embed',
        embed: { url: item.previewUrl },
      },
      {
        type: 'callout',
        callout: {
          icon: { emoji: '✅' },
          rich_text: [{ text: { content: 'Review Checklist' } }],
        },
      },
      // ... review checklist items
    ],
  });
}

// Notion webhook handler (receives review decisions)
export async function handleReviewWebhook(payload: NotionWebhookPayload) {
  const contentId = extractContentId(payload);
  const status = payload.properties['Status'].status.name;
  const reviewers = payload.properties['Reviewers'].people.map(p => p.name);
  const notes = payload.properties['Notes']?.rich_text?.[0]?.text?.content;
  
  if (status === 'Approved') {
    await supabase.from('content_items').update({
      status: 'approved',
      reviewed_by: reviewers,
      review_notes: notes,
    }).eq('id', contentId);
  } else if (status === 'Rejected') {
    await supabase.from('content_items').update({
      status: 'rejected',
      reviewed_by: reviewers,
      review_notes: notes,
    }).eq('id', contentId);
    
    // Optionally trigger regeneration
    if (payload.properties['Regenerate']?.checkbox) {
      await queueRegeneration(contentId);
    }
  }
}
```

---

## 7. API Design

### 7.1 Public API Endpoints

```typescript
// API Routes Structure

// Content Retrieval
GET  /api/content/today                    // Today's content for selected track
GET  /api/content/day/[date]               // Content for specific date
GET  /api/content/perek/[sefer]/[perek]    // Specific perek content
GET  /api/content/item/[id]                // Individual content item

// Rambam Text (cached proxy to Sefaria)
GET  /api/rambam/[sefer]/[perek]           // Full perek text
GET  /api/rambam/[sefer]/[perek]/[halacha] // Individual halacha

// Sichos References
GET  /api/sichos/[sefer]/[perek]           // All sichos for a perek
GET  /api/sichos/[sefer]/[perek]/[halacha] // Sichos for specific halacha

// Sharing
GET  /api/share/[contentId]                // Generate share card image
GET  /api/share/[contentId]/meta           // OG meta for share URLs

// User Preferences
GET  /api/preferences                      // Get current preferences
PUT  /api/preferences                      // Update preferences

// WhatsApp (webhooks)
POST /api/webhook/whatsapp                 // Twilio webhook handler

// Internal/Cron (protected)
POST /api/cron/generate                    // Trigger daily generation
POST /api/cron/publish                     // Trigger publication
POST /api/cron/whatsapp-broadcast          // Send daily WhatsApp
```

### 7.2 API Response Schemas

```typescript
// types/api.ts

interface ContentDay {
  date: string;
  hebrewDate: string;
  track: '1-perek' | '3-perek';
  perakim: PerekContent[];
}

interface PerekContent {
  sefer: string;
  perek: number;
  title: string;
  overview: string;
  halachos: Halacha[];
  contentItems: ContentItem[];
  sichosReferences: SichosReference[];
}

interface Halacha {
  number: number;
  text: string;
  sichosReferences?: SichosReference[];
}

interface ContentItem {
  id: string;
  type: 'conceptual_image' | 'infographic' | 'perek_overview' | 'did_you_know' | 'daily_chart';
  title?: string;
  content: Record<string, any>;
  imageUrl?: string;
  thumbnailUrl?: string;
  shareUrl: string;
}

interface SichosReference {
  id: string;
  halacha: number;
  source: string;
  excerpt?: string;
  url?: string;
}

interface ShareMeta {
  title: string;
  description: string;
  imageUrl: string;
  url: string;
}
```

### 7.3 Caching Strategy

```typescript
// lib/cache.ts
import { Redis } from '@upstash/redis';

const redis = new Redis({
  url: process.env.UPSTASH_REDIS_URL,
  token: process.env.UPSTASH_REDIS_TOKEN,
});

// Cache TTLs
const CACHE_TTLS = {
  rambamText: 60 * 60 * 24,        // 24 hours (rarely changes)
  contentDay: 60 * 5,              // 5 minutes (refreshes after edits)
  sichosRefs: 60 * 60 * 24 * 7,    // 7 days (static data)
  shareImage: 60 * 60,             // 1 hour (generated on demand)
};

export async function getCachedContent<T>(
  key: string,
  fetcher: () => Promise<T>,
  ttl: number
): Promise<T> {
  const cached = await redis.get<T>(key);
  if (cached) return cached;
  
  const fresh = await fetcher();
  await redis.setex(key, ttl, fresh);
  return fresh;
}

// Vercel Edge caching headers
export function cacheHeaders(type: keyof typeof CACHE_TTLS) {
  const ttl = CACHE_TTLS[type];
  return {
    'Cache-Control': `public, s-maxage=${ttl}, stale-while-revalidate=${ttl * 2}`,
  };
}
```

---

## 8. Sharing & Watermarking

### 8.1 Share Card Generation

```typescript
// app/api/share/[contentId]/route.ts
import { ImageResponse } from 'next/og';

export async function GET(
  request: Request,
  { params }: { params: { contentId: string } }
) {
  const content = await getContentItem(params.contentId);
  
  // Generate branded share card
  return new ImageResponse(
    (
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          width: '1200px',
          height: '630px',
          backgroundColor: '#1a365d',
          padding: '40px',
        }}
      >
        {/* Header with branding */}
        <div style={{ display: 'flex', alignItems: 'center', marginBottom: '20px' }}>
          <img src={LOGO_URL} width={60} height={60} />
          <span style={{ color: 'white', fontSize: '24px', marginLeft: '16px' }}>
            Merkos Rambam
          </span>
        </div>
        
        {/* Content area */}
        <div style={{ flex: 1, display: 'flex', gap: '40px' }}>
          {content.imageUrl && (
            <img
              src={content.imageUrl}
              style={{ width: '400px', height: '400px', borderRadius: '12px' }}
            />
          )}
          <div style={{ flex: 1, color: 'white' }}>
            <h1 style={{ fontSize: '36px', marginBottom: '16px' }}>
              {content.title}
            </h1>
            <p style={{ fontSize: '24px', opacity: 0.9 }}>
              {content.excerpt}
            </p>
          </div>
        </div>
        
        {/* Footer with watermark */}
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '20px' }}>
          <span style={{ color: 'white', opacity: 0.7 }}>
            {content.hebrewDate} • {content.sefer} {content.perek}
          </span>
          <span style={{ color: 'white', opacity: 0.7 }}>
            rambam.merkos.com
          </span>
        </div>
      </div>
    ),
    {
      width: 1200,
      height: 630,
    }
  );
}
```

### 8.2 Watermarking Pipeline

```typescript
// lib/watermark.ts
import sharp from 'sharp';

export async function applyWatermark(
  imageBuffer: Buffer,
  options: WatermarkOptions
): Promise<Buffer> {
  const watermarkSvg = generateWatermarkSvg(options);
  
  return sharp(imageBuffer)
    .composite([
      {
        input: Buffer.from(watermarkSvg),
        gravity: 'southeast',
        blend: 'over',
      },
    ])
    .png()
    .toBuffer();
}

function generateWatermarkSvg(options: WatermarkOptions): string {
  return `
    <svg width="300" height="60" xmlns="http://www.w3.org/2000/svg">
      <rect width="300" height="60" fill="rgba(0,0,0,0.5)" rx="8"/>
      <text x="150" y="35" text-anchor="middle" fill="white" font-size="18">
        ${options.siteName} • ${options.date}
      </text>
    </svg>
  `;
}
```

### 8.3 Share URL Structure

```
Share URLs:
- https://rambam.merkos.com/share/[contentId]
  → Renders full share page with OG tags
  → Redirects to main app after preview

OG Tags (for social previews):
- og:title: "Hilchos [Sefer] [Perek]:[Halacha] - Merkos Rambam"
- og:description: [Content excerpt]
- og:image: /api/share/[contentId] (generated card)
- og:url: https://rambam.merkos.com/share/[contentId]
- twitter:card: summary_large_image
```

---

## 9. WhatsApp Integration

### 9.1 Twilio WhatsApp Business API Setup

```typescript
// lib/whatsapp.ts
import twilio from 'twilio';

const client = twilio(
  process.env.TWILIO_ACCOUNT_SID,
  process.env.TWILIO_AUTH_TOKEN
);

const WHATSAPP_FROM = `whatsapp:${process.env.TWILIO_WHATSAPP_NUMBER}`;

export async function sendDailyContent(
  subscriber: WhatsAppSubscriber,
  content: DailyContentPackage
) {
  // Send featured image with caption
  await client.messages.create({
    from: WHATSAPP_FROM,
    to: `whatsapp:${subscriber.phone}`,
    body: formatDailyMessage(content),
    mediaUrl: [content.featuredImageUrl],
  });
}

function formatDailyMessage(content: DailyContentPackage): string {
  return `
📖 *היום ברמב"ם* - ${content.hebrewDate}

${content.perakim.map(p => `• ${p.sefer} פרק ${p.perek}`).join('\n')}

${content.didYouKnow}

🔗 לתוכן מלא: ${content.webUrl}

_להסרה מהרשימה, השב "הסר"_
  `.trim();
}

// Webhook handler for incoming messages
export async function handleIncomingMessage(message: TwilioMessage) {
  const body = message.Body.toLowerCase().trim();
  const from = message.From.replace('whatsapp:', '');
  
  if (body === 'הסר' || body === 'stop' || body === 'unsubscribe') {
    await unsubscribeUser(from);
    await sendMessage(from, 'הוסרת מרשימת התפוצה. להצטרפות מחדש, שלח "הצטרף"');
  } else if (body === 'הצטרף' || body === 'join') {
    await subscribeUser(from);
    await sendMessage(from, 'נרשמת בהצלחה! תקבל תוכן יומי ברמב"ם.');
  }
}
```

### 9.2 Broadcast Scheduling

```typescript
// app/api/cron/whatsapp-broadcast/route.ts
import { NextResponse } from 'next/server';
import { verifySignature } from '@/lib/cron-auth';

export async function POST(request: Request) {
  // Verify this is a legitimate cron call (Vercel Cron or external scheduler)
  if (!verifySignature(request)) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }
  
  const today = getTodayDate();
  const content = await getDailyContentPackage(today);
  const subscribers = await getActiveSubscribers();
  
  // Rate limit: Twilio allows ~80 messages/second
  // Batch in chunks of 50 with delays
  const batches = chunk(subscribers, 50);
  
  for (const batch of batches) {
    await Promise.all(
      batch.map(sub => sendDailyContent(sub, content))
    );
    await sleep(1000); // 1 second between batches
  }
  
  // Log broadcast completion
  await logBroadcast({
    date: today,
    subscriberCount: subscribers.length,
    status: 'completed',
  });
  
  return NextResponse.json({ sent: subscribers.length });
}
```

---

## 10. Non-Functional Requirements

### 10.1 SEO Strategy

```typescript
// app/layout.tsx - Global metadata
export const metadata: Metadata = {
  metadataBase: new URL('https://rambam.merkos.com'),
  title: {
    default: 'Merkos Rambam - Daily Rambam Learning',
    template: '%s | Merkos Rambam',
  },
  description: 'AI-powered visual content for daily Rambam learning',
  keywords: ['Rambam', 'Maimonides', 'Torah', 'Daily Learning', 'Chabad'],
  openGraph: {
    type: 'website',
    locale: 'he_IL',
    alternateLocale: 'en_US',
    siteName: 'Merkos Rambam',
  },
  twitter: {
    card: 'summary_large_image',
  },
  robots: {
    index: true,
    follow: true,
  },
  alternates: {
    canonical: 'https://rambam.merkos.com',
  },
};

// app/day/[date]/page.tsx - Per-page metadata
export async function generateMetadata({ params }): Promise<Metadata> {
  const content = await getDayContent(params.date);
  
  return {
    title: `${content.hebrewDate} - ${content.perakim.map(p => p.title).join(', ')}`,
    description: content.overview,
    openGraph: {
      title: `היום ברמב"ם - ${content.hebrewDate}`,
      description: content.overview,
      images: [content.featuredImage],
    },
  };
}

// Static generation for SEO
export async function generateStaticParams() {
  // Pre-generate pages for the next 30 days and past 30 days
  const dates = generateDateRange(-30, 30);
  return dates.map(date => ({ date }));
}
```

**SEO Implementation Checklist:**

| Requirement | Implementation |
|-------------|----------------|
| **Server-side rendering** | Next.js SSG/SSR for all content pages |
| **Semantic HTML** | Proper heading hierarchy, article/section tags |
| **Structured data** | JSON-LD for Course, Article, BreadcrumbList schemas |
| **Sitemap** | Auto-generated via next-sitemap |
| **Robots.txt** | Configured for search engine access |
| **Canonical URLs** | Set on all pages to prevent duplicates |
| **OG/Twitter cards** | Dynamic generation for all shareable content |
| **Mobile-friendly** | PWA with responsive design |
| **Page speed** | Target >90 Lighthouse score |
| **Hebrew language tags** | `lang="he"` and `dir="rtl"` on HTML |

```typescript
// next-sitemap.config.js
module.exports = {
  siteUrl: 'https://rambam.merkos.com',
  generateRobotsTxt: true,
  exclude: ['/api/*', '/preview/*', '/admin/*'],
  robotsTxtOptions: {
    policies: [
      { userAgent: '*', allow: '/' },
      { userAgent: '*', disallow: ['/api/', '/preview/', '/admin/'] },
    ],
  },
  additionalPaths: async (config) => {
    // Add all historical days
    const days = await getAllLearningDays();
    return days.map(day => ({
      loc: `/day/${day.date}`,
      lastmod: day.updatedAt,
      changefreq: 'daily',
      priority: 0.8,
    }));
  },
};
```

### 10.2 Analytics Implementation

```typescript
// lib/analytics.ts
import posthog from 'posthog-js';

// Initialize PostHog
export function initAnalytics() {
  if (typeof window !== 'undefined') {
    posthog.init(process.env.NEXT_PUBLIC_POSTHOG_KEY!, {
      api_host: process.env.NEXT_PUBLIC_POSTHOG_HOST || 'https://app.posthog.com',
      capture_pageview: false,  // Manual control
      persistence: 'localStorage',
      autocapture: false,       // Manual events only
      disable_session_recording: true,  // Privacy
    });
  }
}

// Event tracking
export const analytics = {
  pageView: (page: string, properties?: Record<string, any>) => {
    posthog.capture('$pageview', { $current_url: page, ...properties });
  },
  
  trackEvent: (event: string, properties?: Record<string, any>) => {
    posthog.capture(event, properties);
  },
  
  // Specific events
  trackShare: (contentId: string, platform: string) => {
    posthog.capture('content_shared', { contentId, platform });
  },
  
  trackContentView: (contentType: string, contentId: string) => {
    posthog.capture('content_viewed', { contentType, contentId });
  },
  
  trackTrackSelection: (track: '1-perek' | '3-perek') => {
    posthog.capture('track_selected', { track });
  },
  
  trackDayNavigation: (direction: 'prev' | 'next', fromDate: string) => {
    posthog.capture('day_navigated', { direction, fromDate });
  },
};
```

**Analytics Events to Track:**

| Category | Event | Properties |
|----------|-------|------------|
| **Engagement** | `content_viewed` | contentType, contentId, sefer, perek |
| **Engagement** | `content_shared` | contentId, platform, source |
| **Navigation** | `track_selected` | track, previousTrack |
| **Navigation** | `day_navigated` | direction, fromDate, toDate |
| **Retention** | `return_visit` | daysSinceLastVisit |
| **WhatsApp** | `whatsapp_link_clicked` | contentId, source |
| **Editorial** | `content_published` | contentId, contentType, generationTime |

### 10.3 Performance Requirements

| Metric | Target | Measurement |
|--------|--------|-------------|
| **First Contentful Paint (FCP)** | <1.5s | Lighthouse, Vercel Analytics |
| **Largest Contentful Paint (LCP)** | <2.5s | Core Web Vitals |
| **Cumulative Layout Shift (CLS)** | <0.1 | Core Web Vitals |
| **Time to Interactive (TTI)** | <3.0s | Lighthouse |
| **Lighthouse Score** | >90 | All categories |
| **API Response Time (p95)** | <200ms | Vercel Analytics |
| **Image Load Time** | <1s | R2 + CDN |

**Performance Optimizations:**

```typescript
// next.config.js
module.exports = {
  images: {
    domains: ['storage.rambam.merkos.com'],
    formats: ['image/avif', 'image/webp'],
    minimumCacheTTL: 60 * 60 * 24 * 365,  // 1 year for immutable content
  },
  
  experimental: {
    optimizeCss: true,
  },
  
  async headers() {
    return [
      {
        source: '/images/:path*',
        headers: [
          { key: 'Cache-Control', value: 'public, max-age=31536000, immutable' },
        ],
      },
      {
        source: '/api/content/:path*',
        headers: [
          { key: 'Cache-Control', value: 's-maxage=300, stale-while-revalidate=600' },
        ],
      },
    ];
  },
};
```

### 10.4 Security Requirements

| Area | Implementation |
|------|----------------|
| **HTTPS** | Enforced via Vercel (automatic) |
| **Content Security Policy** | Strict CSP headers |
| **API Rate Limiting** | Upstash Redis-based rate limiter |
| **Input Validation** | Zod schemas on all API inputs |
| **SQL Injection** | Supabase parameterized queries (automatic) |
| **XSS Prevention** | React automatic escaping + CSP |
| **Secrets Management** | Vercel Environment Variables (encrypted) |
| **Dependency Scanning** | GitHub Dependabot + npm audit |
| **Auth (if needed)** | Supabase Auth or Clerk (Phase 1.5+) |

```typescript
// middleware.ts - Security headers
import { NextResponse } from 'next/server';

export function middleware(request: Request) {
  const response = NextResponse.next();
  
  // Security headers
  response.headers.set('X-DNS-Prefetch-Control', 'on');
  response.headers.set('X-Frame-Options', 'DENY');
  response.headers.set('X-Content-Type-Options', 'nosniff');
  response.headers.set('Referrer-Policy', 'origin-when-cross-origin');
  response.headers.set(
    'Content-Security-Policy',
    "default-src 'self'; img-src 'self' https://storage.rambam.merkos.com data:; script-src 'self' 'unsafe-inline' https://app.posthog.com; style-src 'self' 'unsafe-inline';"
  );
  
  return response;
}

// lib/rate-limit.ts
import { Ratelimit } from '@upstash/ratelimit';
import { Redis } from '@upstash/redis';

export const rateLimiter = new Ratelimit({
  redis: Redis.fromEnv(),
  limiter: Ratelimit.slidingWindow(100, '1 m'),  // 100 requests per minute
  analytics: true,
});
```

### 10.5 Accessibility Requirements

| Requirement | Implementation |
|-------------|----------------|
| **WCAG 2.1 AA Compliance** | Radix UI primitives (accessible by default) |
| **Screen Reader Support** | Proper ARIA labels, landmarks |
| **Keyboard Navigation** | Focus management, skip links |
| **Color Contrast** | 4.5:1 minimum ratio |
| **RTL Support** | Native RTL layout, bidirectional text |
| **Font Scaling** | Relative units (rem), no fixed sizes |
| **Reduced Motion** | `prefers-reduced-motion` media query |
| **Image Alt Text** | AI-generated, human-reviewed |

```typescript
// components/ui/AccessibleImage.tsx
interface AccessibleImageProps {
  src: string;
  alt: string;
  hebrewAlt?: string;  // Hebrew alternative text
  width: number;
  height: number;
}

export function AccessibleImage({ src, alt, hebrewAlt, ...props }: AccessibleImageProps) {
  return (
    <figure>
      <Image
        src={src}
        alt={hebrewAlt || alt}
        {...props}
        loading="lazy"
        placeholder="blur"
      />
      <figcaption className="sr-only">{hebrewAlt || alt}</figcaption>
    </figure>
  );
}
```

### 10.6 Monitoring & Observability

```typescript
// Monitoring Stack:
// - Vercel Analytics (built-in) - Performance, Web Vitals
// - PostHog - Product analytics, feature flags
// - Sentry - Error tracking, performance
// - Better Uptime - Uptime monitoring, status page
// - Supabase Dashboard - Database metrics

// lib/monitoring.ts
import * as Sentry from '@sentry/nextjs';

export function initMonitoring() {
  Sentry.init({
    dsn: process.env.SENTRY_DSN,
    environment: process.env.NODE_ENV,
    tracesSampleRate: 0.1,  // 10% of transactions
    integrations: [
      new Sentry.BrowserTracing({
        tracePropagationTargets: ['rambam.merkos.com', /^\/api/],
      }),
    ],
  });
}

// Custom error boundary
export function captureError(error: Error, context?: Record<string, any>) {
  Sentry.captureException(error, { extra: context });
}

// Performance tracking
export function trackPerformance(name: string, duration: number) {
  Sentry.addBreadcrumb({
    category: 'performance',
    message: `${name}: ${duration}ms`,
    level: 'info',
  });
}
```

**Alerting Configuration:**

| Alert | Condition | Channel |
|-------|-----------|---------|
| **Site Down** | Uptime check fails 2x | Slack + Email |
| **High Error Rate** | >5% 5xx errors in 5 min | Slack |
| **Slow Response** | p95 >2s for 10 min | Slack |
| **Database Issues** | Connection pool >80% | Slack |
| **Content Pipeline** | Generation fails | Slack + Email |
| **WhatsApp Delivery** | Broadcast fails | Slack + Email |

---

## 11. CI/CD Pipeline

### 11.1 GitHub Actions Workflow

```yaml
# .github/workflows/main.yml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  VERCEL_ORG_ID: ${{ secrets.VERCEL_ORG_ID }}
  VERCEL_PROJECT_ID: ${{ secrets.VERCEL_PROJECT_ID }}

jobs:
  lint-and-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      
      - name: Install dependencies
        run: npm ci
      
      - name: Lint
        run: npm run lint
      
      - name: Type check
        run: npm run type-check
      
      - name: Run tests
        run: npm run test
      
      - name: Build
        run: npm run build
        env:
          NEXT_PUBLIC_POSTHOG_KEY: ${{ secrets.POSTHOG_KEY }}

  security-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Run npm audit
        run: npm audit --audit-level=high
      
      - name: Run Snyk
        uses: snyk/actions/node@master
        env:
          SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}

  deploy-preview:
    needs: [lint-and-test]
    if: github.event_name == 'pull_request'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Deploy to Vercel Preview
        uses: amondnet/vercel-action@v25
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.VERCEL_ORG_ID }}
          vercel-project-id: ${{ secrets.VERCEL_PROJECT_ID }}
          scope: ${{ secrets.VERCEL_ORG_ID }}

  deploy-production:
    needs: [lint-and-test, security-scan]
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Deploy to Vercel Production
        uses: amondnet/vercel-action@v25
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.VERCEL_ORG_ID }}
          vercel-project-id: ${{ secrets.VERCEL_PROJECT_ID }}
          vercel-args: '--prod'
          scope: ${{ secrets.VERCEL_ORG_ID }}
      
      - name: Notify Slack
        uses: slackapi/slack-github-action@v1
        with:
          payload: |
            {
              "text": "✅ Deployed to production: ${{ github.sha }}"
            }
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK }}
```

### 11.2 Environment Configuration

```bash
# .env.example

# App
NEXT_PUBLIC_APP_URL=https://rambam.merkos.com
NEXT_PUBLIC_APP_NAME="Merkos Rambam"

# Database
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=xxx
SUPABASE_SERVICE_KEY=xxx

# Storage
CLOUDFLARE_ACCOUNT_ID=xxx
CLOUDFLARE_R2_ACCESS_KEY=xxx
CLOUDFLARE_R2_SECRET_KEY=xxx
CLOUDFLARE_R2_BUCKET=rambam-assets

# Cache
UPSTASH_REDIS_URL=xxx
UPSTASH_REDIS_TOKEN=xxx

# AI Services
PORTKEY_API_KEY=xxx
ANTHROPIC_API_KEY=xxx
REPLICATE_API_TOKEN=xxx

# WhatsApp
TWILIO_ACCOUNT_SID=xxx
TWILIO_AUTH_TOKEN=xxx
TWILIO_WHATSAPP_NUMBER=+1xxxxxxxxxx

# Analytics
NEXT_PUBLIC_POSTHOG_KEY=xxx
NEXT_PUBLIC_POSTHOG_HOST=https://app.posthog.com
SENTRY_DSN=xxx

# Editorial
NOTION_API_KEY=xxx
NOTION_REVIEW_DB_ID=xxx

# Cron Auth
CRON_SECRET=xxx
```

---

## 12. Cost Estimates

### 12.1 Phase 1 Monthly Costs (0-500 DAU)

| Service | Plan | Monthly Cost | Notes |
|---------|------|--------------|-------|
| **Vercel** | Pro | $20 | Includes 1TB bandwidth, serverless functions |
| **Supabase** | Free | $0 | Up to 500MB database, 1GB storage |
| **Cloudflare R2** | Pay-as-you-go | ~$5 | ~500GB storage, no egress fees |
| **Upstash Redis** | Free | $0 | Up to 10K commands/day |
| **PostHog** | Free | $0 | Up to 1M events/month |
| **Sentry** | Free | $0 | Up to 5K errors/month |
| **Better Uptime** | Free | $0 | Up to 3 monitors |
| **Image Generation** | Replicate | ~$30 | ~10K images/month @ $0.003/image |
| **LLM (Claude)** | PortKey/Anthropic | ~$50 | Text generation, analysis |
| **WhatsApp** | Twilio | ~$30 | ~2K subscribers × 30 days |
| **Domain** | Cloudflare | ~$1 | Annual ÷ 12 |

**Phase 1 Total: ~$136/month**

### 12.2 Phase 1 Scaling (500-2,000 DAU)

| Service | Plan Change | Monthly Cost |
|---------|-------------|--------------|
| **Supabase** | Pro ($25) | $25 |
| **Image Generation** | Volume increase | ~$60 |
| **LLM** | Volume increase | ~$100 |
| **WhatsApp** | 5K subscribers | ~$75 |

**Scaled Phase 1 Total: ~$300/month**

### 12.3 Phase 2 Projections (2,000-10,000 DAU)

| Service | Estimate | Notes |
|---------|----------|-------|
| **Infrastructure** | ~$200/month | Vercel Team, Supabase Pro |
| **AI Services** | ~$500/month | Higher volume, vector DB |
| **WhatsApp** | ~$300/month | 10K+ subscribers |
| **Monitoring** | ~$50/month | Upgraded plans |

**Phase 2 Estimate: ~$1,000/month**

---

## 13. Implementation Roadmap

### 13.1 Phase 0: Content Validation (Week 1-2)

| Task | Duration | Owner |
|------|----------|-------|
| Set up image generation script | 2 days | Dev |
| Create style guide and prompts | 1 day | Dev + Rabbi |
| Test with 5 sample days | 2 days | Dev |
| Set up WhatsApp broadcast list | 1 day | Dev |
| Recruit seed groups + teachers | Ongoing | Rayi |
| Begin daily distribution | Day 7+ | Dev |
| Monitor engagement metrics | Ongoing | Rayi |

**Deliverables:**
- [ ] Working image generation script
- [ ] 5 WhatsApp test groups receiving content
- [ ] 2-3 teachers receiving and sharing content
- [ ] Basic engagement tracking spreadsheet

### 13.2 Phase 1: Core Platform (Week 3-6)

**Week 3: Foundation**
| Task | Duration |
|------|----------|
| Next.js project setup with TypeScript | 0.5 day |
| Supabase database schema | 0.5 day |
| Sefaria API integration | 1 day |
| Basic Rambam text display (RTL) | 1 day |
| Day navigation | 0.5 day |
| Track selection | 0.5 day |

**Week 4: Content Integration**
| Task | Duration |
|------|----------|
| Content item display components | 1 day |
| Image display with watermarks | 1 day |
| Sichos references component | 0.5 day |
| Share card generation | 1 day |
| Share buttons (WhatsApp, copy link) | 0.5 day |

**Week 5: Pipeline & Editorial**
| Task | Duration |
|------|----------|
| Content generation pipeline | 2 days |
| Notion editorial workflow | 1 day |
| Publication automation | 1 day |
| WhatsApp broadcast integration | 1 day |

**Week 6: Polish & Launch**
| Task | Duration |
|------|----------|
| PWA configuration | 0.5 day |
| SEO optimization | 0.5 day |
| Analytics integration | 0.5 day |
| Error tracking setup | 0.5 day |
| Performance optimization | 1 day |
| Bug fixes and QA | 2 days |

**Phase 1 Deliverables:**
- [ ] Live PWA at rambam.merkos.com
- [ ] Daily content pipeline operational
- [ ] Editorial workflow in Notion
- [ ] WhatsApp daily broadcast
- [ ] Analytics dashboard
- [ ] 7-day content buffer

### 13.3 Phase 1.5: Interaction Layer (Week 7-10)

| Feature | Effort | Dependencies |
|---------|--------|--------------|
| Daily chatbot (scoped) | 2 weeks | Content pipeline stable |
| Quiz questions | 3 days | Text pipeline |
| Sefer Hamitzvos mapping | 2 days | Data sourcing |
| Bookmarks/notes | 3 days | User accounts |

### 13.4 Quality Gates

| Gate | Criteria | Blocking? |
|------|----------|-----------|
| **Phase 0 → 1** | Organic forwarding, teacher adoption, feature requests | Yes |
| **Phase 1 Launch** | 7-day content buffer, 3+ reviewers, all tests passing | Yes |
| **Phase 1 → 1.5** | 500+ DAU, 25%+ 7-day retention, stable pipeline | Yes |
| **Phase 1.5 → 2** | 1,000+ DAU, 40%+ retention, chatbot accuracy validated | Yes |

---

## 14. Risk Mitigations

### 14.1 Technical Risks

| Risk | Mitigation |
|------|------------|
| **Sefaria API unavailable** | Cache aggressively; build local fallback dataset for critical data |
| **Image generation quality inconsistent** | Multi-image generation per prompt; human selection; style guide refinement |
| **LLM hallucination in content** | Human review mandatory; no bypass; prompt engineering; output validation |
| **WhatsApp API rate limits** | Batch sends with delays; dedicated business number; Twilio support |
| **Database performance** | Proper indexing; read replicas if needed; caching layer |
| **CDN costs unexpectedly high** | R2 has no egress fees; monitor storage growth |

### 14.2 Operational Risks

| Risk | Mitigation |
|------|------------|
| **Volunteer editorial fatigue** | 7-day buffer; degradation policy; rotation schedule; appreciation program |
| **Solo developer availability** | Comprehensive documentation; simple architecture; no custom infrastructure |
| **Content pipeline failure** | Monitoring + alerts; manual fallback process documented |
| **Shabbos/Yom Tov coverage** | Pre-scheduled content; extended buffer during holidays |

---

## 15. Documentation Requirements

### 15.1 Required Documentation

| Document | Purpose | Location |
|----------|---------|----------|
| **README.md** | Project overview, setup instructions | Repo root |
| **CONTRIBUTING.md** | Development workflow, code standards | Repo root |
| **Architecture Decision Records** | Key technical decisions | `/docs/adr/` |
| **API Documentation** | Endpoint specs | Auto-generated from code |
| **Editorial Guide** | Content review process | Notion |
| **Volunteer Handbook** | Reviewer onboarding | Notion |
| **Runbook** | Incident response procedures | `/docs/runbook.md` |
| **Style Guide** | Image generation standards | `/docs/style-guide.md` |

### 15.2 Code Documentation Standards

```typescript
/**
 * Generates a branded share card for a content item.
 * 
 * @param contentId - UUID of the content item
 * @param options - Optional customization (size, branding)
 * @returns PNG buffer of the generated share card
 * 
 * @example
 * const card = await generateShareCard('abc-123', { size: 'whatsapp' });
 */
export async function generateShareCard(
  contentId: string,
  options?: ShareCardOptions
): Promise<Buffer> {
  // Implementation
}
```

---

## 16. Appendices

### A. Sefaria API Reference

```typescript
// Key endpoints for Rambam content

// Get full text of a chapter
GET https://www.sefaria.org/api/texts/Mishneh_Torah,_{Sefer}_{Perek}
// Example: https://www.sefaria.org/api/texts/Mishneh_Torah,_Sabbath_1

// Response structure:
{
  "text": [...],           // Array of halachos (English)
  "he": [...],             // Array of halachos (Hebrew)
  "sectionNames": [...],   // ["Chapter", "Halakhah"]
  "titleVariants": [...],
  "heTitle": "...",
}

// Get index/structure
GET https://www.sefaria.org/api/index/Mishneh_Torah
```

### B. PortKey Configuration

```typescript
// lib/portkey.ts
import Portkey from 'portkey-ai';

const portkey = new Portkey({
  apiKey: process.env.PORTKEY_API_KEY,
  config: {
    retry: { attempts: 3, onStatusCodes: [429, 500, 502, 503] },
    cache: { mode: 'simple' },
  },
});

// Define model routing
const routingConfig = {
  strategy: 'fallback',
  targets: [
    { provider: 'anthropic', model: 'claude-sonnet-4-5-20250929' },
    { provider: 'openai', model: 'gpt-4o', weight: 0 },  // Fallback only
  ],
};
```

### C. Content Type Schemas

```typescript
// Detailed content schemas for each type

interface ConceptualImage {
  type: 'conceptual_image';
  content: {
    prompt: string;           // Generation prompt used
    caption: string;          // Hebrew caption
    captionEnglish?: string;  // Optional English
    halachaContext: string;   // Which halacha this illustrates
  };
  imageUrl: string;
  thumbnailUrl: string;
}

interface Infographic {
  type: 'infographic';
  content: {
    title: string;
    elements: InfographicElement[];  // Structured data for potential re-rendering
    sourceHalachos: number[];        // Which halachos this covers
  };
  imageUrl: string;
}

interface PerekOverview {
  type: 'perek_overview';
  content: {
    summary: string;          // 2-3 sentence overview
    keyTopics: string[];      // Main topics covered
    practicalRelevance?: string;  // Why this matters today
  };
}

interface DidYouKnow {
  type: 'did_you_know';
  content: {
    fact: string;             // The compelling fact
    source: string;           // Halacha reference
    shareText: string;        // Pre-formatted for sharing
  };
}

interface SichosHighlight {
  type: 'sichos_highlight';
  content: {
    excerpt: string;          // Key quote or summary
    context: string;          // Brief context
    sourceVolume: string;     // e.g., "Likkutei Sichos Vol. 19"
    sourcePage: string;
    sourceUrl?: string;       // Link to full sicha if available
  };
}
```

---

*End of Technical Requirements Document*
