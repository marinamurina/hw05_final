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
from posts.models import Comment, Group, Post

User = get_user_model()
fake = Faker()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostCreateFormTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='post_author')
        cls.group = Group.objects.create(
            title=fake.text(),
            slug=fake.word(),
            description=fake.text()
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
            name='small_1.gif',
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

    def test_create_post_by_author(self):
        """Валидная форма создает новый пост."""
        post_count = Post.objects.count()

        small_gif_2 = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        self.uploaded = SimpleUploadedFile(
            name='small_2.gif',
            content=small_gif_2,
            content_type='image/gif'
        )
        form_data = {
            'text': fake.text(),
            'group': PostCreateFormTests.group.id,
            'image': self.uploaded,
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response, reverse(
            'posts:profile', args=(PostCreateFormTests.user.username,),
        ))
        new_post = Post.objects.first()
        self.assertEqual(Post.objects.count(), post_count + 1)
        self.assertEqual(new_post.text, form_data['text'])
        self.assertEqual(new_post.author, PostCreateFormTests.user)
        self.assertEqual(new_post.group, PostCreateFormTests.group)
        self.assertNotEqual(new_post.image, False)
        self.assertEqual(new_post.image, 'posts/small_2.gif')

    def test_create_post_not_by_author(self):
        """Неавторизованный пользователь не может создать новый пост
        и переадресовывается на страницу логина."""
        posts_count = Post.objects.count()
        response = self.guest_client.post(
            reverse('posts:post_create'), follow=True)
        redirect_address = reverse(
            'users:login') + '?next=' + reverse('posts:post_create')
        self.assertRedirects(response, redirect_address)
        self.assertEqual(Post.objects.count(), posts_count)

    def test_edit_post_by_author(self):
        """При редактировании поста автором происходит
        изменение в базе данных."""
        group_2 = Group.objects.create(
            title=fake.text(),
            slug=fake.word(),
            description=fake.text()
        )
        test_post = Post.objects.create(
            group=PostCreateFormTests.group,
            author=PostCreateFormTests.user,
            text=fake.text(),
            image=PostCreateFormTests.uploaded,
        )
        post_count = Post.objects.count()
        edit_data = {
            'text': fake.text(),
            'group': group_2.id
        }
        response = self.authorized_client.post(
            reverse(
                'posts:post_edit', args=(
                    test_post.id,)), data=edit_data, follow=True
        )
        redirect_address = reverse('posts:post_detail', args=(test_post.id,))
        self.assertRedirects(response, redirect_address)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(Post.objects.count(), post_count)
        test_post.refresh_from_db()
        self.assertEqual(test_post.text, edit_data['text'])
        self.assertEqual(test_post.author, PostCreateFormTests.user)
        self.assertEqual(test_post.group, group_2)

    def test_edit_post__not_by_author(self):
        """При редактировании поста не-автором-поста происходит
        переадреcация на страницу поста."""
        PostCreateFormTests.user2 = User.objects.create_user(
            username='another_user'
        )
        self.authorized_client_2 = Client()
        self.authorized_client_2.force_login(self.user2)

        test_post = Post.objects.create(
            group=PostCreateFormTests.group,
            author=PostCreateFormTests.user,
            text=fake.text(),
            image=PostCreateFormTests.uploaded,
        )
        edit_data = {
            'text': fake.text(),
        }
        response = self.authorized_client_2.get(
            reverse(
                'posts:post_edit', args=[
                    test_post.id]), data=edit_data, follow=True
        )
        redirect_address = reverse('posts:post_detail', args=(test_post.id,))
        self.assertIsNot(test_post.text, edit_data.get('text'))
        self.assertRedirects(response, redirect_address)

    def test_add_comment(self):
        """Добавление комментария авторизованным пользователем."""
        comments_count = Comment.objects.count()
        comment_data = {
            'text': fake.text(),
        }
        response = self.authorized_client.post(
            reverse(
                'posts:add_comment', args=(
                    PostCreateFormTests.post.id,)
            ), data=comment_data, follow=True
        )
        redirect_address = reverse(
            'posts:post_detail', args=(PostCreateFormTests.post.id,)
        )
        self.assertRedirects(response, redirect_address)
        self.assertEqual(Comment.objects.count(), comments_count + 1)
        last_comment = response.context['comments'][0]
        self.assertEqual(last_comment.text, comment_data.get('text'))
        self.assertEqual(last_comment.post.id, PostCreateFormTests.post.id)
        self.assertEqual(last_comment.author, PostCreateFormTests.user)

    def test_add_comment(self):
        """Неавторизованный пользователь не может создать комментарий,
        происходит редирект на страницу авторизации."""
        comments_count = Comment.objects.count()
        comment_data = {
            'text': fake.text(),
        }
        response = self.guest_client.post(
            reverse(
                'posts:add_comment', args=(
                    PostCreateFormTests.post.id,)
            ), data=comment_data, follow=True
        )
        redirect_address = reverse(
            'users:login') + '?next=' + reverse(
                'posts:add_comment', args=(PostCreateFormTests.post.id,)
        )
        self.assertRedirects(response, redirect_address)
        self.assertEqual(Comment.objects.count(), comments_count)
