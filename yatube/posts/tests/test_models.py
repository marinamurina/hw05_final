from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from faker import Faker
from posts.models import Group, Post

User = get_user_model()
fake = Faker()


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='post_author')
        cls.group = Group.objects.create(
            title=fake.text(),
            slug=fake.word(),
            description=fake.text(),
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text=fake.text(),
        )

    def test_models_have_correct_object_names(self):
        list = {
            PostModelTest.post: PostModelTest.post.text[
                :settings.FIRST_SYMBOLS_NUMBER
            ],
            PostModelTest.group: PostModelTest.group.title
        }

        for act, answer in list.items():
            with self.subTest(act=act):
                self.assertEqual(
                    str(act), answer, 'Метод __str__ работает неправильно')
