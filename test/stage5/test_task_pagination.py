import pytest

from spiderfoot.live_search import LiveSearchService


@pytest.fixture
def saved_tasks(tmp_path):
    service = LiveSearchService(tmp_path / 'tasks.sqlite', None)
    with service.connect() as db:
        for index in range(1000):
            task_id = f'{index:032x}'
            db.execute('INSERT INTO live_tasks VALUES (?,?,?,?,?,?)',
                       (task_id, 2, 'email', f'demo{index}@example.invalid', index, index))
            db.execute('INSERT INTO live_sources VALUES (?,?,?,?,?,?,?,?)',
                       (task_id, 2, 'holehe', 'completed' if index % 2 else 'failed',
                        'synthetic fixture', 'not a live query', index, '[]'))
        db.execute('INSERT INTO live_tasks VALUES (?,?,?,?,?,?)',
                   ('f' * 32, 3, 'email', 'other@example.invalid', 2000, 2000))
    try:
        yield service
    finally:
        service.close()


def test_bounded_pages_keep_history_and_do_not_load_results(saved_tasks):
    first = saved_tasks.list_page(2)
    last = saved_tasks.list_page(2, page=200)
    assert (first['total'], first['pages'], len(first['items'])) == (1000, 200, 5)
    assert last['page'] == 200 and len(last['items']) == 5
    assert {item['id'] for item in first['items']}.isdisjoint(item['id'] for item in last['items'])
    assert all('results' not in item and 'sources' not in item for item in first['items'])
    assert all('demo999@example.invalid' != item['query'] for item in first['items'])
    assert saved_tasks.list_page(2, page=999)['page'] == 200


def test_search_status_and_ownership_are_applied_before_paging(saved_tasks):
    found = saved_tasks.list_page(2, search='demo999@example.invalid')
    assert found['total'] == 1 and found['items'][0]['id'] == f'{999:032x}'
    assert saved_tasks.list_page(2, status='failed')['total'] == 500
    assert saved_tasks.list_page(2, search='other@example.invalid')['total'] == 0
    assert saved_tasks.list_page(3)['total'] == 1
    assert saved_tasks.list_page(2, search="%' OR 1=1 --")['total'] == 0
    assert saved_tasks.list_page(2, search='not-present')['items'] == []


@pytest.mark.parametrize('params', [dict(page=0), dict(page=True), dict(page_size=51),
                                  dict(status='unknown'), dict(search='x' * 255)])
def test_invalid_pagination_is_rejected_without_changing_history(saved_tasks, params):
    with pytest.raises(ValueError):
        saved_tasks.list_page(2, **params)
    assert saved_tasks.list_page(2)['total'] == 1000
