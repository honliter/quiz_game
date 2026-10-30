from django.conf import settings
from django.db import models
from django.utils import timezone


class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(blank=True)
    avatar = models.URLField(blank=True)
    quiz_coins = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.user.username


class Quiz(models.Model):
    CATEGORY_CHOICES = [
        ('games', 'Ігри'),
        ('movies', 'Кіно та серіали'),
        ('school', 'Шкільні предмети'),
        ('science', 'Наука'),
        ('history', 'Історія'),
        ('sports', 'Спорт'),
        ('music', 'Музика'),
        ('other', 'Інше'),
    ]
    DIFFICULTY_CHOICES = [
        ('easy', 'Легка'),
        ('medium', 'Середня'),
        ('hard', 'Складна'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='other')
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default='medium')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='quizzes')
    invite_code = models.CharField(max_length=20, unique=True)
    is_public = models.BooleanField(default=True)
    level_number = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['level_number', 'created_at']

    def __str__(self):
        return self.title

    def is_unlocked_for_user(self, user):
        if not user or not user.is_authenticated:
            return self.level_number == 1
        if self.level_number == 1:
            return True

        branch_key = self.category or 'other'
        previous_levels = Quiz.objects.filter(category=branch_key, level_number__lt=self.level_number).order_by('level_number')

        for previous_level in previous_levels:
            previous_max_score = previous_level.questions.count()
            if not previous_level.attempts.filter(
                user=user,
                completed_at__isnull=False,
                score=previous_max_score,
            ).exists():
                return False

        return True

    def get_next_level(self):
        return Quiz.objects.filter(category=self.category, level_number=self.level_number + 1).order_by('level_number').first()


class Question(models.Model):
    QUESTION_TYPES = [
        ('text', 'Text'),
        ('image', 'Image'),
        ('video', 'Video'),
    ]

    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    prompt = models.CharField(max_length=500)
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES, default='text')
    media_url = models.URLField(blank=True)
    time_limit = models.PositiveIntegerField(default=30)
    order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.quiz.title} - Q{self.order}"


class Answer(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='answers')
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.question} - {self.text[:30]}"


class QuizAttempt(models.Model):
    COINS_PER_POINT = 10

    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='attempts')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='quiz_attempts')
    score = models.PositiveIntegerField(default=0)
    coins_earned = models.PositiveIntegerField(default=0)
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} -> {self.quiz.title}"


class QuizAttemptAnswer(models.Model):
    attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='attempts')
    selected_answer = models.ForeignKey(Answer, on_delete=models.CASCADE, related_name='user_selections')
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.attempt} - {self.question}"
