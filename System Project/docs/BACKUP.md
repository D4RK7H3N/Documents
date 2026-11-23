# Off-site backup of the school management system

Automatic backup of the **database** and the **uploaded files** (student
photos, documents, school logo) to a private GitHub repository:
https://github.com/D4RK7H3N/SMS-Backup

It costs nothing and needs no payment method. The repository is private, so
nothing here is public.

## What is backed up

| Path | What it is | Restore with |
|---|---|---|
| `db.json` | Django data dump of every table (except sessions and API tokens) | `python manage.py loaddata db.json` |
| `media/` | Everything uploaded through the app (photos, documents, logo) | copy the folder into `MEDIA_ROOT` |
| `MANIFEST.txt` | When the backup was taken and what it contains | - |

The database itself lives on Railway, so it is already off this machine; the
media folder was the only thing that was kept nowhere else.

## Running it

```
cd C:\Users\DarkZhen\Documents\System Project\school_pos
.venv\Scripts\python.exe manage.py backup_to_git
```

It clones the repository into `C:\SMS-Backup\repo` on the first run, replaces
`db.json` and `media/`, commits and pushes. The repository history keeps the
earlier snapshots.

Options:

- `--no-push` — refresh the files without committing
- `--dir <path>` — use a different working folder
- `--remote <url>` — back up somewhere else

## Automatic run

A scheduled task runs it every night at 02:00:

```
schtasks /query /tn "SMS-Backup"
```

## Note on what is left out

`rest_framework.authtoken` rows are never included - they are live API
credentials and must not leave the server. Sessions are excluded because they
are worthless after a restart. Permissions and content types are rebuilt from
the code.
