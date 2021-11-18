from apiritif import http
from unittest import TestCase


class TestHTTPMethods(TestCase):
    def test_get(self):
        http.get('https://blazedemo.com/?tag=get')

    def test_post(self):
        http.post('https://blazedemo.com/?tag=post')

    def test_put(self):
        http.put('https://blazedemo.com/?tag=put')

    def test_patch(self):
        http.patch('https://blazedemo.com/?tag=patch')

    def test_head(self):
        http.head('https://blazedemo.com/?tag=head')

    def test_delete(self):
        http.delete('https://blazedemo.com/?tag=delete')

    def test_options(self):
        http.options('https://blazedemo.com/echo.php?echo=options')


class TestTargetMethods(TestCase):
    def setUp(self):
        self.target = http.target('https://blazedemo.com', auto_assert_ok=False)

    def test_get(self):
        self.target.get('/echo.php?echo=get').assert_ok()

    def test_post(self):
        self.target.post('/echo.php?echo=post').assert_ok()

    def test_put(self):
        self.target.put('/echo.php?echo=put').assert_ok()

    def test_patch(self):
        self.target.patch('/echo.php?echo=patch').assert_ok()

    def test_delete(self):
        self.target.delete('/echo.php?echo=delete').assert_ok()

    def test_head(self):
        self.target.head('/echo.php?echo=head').assert_ok()

    def test_options(self):
        self.target.options('/echo.php?echo=options').assert_ok()

    def test_connect(self):
        self.target.connect('/echo.php?echo=connect')
