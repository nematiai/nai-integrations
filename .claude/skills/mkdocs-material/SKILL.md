---
name: mkdocs-material
description: "Update and maintain nai-integrations developer documentation using mkdocs-material. Handles content updates, SEO optimization, multi-language code examples, navigation structure, and documentation standards. Use when user says update docs, fix documentation, add examples, or mkdocs."
disable-model-invocation: true
allowed-tools: Read, Grep, Glob, Bash
---

# MkDocs-Material — nai-integrations Documentation Management

**RULE: Read router files for accurate schemas. Do not guess.**
**RULE: Use pymdownx.tabbed for multi-language code examples.**
**RULE: Update "Last updated" dates on modified pages.**
**RULE: Do not document internal endpoints (auth, user, admin, media, payments, analytics).**

---

## Constants

- **Docs site:** https://nai-integrations.com/docs/
- **Base API URL:** https://api.nai-integrations.com
- **OpenAI SDK base_url:** https://api.nai-integrations.com/v1
- **Auth header:** Authorization: Bearer YOUR_API_KEY
- **API key format:** indox-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
- **Swagger UI:** https://api.nai-integrations.com/api/v1/docs
- **ReDoc:** https://api.nai-integrations.com/api/v1/redoc
- **Backend repo:** D:/NAI_Project/BACKENDS/nai-integrations
- **Router files:** app/api/routers/
- **Docs source (container):** /docs/ inside nai-integrations-docs container

### Approved model names for examples
- openai/gpt-4o-mini (cheap, fast)
- anthropic/claude-3-haiku-20240307 (cheap, fast)
- deepseek/deepseek-chat (cheapest)
- openai/gpt-4o (premium)
- anthropic/claude-3-opus-20240229 (premium)

### Router file → Doc page mapping
| Router file | Doc page |
|-------------|----------|
| app/api/routers/chat.py | usage/chat.md |
| app/api/routers/completion.py | usage/completions.md |
| app/api/routers/embedding.py | usage/embeddings.md |
| app/api/routers/image.py | usage/images.md |
| app/api/routers/video.py | usage/video.md |
| app/api/routers/audio.py | usage/tts.md, usage/stt.md |
| app/api/routers/model.py | usage/models.md |

