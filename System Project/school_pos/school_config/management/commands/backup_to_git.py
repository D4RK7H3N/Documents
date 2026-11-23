"""
Off-site backup of the school system: the database and the uploaded files.

The school runs its own server, so the database (on Railway) and the uploaded
media (on this machine) are the only things that would be lost if the machine
died. This command copies both into a private GitHub repository, which costs
nothing and needs no payment method:

    python manage.py backup_to_git

It is meant to run from a scheduled task once a day. Every run replaces
db.json and the media/ folder, so the repository history keeps the earlier
snapshots without the working copy growing.
"""
import datetime
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand

# Excluded models:
#  - contenttypes / permissions / migrations: rebuilt from the code
#  - sessions: worthless after a restart
#  - authtoken: live API credentials - they must never leave the server
#  - admin.logentry: noise
EXCLUDE = [
    "contenttypes",
    "auth.permission",
    "sessions",
    "authtoken.token",
    "admin.logentry",
]


class Command(BaseCommand):
    help = "Back up the database and uploaded media to the private backup repository."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dir",
            default=os.environ.get("SMS_BACKUP_DIR", r"C:\SMS-Backup"),
            help="Where the backup repository is cloned (default C:\\SMS-Backup).",
        )
        parser.add_argument(
            "--remote",
            default=os.environ.get(
                "SMS_BACKUP_REMOTE", "https://github.com/D4RK7H3N/SMS-Backup.git"
            ),
            help="The private repository the backup is pushed to.",
        )
        parser.add_argument(
            "--no-push",
            action="store_true",
            help="Refresh the files but do not commit or push.",
        )

    def handle(self, *args, **options):
        root = Path(options["dir"])
        repo = root / "repo"
        stamp = datetime.datetime.now().isoformat(timespec="seconds")

        if not (repo / ".git").exists():
            root.mkdir(parents=True, exist_ok=True)
            self.stdout.write(f"Cloning the backup repository into {repo} ...")
            subprocess.run(
                ["git", "clone", options["remote"], str(repo)],
                check=True,
                capture_output=True,
                text=True,
            )

        # ---- database ------------------------------------------------------
        db_target = repo / "db.json"
        self.stdout.write("Dumping the database ...")
        with db_target.open("w", encoding="utf-8") as fh:
            # `exclude` is an OPTION, not a list of labels. Passing the
            # exclusions positionally made dumpdata dump ONLY those models,
            # which left the backup without students, sales or products.
            call_command(
                "dumpdata",
                exclude=list(EXCLUDE),
                natural_foreign=True,
                natural_primary=True,
                indent=1,
                stdout=fh,
            )
        db_size = db_target.stat().st_size

        # ---- uploaded files -------------------------------------------------
        media_source = Path(settings.MEDIA_ROOT)
        media_target = repo / "media"
        if media_source.exists():
            if media_target.exists():
                shutil.rmtree(media_target)
            shutil.copytree(media_source, media_target)
            file_count = sum(1 for p in media_target.rglob("*") if p.is_file())
            media_size = sum(p.stat().st_size for p in media_target.rglob("*") if p.is_file())
        else:
            file_count = 0
            media_size = 0

        (repo / "MANIFEST.txt").write_text(
            "\n".join(
                [
                    f"backup taken: {stamp}",
                    f"database dump: {db_size / 1048576:.2f} MB (db.json)",
                    f"uploaded files: {file_count} files, {media_size / 1048576:.2f} MB (media/)",
                    "",
                    "Restore: copy db.json back with",
                    "  python manage.py loaddata db.json",
                    "and the media folder into MEDIA_ROOT.",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        self.stdout.write(
            f"Prepared: db.json {db_size / 1048576:.2f} MB, media {file_count} files"
        )

        if options["no_push"]:
            self.stdout.write("Not committing (--no-push).")
            return

        def git(*args):
            return subprocess.run(
                ["git", *args],
                cwd=repo,
                check=True,
                capture_output=True,
                text=True,
            )

        git("add", "-A")
        status = git("status", "--porcelain").stdout.strip()
        if not status:
            self.stdout.write("Nothing changed - the backup is already up to date.")
            return

        git("commit", "-m", f"backup {stamp}")
        git("push", "origin", "HEAD")
        self.stdout.write(self.style.SUCCESS(f"Backup pushed: {stamp}"))
