from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import F, Q
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.crypto import get_random_string

from .models import Answer, Question, Quiz, QuizAttempt, QuizAttemptAnswer, UserProfile


def home(request):
    search_query = request.GET.get('q', '').strip()
    quiz_queryset = Quiz.objects.filter(is_public=True)

    if search_query:
        quiz_queryset = quiz_queryset.filter(
            Q(title__icontains=search_query)
            | Q(description__icontains=search_query)
            | Q(category__icontains=search_query)
        )

    quizzes = list(quiz_queryset.order_by('-created_at')[:6])
    branch_order = ['games', 'movies', 'school', 'science', 'history', 'sports', 'music', 'other']
    campaign_branches = []

    for branch_key, branch_label in Quiz.CATEGORY_CHOICES:
        if branch_key not in branch_order:
            branch_order.append(branch_key)

    for branch_key in branch_order:
        branch_quizzes = quiz_queryset.filter(category=branch_key).order_by('level_number')
        if not branch_quizzes.exists():
            continue
        for quiz in branch_quizzes:
            if request.user.is_authenticated:
                quiz.unlocked = quiz.is_unlocked_for_user(request.user)
            else:
                quiz.unlocked = quiz.level_number == 1
        campaign_branches.append({
            'key': branch_key,
            'label': dict(Quiz.CATEGORY_CHOICES).get(branch_key, branch_key),
            'quizzes': list(branch_quizzes),
        })

    if not campaign_branches:
        campaign_levels = []
    else:
        campaign_levels = [quiz for branch in campaign_branches for quiz in branch['quizzes']]

    return render(request, 'main/home.html', {
        'quizzes': quizzes,
        'campaign_levels': campaign_levels,
        'campaign_branches': campaign_branches,
        'search_query': search_query,
        'stats': {
            'quizzes_total': Quiz.objects.filter(is_public=True).count(),
            'players_total': User.objects.count(),
            'categories_total': len(Quiz.CATEGORY_CHOICES),
        },
    })


def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            UserProfile.objects.get_or_create(user=user)
            login(request, user)
            messages.success(request, 'Реєстрація успішна!')
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'main/register.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            UserProfile.objects.get_or_create(user=user)
            login(request, user)
            return redirect('home')
        messages.error(request, 'Невірне ім’я користувача або пароль.')
    return render(request, 'main/login.html')


@login_required
def logout_view(request):
    logout(request)
    return redirect('home')


@login_required
def profile(request):
    profile_obj, _ = UserProfile.objects.get_or_create(user=request.user)
    completed_attempts = request.user.quiz_attempts.filter(completed_at__isnull=False).select_related('quiz').order_by('-completed_at')
    best_score = completed_attempts.order_by('-score').values_list('score', flat=True).first() or 0
    total_questions = sum(attempt.quiz.questions.count() for attempt in completed_attempts)
    total_points = sum(attempt.score for attempt in completed_attempts)
    accuracy = round((total_points / total_questions) * 100, 1) if total_questions else 0
    recent_attempts = list(completed_attempts[:5])
    for attempt in recent_attempts:
        total_questions_in_quiz = attempt.quiz.questions.count()
        attempt.accuracy = round((attempt.score / total_questions_in_quiz) * 100, 1) if total_questions_in_quiz else 0

    return render(request, 'main/profile.html', {
        'profile': profile_obj,
        'stats': {
            'total_attempts': request.user.quiz_attempts.count(),
            'completed_attempts': completed_attempts.count(),
            'best_score': best_score,
            'average_accuracy': accuracy,
        },
        'recent_attempts': recent_attempts,
    })


