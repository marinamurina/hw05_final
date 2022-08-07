import random
import shutil
import tempfile
from http import HTTPStatus

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from faker import Faker
from posts.forms import PostForm
from posts.models import Follow, Group, Post

User = get_user_model()
fake = Faker()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostsPagesTests(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='post_author')
        cls.group = Group.objects.create(
            title=fake.text(),
            slug=fake.word(),
            description=fake.text(),
        )
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        cls.post = Post.objects.create(
            group=cls.group,
            author=cls.user,
            text=fake.text(),
            image=cls.uploaded,
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        cache.clear()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def test_index_correct_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        response = self.guest_client.get(reverse('posts:index'))
        self.assertIn('page_obj', response.context)
        test_object_dict = {
            response.context['page_obj'][0]: PostsPagesTests.post,
            response.context['page_obj'][0].image: PostsPagesTests.post.image
        }
        for test_object, send_object in test_object_dict.items():
            with self.subTest(test_object=test_object):
                self.assertEqual(test_object, send_object)

    def test_profile_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        response = self.guest_client.get(
            reverse('posts:profile', args=[
                PostsPagesTests.user.username]))
        self.assertIn('author', response.context)
        self.assertIn('page_obj', response.context)
        test_object_dict = {
            response.context['page_obj'][0]: PostsPagesTests.post,
            response.context['author']: PostsPagesTests.user,
            response.context['page_obj'][0].image: PostsPagesTests.post.image
        }
        for test_object, send_object in test_object_dict.items():
            with self.subTest(test_object=test_object):
                self.assertEqual(test_object, send_object)

    def test_group_list_correct_context(self):
        """Шаблон group_list сформирован с правильным контекстом."""
        response = self.guest_client.get(
            reverse('posts:group_posts', args=[
                PostsPagesTests.group.slug]))
        self.assertIn('page_obj', response.context)
        self.assertIn('group', response.context)
        test_object_dict = {
            response.context['page_obj'][0]: PostsPagesTests.post,
            response.context['group'].slug: PostsPagesTests.group.slug,
            response.context['page_obj'][0].image: PostsPagesTests.post.image
        }
        for test_object, send_object in test_object_dict.items():
            with self.subTest(test_object=test_object):
                self.assertEqual(test_object, send_object)

    def test_post_detail_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = self.guest_client.get(
            reverse('posts:post_detail', args={
                PostsPagesTests.post.id}))
        self.assertIn('post', response.context)
        post_detail_object = response.context['post']
        test_object_dict = {
            post_detail_object: PostsPagesTests.post,
            post_detail_object.group: PostsPagesTests.group,
            post_detail_object.image: PostsPagesTests.post.image
        }
        for test_object, send_object in test_object_dict.items():
            with self.subTest(test_object=test_object):
                self.assertEqual(test_object, send_object)

    def test_post_create_correct_context(self):
        """Шаблон post_create сформирован с правильным контекстом."""
        post_adress = [
            reverse('posts:post_create'),
            reverse('posts:post_edit', args=[PostsPagesTests.post.id])
        ]
        for address in post_adress:
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertIn('form', response.context)
                form_object = response.context['form']
                self.assertIsInstance(form_object, PostForm)
                if 'is_edit' in response.context:
                    form = response.context['is_edit']
                    self.assertTrue(form)

    def test_post_get_the_right_group(self):
        """Созданный пост не попадает в другую группу"""
        PostsPagesTests.post_2 = Post.objects.create(
            group=PostsPagesTests.group,
            author=PostsPagesTests.user,
            text=fake.text(),
        )
        group_2 = Group.objects.create(
            title=fake.text(),
            slug=fake.word(),
            description=fake.text(),
        )
        response = self.authorized_client.get(
            reverse('posts:group_posts', args=[group_2.slug])
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(len(response.context['page_obj']), 0)

    def test_сashe(self):
        """Проверка работы кэширования на главной странице."""
        test_post = Post.objects.create(
            group=PostsPagesTests.group,
            author=PostsPagesTests.user,
            text=fake.text()
        )
        index_url = reverse('posts:index')
        response_1 = self.guest_client.get(index_url)
        test_post.delete()
        response_2 = self.guest_client.get(index_url)
        self.assertEqual(response_1.content, response_2.content)
        cache.clear()
        response_3 = self.guest_client.get(index_url)
        self.assertNotEqual(response_1.content, response_3.content)

    def test_follow(self):
        """Авторизованный пользователь может подписаться
        на других пользователей"""
        test_user = User.objects.create_user(username='new_user')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        test_count_1 = Follow.objects.count()
        test_object = Follow.objects.create(
            user=test_user, author=PostsPagesTests.user)
        test_count_2 = Follow.objects.count()
        self.assertEqual(test_count_1 + 1, test_count_2)
        self.assertEqual(test_object.user, test_user)
        self.assertEqual(test_object.author, PostsPagesTests.user)


class FollowTests(TestCase):

    def setUp(self):
        FollowTests.follower_user = User.objects.create_user(
            username='follower')
        FollowTests.following_user = User.objects.create_user(
            username='following')

        self.auth_follower_user = Client()
        self.auth_following_user = Client()
        self.auth_follower_user.force_login(self.follower_user)
        self.auth_following_user.force_login(self.following_user)

        self.post = Post.objects.create(
            author=self.following_user,
            text=fake.text()
        )

    def test_follow_unfollow(self):
        """Авторизованный пользователь может подписаться
        и отписаться от других пользователей"""
        test_count_1 = Follow.objects.count()
        self.auth_follower_user.get(
            reverse(
                'posts:profile_follow', args=[
                    FollowTests.following_user.username]
            )
        )
        test_count_2 = Follow.objects.count()
        self.assertEqual(test_count_1 + 1, test_count_2)
        self.auth_follower_user.get(
            reverse(
                'posts:profile_unfollow', args=[
                    FollowTests.following_user.username]
            )
        )
        test_count_3 = Follow.objects.count()
        self.assertEqual(test_count_1, test_count_3)

    def test_subscription_feed(self):
        """Новая запись пользователя появляется
        только в ленте тех, кто на него подписан."""
        Follow.objects.create(user=self.follower_user,
                              author=self.following_user)
        response = self.auth_follower_user.get('/follow/')
        self.assertIn('page_obj', response.context)
        post_text = response.context["page_obj"][0].text
        self.assertEqual(post_text, self.post.text)
        response = self.auth_following_user.get('/follow/')
        self.assertNotContains(response,
                               self.post.text)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        test_post_number = random.randint(
            settings.VIEW_POST_NUMBER + 2, settings.VIEW_POST_NUMBER * 2)

        cls.user = User.objects.create_user(username='post_author')
        cls.group = Group.objects.create(
            title=fake.text(),
            slug=fake.word(),
            description=fake.text(),
        )
        for i in range(test_post_number):
            Post.objects.bulk_create(
                [Post(
                    text=fake.text(),
                    author=cls.user,
                    group=cls.group
                )]
            )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        cache.clear()

    def test_paginator(self):
        """Проверка количества постов на странице."""
        first_page_posts = settings.VIEW_POST_NUMBER
        total_posts = Post.objects.count()
        second_page_posts = total_posts - first_page_posts
        test_addresses_list = [
            reverse('posts:index'),
            reverse(
                'posts:group_posts', args=[
                    PaginatorViewsTest.group.slug]),
            reverse(
                'posts:profile', args=[
                    PaginatorViewsTest.user.username])
        ]
        for address in test_addresses_list:
            with self.subTest(address=address):
                page_number_dict = {
                    1: first_page_posts,
                    2: second_page_posts
                }
                for page_number, page in page_number_dict.items():
                    response = self.guest_client.get(
                        address, {'page': page_number}
                    )
                    self.assertEqual(len(
                        response.context['page_obj']), page
                    )
