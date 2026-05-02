# NAI Health — Master Plan v3 (Updated April 14, 2026)

## CHANGELOG
- v1 (Apr 12) — Initial plan
- v2 (Apr 13) — Locked tech decisions, Flutter Riverpod, backend architecture
- v3 (Apr 14) — Backend scaffold COMPLETE. 16 apps, 8 with full API, Docker, 55 tests passing.

---

## Build Progress

### Backend (nai-health-backend) — SCAFFOLDED ✅

| # | App | Models | Admin | API | Tests |
|---|---|---|---|---|---|
| 1 | core | ✅ BaseModel, AuditLog | ✅ Unfold | ✅ audit service | ✅ 3 |
| 2 | accounts | ✅ User (custom) | ✅ Unfold | ✅ register/login/refresh/me | ✅ 8 |
| 3 | patients | ✅ PatientProfile, Condition, Allergy | ✅ Unfold | ✅ full CRUD | ✅ 9 |
| 4 | labs | ✅ LabPanel, LabResult | ✅ Unfold | ✅ panels/results/trends/egfr | ✅ 7 |
| 5 | medications | ✅ Medication, MedSchedule, MedLog, DrugInteraction | ✅ Unfold | ✅ meds/schedule/log | ✅ 7 |
| 6 | vitals | ✅ VitalReading, FluidIntake, FluidGoal | ✅ Unfold | ✅ vitals/fluid/goal | ✅ 8 |
| 7 | documents | ✅ EmergencyCard, Document | ✅ Unfold | ✅ emergency card/docs | ✅ 5 |
| 8 | notifications | ✅ Notification, NotificationPreference | ✅ Unfold | ✅ prefs/fcm/read | ✅ 6 |
| 9 | ai_chat | 📁 Stub | — | — | — |
| 10 | nutrition | 📁 Stub | — | — | — |
| 11 | family | 📁 Stub | — | — | — |
| 12 | appointments | 📁 Stub | — | — | — |
| 13 | fhir | 📁 Stub | — | — | — |
| 14 | wearables | 📁 Stub | — | — | — |
| 15 | knowledge | 📁 Stub | — | — | — |
| 16 | telemedicine | 📁 Stub | — | — | — |

**Total: 55 tests passing. Docker (dev + prod) configured.**

### Known Bugs (found by tests, pending fix)
1. Route ordering: literal routes must be before {id} param routes
2. UUID coercion: Out schemas need `id: UUID` not `id: str`
3. Ninja deprecation: tuple returns → Status() pattern

### Flutter (com.nematiai.health) — NOT STARTED
- Architecture doc locked (Riverpod, Clean Arch, Feature-First)
- 82 HTML mockup screens built
- 15 screens scoped for Simple Launch

### HTML Mockups — COMPLETE ✅
- 82 screens built and delivered as HTML files
- Design tokens: Lora + Mulish, sage/sand palette

---

## Tech Stack (LOCKED)

### Backend
| Layer | Technology | Version |
|---|---|---|
| Framework | Django + Django Ninja | 6.0.4 + 1.6.2 |
| Python | Python | 3.13+ |
| Admin | django-unfold | 0.87.0 |
| Auth | PyJWT | 2.12.1 |
| DB | PostgreSQL (Docker) | 16 |
| Cache | Redis (Docker) | 7.4.0 |
| Queue | Celery + RabbitMQ (Docker) | 5.6.3 |
| Scheduler | django-celery-beat | 2.9.0 |
| Config | django-environ | 0.12.0 |
| Crash | Sentry SDK | 2.25.1 |
| Testing | pytest-django + factory-boy | latest |

### Flutter (LOCKED)
| Decision | Choice |
|---|---|
| State Management | Riverpod 3.x |
| Architecture | Clean Architecture (3 layers) |
| Navigation | GoRouter 14.x |
| Networking | Dio + Retrofit |
| Local Storage | Drift + flutter_secure_storage |
| Serialization | freezed + json_serializable |

---

## What's Built vs What's Missing

### Built ✅
- Django project scaffold with split settings (local/staging/prod)
- 16 Django apps (8 with full models + API, 8 stubs)
- Custom User model (email-based, UUID pk, roles)
- JWT authentication (register, login, refresh, me)
- HIPAA audit logging (immutable AuditLog model)
- Unfold modern admin panel
- Full CRUD API endpoints for all Simple Launch apps
- Docker dev stack (Django + PostgreSQL + Redis + RabbitMQ)
- Docker prod stack (gunicorn)
- 55 automated tests
- Per-app service layer pattern (services/ + selectors/)

