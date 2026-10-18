import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("teams", "0004_populate_default_season"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="team",
            options={
                "ordering": ["saison__startdatum", "name"],
                "verbose_name": "Mannschaft",
                "verbose_name_plural": "Mannschaften",
            },
        ),
        migrations.AlterField(
            model_name="team",
            name="saison",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="teams",
                to="teams.season",
                verbose_name="Saison",
            ),
        ),
        migrations.AddConstraint(
            model_name="team",
            constraint=models.UniqueConstraint(
                fields=("name", "saison"), name="unique_team_per_saison"
            ),
        ),
    ]