@login_required
def quiz_create(request):
    answer_slots = range(4)
    question_rows = [{'prompt': '', 'answers': ['', '', '', ''], 'correct': None}]
    errors = []
    selected_category = 'other'
    selected_difficulty = 'medium'
    selected_level_number = 1

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        selected_category = request.POST.get('category', 'other')
        selected_difficulty = request.POST.get('difficulty', 'medium')
        selected_level_number = request.POST.get('level_number', '1').strip()

        try:
            selected_level_number = int(selected_level_number)
        except ValueError:
            selected_level_number = 1

        if selected_level_number >= 2:
            selected_difficulty = 'hard'

        if not title:
            errors.append('Вкажіть назву вікторини.')
        if selected_category not in dict(Quiz.CATEGORY_CHOICES):
            errors.append('Оберіть доступну категорію.')
            selected_category = 'other'
        if selected_difficulty not in dict(Quiz.DIFFICULTY_CHOICES):
            errors.append('Оберіть доступну складність.')
            selected_difficulty = 'medium'
        if selected_level_number < 1:
            errors.append('Рівень кампанії має бути більше 0.')
            selected_level_number = 1

        try:
            question_count = int(request.POST.get('question_count', '0'))
        except ValueError:
            question_count = 0
        if not 1 <= question_count <= 50:
            errors.append('Додайте від 1 до 50 питань.')
            question_count = max(1, min(question_count, 50))

        question_rows = []
        for question_index in range(question_count):
            prompt = request.POST.get(f'question_{question_index}_prompt', '').strip()
            answers = [
                request.POST.get(f'question_{question_index}_answer_{answer_index}', '').strip()
                for answer_index in answer_slots
            ]
            try:
                correct = int(request.POST.get(f'question_{question_index}_correct', ''))
            except ValueError:
                correct = None

            question_rows.append({'prompt': prompt, 'answers': answers, 'correct': correct})
            if not prompt:
                errors.append(f'Заповніть текст питання {question_index + 1}.')
            if any(not answer for answer in answers):
                errors.append(f'Заповніть усі 4 варіанти відповіді для питання {question_index + 1}.')
            if correct not in answer_slots:
                errors.append(f'Позначте правильну відповідь для питання {question_index + 1}.')

        if not errors:
            with transaction.atomic():
                quiz = Quiz.objects.create(
                    title=title,
                    description=description,
                    category=selected_category,
                    difficulty=selected_difficulty,
                    created_by=request.user,
                    invite_code=f'QZ-{get_random_string(8).upper()}',
                    level_number=selected_level_number,
                )
                for question_index, row in enumerate(question_rows):
                    question = Question.objects.create(
                        quiz=quiz,
                        prompt=row['prompt'],
                        order=question_index + 1,
                    )
                    Answer.objects.bulk_create([
                        Answer(
                            question=question,
                            text=answer_text,
                            is_correct=answer_index == row['correct'],
                            order=answer_index + 1,
                        )
                        for answer_index, answer_text in enumerate(row['answers'])
                    ])
            messages.success(request, 'Вікторину успішно створено!')
            return redirect('quiz_detail', quiz_id=quiz.id)

    return render(request, 'main/quiz_create.html', {
        'categories': Quiz.CATEGORY_CHOICES,
        'difficulties': Quiz.DIFFICULTY_CHOICES,
        'selected_category': selected_category,
        'selected_difficulty': selected_difficulty,
        'selected_level_number': selected_level_number,
        'question_rows': question_rows,
        'answer_slots': answer_slots,
        'question_count': len(question_rows),
        'errors': errors,
    })


