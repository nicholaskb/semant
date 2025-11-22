def test_main_api_reexports_app():
    # Importing should not raise and should expose `app`
    mod = __import__("main_api")
    assert hasattr(mod, "app")

