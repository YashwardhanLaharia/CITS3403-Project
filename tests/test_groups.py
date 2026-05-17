import json

from extensions import db
from models import Group, Membership


def test_group_creation_requires_name(client, user_factory, login_user):
    user, password = user_factory()
    login_user(user.email, password)

    response = client.post(
        '/groups/create',
        data={'group_name': '', 'currency': 'AUD'},
        follow_redirects=True,
    )

    assert user.created_groups.count() == 0


def test_group_creation_assigns_admin(client, user_factory, login_user):
    user, password = user_factory()
    login_user(user.email, password)

    response = client.post(
        '/groups/create',
        data={'group_name': 'Roommates', 'currency': 'AUD'},
        follow_redirects=True,
    )

    group = Group.query.filter_by(name='Roommates').first()
    assert group is not None
    membership = Membership.query.filter_by(group_id=group.id, user_id=user.id).first()
    assert membership.role == 'admin'


def test_join_group_invalid_code(client, user_factory, login_user):
    user, password = user_factory()
    login_user(user.email, password)

    response = client.post(
        '/groups/join',
        data={'invite_code': 'INVALID'},
        follow_redirects=True,
    )

    assert Membership.query.filter_by(user_id=user.id).count() == 0


def test_join_group_creates_membership(client, user_factory, group_factory, login_user):
    admin, _ = user_factory(email='admin@example.com')
    group = group_factory(creator=admin)
    member, password = user_factory(email='member@example.com')
    login_user(member.email, password)

    response = client.post(
        '/groups/join',
        data={'invite_code': group.invite_code},
        follow_redirects=True,
    )

    membership = Membership.query.filter_by(group_id=group.id, user_id=member.id).first()
    assert membership is not None
    assert membership.role == 'member'


def test_group_dashboard_requires_login(client, user_factory, group_factory):
    admin, _ = user_factory(email='admin-group@example.com')
    group = group_factory(creator=admin)

    response = client.get(f'/groups/{group.id}', follow_redirects=False)
    assert response.status_code == 302
    assert '/login' in response.headers['Location']


def test_group_dashboard_returns_404_for_non_member(client, user_factory, group_factory, login_user):
    admin, _ = user_factory(email='admin-nonmember@example.com')
    group = group_factory(creator=admin)
    other_user, other_password = user_factory(email='other@example.com')
    login_user(other_user.email, other_password)

    response = client.get(f'/groups/{group.id}')
    assert response.status_code == 404


def test_group_dashboard_accessible_for_member(client, user_factory, group_factory, login_user):
    admin, password = user_factory(email='admin-access@example.com')
    group = group_factory(creator=admin)
    login_user(admin.email, password)

    response = client.get(f'/groups/{group.id}')
    assert response.status_code == 200
    assert group.name.encode() in response.data


def test_group_data_api_returns_json(client, user_factory, group_factory, login_user):
    admin, password = user_factory(email='admin-api@example.com')
    group = group_factory(creator=admin)
    login_user(admin.email, password)

    response = client.get(f'/groups/{group.id}/data')
    assert response.status_code == 200
    assert response.content_type == 'application/json'

    data = json.loads(response.data)
    assert 'group' in data
    assert data['group']['name'] == group.name


def test_group_data_api_requires_login(client, user_factory, group_factory):
    admin, _ = user_factory(email='admin-api-login@example.com')
    group = group_factory(creator=admin)

    response = client.get(f'/groups/{group.id}/data')
    assert response.status_code == 302


def test_group_data_api_returns_404_for_non_member(client, user_factory, group_factory, login_user):
    admin, _ = user_factory(email='admin-apifail@example.com')
    group = group_factory(creator=admin)
    other_user, other_password = user_factory(email='other2@example.com')
    login_user(other_user.email, other_password)

    response = client.get(f'/groups/{group.id}/data')
    assert response.status_code == 404


def test_join_group_already_member_fails(client, user_factory, group_factory, login_user):
    admin, _ = user_factory(email='admin-member@example.com')
    group = group_factory(creator=admin)
    member, password = user_factory(email='member-already@example.com')
    login_user(member.email, password)

    client.post(
        '/groups/join',
        data={'invite_code': group.invite_code},
        follow_redirects=True,
    )

    response = client.post(
        '/groups/join',
        data={'invite_code': group.invite_code},
        follow_redirects=True,
    )

    assert b'already a member' in response.data


def test_join_group_requires_login(client):
    response = client.post(
        '/groups/join',
        data={'invite_code': 'ANYPASS'},
        follow_redirects=False,
    )
    assert response.status_code == 302


def test_leave_group_success(client, user_factory, group_factory, login_user):
    admin, _ = user_factory(email='admin-leave@example.com')
    group = group_factory(creator=admin)
    member, member_password = user_factory(email='member-leave@example.com')

    db.session.add(Membership(user_id=member.id, group_id=group.id, role='member'))
    db.session.commit()

    login_user(member.email, member_password)
    response = client.post(f'/groups/{group.id}/leave', follow_redirects=True)

    assert b'left the group' in response.data
    membership = Membership.query.filter_by(user_id=member.id, group_id=group.id).first()
    assert membership is None


def test_leave_group_admin_blocked(client, user_factory, group_factory, login_user):
    admin, admin_password = user_factory(email='admin-blocked@example.com')
    group = group_factory(creator=admin)
    login_user(admin.email, admin_password)

    response = client.post(f'/groups/{group.id}/leave', follow_redirects=True)

    assert b'Admins cannot leave' in response.data
    membership = Membership.query.filter_by(user_id=admin.id, group_id=group.id).first()
    assert membership is not None


def test_leave_group_requires_login(client, user_factory, group_factory):
    admin, _ = user_factory(email='admin-logout-leave@example.com')
    group = group_factory(creator=admin)

    response = client.post(f'/groups/{group.id}/leave', follow_redirects=False)
    assert response.status_code == 302


def test_leave_group_non_member_404(client, user_factory, group_factory, login_user):
    admin, _ = user_factory(email='admin-nonmember-leave@example.com')
    group = group_factory(creator=admin)
    other, other_password = user_factory(email='other-leave@example.com')
    login_user(other.email, other_password)

    response = client.post(f'/groups/{group.id}/leave')
    assert response.status_code == 404


def test_join_group_case_insensitive_invite_code(client, user_factory, group_factory, login_user):
    admin, _ = user_factory(email='admin-case@example.com')
    group = group_factory(creator=admin)

    member, member_password = user_factory(email='member-case@example.com')
    login_user(member.email, member_password)

    client.post(
        '/groups/join',
        data={'invite_code': group.invite_code.lower()},
        follow_redirects=True,
    )
    membership = Membership.query.filter_by(group_id=group.id, user_id=member.id).first()
    assert membership is not None
