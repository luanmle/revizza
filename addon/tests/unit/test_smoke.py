import tempfile

from anki.collection import Collection


def test_addon_package_imports():
    import ankihub_br  # noqa: F401


def test_headless_collection_opens():
    with tempfile.TemporaryDirectory() as tmp:
        col = Collection(f"{tmp}/collection.anki2")
        assert col.decks.all_names_and_ids()
        col.close()
