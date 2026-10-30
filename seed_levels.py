import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'quiz.settings')
django.setup()

from django.contrib.auth.models import User
from main.models import Quiz, Question, Answer


USER_CANDIDATES = [
    {'username': 'admin', 'password': 'admin123'},
    {'username': 'quizmaster', 'password': 'admin123'},
]


def get_user():
    user = User.objects.filter(is_superuser=True).first() or User.objects.order_by('id').first()
    if user is not None:
        return user
    for candidate in USER_CANDIDATES:
        if not User.objects.filter(username=candidate['username']).exists():
            return User.objects.create_user(username=candidate['username'], password=candidate['password'])
    return User.objects.create_user(username='admin_seed', password='admin123')


def ensure_question(quiz, order, prompt, choices, correct_index):
    question = Question.objects.filter(quiz=quiz, order=order).first()
    if question is None:
        question = Question.objects.create(quiz=quiz, prompt=prompt, order=order)
    else:
        question.prompt = prompt
        question.save(update_fields=['prompt'])

    Answer.objects.filter(question=question).delete()
    for index, text in enumerate(choices):
        Answer.objects.create(
            question=question,
            text=text,
            is_correct=index == correct_index,
            order=index + 1,
        )


def ensure_quiz(category, level_number, title, description, difficulty, questions):
    quiz = Quiz.objects.filter(category=category, level_number=level_number).first()
    if quiz is None:
        quiz = Quiz.objects.create(
            title=title,
            description=description,
            category=category,
            difficulty=difficulty,
            created_by=user,
            invite_code=f'QZ-{category.upper()[:3]}{level_number}',
            level_number=level_number,
            is_public=True,
        )
    else:
        quiz.title = title
        quiz.description = description
        quiz.difficulty = difficulty
        quiz.save(update_fields=['title', 'description', 'difficulty'])

    for idx, item in enumerate(questions, start=1):
        ensure_question(quiz, idx, item['prompt'], item['choices'], item['correct_index'])

    return quiz


user = get_user()

ensure_quiz(
    'games',
    1,
    'Ігрова гілка: рівень 1',
    'Початкова гра про відеоігри та жанри.',
    'easy',
    [
        {
            'prompt': 'Яка гра відома персонажем Маріо?',
            'choices': ['Super Mario', 'Minecraft', 'GTA', 'The Sims'],
            'correct_index': 0,
        },
        {
            'prompt': 'Яка платформа зберегла жанр RPG?',
            'choices': ['Nintendo Switch', 'Телефон', 'Посудомийка', 'Калькулятор'],
            'correct_index': 0,
        },
    ],
)

ensure_quiz(
    'games',
    2,
    'Ігрова гілка: рівень 2',
    'Складніші питання про ігровий світ.',
    'hard',
    [
        {
            'prompt': 'Хто створив Minecraft?',
            'choices': ['Mojang', 'Epic Games', 'Ubisoft', 'Valve'],
            'correct_index': 0,
        },
        {
            'prompt': 'Яка гра вважається класикою шутера?',
            'choices': ['Doom', 'Tetris', 'Pac-Man', 'Snake'],
            'correct_index': 0,
        },
    ],
)

ensure_quiz(
    'movies',
    1,
    'Кіногілка: рівень 1',
    'Короткий шлях про фільми та героїв.',
    'easy',
    [
        {
            'prompt': 'Хто грав головного героя у фільмі “Той, хто біжить по лезу”?',
            'choices': ['Річард Бартон', 'Гаррісон Форд', 'Брюс Вілліс', 'Раян Гослінг'],
            'correct_index': 0,
        },
        {
            'prompt': 'Який жанр має фільм “Аватар”?',
            'choices': ['Фантастика', 'Комедія', 'Мелодрама', 'Документальний'],
            'correct_index': 0,
        },
    ],
)

ensure_quiz(
    'movies',
    2,
    'Кіногілка: рівень 2',
    'Складніше про кіно і спецефекти.',
    'hard',
    [
        {
            'prompt': 'Який фільм став відомий завдяки фразі “Я не можу зробити це”?',
            'choices': ['Ірон Людина', 'Тор', 'Матриця', 'Зоряні війни'],
            'correct_index': 0,
        },
        {
            'prompt': 'Хто режисер фільму “Початок”?',
            'choices': ['Крістофер Нолан', 'Стенлі Кубрик', 'Педро Альмодовар', 'Тім Бертон'],
            'correct_index': 0,
        },
    ],
)

ensure_quiz(
    'school',
    1,
    'Шкільна гілка: рівень 1',
    'Основні предмети та базові знання.',
    'easy',
    [
        {
            'prompt': 'Який предмет вивчає закони природи?',
            'choices': ['Фізика', 'Математика', 'Література', 'Географія'],
            'correct_index': 0,
        },
        {
            'prompt': 'Який предмет вивчає історію?',
            'choices': ['Історія', 'Біологія', 'Хімія', 'Музика'],
            'correct_index': 0,
        },
    ],
)

ensure_quiz(
    'school',
    2,
    'Шкільна гілка: рівень 2',
    'Складніше про предмети та уроки.',
    'hard',
    [
        {
            'prompt': 'Який предмет вивчає будову клітин?',
            'choices': ['Біологія', 'Українська мова', 'Фізкультура', 'Мистецтво'],
            'correct_index': 0,
        },
        {
            'prompt': 'Який предмет допомагає розвивати логічне мислення?',
            'choices': ['Математика', 'Історія', 'Географія', 'Трудове навчання'],
            'correct_index': 0,
        },
    ],
)

