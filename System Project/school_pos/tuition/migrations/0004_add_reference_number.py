from django.db import migrations, models


def add_reference_number_if_missing(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = 'tuition_tuitionpayment' AND column_name = 'reference_number'"
        )
        if not cursor.fetchone():
            cursor.execute(
                "ALTER TABLE tuition_tuitionpayment "
                "ADD COLUMN reference_number varchar(20) NULL UNIQUE"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS tuition_tui_referen_cafcf0_idx "
                "ON tuition_tuitionpayment (reference_number)"
            )


class Migration(migrations.Migration):

    dependencies = [
        ('tuition', '0003_tuitionpayment_notes_tuitionpayment_payment_date_and_more'),
    ]

    operations = [
        migrations.RunPython(add_reference_number_if_missing, reverse_code=migrations.RunPython.noop),
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name='tuitionpayment',
                    name='reference_number',
                    field=models.CharField(blank=True, max_length=20, null=True, unique=True),
                ),
                migrations.AddIndex(
                    model_name='tuitionpayment',
                    index=models.Index(fields=['reference_number'], name='tuition_tui_referen_cafcf0_idx'),
                ),
            ],
            database_operations=[],
        ),
    ]
