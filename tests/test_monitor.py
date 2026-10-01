import gzip
import unittest
from unittest.mock import Mock, patch

import monitor
from notify import notify

PRODUCT = 'https://www.elgiganten.se/product/gaming/vr/valve-steam-frame/123'
CHILD = 'https://www.elgiganten.se/sitemaps/products.xml'


class MonitorTests(unittest.TestCase):
    def test_matching_uses_swedish_product_path_not_query(self):
        self.assertTrue(monitor.is_steam_frame_url(PRODUCT))
        for url in ['https://evil.example/product/steam-frame',
                    'https://www.elgiganten.se/search?query=steam-frame',
                    'https://www.elgiganten.se/product/samsung-the-frame-steamer',
                    'https://www.elgiganten.se/product/steam-framework',
                    'https://www.elgiganten.se/product/other?query=steam-frame']:
            self.assertFalse(monitor.is_steam_frame_url(url))

    def test_gzip_namespaces_and_image_locs(self):
        xml = f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1"><url><loc>{PRODUCT}</loc><image:image><image:loc>https://images.example/a.jpg</image:loc></image:image></url></urlset>'.encode()
        self.assertEqual(monitor.parse_sitemap(gzip.compress(xml)), ('urlset', [PRODUCT]))

    def test_html_empty_and_foreign_sitemaps_fail(self):
        for xml in [b'<html/>', b'<urlset/>', b'<urlset><url><loc>https://evil.example/a</loc></url></urlset>']:
            with self.assertRaises(ValueError):
                monitor.parse_sitemap(xml)

    @patch('monitor.inspect_sitemap')
    def test_complete_no_match(self, inspect):
        inspect.side_effect = [('sitemapindex', [CHILD]), ('urlset', ['https://www.elgiganten.se/product/other/123'])]
        status = monitor.check()
        self.assertTrue(status['complete'])
        self.assertFalse(status['found'])
        self.assertEqual(status['products_checked'], 1)
        self.assertEqual(status['sitemaps_checked'], 2)

    @patch('monitor.inspect_sitemap')
    def test_failed_child_cannot_report_success(self, inspect):
        inspect.side_effect = [('sitemapindex', [CHILD]), RuntimeError('429')]
        status = monitor.check()
        self.assertFalse(status['complete'])
        self.assertTrue(status['error'])

    @patch('monitor.inspect_product', return_value=True)
    @patch('monitor.inspect_sitemap')
    def test_matches_preserved_on_partial_failure(self, inspect, product):
        def response(url):
            if url == monitor.SITEMAP_INDEX:
                return 'sitemapindex', [CHILD, CHILD + '?other']
            if url == CHILD:
                return 'urlset', [PRODUCT]
            raise RuntimeError('503')
        inspect.side_effect = response
        status = monitor.check()
        self.assertTrue(status['found'])
        self.assertFalse(status['complete'])
        self.assertEqual(status['matches'], [PRODUCT])

    @patch('monitor.inspect_sitemap', return_value=('sitemapindex', [monitor.SITEMAP_INDEX]))
    def test_cycle_with_no_products_fails(self, inspect):
        self.assertFalse(monitor.check()['complete'])



class AvailabilityTests(unittest.TestCase):
    def page(self, state="InStock", price="999", name="Valve Steam Frame", url=PRODUCT, offer_name="Standard Price"):
        import json
        product = {"@type": "Product", "url": url, "name": name,
                   "offers": [{"name": offer_name, "price": price, "priceCurrency": "SEK",
                               "availability": "https://schema.org/" + state}]}
        return '<script type="application/ld+json">' + json.dumps(product) + '</script>'

    def test_stock_and_preorder_can_alert(self):
        for state in ["InStock", "LimitedAvailability", "PreOrder", "PreSale", "OnlineOnly"]:
            self.assertTrue(monitor.product_availability(self.page(state), PRODUCT))

    def test_unavailable_and_unpriced_do_not_alert(self):
        for state in ["OutOfStock", "SoldOut", "Discontinued", "InStoreOnly"]:
            self.assertFalse(monitor.product_availability(self.page(state), PRODUCT))
        for price in ["0", "NaN", "Infinity", "", "invalid"]:
            self.assertFalse(monitor.product_availability(self.page(price=price), PRODUCT))

    def test_recommendations_business_and_missing_data_fail_closed(self):
        for html in [self.page(name="Other headset"), self.page(url=PRODUCT + "other"),
                     self.page(offer_name="Business Price"), '<html>Buy now</html>']:
            with self.assertRaises(ValueError):
                monitor.product_availability(html, PRODUCT)

    @patch('monitor.inspect_product', return_value=False)
    @patch('monitor.inspect_sitemap', return_value=('urlset', [PRODUCT]))
    def test_listing_without_stock_does_not_alert(self, sitemap, product):
        status = monitor.check()
        self.assertFalse(status['found'])
        self.assertEqual(status['listing_matches'], [PRODUCT])
        self.assertEqual(status['matches'], [])

    @patch('monitor.inspect_product', side_effect=RuntimeError('blocked'))
    @patch('monitor.inspect_sitemap', return_value=('urlset', [PRODUCT]))
    def test_blocked_product_is_unknown_and_does_not_alert(self, sitemap, product):
        status = monitor.check()
        self.assertFalse(status['complete'])
        self.assertFalse(status['found'])

class AlertTests(unittest.TestCase):
    def test_no_match_does_not_contact_github(self):
        session = Mock()
        notify({'found': False}, session, 'stephanieher/steam-frame-monitor', 'stephanieher')
        session.get.assert_not_called()
        session.post.assert_not_called()

    def test_assigned_issue_and_closed_issue_deduplication(self):
        session = Mock()
        session.get.return_value.json.return_value = []
        session.post.return_value.json.return_value = {'html_url': 'https://github.com/example/1', 'assignees': [{'login': 'stephanieher'}]}
        status = {'found': True, 'matches': [PRODUCT, PRODUCT + '-other-model'], 'checked_at': '2026-09-24'}
        notify(status, session, 'stephanieher/steam-frame-monitor', 'stephanieher')
        body = session.post.call_args.kwargs['json']
        self.assertEqual(body['assignees'], ['stephanieher'])
        self.assertIn(PRODUCT, body['body'])
        self.assertEqual(session.post.call_count, 1)
        session.get.return_value.json.return_value = [{'state': 'closed', 'body': body['body']}]
        session.post.reset_mock()
        status['matches'] = [PRODUCT + '-new-model']
        notify(status, session, 'stephanieher/steam-frame-monitor', 'stephanieher')
        session.post.assert_not_called()

    def test_assignment_failure_is_reported(self):
        session = Mock()
        session.get.return_value.json.return_value = []
        session.post.return_value.json.return_value = {'html_url': 'https://github.com/example/1', 'assignees': []}
        with self.assertRaises(RuntimeError):
            notify({'found': True, 'matches': [PRODUCT], 'checked_at': 'now'}, session, 'owner/repo', 'stephanieher')


if __name__ == '__main__':
    unittest.main()