ensure_quiz(
    'science',
    1,
    'Наукова гілка: рівень 1',
    'Питання про космос, природу та відкриття.',
    'easy',
    [
        {
            'prompt': 'Яка планета найближча до Сонця?',
            'choices': ['Меркурій', 'Венера', 'Марс', 'Земля'],
            'correct_index': 0,
        },
        {
            'prompt': 'Що є основною одиницею життя?',
            'choices': ['Клітина', 'Молекула', 'Атом', 'Тканина'],
            'correct_index': 0,
        },
    ],
)

ensure_quiz(
    'science',
    2,
    'Наукова гілка: рівень 2',
    'Складніші питання про фізику та космос.',
    'hard',
    [
        {
            'prompt': 'Яка сила утримує планети навколо Сонця?',
            'choices': ['Гравітація', 'Електрика', 'Магнетизм', 'Тиск'],
            'correct_index': 0,
        },
        {
            'prompt': 'Який газ найбільше в атмосфері Землі?',
            'choices': ['Азот', 'Кисень', 'Вуглекислий газ', 'Гелій'],
            'correct_index': 0,
        },
    ],
)

ensure_quiz(
    'history',
    1,
    'Історична гілка: рівень 1',
    'Базові факти про давні цивілізації й події.',
    'easy',
    [
        {
            'prompt': 'Хто був першим президентом США?',
            'choices': ['Джордж Вашингтон', 'Авраам Лінкольн', 'Томас Джефферсон', 'Бенджамін Франклін'],
            'correct_index': 0,
        },
        {
            'prompt': 'Яка цивілізація побудувала піраміди?',
            'choices': ['Стародавні єгиптяни', 'Римляни', 'Греки', 'Вікінги'],
            'correct_index': 0,
        },
    ],
)

ensure_quiz(
    'history',
    2,
    'Історична гілка: рівень 2',
    'Більш складні питання про війну та держави.',
    'hard',
    [
        {
            'prompt': 'У який рік відбулася Перша світова війна?',
            'choices': ['1914', '1812', '1945', '1700'],
            'correct_index': 0,
        },
        {
            'prompt': 'Хто був останнім імператором Російської імперії?',
            'choices': ['Микола II', 'Петро I', 'Олександр III', 'Олександр II'],
            'correct_index': 0,
        },
    ],
)

ensure_quiz(
    'sports',
    1,
    'Спортивна гілка: рівень 1',
    'Тести про популярні види спорту та чемпіонати.',
    'easy',
    [
        {
            'prompt': 'Скільки гравців у стандартній команді футболу на полі?',
            'choices': ['11', '9', '7', '15'],
            'correct_index': 0,
        },
        {
            'prompt': 'Який вид спорту включає “свічку”?',
            'choices': ['Фігурне катання', 'Баскетбол', 'Бокс', 'Теніс'],
            'correct_index': 0,
        },
    ],
)

ensure_quiz(
    'sports',
    2,
    'Спортивна гілка: рівень 2',
    'Складніші задачі про рекорди та турніри.',
    'hard',
    [
        {
            'prompt': 'Якій країні належить стадіон “Маракана”?',
            'choices': ['Бразилія', 'Іспанія', 'Німеччина', 'Італія'],
            'correct_index': 0,
        },
        {
            'prompt': 'У якому спорті використовують “шахи” в дії?',
            'choices': ['Шахи', 'Гольф', 'Бадмінтон', 'Хокей'],
            'correct_index': 0,
        },
    ],
)

ensure_quiz(
    'music',
    1,
    'Музична гілка: рівень 1',
    'Основи музики та відомі інструменти.',
    'easy',
    [
        {
            'prompt': 'Який інструмент має 88 клавіш?',
            'choices': ['Піаніно', 'Гітара', 'Скрипка', 'Труба'],
            'correct_index': 0,
        },
        {
            'prompt': 'Який темп характеризує швидку музику?',
            'choices': ['Алігро', 'Ленто', 'Адажіо', 'Сольо'],
            'correct_index': 0,
        },
    ],
)

ensure_quiz(
    'music',
    2,
    'Музична гілка: рівень 2',
    'Питання про жанри, композиторів та ритм.',
    'hard',
    [
        {
            'prompt': 'Хто написав “Лунну сонату”?',
            'choices': ['Бетховен', 'Моцарт', 'Шуберт', 'Чайковський'],
            'correct_index': 0,
        },
        {
            'prompt': 'Який жанр пов’язаний з електронною музикою?',
            'choices': ['EDM', 'Класика', 'Фолк', 'Блюз'],
            'correct_index': 0,
        },
    ],
)

ensure_quiz(
    'other',
    1,
    'Інша гілка: рівень 1',
    'Загальні знання на різні теми.',
    'easy',
    [
        {
            'prompt': 'Яка мова використовується для стилізації веб-сторінок?',
            'choices': ['CSS', 'HTML', 'SQL', 'Python'],
            'correct_index': 0,
        },
        {
            'prompt': 'Яка країна має найбільше озер у світі?',
            'choices': ['Канада', 'Україна', 'Франція', 'Японія'],
            'correct_index': 0,
        },
    ],
)

ensure_quiz(
    'other',
    2,
    'Інша гілка: рівень 2',
    'Кросс-тематичні питання для веселого тренування.',
    'hard',
    [
        {
            'prompt': 'Який символ використовується для коментаря в Python?',
            'choices': ['#', '@', '/', '*'],
            'correct_index': 0,
        },
        {
            'prompt': 'Яка столиця Японії?',
            'choices': ['Токіо', 'Осака', 'Кіото', 'Нагоя'],
            'correct_index': 0,
        },
    ],
)

print(list(Quiz.objects.order_by('category', 'level_number').values_list('category', 'title', 'level_number')))
