import sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_rvpi import classify_provider, norm_name, zscore


def test_name_normalisation():
    assert norm_name("The Example NHS Foundation Trust") == "EXAMPLE"


def test_zscore_is_centred():
    out = zscore(pd.Series([1, 2, 3]))
    assert np.isclose(out.mean(), 0)
    assert np.isclose(out.std(ddof=0), 1)


def test_constant_zscore_is_zero():
    assert (zscore(pd.Series([4, 4])) == 0).all()


def test_provider_classification_uses_exact_eric_type():
    assert classify_provider("ACUTE - TEACHING", "Example NHS Trust") == ("acute_general", "eric_trust_type")
    assert classify_provider("ACUTE - SPECIALIST", "Example NHS Trust") == ("specialist", "eric_trust_type")


def test_provider_classification_name_fallback_is_literal_not_fuzzy():
    assert classify_provider(None, "Example Ambulance Service NHS Trust")[0] == "ambulance"
    assert classify_provider(None, "Example General Hospital NHS Trust")[0] == "unknown_or_other"
