🔷 1. Project Overview
📌 What this project does

A smart web scraping engine that:
Takes a URL
Tries scraping using Crawl4AI (primary engine)
Falls back to Playwright (browser-based scraping)
Cleans + scores content
Returns structured response via API

🔷 2. Folder Structure (Explained)
voice-agent-scrapper/
│
├── api.py                  # FastAPI server (entry point for API)
├── main.py                 # CLI-based testing entry point
├── requirements.txt       # Dependencies
├── pyrightconfig.json     # Type checking config
│
├── core/                  # Business logic layer
│   ├── orchestrator.py    # Main pipeline controller (VERY IMPORTANT)
│   ├── scoring.py         # Content quality scoring logic
│   ├── url_validator.py   # URL validation
│
├── engines/               # Scraping engines
│   ├── crawl4ai_engine.py # Primary scraping engine
│   ├── playwright_engine.py # Fallback engine
│
├── schemas/               # Data models
│   ├── response_schema.py # ScrapeResult model
│
├── utils/                 # Helper utilities
│   ├── content_cleaner.py # Content cleanup logic
│   ├── logger.py          # Logging setup


🔷 3. High-Level Architecture (HLD)
Client (Postman / Frontend / CLI)
          │
          ▼
     FastAPI (api.py)
          │
          ▼
   Orchestrator (core)
          │
   ┌──────┴────────┐
   ▼               ▼
Crawl4AI       Playwright
(Primary)      (Fallback)
   │               │
   └──────┬────────┘
          ▼
   Content Cleaning
          ▼
   Quality Scoring
          ▼
   Structured Response (Schema)
          ▼
       Client


🔷 4. Low-Level Architecture (LLD)

🔁 Flow inside orchestrator.py
scrape_url(url):
    1. Validate URL
    2. Call Crawl4AI
    3. Get content
    4. Compute quality score
    5. IF score >= 75:
           return result
       ELSE:
           fallback → Playwright
    6. Clean content
    7. Return structured result


🔷 5. Core Modules (Clear Responsibility)
         🧠 orchestrator.py
        Brain of the system
        Decides:
        Which engine to trust
        When to fallback
        When to reject
   ⚙️ crawl4ai_engine.py
        Fast scraping
        Works well for:
        Static sites
        Light JS
   🌐 playwright_engine.py
        Browser automation
        Handles:
        Heavy JS websites
        Lazy loading / scrolling
   📊 scoring.py
        Determines content quality
        Based on:
        Length
        Title presence
        UI junk phrases
        Text density
🧹 content_cleaner.py
        Removes:
        Ads
        Cookie banners
        Navigation junk
        Markdown noise
        URLs
🔒 url_validator.py
        Prevents:
        Invalid URLs
        Security issues
        Garbage input
📦 response_schema.py
        Standard output format
        Ensures consistency
🔷 6. Tech Stack
    Backend
        FastAPI → API layer
           Python (asyncio) → async execution
    Scraping
           Crawl4AI → primary scraper
           Playwright → browser automation
           BeautifulSoup → HTML parsing
    Validation & Models
        Pydantic → schema validation
    Utilities
        Logging system
        Regex-based cleaning

🔷 7. Packages (requirements.txt inferred)
fastapi
uvicorn
playwright
beautifulsoup4
crawl4ai
pydantic
lxml


🔷 8. Database Schema
❌ Currently: No database used
👉 Everything is:

Real-time
Stateless
If you scale → recommended schema:
Table: scrape_logs
- id
- url
- status
- engine_used
- content_length
- created_at

Table: scraped_content
- id
- url
- title
- content
- metadata


🔷 9. Text-Based Pipeline Diagram
INPUT URL
   │
   ▼
[ URL VALIDATOR ]
   │
   ▼
[ CRAWL4AI ENGINE ]
   │
   ▼
[ QUALITY SCORING ]
   │
   ├── GOOD → CLEAN → RETURN
   │
   └── BAD → PLAYWRIGHT ENGINE
                  │
                  ▼
             CLEAN CONTENT
                  │
                  ▼
              RETURN RESULT


🔷 10. API Design
POST /scrape
Request
{
  "url": "https://example.com"
}
Response
{
  "url": "...",
  "status": "success",
  "engine_used": "crawl4ai",
  "title": "...",
  "content": "...",
  "content_length": 1200,
  "metadata": {},
  "error_message": null
}


🔷 11. Weak Points (Important Improvements)
❌ 3. No Caching --> (once finalised it will be added )
Same URL scraped again and again
👉 Add Redis caching
❌ 4. No Rate Limiting
Can get blocked by websites
❌ 5. No Queue System

👉 For production:

Use Kafka / RabbitMQ / Redis Queue
❌ 6. No Metadata Extraction
Only content + title
👉 Add:
headings
images
links


🔷 13. Production-Level Architecture (Upgrade Path)
Client
  │
API Gateway
  │
FastAPI Service
  │
Queue (Kafka)
  │
Worker Services
 ├── Crawl4AI Worker
 ├── Playwright Worker
  │
Redis Cache
  │
Database (Postgres)


🔷 14. Complete KT (Simple Explanation for Anyone)

👉 This system is a smart scraper that:

Accepts a URL
Validates it
Tries fast scraping (Crawl4AI)
Checks if content is good
If bad → uses browser scraping (Playwright)
Cleans useless text
Returns structured output