### Do NOT document these endpoints
- /auth/* (frontend handles login/register)
- /user/* (dashboard handles profile/credits)
- /admin/* (internal admin panel)
- /media/* (internal file management)
- /payments/* (frontend/Stripe handles this)
- /analytics/* (dashboard feature)

---

## Phase 1 — Context Gathering

```bash
# Verify docs structure
cat mkdocs.yml
find docs -name "*.md" | sort
ls docs/overrides/main.html 2>/dev/null || echo "NO SEO TEMPLATE"
```

Read current mkdocs.yml and verify all .md files exist.
Check docs/overrides/main.html for SEO setup.

---

## Phase 2 — Content Updates

For each .md file:
- Fix "IndoxRouter" → "nai-integrations" references
- Update outdated examples with approved model names
- Fix dead links
- Update "Last updated" date to today

---

## Phase 3 — SEO Implementation

Create docs/overrides/main.html:
```html
{% extends "base.html" %}
{% block extrahead %}
{% set title = config.site_name %}
{% if page and page.meta and page.meta.title %}
  {% set title = page.meta.title ~ " | " ~ config.site_name %}
{% elif page and page.title and not page.is_homepage %}
  {% set title = page.title | striptags ~ " | " ~ config.site_name %}
{% endif %}
{% set description = config.site_description %}
{% if page and page.meta and page.meta.description %}
  {% set description = page.meta.description %}
{% endif %}
<meta property="og:type" content="website" />
<meta property="og:title" content="{{ title }}" />
<meta property="og:description" content="{{ description }}" />
<meta property="og:url" content="{{ page.canonical_url }}" />
<meta property="og:site_name" content="{{ config.site_name }}" />
<meta property="og:image" content="https://nai-integrations.com/docs/assets/og-image.png" />
<meta property="og:image:width" content="1200" />
<meta property="og:image:height" content="630" />
<meta name="twitter:card" content="summary_large_image" />
<meta name="twitter:title" content="{{ title }}" />
<meta name="twitter:description" content="{{ description }}" />
<meta name="twitter:image" content="https://nai-integrations.com/docs/assets/og-image.png" />
{% endblock %}
```

Add to mkdocs.yml:
```yaml
theme:
  custom_dir: overrides

plugins:
  - search
  - meta
```

Add front matter to EVERY .md file:
```yaml
---
title: Page Title Here
description: Concise description under 160 chars for SEO.
---
```

---

## Phase 4 — Multi-Language Examples

For each page in the router mapping table:
1. Read the actual Pydantic schema from the router file
2. Add tabbed examples using pymdownx.tabbed:

```markdown
=== "Python"
    ```python
    from nai-integrations import Client
    client = Client(api_key="YOUR_API_KEY")
    response = client.chat(
        messages=[{"role": "user", "content": "Hello"}],
        model="openai/gpt-4o-mini"
    )
    print(response['data'])
    ```

=== "JavaScript"
    ```javascript
    const response = await fetch('https://api.nai-integrations.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Authorization': 'Bearer YOUR_API_KEY',
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        model: 'openai/gpt-4o-mini',
        messages: [{ role: 'user', content: 'Hello' }]
      })
    });
    ```

=== "cURL"
    ```bash
    curl https://api.nai-integrations.com/v1/chat/completions \
      -H "Authorization: Bearer YOUR_API_KEY" \
      -H "Content-Type: application/json" \
      -d '{"model": "openai/gpt-4o-mini", "messages": [{"role": "user", "content": "Hello"}]}'
    ```

=== "OpenAI SDK"
    ```python
    from openai import OpenAI
    client = OpenAI(
        api_key="YOUR_API_KEY",
        base_url="https://api.nai-integrations.com/v1"
    )
    response = client.chat.completions.create(
        model="openai/gpt-4o-mini",
        messages=[{"role": "user", "content": "Hello"}]
    )
    ```
```

---

## Phase 5 — New Pages

Create these if they don't exist:
- **usage/models.md** — GET /models/ endpoints, browse by provider/capability
- **usage/streaming.md** — SSE streaming, stop-stream endpoint
- **examples/openai-sdk.md** — Complete OpenAI SDK compatibility guide

---

## Phase 6 — Navigation

Update mkdocs.yml nav:
```yaml
nav:
  - Home: index.md
  - Getting Started: getting-started.md
  - Usage Guide:
      - Basic Usage: usage/basic-usage.md
      - Chat Completions: usage/chat.md
      - Vision & Multimodal: usage/vision.md
      - Text Completions: usage/completions.md
      - Embeddings: usage/embeddings.md
      - Image Generation: usage/images.md
      - Video Generation: usage/video.md
      - Text-to-Speech: usage/tts.md
      - Speech-to-Text: usage/stt.md
      - Models: usage/models.md
      - Streaming: usage/streaming.md
      - BYOK Support: usage/byok.md
      - Response Format: usage/responses.md
      - Usage Tracking: usage/tracking.md
      - Rate Limits: usage/rate-limits.md
  - Examples:
      - Basic Examples: examples/basic.md
      - Advanced Examples: examples/advanced.md
      - OpenAI SDK Usage: examples/openai-sdk.md
  - API Reference:
      - Overview: api-reference/api-reference.md
      - Client Methods: api/client.md
      - Response Schemas: api/responses.md
      - Exceptions: api/exceptions.md
      - Interactive API Docs: https://api.nai-integrations.com/api/v1/docs
  - Use Cases:
      - Chatbots: use-cases/chatbots.md
      - RAG Systems: use-cases/rag-systems.md
      - Content Generation: use-cases/content-generation.md
      - Document Processing: use-cases/document-processing.md
```

---

## Phase 7 — Validation

```bash
mkdocs build --strict
```

Verify: no build errors, all links resolve, SEO tags present in built HTML.

---

## Phase 8 — Report

```
## MkDocs Update Complete
- [x] Content updated (IndoxRouter → nai-integrations)
- [x] SEO meta tags implemented
- [x] Navigation updated with new pages
- [x] Multi-language examples added (Python/JS/cURL/OpenAI SDK)
- [x] New pages created (models, streaming, openai-sdk)
- [x] Build validated
- [x] Last updated dates set

**Status:** Documentation updated successfully
```


Key additions: constants section, router-to-doc mapping table, approved model names, actual SEO template code, tabbed example format, excluded endpoint list. Now the agent has everything without needing to ask questions.
