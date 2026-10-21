from spiderfoot.privacy_action import PrivacyActionDB
from test.stage2.test_privacy_real_mysql import privacy_mysql


def test_same_timestamp_requests_have_stable_nonoverlapping_pages(privacy_mysql):
    server, auth = privacy_mysql
    alice_id = auth.get_user('alice')['id']
    store = PrivacyActionDB()
    with server.connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute('USE stage2_privacy_test')
            cursor.executemany(
                'INSERT INTO privacy_actions '
                '(id,user_id,username,action_type,platform,content,status,note,created_at,updated_at) '
                'VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',
                [(f'privacy-page-{n:03}', alice_id, 'alice', 'hide', 'example.invalid',
                  'https://example.invalid/synthetic', 'recorded', 'synthetic fixture', 2000000000, 2000000000)
                 for n in range(20)],
            )
    for admin in (False, True):
        pages = [store.list_actions(alice_id, page, 5, admin=admin) for page in range(1, 5)]
        assert all(result['success'] for result in pages)
        actual = [row['id'] for result in pages for row in result['items']]
        assert actual == [f'privacy-page-{n:03}' for n in reversed(range(20))]
        assert len(set(actual)) == 20
