from django.db import migrations


class Migration(migrations.Migration):
    """The tuition fee is collected in four terms, not four quarters.

    Renamed rather than re-created so every existing breakdown keeps its
    amounts.
    """

    dependencies = [
        ("tuition", "0009_tuitionpayment_created_by_tuitionpayment_terminal"),
    ]

    operations = [
        migrations.RenameField(
            model_name="tuitionbreakdown",
            old_name="first_quarter",
            new_name="first_term",
        ),
        migrations.RenameField(
            model_name="tuitionbreakdown",
            old_name="second_quarter",
            new_name="second_term",
        ),
        migrations.RenameField(
            model_name="tuitionbreakdown",
            old_name="third_quarter",
            new_name="third_term",
        ),
        migrations.RenameField(
            model_name="tuitionbreakdown",
            old_name="fourth_quarter",
            new_name="final_term",
        ),
    ]
