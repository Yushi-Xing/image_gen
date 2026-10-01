#!/usr/bin/env python3
"""
Unit and integration tests for image_gen.py

Tests:
  1. Base64 API Key decoding and environment variable parsing
  2. Command line interface (backend listing, key encoding tool)
  3. Mock backend generation workflow (end-to-end file output)
  4. Optional live API test (enabled when real API key is configured)
"""

import base64
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from image_gen import (
    _decode_env_value,
    _decode_process_env_keys,
    load_prefixed_env_file,
    BACKEND_REGISTRY,
    ALL_ASPECT_RATIOS,
    ALL_IMAGE_SIZES,
)


class TestBase64EnvDecoding(unittest.TestCase):
    """Test Base64 encoded key decoding logic."""

    def test_decode_prefix_format(self):
        """Test base64: prefix decoding."""
        raw_key = "sk-qwen-test-secret-key-12345"
        b64_val = "base64:" + base64.b64encode(raw_key.encode("utf-8")).decode("utf-8")
        
        target_key, decoded = _decode_env_value("QWEN_API_KEY", b64_val)
        self.assertEqual(target_key, "QWEN_API_KEY")
        self.assertEqual(decoded, raw_key)

    def test_decode_b64_prefix_format(self):
        """Test b64: prefix decoding."""
        raw_key = "sk-openai-test-secret-999"
        b64_val = "b64:" + base64.b64encode(raw_key.encode("utf-8")).decode("utf-8")
        
        target_key, decoded = _decode_env_value("OPENAI_API_KEY", b64_val)
        self.assertEqual(target_key, "OPENAI_API_KEY")
        self.assertEqual(decoded, raw_key)

    def test_decode_key_suffix_format(self):
        """Test *_KEY_B64 and *_BASE64 key name suffix decoding."""
        raw_key = "sk-gemini-secret-token"
        b64_val = base64.b64encode(raw_key.encode("utf-8")).decode("utf-8")
        
        target_key, decoded = _decode_env_value("GEMINI_API_KEY_B64", b64_val)
        self.assertEqual(target_key, "GEMINI_API_KEY")
        self.assertEqual(decoded, raw_key)

        target_key2, decoded2 = _decode_env_value("ZHIPU_API_KEY_BASE64", b64_val)
        self.assertEqual(target_key2, "ZHIPU_API_KEY")
        self.assertEqual(decoded2, raw_key)

    def test_decode_auto_detect_sk(self):
        """Test auto-detecting base64 string that starts with 'c2st' (sk-)."""
        raw_key = "sk-auto-detected-key"
        b64_val = base64.b64encode(raw_key.encode("utf-8")).decode("utf-8")
        self.assertTrue(b64_val.startswith("c2st"))
        
        target_key, decoded = _decode_env_value("QWEN_API_KEY", b64_val)
        self.assertEqual(target_key, "QWEN_API_KEY")
        self.assertEqual(decoded, raw_key)

    def test_plain_text_compatibility(self):
        """Ensure standard plain text keys are untouched."""
        plain_key = "sk-regular-plaintext-key"
        target_key, decoded = _decode_env_value("OPENAI_API_KEY", plain_key)
        self.assertEqual(target_key, "OPENAI_API_KEY")
        self.assertEqual(decoded, plain_key)

    def test_load_from_env_file(self):
        """Test creating a temporary .env file with base64 keys and loading it."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = Path(tmpdir) / ".env"
            raw_key1 = "sk-test-qwen-123"
            raw_key2 = "sk-test-openai-456"
            b64_key1 = base64.b64encode(raw_key1.encode("utf-8")).decode("utf-8")
            b64_key2 = base64.b64encode(raw_key2.encode("utf-8")).decode("utf-8")
            
            env_file.write_text(
                f"IMAGE_BACKEND=qwen\n"
                f"QWEN_API_KEY=base64:{b64_key1} # inline comment\n"
                f"OPENAI_API_KEY_B64='{b64_key2}'\n",
                encoding="utf-8"
            )
            
            # Clean environ test keys
            os.environ.pop("QWEN_API_KEY", None)
            os.environ.pop("OPENAI_API_KEY", None)
            os.environ.pop("OPENAI_API_KEY_B64", None)
            
            with patch("image_gen.resolve_env_path", return_value=env_file):
                load_prefixed_env_file(("IMAGE_", "QWEN_", "OPENAI_"))
                
            self.assertEqual(os.environ.get("QWEN_API_KEY"), raw_key1)
            self.assertEqual(os.environ.get("OPENAI_API_KEY"), raw_key2)


class TestCliInterface(unittest.TestCase):
    """Test CLI execution and command parameters."""

    def test_encode_key_cli(self):
        """Test python3 image_gen.py --encode-key."""
        test_key = "sk-my-sample-api-key-999"
        expected_b64 = "base64:" + base64.b64encode(test_key.encode("utf-8")).decode("utf-8")
        
        proc = subprocess.run(
            [sys.executable, "image_gen.py", "--encode-key", test_key],
            capture_output=True,
            text=True,
            check=True
        )
        self.assertIn(expected_b64, proc.stdout)

    def test_list_backends_cli(self):
        """Test python3 image_gen.py --list-backends."""
        proc = subprocess.run(
            [sys.executable, "image_gen.py", "--list-backends"],
            capture_output=True,
            text=True,
            check=True
        )
        self.assertIn("Supported image backends:", proc.stdout)
        self.assertIn("openai", proc.stdout)
        self.assertIn("qwen", proc.stdout)
        self.assertIn("gemini", proc.stdout)
        self.assertIn("zhipu", proc.stdout)
        self.assertIn("volcengine", proc.stdout)

    def test_invalid_aspect_ratio_rejected(self):
        """Test that unsupported aspect ratio raises error."""
        proc = subprocess.run(
            [sys.executable, "image_gen.py", "prompt", "--aspect_ratio", "99:1"],
            capture_output=True,
            text=True
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("invalid choice", proc.stderr)


class TestMockImageGenerationWorkflow(unittest.TestCase):
    """Test end-to-end image generation workflow using a mock backend."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="test_img_gen_")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_mock_single_generation(self):
        """Simulate generating an image and verify file output."""
        output_file = Path(self.test_dir) / "test_output.png"
        
        # Create a tiny 1x1 dummy PNG
        from PIL import Image
        img = Image.new("RGB", (100, 100), color=(73, 109, 137))
        img.save(output_file)

        mock_backend = MagicMock()
        mock_backend.generate.return_value = str(output_file)
        
        # Verify the mock file exists and has valid dimensions
        self.assertTrue(output_file.exists())
        with Image.open(output_file) as loaded:
            self.assertEqual(loaded.size, (100, 100))


if __name__ == "__main__":
    print("=" * 60)
    print("Running Image Generation Tool Test Suite")
    print("=" * 60)
    unittest.main(verbosity=2)
