import unittest
from datetime import datetime, timezone
from unittest.mock import Mock
from announcement_monitor import announcement_kind, parse_feed, check

URL = 'https://via.tt.se/pressmeddelande/123/steam-frame?lang=sv'
NOW = datetime(2026, 10, 4, tzinfo=timezone.utc)

def feed(text='Steam Frame finns nu att köpa hos Elgiganten.', date='Sat, 03 Oct 2026 12:00:00 GMT', url=URL):
    return f'<rss><channel><title>Elgiganten - senaste pressmeddelandena</title><item><title>Steam Frame</title><description>{text}</description><link>{url}</link><pubDate>{date}</pubDate></item></channel></rss>'

class AnnouncementTests(unittest.TestCase):
    def test_explicit_current_availability(self):
        for text in ['Steam Frame finns nu att köpa hos Elgiganten.', 'Steam Frame is now in stock at Elgiganten.', 'Steam Frame kan nu köpas hos Elgiganten.']:
            self.assertEqual(announcement_kind(text), 'available')
        for text in ['Steam Frame kan nu förbeställas hos Elgiganten.', 'Förbeställ Steam Frame hos Elgiganten.', 'Steam Frame is now available for preorder at Elgiganten.']:
            self.assertEqual(announcement_kind(text), 'preorder')

    def test_mentions_other_products_negation_future_and_rumours_stay_quiet(self):
        for text in ['Steam Frame kommer snart.', 'Steam Frame news. Steam Deck is now in stock at Elgiganten.', 'Steam Frame finns inte att köpa hos Elgiganten.', 'Steam Frame finns nu att köpa hos Elgiganten från och med nästa vecka.', 'Ryktet säger: Steam Frame is now in stock at Elgiganten.', 'Steam Frame is now in stock at another shop.', 'Example: Steam Frame is now in stock at Elgiganten.']:
            self.assertIsNone(announcement_kind(text), text)

    def test_dates_filter_old_and_future_announcements(self):
        self.assertEqual(parse_feed(feed(), NOW)[1], [URL])
        for date in ['Fri, 02 Oct 2026 12:00:00 GMT', 'Mon, 05 Oct 2026 12:00:00 GMT', 'Sat, 20 Sep 2025 12:00:00 GMT']:
            self.assertEqual(parse_feed(feed(date=date), NOW)[1], [])
        self.assertEqual(parse_feed(feed(), datetime(2026, 10, 20, tzinfo=timezone.utc))[1], [])

    def test_bad_feed_and_external_links_fail_closed(self):
        for data in ['<html>Login</html>', '<rss><channel><title>Other shop</title></channel></rss>', feed(url='https://example.com/pressmeddelande/123')]:
            with self.assertRaises(ValueError):
                parse_feed(data, NOW)

    def test_preorder_email_is_clear_and_deduplicated(self):
        from notify import notify
        session = Mock()
        session.get.return_value.json.return_value = []
        session.post.return_value.json.return_value = {'html_url': 'https://github.com/example/1', 'assignees': [{'login': 'stephanieher'}]}
        status = {'found': True, 'matches': [URL], 'checked_at': 'now', 'mode': 'official-announcements', 'announcements': {URL: {'kind': 'preorder'}}}
        notify(status, session, 'owner/repo', 'stephanieher')
        payload = session.post.call_args.kwargs['json']
        self.assertIn('PREORDERS ARE OPEN', payload['title'])
        self.assertIn('official availability announcement', payload['body'])
        self.assertNotIn('priced Steam Frame offer', payload['body'])
        session.get.return_value.json.return_value = [{'body': payload['body'], 'state': 'closed'}]
        session.post.reset_mock()
        notify(status, session, 'owner/repo', 'stephanieher')
        session.post.assert_not_called()

    def test_http_error_cannot_become_absence(self):
        session = Mock()
        session.get.return_value.raise_for_status.side_effect = RuntimeError('Blocked')
        status = check(session, NOW)
        self.assertFalse(status['complete'])
        self.assertFalse(status['found'])
        self.assertEqual(status['error'], 'Blocked')

if __name__ == '__main__':
    unittest.main()
