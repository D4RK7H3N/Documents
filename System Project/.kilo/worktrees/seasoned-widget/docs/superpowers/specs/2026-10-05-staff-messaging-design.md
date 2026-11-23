# Staff Messaging — Announcements & Direct Messages

**Date:** 2026-10-05
**Status:** Draft for review
**Scope:** Internal staff-to-staff communication inside the existing School Management System.

---

## 1. Problem

Staff cannot talk to each other through the system. The only shared surface today is
the global `maintenance_mode` banner on `SchoolConfiguration`
(`school_pos/school_config/models.py:113-121`), which is all-or-nothing and carries no
author or history.

The bell dropdown that looks like a notification system
(`frontend/src/layouts/MainLayout.jsx:169-230`) is **not** one. It is fed by
`NotificationContext` (`frontend/src/context/NotificationContext.jsx`), which generates
entries **client-side from the acting user's own actions** (`notifyPayment`,
`notifyEnrollment`, `notifySale`, `notifyLogin` at `:38-61`), keeps them in React state,
caps them at 20 (`:36`), and loses them on reload. No other user can ever receive one.
The four `notificationSettings` toggles in `SettingsPage.jsx:31-38` are persisted to
`localStorage` and read by nothing.

Result: a cashier who needs the registrar to action something has to walk over and ask.

## 2. Goals

1. Any staff member can post an announcement that all other staff can read, with an
   author and a timestamp, and see which announcements they have already read.
2. Any two staff members can hold a private, persisted direct-message conversation and
   return to its history later.
3. The existing bell shows a real, server-backed unread count across both features.

## 3. Non-goals (explicitly out of scope, v1)

Attachments · reactions or emoji · thread replies · editing or deleting sent messages ·
full-text search · WebSockets or push · mobile/background delivery · per-person read
receipts for announcements (a read marker only) · message moderation or retention
policies.

Also out of scope: introducing a role model. The codebase has only `is_staff` /
`is_superuser` (`staff/models.py` has no role field), and adding one is a separate
concern. Anyone who can sign in can post; every message is attributed to a real
`User` FK.

---

## 4. Decisions made (confirm or override these)

| # | Decision | Rationale |
|---|---|---|
| D1 | **Short-polling, not WebSockets** | No Channels, no `ASGI_APPLICATION`, no Redis, no Celery in `requirements.txt`. Waitress is WSGI/thread-based. Adding ASGI would mean daphne + a channel layer + reconfiguring the `DarkZSMS-Backend` NSSM service. Polling is sufficient for a school office. |
| D2 | **Poll every 20s, only when the tab is visible** | Avoids burning the `user: 1000/hour` throttle (`settings.py:338-341`) and pointless traffic. 20s is a reasonable "office chat" latency. |
| D3 | **New `messaging/` Django app** | Follows the per-domain app convention already used by `dorm`, `tours`, `graduation`, `assessment`. The empty `accounts/` stub was rejected — the name implies auth. |
| D4 | **Routed at `/api/messaging/` via its own `urls.py`** | Exactly the `school_config` pattern: `path('api/', include('school_config.urls'))` at `school_pos/urls.py:38`. |
| D5 | **Announcements have no replies** | Keeps it to one model and one feed. Replies would immediately require threads. |
| D6 | **A DM is exactly two people, stored as a canonical ordered pair** | Avoids a participants M2M and a group-permission matrix in v1. `user_a.id < user_b.id` is enforced on creation so the same pair can never produce two conversations. |
| D7 | **No end-to-end encryption** | Messages are staff business communication, not regulated data. Server must read them to enforce participant checks and power search later. |
| D8 | **Soft-delete not implemented; authors can delete their own announcement** | Simplest defensible rule for v1. |

---

## 5. Architecture

```
Browser (React SPA)
  MessagesPage.jsx  ── tabs: Announcements | Direct Messages
        │
        │  axios  Authorization: Token <…>          (api.js:42 interceptor)
        ▼
  Cloudflare Worker  nexus-bridge  (gw.darkzhub.asia)
        │  allowlisted CORS, strips upstream CORS
        ▼
  cloudflared tunnel  sms2-backend  →  localhost:8000
        ▼
  Waitress (WSGI, 8 threads)  →  Django
        ▼
  messaging/ app  (views → serializers → models → PostgreSQL)
```

Polling reuses the existing axios instance, so auth, the 401 handler, and the
pagination auto-unflattening interceptor (`api.js:103-111`) all apply unchanged.

## 6. Data model

New file `school_pos/messaging/models.py`. All models reference
`django.contrib.auth.models.User`.

