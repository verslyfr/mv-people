import os
import pytest
from src.detector import PersonDetector

# Define the path to test images
TEST_IMAGES_DIR = os.path.join(os.path.dirname(__file__), 'test-images')

@pytest.fixture
def detector():
    return PersonDetector()

def get_images(prefix):
    """Helper to find images starting with a prefix in the test directory."""
    images = []
    if not os.path.exists(TEST_IMAGES_DIR):
        return images
    
    for filename in os.listdir(TEST_IMAGES_DIR):
        if filename.startswith(prefix):
            images.append(os.path.join(TEST_IMAGES_DIR, filename))
    return images

def test_detects_people(detector):
    images = get_images("has-people")
    if not images:
        pytest.skip("No 'has-people' images found in tests/test-images")
    
    failures = []
    for img_path in images:
        if not detector.contains_people(img_path):
            failures.append(os.path.basename(img_path))
    
    assert not failures, f"Failed to detect people in: {failures}"

def test_detects_no_people(detector):
    images = get_images("no-people")
    if not images:
        pytest.skip("No 'no-people' images found in tests/test-images")
    
    failures = []
    for img_path in images:
        if detector.contains_people(img_path):
            failures.append(os.path.basename(img_path))
            
    assert not failures, f"Falsely detected people in: {failures}"