def quiz_detail(request, quiz_id):
    quiz = Quiz.objects.prefetch_related('questions__answers').get(pk=quiz_id)
    if request.user.is_authenticated and not quiz.is_unlocked_for_user(request.user):
        messages.error(request, 'Спочатку пройдіть попередній рівень, щоб відкрити цей рівень кампанії.')
        return redirect('home')

    selected_answers = {}
    current_attempt = None
    show_results = False
    next_level = quiz.get_next_level()
    next_level_unlocked = bool(next_level and request.user.is_authenticated and next_level.is_unlocked_for_user(request.user))

    if request.user.is_authenticated:
        current_attempt = quiz.attempts.filter(user=request.user, completed_at__isnull=True).order_by('-started_at').first()
        if current_attempt is None:
            current_attempt = quiz.attempts.filter(user=request.user).order_by('-started_at').first()
        if current_attempt and current_attempt.completed_at:
            show_results = True
            selected_answers = {
                item.question_id: item.selected_answer_id
                for item in current_attempt.answers.select_related('selected_answer').all()
            }

    if request.method == 'POST':
        if not request.user.is_authenticated:
            return redirect('login')

        attempt = quiz.attempts.filter(user=request.user, completed_at__isnull=True).order_by('-started_at').first()
        if attempt is None:
            attempt = QuizAttempt.objects.create(quiz=quiz, user=request.user)

        selected_answers = {}
        correct_answers = 0
        for question in quiz.questions.prefetch_related('answers').all():
            selected_id = request.POST.get(f'question_{question.id}')
            if selected_id:
                selected_answer = question.answers.filter(pk=selected_id).first()
                if selected_answer:
                    selected_answers[question.id] = selected_answer.id
                    is_correct = selected_answer.is_correct
                    QuizAttemptAnswer.objects.update_or_create(
                        attempt=attempt,
                        question=question,
                        defaults={'selected_answer': selected_answer, 'is_correct': is_correct},
                    )
                    if is_correct:
                        correct_answers += 1

        coins_earned = correct_answers * QuizAttempt.COINS_PER_POINT
        profile_obj, _ = UserProfile.objects.get_or_create(user=request.user)
        with transaction.atomic():
            attempt.score = correct_answers
            attempt.coins_earned = coins_earned
            attempt.completed_at = timezone.now()
            attempt.save(update_fields=['score', 'coins_earned', 'completed_at'])
            UserProfile.objects.filter(pk=profile_obj.pk).update(
                quiz_coins=F('quiz_coins') + coins_earned,
            )
        show_results = True

        current_attempt = attempt
        selected_answers = {
            item.question_id: item.selected_answer_id
            for item in attempt.answers.select_related('selected_answer').all()
        }

    question_results = []
    for question in quiz.questions.prefetch_related('answers').all():
        correct_answer = question.answers.filter(is_correct=True).first()
        selected_answer_id = selected_answers.get(question.id)
        question_results.append({
            'question': question,
            'answers': list(question.answers.all()),
            'selected_answer_id': selected_answer_id,
            'correct_answer': correct_answer,
            'is_correct': bool(correct_answer and selected_answer_id == correct_answer.id),
            'was_not_answered': selected_answer_id is None,
        })

    return render(request, 'main/quiz_detail.html', {
        'quiz': quiz,
        'selected_answers': selected_answers,
        'show_results': show_results,
        'attempt': current_attempt,
        'question_results': question_results,
        'next_level': next_level,
        'next_level_unlocked': next_level_unlocked,
    })


@login_required
def join_quiz(request, quiz_id):
    quiz = Quiz.objects.get(pk=quiz_id)
    if not quiz.is_unlocked_for_user(request.user):
        messages.error(request, 'Цей рівень ще заблокований. Пройдіть попередній рівень, щоб відкрити його.')
        return redirect('home')

    if request.method == 'POST':
        attempt = quiz.attempts.filter(user=request.user, completed_at__isnull=True).order_by('-started_at').first()
        if attempt is None:
            attempt = QuizAttempt.objects.create(quiz=quiz, user=request.user)
        messages.success(request, 'Ви приєдналися до вікторини!')
        return redirect('quiz_detail', quiz_id=quiz.id)
    return render(request, 'main/join_quiz.html', {'quiz': quiz})


def leaderboard(request):
    attempts = QuizAttempt.objects.select_related('user', 'quiz').order_by('-score')[:10]
    return render(request, 'main/leaderboard.html', {'attempts': attempts})