```python
class Announcement(models.Model):
    title     = models.CharField(max_length=200)
    body      = models.TextField()
    author    = models.ForeignKey(User, on_delete=models.PROTECT, related_name="announcements")
    is_pinned = models.BooleanField(default=False)      # sorts above the rest
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_pinned", "-created_at"]


class AnnouncementRead(models.Model):
    announcement = models.ForeignKey(Announcement, on_delete=models.CASCADE, related_name="reads")
    user         = models.ForeignKey(User, on_delete=models.CASCADE, related_name="announcement_reads")
    read_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["announcement", "user"], name="uniq_announcement_read")
        ]


class Conversation(models.Model):
    user_a          = models.ForeignKey(User, on_delete=models.CASCADE, related_name="conversations_as_a")
    user_b          = models.ForeignKey(User, on_delete=models.CASCADE, related_name="conversations_as_b")
    created_at      = models.DateTimeField(auto_now_add=True)
    last_message_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user_a", "user_b"], name="uniq_dm_pair")
        ]


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender       = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_messages")
    body         = models.TextField()
    created_at   = models.DateTimeField(auto_now_add=True)
    read_at      = models.DateTimeField(null=True, blank=True)   # set when the recipient opens it
```

`on_delete=models.PROTECT` on `Announcement.author` is deliberate: deleting a staff
account must not silently orphan announcements other people need to read.

**Canonical pair.** A helper enforces ordering before any create:

```python
def canonical_pair(u1, u2):
    a, b = sorted([u1, u2], key=lambda u: u.id)
    return a, b
```

`Conversation.objects.get_or_create(user_a=a, user_b=b)` then makes starting a DM
idempotent — clicking the same person twice reuses the thread.

## 7. API surface

