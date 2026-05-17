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
