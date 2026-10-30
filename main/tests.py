from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Answer, Question, Quiz, QuizAttempt


class QuizCreationTests(TestCase):
	def setUp(self):
		self.user = User.objects.create_user(username='quiz_creator', password='test-password-123')
		self.client.force_login(self.user)

	def test_quiz_form_includes_question_and_answer_fields(self):
		response = self.client.get(reverse('quiz_create'))

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'name="question_0_prompt"')
		self.assertContains(response, 'name="question_0_answer_3"')
		self.assertContains(response, 'id="add-question"')

	def test_registered_user_can_create_quiz_with_category_and_difficulty(self):
		response = self.client.post(reverse('quiz_create'), {
			'title': 'Вікторина про ігри',
			'description': 'Перевір свої знання про відеоігри.',
			'category': 'games',
			'difficulty': 'hard',
			'question_count': '2',
			'question_0_prompt': 'Хто створив Minecraft?',
			'question_0_answer_0': 'Mojang',
			'question_0_answer_1': 'Nintendo',
			'question_0_answer_2': 'Valve',
			'question_0_answer_3': 'Epic Games',
			'question_0_correct': '0',
			'question_1_prompt': 'На якій планеті відбувається дія гри?',
			'question_1_answer_0': 'Марс',
			'question_1_answer_1': 'Земля',
			'question_1_answer_2': 'Вигаданий світ',
			'question_1_answer_3': 'Венера',
			'question_1_correct': '2',
		})

		quiz = Quiz.objects.get(title='Вікторина про ігри')
		self.assertRedirects(response, reverse('quiz_detail', args=[quiz.id]))
		self.assertEqual(quiz.created_by, self.user)
		self.assertEqual(quiz.category, 'games')
		self.assertEqual(quiz.difficulty, 'hard')
		self.assertTrue(quiz.invite_code.startswith('QZ-'))
		self.assertEqual(quiz.questions.count(), 2)
		first_question = quiz.questions.get(order=1)
		self.assertEqual(first_question.prompt, 'Хто створив Minecraft?')
		correct_answer = first_question.answers.get(is_correct=True)
		self.assertEqual(correct_answer.text, 'Mojang')

	def test_quiz_is_not_saved_when_a_question_is_incomplete(self):
		response = self.client.post(reverse('quiz_create'), {
			'title': 'Незаповнена вікторина',
			'question_count': '1',
			'question_0_prompt': '',
			'question_0_answer_0': 'Відповідь',
			'question_0_correct': '0',
		})

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Заповніть текст питання 1.')
		self.assertFalse(Quiz.objects.filter(title='Незаповнена вікторина').exists())
		self.assertEqual(Question.objects.count(), 0)
		self.assertEqual(Answer.objects.count(), 0)

	def test_school_subject_campaigns_are_supported_and_visible_on_homepage(self):
		response = self.client.post(reverse('quiz_create'), {
			'title': 'Кампанія: Шкільні предмети',
			'description': 'Більше питань про уроки та шкільні предмети.',
			'category': 'school',
			'difficulty': 'medium',
			'level_number': '1',
			'question_count': '1',
			'question_0_prompt': 'Який предмет вивчає закони природи?',
			'question_0_answer_0': 'Фізика',
			'question_0_answer_1': 'Математика',
			'question_0_answer_2': 'Історія',
			'question_0_answer_3': 'Література',
			'question_0_correct': '0',
		})

		quiz = Quiz.objects.get(title='Кампанія: Шкільні предмети')
		self.assertEqual(response.status_code, 302)
		self.assertEqual(quiz.category, 'school')

		home_response = self.client.get(reverse('home'))
		self.assertContains(home_response, 'Шкільні предмети')
		self.assertContains(home_response, 'Кампанія: Шкільні предмети')


