import os
import pytest

GUIDE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'guides_you_requested')

@pytest.mark.parametrize('filename', [f for f in os.listdir(GUIDE_DIR) if f.endswith('.pdf')])
def test_pdf_exists(filename):
    path = os.path.join(GUIDE_DIR, filename)
    assert os.path.isfile(path), f'{path} does not exist'
    assert os.path.getsize(path) > 0, f'{path} is empty'

@pytest.mark.parametrize('filename', [f for f in os.listdir(GUIDE_DIR) if f.endswith('.pdf')])
def test_pdf_header(filename):
    path = os.path.join(GUIDE_DIR, filename)
    with open(path, 'rb') as fh:
        header = fh.read(5)
    assert header == b'%PDF-', f'{filename} does not start with a PDF header'
