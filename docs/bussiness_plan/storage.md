Quick answer — these are all realistic with the same adapter pattern:

| Storage | Free API? | Difficulty | Worth it? |
|---|---|---|---|
| **S3 / MinIO** | Yes | Easy | ✅ Must have — universal standard |
| **Backblaze B2** | Yes (10GB free) | Easy | ✅ S3-compatible, cheap |
| **Wasabi** | Yes | Easy | ✅ S3-compatible |
| **Google Cloud Storage** | Free tier | Easy | ✅ Already have Google OAuth |
| **Azure Blob** | Free tier | Medium | ✅ Already have OneDrive/Azure OAuth |
| **Nextcloud** | Yes (self-hosted) | Medium | ✅ Popular self-hosted |
| **MEGA** | Yes | Medium | ⚠️ Encrypted, tricky API |
| **pCloud** | Yes | Medium | ⚠️ Niche |
| **iCloud** | No public API | Hard | ❌ Skip |
| **FTP/SFTP** | Yes | Easy | ✅ Legacy but many still use |
| **WebDAV** | Yes | Easy | ✅ Universal protocol |

**Realistic Phase plan for storage:**

| Phase | Storage adapters |
|---|---|
| Phase 1 (now) | Google Drive, Dropbox, OneDrive, Box (EXISTS) |
| Phase 2 | S3/MinIO, Backblaze B2 (S3-compatible = same adapter) |
| Phase 3 | Nextcloud (WebDAV), FTP/SFTP, Azure Blob, Google Cloud Storage |

**Key insight:** If you build the S3 adapter, you automatically get Backblaze B2, Wasabi, DigitalOcean Spaces, Cloudflare R2 — they're all S3-compatible. One adapter, 5+ providers.

Same for WebDAV — covers Nextcloud, ownCloud, and any WebDAV server.

So realistically: **2 new adapters (S3 + WebDAV) = 8+ additional storage providers.**

Now stop researching. Go build Phase 1. Tell the agent to proceed.