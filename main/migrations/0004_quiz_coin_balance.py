from django.db import migrations, models


def backfill_quiz_coins(apps, schema_editor):
    QuizAttempt = apps.get_model('main', 'QuizAttempt')
    UserProfile = apps.get_model('main', 'UserProfile')
    database = schema_editor.connection.alias
    coins_by_user = {}

    completed_attempts = QuizAttempt.objects.using(database).filter(
        completed_at__isnull=False,
    )
    for attempt in completed_attempts.iterator():
        attempt.coins_earned = attempt.score * 10
        attempt.save(update_fields=['coins_earned'], using=database)
        coins_by_user[attempt.user_id] = coins_by_user.get(attempt.user_id, 0) + attempt.coins_earned

    for user_id, coins in coins_by_user.items():
        profile, created = UserProfile.objects.using(database).get_or_create(
            user_id=user_id,
            defaults={'quiz_coins': coins},
        )
        if not created:
            profile.quiz_coins = coins
            profile.save(update_fields=['quiz_coins'], using=database)


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0003_alter_quiz_options_quiz_level_number'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='quiz_coins',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='quizattempt',
            name='coins_earned',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.RunPython(backfill_quiz_coins, migrations.RunPython.noop),
    ]
