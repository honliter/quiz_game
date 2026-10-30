from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='quiz',
            name='category',
            field=models.CharField(
                choices=[
                    ('games', 'Ігри'),
                    ('movies', 'Кіно та серіали'),
                    ('science', 'Наука'),
                    ('history', 'Історія'),
                    ('sports', 'Спорт'),
                    ('music', 'Музика'),
                    ('other', 'Інше'),
                ],
                default='other',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='quiz',
            name='difficulty',
            field=models.CharField(
                choices=[
                    ('easy', 'Легка'),
                    ('medium', 'Середня'),
                    ('hard', 'Складна'),
                ],
                default='medium',
                max_length=10,
            ),
        ),
    ]