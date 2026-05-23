"""Tests for the images exporter."""
from pathlib import Path
from unittest.mock import patch

from grand_sumo.exporters.images import download_rikishi_images, RIKISHI


class TestRikishiList:
    def test_has_entries(self):
        assert len(RIKISHI) > 0
        assert all(isinstance(name, str) and isinstance(pid, int) for name, pid in RIKISHI)

    def test_known_rikishi(self):
        names = [name for name, _ in RIKISHI]
        assert "Hoshoryu" in names
        assert "Onosato" in names


class TestDownloadRikishiImages:
    def test_profile_fetch_error_does_not_crash(self, tmp_path):
        with patch("grand_sumo.exporters.images._fetch_url") as mock_fetch:
            mock_fetch.side_effect = Exception("Connection error")
            with patch("grand_sumo.exporters.images.time.sleep"):
                download_rikishi_images(
                    output_dir=tmp_path,
                )
        # Should not crash; failed rikishi are logged, not raised
        assert True

    def test_creates_output_dir(self, tmp_path):
        out = tmp_path / "new_images"
        assert not out.exists()
        with patch("grand_sumo.exporters.images._fetch_url") as mock_fetch:
            mock_fetch.side_effect = Exception("Connection error")
            with patch("grand_sumo.exporters.images.time.sleep"):
                download_rikishi_images(output_dir=out)
        assert out.exists()

    def test_successful_download(self, tmp_path):
        html_with_image = 'src="/img/sumo_data/rikishi/270x474/1234.jpg"'
        with patch("grand_sumo.exporters.images._fetch_url") as mock_fetch:
            mock_fetch.side_effect = [
                html_with_image,  # profile page
                b"fake_image_bytes",  # image data
            ]
            with patch("grand_sumo.exporters.images.time.sleep"):
                download_rikishi_images(
                    output_dir=tmp_path,
                )
        assert (tmp_path / "Hoshoryu.jpg").exists()
        assert (tmp_path / "Hoshoryu.jpg").read_bytes() == b"fake_image_bytes"

    def test_image_url_not_found(self, tmp_path):
        html_no_image = "<html>no image here</html>"
        with patch("grand_sumo.exporters.images._fetch_url") as mock_fetch:
            mock_fetch.return_value = html_no_image
            with patch("grand_sumo.exporters.images.time.sleep"):
                download_rikishi_images(
                    output_dir=tmp_path,
                )
        # Should not crash, just log failure
        assert True
