from django.contrib import admin

from .models import Answer, Question, Quiz, QuizAttempt, QuizAttemptAnswer, UserProfile


admin.site.register(UserProfile)
admin.site.register(Quiz)
admin.site.register(Question)
admin.site.register(Answer)
admin.site.register(QuizAttempt)
admin.site.register(QuizAttemptAnswer)
