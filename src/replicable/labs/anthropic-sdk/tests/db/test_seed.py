"""The sample cards every run starts with."""

import db


def test_seed_adds_every_sample_in_order():
    """Seeding an empty store gives exactly the samples, in the order they are written."""
    db.store.clear()
    assert db.list_cards() == []

    db.seed.seed()

    assert [(c.title, c.content) for c in db.list_cards()] == db.seed.SAMPLES
