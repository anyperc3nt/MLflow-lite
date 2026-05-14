"""Unit-тесты ORM-моделей и ограничений уникальности."""
import pytest
from sqlalchemy.exc import IntegrityError

from app.models import Experiment, Metric, Param, Run, RunStatus, User, UserRole


def _make_user(session, email: str = "u@example.com") -> User:
    user = User(email=email, hashed_password="x", name="Test")
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def _make_experiment(session, owner: User, name: str = "exp-1") -> Experiment:
    exp = Experiment(name=name, owner_id=owner.id)
    session.add(exp)
    session.commit()
    session.refresh(exp)
    return exp


def test_create_user_defaults_to_user_role(db_session):
    user = _make_user(db_session)
    assert user.id is not None
    assert user.role == UserRole.USER
    assert user.created_at is not None


def test_user_email_is_unique(db_session):
    _make_user(db_session, "dup@example.com")
    duplicate = User(email="dup@example.com", hashed_password="y", name="Other")
    db_session.add(duplicate)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_experiment_unique_per_owner(db_session):
    user = _make_user(db_session)
    _make_experiment(db_session, user, name="train")
    other = Experiment(name="train", owner_id=user.id)
    db_session.add(other)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_two_users_can_have_same_experiment_name(db_session):
    user_a = _make_user(db_session, "a@example.com")
    user_b = _make_user(db_session, "b@example.com")
    _make_experiment(db_session, user_a, name="shared")
    _make_experiment(db_session, user_b, name="shared")
    assert db_session.query(Experiment).count() == 2


def test_run_defaults_to_running_status(db_session):
    user = _make_user(db_session)
    exp = _make_experiment(db_session, user)
    run = Run(experiment_id=exp.id)
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)
    assert run.status == RunStatus.RUNNING
    assert run.ended_at is None


def test_param_unique_per_run_key(db_session):
    user = _make_user(db_session)
    exp = _make_experiment(db_session, user)
    run = Run(experiment_id=exp.id)
    db_session.add(run)
    db_session.commit()

    db_session.add(Param(run_id=run.id, key="lr", value="0.01"))
    db_session.commit()
    db_session.add(Param(run_id=run.id, key="lr", value="0.02"))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_metric_unique_per_run_key_step(db_session):
    user = _make_user(db_session)
    exp = _make_experiment(db_session, user)
    run = Run(experiment_id=exp.id)
    db_session.add(run)
    db_session.commit()

    db_session.add(Metric(run_id=run.id, key="loss", value=0.5, step=0))
    db_session.add(Metric(run_id=run.id, key="loss", value=0.4, step=1))
    db_session.commit()

    db_session.add(Metric(run_id=run.id, key="loss", value=0.45, step=1))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_cascade_delete_user_removes_experiments_and_runs(db_session):
    user = _make_user(db_session)
    exp = _make_experiment(db_session, user)
    run = Run(experiment_id=exp.id)
    db_session.add(run)
    db_session.commit()

    db_session.delete(user)
    db_session.commit()

    assert db_session.query(Experiment).count() == 0
    assert db_session.query(Run).count() == 0
