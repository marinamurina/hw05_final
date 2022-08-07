from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse
from faker import Faker
from posts.models import Group, Post

User = get_user_model()
fake = Faker()


class StaticURLTests(TestCase):
    def setUp(self):
        self.guest_client = Client()

    def test_homepage(self):
        response = self.guest_client.get(reverse('posts:index'))
        self.assertEqual(response.status_code, HTTPStatus.OK)


class PostsURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='post_author')
        cls.user2 = User.objects.create_user(username='another_user')
        cls.group = Group.objects.create(
            title=fake.text(),
            slug=fake.word(),
            description=fake.text(),
        )
        cls.post = Post.objects.create(
            group=cls.group,
            author=cls.user,
            text=fake.text(),
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.authorized_client_2 = Client()
        self.authorized_client_2.force_login(self.user2)
        cache.clear()

    def test_piblic_urls_exists_at_desired_location(self):
        """Доступность публичных страниц любому пользователю."""
        templates_public_urls = [
            reverse('posts:index'),
            reverse('posts:group_posts', args=[PostsURLTests.group.slug]),
            reverse('posts:profile', args=[PostsURLTests.user.username]),
            reverse('posts:post_detail', args=[PostsURLTests.post.id])
        ]
        for address in templates_public_urls:
            with self.subTest(address=address):
                response = self.guest_client.get(address)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_private_urls_exists_at_desired_location(self):
        """Доступность приватных страниц автору."""
        self.authorized_client.force_login(PostsURLTests.user)
        templates_private_urls = [
            reverse('posts:post_edit', args=[PostsURLTests.post.id]),
            reverse('posts:post_create'),
        ]
        for address in templates_private_urls:
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_create_post_url_redirect_not_author(self):
        """Адрес редактирования поста для авторизованного пользователя,
        не являющегося автором, ведет на редиректную страницу."""
        self.authorized_client.force_login(PostsURLTests.user2)
        response = self.authorized_client.get(
            reverse(
                'posts:post_edit', args=[
                    PostsURLTests.post.id]), follow=True
        )
        redirect_address = reverse(
            'posts:post_detail', args=[PostsURLTests.post.id]
        )
        self.assertRedirects(response, redirect_address)

    def test_private_urls_redirect_guest(self):
        """Приватные адреса не доступны для неавторизованных пользователей,
         ведут на редиректную страницу"""
        templates_private_urls = {
            reverse(
                'posts:post_edit', args=[PostsURLTests.post.id]
            ): reverse('posts:post_detail', args={PostsURLTests.post.id}),
            reverse(
                'posts:post_create'): reverse(
                    'users:login') + '?next=' + reverse('posts:post_create')
        }
        for address, redirect_address in templates_private_urls.items():
            with self.subTest(address=address):
                response = self.guest_client.get(address, follow=True)
                self.assertRedirects(response, redirect_address)

    def test_comments(self):
        "Неавторизованный пользователь не может добавить комментарий."
        address = reverse('posts:add_comment', args=[PostsURLTests.post.id])
        redirect_address = reverse(
            'users:login') + '?next=' + reverse(
                'posts:add_comment', args=[PostsURLTests.post.id]
        )
        response = self.guest_client.get(address, follow=True)
        self.assertRedirects(response, redirect_address)

    def test_url_unexisting_page(self):
        """Проверка несуществующей страницы"""
        response = self.guest_client.get('/unexisting_page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertTemplateUsed(response, 'core/404.html')

    def test__public_urls_uses_correct_template(self):
        """Публичные URL-адреса используют соответствующий шаблон."""
        templates_url_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse(
                'posts:group_posts', args=[
                    PostsURLTests.group.slug]): 'posts/group_list.html',
            reverse(
                'posts:profile', args=[
                    PostsURLTests.user.username]): 'posts/profile.html',
            reverse(
                'posts:post_detail', args=[
                    PostsURLTests.post.id]): 'posts/post_detail.html'
        }

        for address, template in templates_url_names.items():
            with self.subTest(address=address):
                response = self.guest_client.get(address)
                self.assertTemplateUsed(response, template)

    def test_private_urls_uses_correct_template(self):
        """ Приватные URL-адреса используют соответствующий шаблон."""
        templates_url_names = {
            reverse(
                'posts:post_edit', args=[
                    PostsURLTests.post.id]): 'posts/create_post.html',
            reverse('posts:post_create'): 'posts/create_post.html'
        }
        for address, template in templates_url_names.items():
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertTemplateUsed(response, template)