### Missing ❌
| What | Priority | Effort |
|---|---|---|
| Fix 2 bugs (route ordering + UUID) | NOW | 10 min |
| CORS for Flutter | NOW | 5 min |
| Seed data (LOINC codes, drug interactions) | HIGH | 2 hrs |
| Firebase push notification wiring | HIGH | 1 day |
| S3 file upload for documents | HIGH | 1 day |
| Photo OCR pipeline (ML Kit → parse) | HIGH | 3 days |
| SendGrid email wiring | MEDIUM | 2 hrs |
| Twilio SMS wiring | MEDIUM | 2 hrs |
| Claude API + RAG pipeline (ai_chat) | Phase 1 | 1-2 weeks |
| FHIR integration (Epic/Cerner) | Phase 2 | 2-3 weeks |
| Family/caregiver sharing | Phase 2 | 1 week |
| Knowledge graph (PostgreSQL tables) | Phase 2 | 1 week |
| Wearables integration | Phase 3 | 2 weeks |
| Telemedicine (LiveKit) | Phase 4 | 3-4 weeks |

---

## API Endpoints Summary

```
/api/v1/health/                          GET     — system health check
/api/v1/auth/register/                   POST    — create account
/api/v1/auth/login/                      POST    — get JWT tokens
/api/v1/auth/refresh/                    POST    — refresh access token
/api/v1/auth/me/                         GET     — current user profile
/api/v1/patients/profile/                GET/POST/PATCH/DELETE
/api/v1/patients/conditions/             GET/POST
/api/v1/patients/conditions/{id}/        GET/PATCH/DELETE
/api/v1/patients/allergies/              GET/POST
/api/v1/patients/allergies/{id}/         GET/PATCH/DELETE
/api/v1/labs/panels/                     GET/POST
/api/v1/labs/panels/{id}/                GET/PATCH/DELETE
/api/v1/labs/panels/{id}/results/        POST
/api/v1/labs/results/                    GET
/api/v1/labs/results/{id}/               GET/PATCH/DELETE
/api/v1/labs/trends/{loinc_code}/        GET
/api/v1/labs/trends/egfr/                GET
/api/v1/medications/                     GET/POST
/api/v1/medications/{id}/                GET/PATCH/DELETE
/api/v1/medications/today/               GET
/api/v1/medications/logs/                POST
/api/v1/vitals/                          GET/POST
/api/v1/vitals/{id}/                     GET/PATCH/DELETE
/api/v1/vitals/trends/{vital_type}/      GET
/api/v1/vitals/fluids/                   GET/POST
/api/v1/vitals/fluids/goal/              GET/POST/PATCH
/api/v1/documents/emergency-card/        GET/POST/PATCH
/api/v1/documents/                       GET/POST
/api/v1/documents/{id}/                  GET/DELETE
/api/v1/notifications/                   GET
/api/v1/notifications/{id}/read/         POST
/api/v1/notifications/unread-count/      GET
/api/v1/notifications/preferences/       GET/PATCH
/api/v1/notifications/fcm-token/         POST
```

---

## Simple Launch Scope (15 Screens → Backend Mapping)

| # | Screen | Backend Endpoint |
|---|---|---|
| 1 | Welcome | — |
| 2 | Login | /auth/login/ |
| 3 | Sign Up | /auth/register/ |
| 4 | Consent | — (client-side) |
| 5 | Profile Setup | /patients/profile/ POST |
| 6 | Home Dashboard | /patients/profile/ + /vitals/ + /medications/today/ + /labs/trends/egfr/ |
| 7 | Vitals Overview | /vitals/?type=... |
| 8 | Vitals Log | /vitals/ POST |
| 9 | Meds Overview | /medications/ |
| 10 | Med Schedule | /medications/today/ |
| 11 | Labs Overview | /labs/panels/ |
| 12 | Labs Trend | /labs/trends/egfr/ |
| 13 | Emergency Card | /documents/emergency-card/ |
| 14 | Profile | /auth/me/ + /patients/profile/ |
| 15 | Settings | /notifications/preferences/ |

---

## Reference Documents

| Document | Contains | Version |
|---|---|---|
| nai-health-master-plan-v3.md | This document | v3 |
| nai-health-product-final.md | Full product spec — 82 screens | v3 |
| nai-health-api-reference.md | External APIs — 29 APIs, OAuth, .env | v3 |
| MedHub-Flutter-Architecture.md | Flutter arch — Riverpod, LOCKED | v2 |

---

*Version: 3.0*
*Author: Ali Nemati / Nemati AI LLC*
*Updated: April 14, 2026*
*CONFIDENTIAL*
