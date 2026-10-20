import secrets
import members.models
from django.db import migrations, models


def populate_member_ical_tokens(apps, schema_editor):
    Member = apps.get_model('members', 'Member')
    for member in Member.objects.all():
        member.ical_token = secrets.token_urlsafe(24)
        member.save(update_fields=['ical_token'])


class Migration(migrations.Migration):

    dependencies = [
        ('members', '0005_member_dwz_member_dwz_index_member_fide_id_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='member',
            name='ical_token',
            field=models.CharField(default=members.models.generate_ical_token, max_length=64, null=True, verbose_name='iCal-Token'),
        ),
        migrations.RunPython(populate_member_ical_tokens, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='member',
            name='ical_token',
            field=models.CharField(default=members.models.generate_ical_token, max_length=64, unique=True, verbose_name='iCal-Token'),
        ),
    ]
