import unittest
from app import app, db, User, Task


class FlaskTestCase(unittest.TestCase):

    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app = app.test_client()
        with app.app_context():
            db.create_all()

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()

    def test_home_page(self):
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)

    def test_user_registration(self):
        response = self.app.post('/register', data=dict(
            username="testuser",
            password="password123"
        ), follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        with app.app_context():
            user = User.query.filter_by(username="testuser").first()
            self.assertIsNotNone(user)

    def test_add_task(self):
        self.app.post('/register', data=dict(username="u", password="p"), follow_redirects=True)
        self.app.post('/login', data=dict(username="u", password="p"), follow_redirects=True)

        response = self.app.post('/tasks', data=dict(
            title="Unit Test Task",
            description="Testing"
        ), follow_redirects=True)

        self.assertIn(b"Unit Test Task", response.data)


if __name__ == '__main__':
    unittest.main()