import unittest
from types import SimpleNamespace as Obj
from unittest.mock import Mock

from engine import StopRun, execute, scan


class BatchTests(unittest.TestCase):
    def setUp(self):
        self.client = Mock(user_id="1")
        self.client.user_info_v1.return_value = Obj(follower_count=1, following_count=2)
        self.client.user_followers.return_value = {"2": Obj(username="mutuo")}
        self.client.user_following.return_value = {
            "2": Obj(username="mutuo"), "3": Obj(username="altro")}
        self.client.user_friendship_v1.return_value = Obj(user_id="3", following=True, followed_by=False)
        self.client.user_unfollow.return_value = True
        self.plan = scan(self.client)
        self.report = Mock()

    def apply(self, protected=(), stop=lambda: False):
        execute(self.client, self.plan, protected, stop, self.report)

    def test_automatic(self):
        self.apply()
        self.client.user_unfollow.assert_called_once_with("3")
        self.report.assert_called_once_with("altro", "rimosso")

    def test_incomplete(self):
        self.client.user_followers.return_value = {}
        with self.assertRaises(StopRun):
            scan(self.client)

    def test_changed_during_scan(self):
        self.client.user_info_v1.side_effect = [
            Obj(follower_count=1, following_count=2), Obj(follower_count=2, following_count=2)]
        with self.assertRaises(StopRun):
            scan(self.client)

    def test_new_follower(self):
        self.client.user_friendship_v1.return_value.followed_by = True
        self.apply()
        self.client.user_unfollow.assert_not_called()

    def test_unknown_relation(self):
        self.client.user_friendship_v1.return_value = None
        with self.assertRaises(StopRun):
            self.apply()
        self.client.user_unfollow.assert_not_called()

    def test_account_changed(self):
        self.client.user_id = "5"
        with self.assertRaises(StopRun):
            self.apply()
        self.client.user_unfollow.assert_not_called()

    def test_protected(self):
        self.apply({"3"})
        self.client.user_unfollow.assert_not_called()

    def test_pause_after_check(self):
        states = iter([False, True])
        self.apply(stop=lambda: next(states))
        self.client.user_unfollow.assert_not_called()

    def test_rejected(self):
        self.client.user_unfollow.return_value = False
        with self.assertRaises(StopRun):
            self.apply()
        self.report.assert_not_called()

    def test_pause_during_follower_fetch(self):
        stopped = False
        def read(*args, **kwargs):
            nonlocal stopped
            stopped = True
            return {"2": Obj(username="mutuo")}
        self.client.user_followers.side_effect = read
        self.client.user_following.reset_mock()
        with self.assertRaisesRegex(StopRun, "interrotta"):
            scan(self.client, lambda: stopped)
        self.client.user_following.assert_not_called()

    def test_account_change_after_relation_check(self):
        def read(uid):
            self.client.user_id = "9"
            return Obj(user_id=uid, following=True, followed_by=False)
        self.client.user_friendship_v1.side_effect = read
        with self.assertRaisesRegex(StopRun, "Account cambiato"):
            self.apply()
        self.client.user_unfollow.assert_not_called()

    def test_failure_after_first_success(self):
        self.client.user_info_v1.return_value.following_count = 4
        self.client.user_following.return_value.update({"4": Obj(username="quattro"), "5": Obj(username="cinque")})
        self.plan = scan(self.client)
        self.client.user_friendship_v1.side_effect = lambda uid: Obj(user_id=uid, following=True, followed_by=False)
        self.client.user_unfollow.side_effect = [True, TimeoutError()]
        with self.assertRaisesRegex(StopRun, "sconosciuto per @quattro"):
            self.apply()
        self.assertEqual(self.client.user_unfollow.call_count, 2)
        self.report.assert_called_once_with("altro", "rimosso")

    def test_interrupted_before_scan(self):
        self.client.reset_mock()
        with self.assertRaisesRegex(StopRun, "interrotta"):
            scan(self.client, lambda: True)
        self.client.user_info_v1.assert_not_called()
