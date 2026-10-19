from src.capabilities.memory import NOT_SET, ProfileStore, UserProfile


def test_profile_roundtrip(tmp_path):
    store = ProfileStore(tmp_path / "profile.json")
    profile = UserProfile("Non-EU citizen", "Degree student", "1 year or more", "Hämeenlinna")
    store.save(profile)
    assert store.load() == profile


def test_invalid_profile_values_fall_back_to_not_set():
    profile = UserProfile(citizenship="Martian", student_type="??", city="x" * 200)
    assert profile.citizenship == NOT_SET
    assert profile.student_type == NOT_SET
    assert len(profile.city) <= 60


def test_corrupt_profile_file_returns_empty_profile(tmp_path):
    path = tmp_path / "profile.json"
    path.write_text("{not json", encoding="utf-8")
    assert ProfileStore(path).load().is_empty()


def test_empty_profile_description():
    assert "Unknown" in UserProfile().describe()
