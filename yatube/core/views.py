from http import HTTPStatus

from django.shortcuts import render


def page_not_found(request, exception):
    return render(
        request, 'core/404.html', status=HTTPStatus.NOT_FOUND
    )


def csrf_failure(request, reason=''):
    return render(request, 'core/403csrf.html')


def internal_server_error(request, reason=''):
    return render(request, 'core/500.html')