All endpoints `permission_classes = [IsAuthenticated]`.

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/messaging/staff/` | Recipient picker: id, full name, `department`, `position`, avatar. Excludes the caller. |
| GET | `/api/messaging/announcements/` | List, paginated. Each item carries `is_read` for the caller and `read_count`. |
| POST | `/api/messaging/announcements/` | Create. `author` is forced to `request.user`, never taken from the body. |
| POST | `/api/messaging/announcements/{id}/read/` | Idempotent mark-read for the caller. |
| DELETE | `/api/messaging/announcements/{id}/` | Author or superuser only. |
| GET | `/api/messaging/conversations/` | Caller's threads: other participant, last message, unread count. |
| POST | `/api/messaging/conversations/` | Body `{user_id}`. Returns existing or new thread. |
| GET | `/api/messaging/conversations/{id}/messages/` | History, paginated, oldest-first. Side effect: marks the thread read for the caller. |
| POST | `/api/messaging/conversations/{id}/messages/` | Send. Rejects non-participants with 403. |
| GET | `/api/messaging/unread-count/` | Single cheap poll for the badge: `{announcements: n, messages: n, total: n}`. |

The badge endpoint is deliberately one aggregated query set rather than N requests —
it is the only endpoint polled continuously.

Implementation follows the canonical ViewSet shape in `api/views.py:2229-2250`
(`queryset` / `serializer_class` / `permission_classes` as class attributes,
`get_queryset()` for scoping, `@action` for extras).

## 8. Frontend

**New file** `frontend/src/pages/MessagesPage.jsx`, following the `TracksPage`
pattern already described in the project memory: coloured stat cards
(`rounded-2xl p-4 border border-transparent`), search card (`rounded-2xl border-gray-100`),
modal (`backdrop-blur-sm`, `rounded-2xl shadow-2xl`, sticky header), and local `toast`.

Structure:
- Header stat cards: unread announcements, unread messages, total threads.
- Tab 1 **Announcements** — pinned first, unread marked, compose modal for staff,
  "Mark all read".
- Tab 2 **Direct Messages** — thread list + selected thread; composer at the bottom.

**`api.js`** — new group alongside the existing ones (pattern at `api.js:413-420`):

```js
export const messagingAPI = {
  listStaff:        () => data(apiClient.get('/api/messaging/staff/')),
  listAnnouncements:() => data(apiClient.get('/api/messaging/announcements/')),
  createAnnouncement:(d) => data(apiClient.post('/api/messaging/announcements/', d)),
  markAnnouncementRead:(id) => data(apiClient.post(`/api/messaging/announcements/${id}/read/`)),
  deleteAnnouncement:(id) => data(apiClient.delete(`/api/messaging/announcements/${id}/`)),
  listConversations:() => data(apiClient.get('/api/messaging/conversations/')),
  startConversation:(userId) => data(apiClient.post('/api/messaging/conversations/', { user_id: userId })),
  listMessages:(id, params) => data(apiClient.get(`/api/messaging/conversations/${id}/messages/`, { params })),
  sendMessage:(id, body) => data(apiClient.post(`/api/messaging/conversations/${id}/messages/`, { body })),
  unreadCount:      () => data(apiClient.get('/api/messaging/unread-count/')),
}
```

**Wiring — three places, matching how every other page is registered:**
1. `App.jsx:11-30` — `const MessagesPage = lazy(() => import('./pages/MessagesPage'))`
2. `App.jsx:61-82` — `routeTitles['/messages'] = 'Messages'`
3. `MainLayout.jsx:36-78` — add to `navigationGroups` (not `adminOnly`)

**Bell repoint.** `NotificationContext` gains a server-backed feed. The existing local
`notifyPayment`/`notifyEnrollment` calls stay (they are useful immediate feedback), but
the dropdown list becomes a merge of: server announcements + DM previews, refreshed by
the 20s poll. This is deliberately additive so the bell never appears broken on a failed
poll — on error, keep the last good payload and skip the update.

**Polling lifecycle** (this would be the first `setInterval` in the codebase, so it
must be correct):

```js
useEffect(() => {
  let timer = null
  const tick = () => {
    if (document.visibilityState === 'visible') refreshUnread()
    timer = setTimeout(tick, 20000)   // timeout chain, not setInterval
  }
  tick()
  return () => clearTimeout(timer)
}, [])
```

A recursive `setTimeout` rather than `setInterval` means a slow response cannot queue up
overlapping requests. Visibility-gated so a backgrounded tab costs nothing.

## 9. Security & privacy

- **Participant enforcement is the critical control.** Every conversation endpoint calls
  a shared guard that returns 403 unless `request.user` is `user_a` or `user_b`. Without
  this, any authenticated staff member could read any DM by guessing an id.
- **`author`/`sender` are always server-derived** from `request.user`, never read from
  the request body, so messages cannot be forged.
- **Message bodies render as plain text.** No `dangerouslySetInnerHTML` anywhere; this
  avoids stored XSS entirely.
- **Body length cap** of 5,000 characters, enforced server-side, to stop the text field
  being used as unbounded storage.
- **Pagination** on both announcements and message history.
- **No student PII in messages.** This system holds data on minors. The spec adds no
  technical control for that, so it is stated as a usage rule in the compose UI as a
  one-line hint, not as enforcement.
- Messages are visible to all staff in the announcement feed and to the two
  participants in a DM. There is no encryption at rest (D7).

## 10. Error handling

| Case | Behaviour |
|---|---|
| Non-participant opens a thread | 403 `{"error": "..."}`, matching the existing `{"error": ...}` convention at `api/views.py:266-269` |
| Empty / whitespace body | 400 |
| Body over 5,000 chars | 400 |
| Unknown staff id when starting a DM | 404 |
| Announce/serve the same staff id twice | Idempotent — reuses the thread |
| Poll fails | Silent. Keep last count, retry on next tick, no toast spam |
| Send fails | Toast + keep the text in the composer so nothing is lost |

## 11. Testing

**Backend** (`APIClient`, new `messaging/tests.py`):
- Non-participant gets 403 on message list and send — the highest-value test here.
- `author`/`sender` cannot be spoofed via the request body.
- Starting a DM twice returns the same conversation id.
- Ordering is canonical regardless of argument order.
- Mark-announcement-read is idempotent and does not double-count.
- Unread count decrements after reading.
- Empty body rejected; over-length body rejected.

**Frontend** manual checklist: unread badge increments; opening a thread clears it;
announcement compose → appears for a second browser; refresh does not lose an open
thread; backgrounded tab issues no requests.

## 12. Rollout

1. `messaging/` app: `models.py`, `serializers.py`, `views.py`, `urls.py`, `admin.py`
2. Register in `INSTALLED_APPS` (`settings.py`, near the other domain apps)
3. `path("api/messaging/", include("messaging.urls"))` in `school_pos/urls.py`
4. `makemigrations messaging` → `0001_initial`
5. `manage.py check` and `manage.py test messaging`
6. Restart the `DarkZSMS-Backend` service
7. Frontend: `api.js` group → `MessagesPage.jsx` → route + title + nav → bell repoint
8. Build, deploy to `sms-3`, hard refresh

**Risk:** low. Additive only — no existing model, endpoint, or page is modified. The
only change to shared code is additive entries in `NotificationContext`, `App.jsx`, and
`MainLayout.jsx`. Reversible by removing the nav entry.

## 13. Open items for you to confirm

1. **Poll interval of 20s** — acceptable, or do you want snappier/cheaper?
2. **Anyone can post announcements** — or restrict to `is_superuser`?
3. **No replies on announcements** — correct, or do you need threaded discussion?
4. **Retention** — messages kept indefinitely. Is there a school policy or expected
   term that needs a cleanup job?
5. **Group messaging** — deliberately excluded from v1. Confirm that is acceptable.
