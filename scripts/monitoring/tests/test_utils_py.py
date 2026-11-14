from unittest.mock import patch

import pytest

from scripts.monitoring.utils import OlBlockingScheduler, bash_run, limit_server


def test_bash_run():
    with patch("subprocess.run") as mock_subprocess_run:
        # Test without sources
        bash_run("echo 'Hello, World!'")
        assert mock_subprocess_run.call_args[0][0] == [
            "bash",
            "-c",
            "set -e\necho 'Hello, World!'",
        ]

        # Test with sources
        mock_subprocess_run.reset_mock()
        bash_run("echo 'Hello, World!'", sources=["source1.sh", "source2.sh"])
        assert mock_subprocess_run.call_args[0][0] == [
            "bash",
            "-c",
            'set -e\nsource "scripts/monitoring/source1.sh"\nsource "scripts/monitoring/source2.sh"\necho \'Hello, World!\'',
        ]


def test_limit_server_matches_exact_and_prefix_hosts():
    cases = [
        ("allowed-server", ["allowed-server"], True),
        ("allowed-server-suffix", ["allowed-server"], False),
        ("allowed-server0", ["allowed-server*"], True),
        ("other-server", ["allowed-server*"], False),
        ("ol-web0.us.archive.org", ["ol-web*"], True),
        ("ol-web0.us.archive.org", ["ol-web0"], True),
        ("other-server", ["first", "other-server"], True),
        ("allowed-server", [], False),
    ]
    for hostname, allowed_servers, allowed in cases:
        with patch("os.environ.get", return_value=hostname):
            scheduler = OlBlockingScheduler()

            @limit_server(allowed_servers, scheduler, "interval", seconds=60, id="scoped-job")
            def sample_job():
                return "ran"

            job = scheduler.get_job("scoped-job")
            assert (job is not None) is allowed
            assert sample_job() == "ran"
            if job is not None:
                assert job.func is sample_job
                assert job.id == "scoped-job"
                assert job.trigger.interval.total_seconds() == 60


def test_limit_server_fails_fast_without_hostname():
    for hostname in (None, ""):
        with patch("os.environ.get", return_value=hostname):
            scheduler = OlBlockingScheduler()
            with pytest.raises(AssertionError):

                @limit_server(["allowed-server"], scheduler, "interval", seconds=60)
                def sample_job():
                    pass


def test_limit_server_does_not_affect_unrelated_jobs():
    with patch("os.environ.get", return_value="other-server"):
        scheduler = OlBlockingScheduler()
        scheduler.add_job(lambda: None, "interval", seconds=60, id="unrelated")

        @limit_server(["allowed-server"], scheduler, "interval", seconds=60)
        def sample_job():
            pass

        assert scheduler.get_job("sample_job") is None
        assert scheduler.get_job("unrelated") is not None