class QuizAttemptTests(TestCase):
	def setUp(self):
		self.user = User.objects.create_user(username='player', password='player-password-123')
		self.client.force_login(self.user)
		self.quiz = Quiz.objects.create(
			title='Тестова вікторина',
			description='Відповіді для перевірки.',
			created_by=self.user,
			invite_code='QZ-TEST123',
		)
		self.question = Question.objects.create(quiz=self.quiz, prompt='Що означає HTML?', order=1)
		self.correct_answer = Answer.objects.create(question=self.question, text='Мова розмітки', is_correct=True, order=1)
		self.wrong_answer = Answer.objects.create(question=self.question, text='Мова програмування', is_correct=False, order=2)
		self.second_answer = Answer.objects.create(question=self.question, text='База даних', is_correct=False, order=3)
		self.third_answer = Answer.objects.create(question=self.question, text='Операційна система', is_correct=False, order=4)

	def test_user_can_submit_answers_and_see_correct_answers_after_finishing(self):
		response = self.client.post(reverse('quiz_detail', args=[self.quiz.id]), {
			f'question_{self.question.id}': str(self.wrong_answer.id),
		})

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Правильна відповідь')
		self.assertContains(response, 'Мова розмітки')
		self.assertContains(response, 'name="question_' + str(self.question.id) + '"')

	def test_correct_answers_earn_coins_and_replays_add_to_balance(self):
		url = reverse('quiz_detail', args=[self.quiz.id])
		response = self.client.post(url, {
			f'question_{self.question.id}': str(self.correct_answer.id),
		})

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, '+10 Quiz Coins')
		attempt = QuizAttempt.objects.get(user=self.user, quiz=self.quiz)
		self.assertEqual(attempt.coins_earned, 10)
		self.user.profile.refresh_from_db()
		self.assertEqual(self.user.profile.quiz_coins, 10)

		self.client.post(url, {
			f'question_{self.question.id}': str(self.correct_answer.id),
		})
		self.user.profile.refresh_from_db()
		self.assertEqual(self.user.profile.quiz_coins, 20)
		self.assertEqual(QuizAttempt.objects.filter(user=self.user, quiz=self.quiz).count(), 2)

	def test_next_level_unlocks_after_successful_pass(self):
		level_one = Quiz.objects.create(
			title='Рівень 1',
			description='Перший рівень кампанії',
			created_by=self.user,
			invite_code='QZ-LEVEL1',
			level_number=1,
			category='games',
		)
		level_two = Quiz.objects.create(
			title='Рівень 2',
			description='Другий рівень кампанії',
			created_by=self.user,
			invite_code='QZ-LEVEL2',
			level_number=2,
			category='games',
		)
		question_one = Question.objects.create(quiz=level_one, prompt='Який колір сонця?', order=1)
		correct_one = Answer.objects.create(question=question_one, text='Жовтий', is_correct=True, order=1)
		Answer.objects.create(question=question_one, text='Синій', is_correct=False, order=2)
		question_two = Question.objects.create(quiz=level_two, prompt='Скільки буде 2 + 2?', order=1)
		Answer.objects.create(question=question_two, text='3', is_correct=False, order=1)
		Answer.objects.create(question=question_two, text='4', is_correct=True, order=2)

		self.client.post(reverse('quiz_detail', args=[level_one.id]), {
			f'question_{question_one.id}': str(correct_one.id),
		})

		self.assertTrue(level_two.is_unlocked_for_user(self.user))

		response = self.client.get(reverse('quiz_detail', args=[level_one.id]))
		self.assertContains(response, 'Продовжити')
		self.assertContains(response, reverse('quiz_detail', args=[level_two.id]))

	def test_next_level_requires_maximum_score(self):
		level_one = Quiz.objects.create(
			title='Рівень 1',
			description='Перший рівень кампанії',
			created_by=self.user,
			invite_code='QZ-LEVEL1-LOCK',
			level_number=1,
			category='school',
		)
		level_two = Quiz.objects.create(
			title='Рівень 2',
			description='Другий рівень кампанії',
			created_by=self.user,
			invite_code='QZ-LEVEL2-LOCK',
			level_number=2,
			category='school',
		)
		question_one = Question.objects.create(quiz=level_one, prompt='Який предмет вивчає природу?', order=1)
		Question.objects.create(quiz=level_one, prompt='Скільки буде 2 + 2?', order=2)
		correct_answer = Answer.objects.create(question=question_one, text='Фізика', is_correct=True, order=1)
		Answer.objects.create(question=question_one, text='Математика', is_correct=False, order=2)
		Answer.objects.create(question=question_one, text='Історія', is_correct=False, order=3)
		Answer.objects.create(question=question_one, text='Література', is_correct=False, order=4)

		QuizAttempt.objects.create(
			quiz=level_one,
			user=self.user,
			score=1,
			completed_at=timezone.now(),
		)
		self.assertFalse(level_two.is_unlocked_for_user(self.user))

		attempt = QuizAttempt.objects.create(
			quiz=level_one,
			user=self.user,
			score=2,
			completed_at=timezone.now(),
		)
		attempt.answers.create(
			question=question_one,
			selected_answer=correct_answer,
			is_correct=True,
		)
		self.assertTrue(level_two.is_unlocked_for_user(self.user))

	def test_second_level_is_created_as_hard(self):
		response = self.client.post(reverse('quiz_create'), {
			'title': 'Рівень 2',
			'description': 'Більш складне завдання',
			'category': 'science',
			'difficulty': 'medium',
			'level_number': '2',
			'question_count': '1',
			'question_0_prompt': 'Що таке гравітація?',
			'question_0_answer_0': 'Сила тяжіння',
			'question_0_answer_1': 'Тип комп’ютерної миші',
			'question_0_answer_2': 'Рівень освітлення',
			'question_0_answer_3': 'Вид музики',
			'question_0_correct': '0',
		})

		self.assertEqual(response.status_code, 302)
		quiz = Quiz.objects.get(title='Рівень 2')
		self.assertEqual(quiz.level_number, 2)
		self.assertEqual(quiz.difficulty, 'hard')

	def test_home_search_filters_quizzes_by_title(self):
		Quiz.objects.create(
			title='Math Challenge',
			description='Logical tasks for school level.',
			created_by=self.user,
			invite_code='QZ-MATH001',
			is_public=True,
		)
		Quiz.objects.create(
			title='History Marathon',
			description='Unique questions from history.',
			created_by=self.user,
			invite_code='QZ-HIST001',
			is_public=True,
		)

		response = self.client.get(reverse('home'), {'q': 'math'})

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Math Challenge')
		self.assertNotContains(response, 'History Marathon')

	def test_profile_view_shows_stats_and_recent_results(self):
		quiz = Quiz.objects.create(
			title='Profile Results',
			description='Checking player ranking.',
			created_by=self.user,
			invite_code='QZ-PROFILE1',
		)
		question = Question.objects.create(quiz=quiz, prompt='2 + 2?', order=1)
		correct = Answer.objects.create(question=question, text='4', is_correct=True, order=1)
		Answer.objects.create(question=question, text='3', is_correct=False, order=2)

		attempt = quiz.attempts.create(user=self.user, score=1, completed_at='2024-01-01T12:00:00Z')
		attempt.answers.create(question=question, selected_answer=correct, is_correct=True)

		response = self.client.get(reverse('profile'))

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Results')
		self.assertContains(response, 'Profile Results')
		self.assertContains(response, '100.0%')
		self.assertContains(response, 'Баланс Quiz Coins')

	def test_user_can_open_and_confirm_join_quiz_flow(self):
		quiz = Quiz.objects.create(
			title='Join flow quiz',
			description='Testing join actions.',
			created_by=self.user,
			invite_code='QZ-JOIN001',
			level_number=1,
		)

		get_response = self.client.get(reverse('join_quiz', args=[quiz.id]))
		self.assertEqual(get_response.status_code, 200)
		self.assertContains(get_response, 'Підтвердити участь')

		post_response = self.client.post(reverse('join_quiz', args=[quiz.id]))
		self.assertRedirects(post_response, reverse('quiz_detail', args=[quiz.id]))
		self.assertTrue(quiz.attempts.filter(user=self.user, completed_at__isnull=True).exists())

	def test_unauthenticated_user_is_redirected_to_custom_login_page(self):
		self.client.logout()
		quiz = Quiz.objects.create(
			title='Locked join quiz',
			description='Unauthenticated user should be redirected to login.',
			created_by=self.user,
			invite_code='QZ-LOCK001',
			level_number=1,
		)
		response = self.client.get(reverse('join_quiz', args=[quiz.id]))
		self.assertEqual(response.status_code, 302)
		self.assertEqual(response.url, f'/login/?next=/quiz/{quiz.id}/join/')
