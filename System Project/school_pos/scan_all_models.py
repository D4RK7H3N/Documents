"""Scan every model in the project and print the row counts, so nothing that
holds a transaction is missed."""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "school_pos.settings")
django.setup()

from django.apps import apps  # noqa: E402

rows = []
for model in apps.get_models():
    try:
        count = model.objects.count()
    except Exception as exc:  # a model without a table (proxy/m2m)
        continue
    if count:
        rows.append((model._meta.app_label, model.__name__, count))

rows.sort(key=lambda r: -r[2])
for app, name, count in rows:
    print("%-14s %-26s %d" % (app, name, count))
print("---")
print("models with rows:", len(rows))
