"""Tests for the AI customer-support chat (n8n integration).

Run:  python manage.py test cms_pages -v 2
The n8n webhook is always mocked - no network access is needed.
"""
import json
from unittest import mock

import requests
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import CustomUser


def _n8n_response(payload):
    resp = mock.Mock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = payload
    return resp


class SupportChatTests(TestCase):
    def setUp(self):
        cache.clear()
        self.url = reverse('support_chat_api')

    def _post(self, body):
        return self.client.post(self.url, data=json.dumps(body), content_type='application/json')

    # -- page ---------------------------------------------------------------
    def test_support_page_renders_chat_ui(self):
        resp = self.client.get(reverse('support_page'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'id="chat-window"')
        self.assertContains(resp, 'id="chat-form"')
        self.assertContains(resp, 'id="chat-config"')
        cfg = resp.context['chat_config']
        self.assertEqual(cfg['mode'], 'server')
        self.assertTrue(cfg['sessionId'])

    def test_support_page_is_linked_from_navigation(self):
        resp = self.client.get(reverse('home'))
        self.assertContains(resp, reverse('support_page'))

    @override_settings(SUPPORT_CHAT_MODE='browser', N8N_WEBHOOK_URL='https://n8n.example/webhook/x')
    def test_browser_mode_exposes_webhook_url(self):
        cfg = self.client.get(reverse('support_page')).context['chat_config']
        self.assertEqual(cfg['mode'], 'browser')
        self.assertEqual(cfg['webhookUrl'], 'https://n8n.example/webhook/x')

    def test_server_mode_never_exposes_webhook_url(self):
        cfg = self.client.get(reverse('support_page')).context['chat_config']
        self.assertNotIn('webhookUrl', cfg)

    # -- API ----------------------------------------------------------------
    def test_get_not_allowed(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)

    def test_empty_message_rejected(self):
        self.assertEqual(self._post({'message': '   '}).status_code, 400)

    def test_invalid_json_rejected(self):
        resp = self.client.post(self.url, data='not json', content_type='application/json')
        self.assertEqual(resp.status_code, 400)

    @mock.patch('cms_pages.views.requests.post')
    def test_reply_is_forwarded_with_session_id(self, post):
        post.return_value = _n8n_response({'reply': 'We deliver Wed-Sun.'})
        self.client.get(reverse('support_page'))  # creates the session
        resp = self._post({'message': 'When do you deliver?'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['reply'], 'We deliver Wed-Sun.')
        sent = post.call_args.kwargs['json']
        self.assertEqual(sent['message'], 'When do you deliver?')
        self.assertTrue(sent['session_id'])
        self.assertNotIn('auth_token', sent)  # guests get no token

    @mock.patch('cms_pages.views.requests.post')
    def test_same_session_id_across_messages(self, post):
        post.return_value = _n8n_response({'reply': 'ok'})
        self._post({'message': 'one'})
        self._post({'message': 'two'})
        first, second = (c.kwargs['json']['session_id'] for c in post.call_args_list)
        self.assertEqual(first, second)

    @mock.patch('cms_pages.views.requests.post')
    def test_accepts_output_key_and_list_shapes(self, post):
        post.return_value = _n8n_response([{'output': 'From the agent node'}])
        self.assertEqual(self._post({'message': 'hi'}).json()['reply'], 'From the agent node')

    @mock.patch('cms_pages.views.requests.post')
    def test_message_is_truncated(self, post):
        post.return_value = _n8n_response({'reply': 'ok'})
        self._post({'message': 'x' * 5000})
        self.assertEqual(len(post.call_args.kwargs['json']['message']), 600)

    @mock.patch('cms_pages.views.requests.post')
    def test_logged_in_user_token_is_attached(self, post):
        post.return_value = _n8n_response({'reply': 'ok'})
        user = CustomUser.objects.create_user(
            email='chat@example.com', username='chat@example.com', password='pw-12345-xyz',
            first_name='Sam', last_name='Lee',
        )
        self.client.force_login(user)
        self._post({'message': 'where is my order?'})
        sent = post.call_args.kwargs['json']
        self.assertTrue(sent['auth_token'])
        self.assertEqual(sent['user_name'], 'Sam Lee')

    @mock.patch('cms_pages.views.requests.post', side_effect=requests.ConnectionError('down'))
    def test_upstream_failure_returns_502_with_friendly_error(self, _post):
        resp = self._post({'message': 'hello'})
        self.assertEqual(resp.status_code, 502)
        self.assertIn('problem connecting', resp.json()['error'])

    @mock.patch('cms_pages.views.requests.post')
    def test_non_json_upstream_is_handled(self, post):
        bad = mock.Mock()
        bad.raise_for_status.return_value = None
        bad.json.side_effect = ValueError('no json')
        post.return_value = bad
        self.assertEqual(self._post({'message': 'hello'}).status_code, 502)

    @mock.patch('cms_pages.views.requests.post')
    def test_rate_limit(self, post):
        post.return_value = _n8n_response({'reply': 'ok'})
        for _ in range(30):
            self.assertEqual(self._post({'message': 'hi'}).status_code, 200)
        self.assertEqual(self._post({'message': 'hi'}).status_code, 429)
