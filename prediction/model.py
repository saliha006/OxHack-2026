"""Simple logistic regression; NumPy is needed only for offline fitting."""
import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path

from prediction.features import FEATURE_NAMES, VERSION, featurize


def sigmoid(x: float) -> float:
    return 1 / (1 + math.exp(-max(-35, min(35, x))))


@dataclass
class WinModel:
    weights: list[float]
    means: list[float]
    scales: list[float]
    bias: float = 0
    calibration_slope: float = 1
    calibration_intercept: float = 0
    feature_version: int = VERSION
    feature_names: list[str] = field(default_factory=lambda: list(FEATURE_NAMES))
    metadata: dict = field(default_factory=dict)

    def logit(self, state: dict) -> float:
        if self.feature_version != VERSION or self.feature_names != list(FEATURE_NAMES):
            raise ValueError("model feature schema does not match the serving featurizer")
        return self.bias + sum(w * (x - mean) / scale for w, x, mean, scale in
                               zip(self.weights, featurize(state), self.means, self.scales))

    def predict(self, state: dict, *, calibrated: bool = True) -> float:
        raw = self.logit(state)
        return sigmoid(self.calibration_slope * raw + self.calibration_intercept if calibrated else raw)

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(asdict(self), indent=2) + "\n", encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path):
        model = cls(**json.loads(Path(path).read_text(encoding="utf-8")))
        if model.feature_version != VERSION or model.feature_names != list(FEATURE_NAMES):
            raise ValueError("unsupported feature schema")
        if not (len(model.weights) == len(model.means) == len(model.scales) == len(FEATURE_NAMES)):
            raise ValueError("invalid model dimensions")
        if any(s <= 0 or not math.isfinite(s) for s in model.scales):
            raise ValueError("invalid feature scales")
        return model


def _fit(x, y, weights, *, epochs: int, rate: float, l2: float, initial=None):
    import numpy as np
    coefficients = np.zeros(x.shape[1]) if initial is None else np.asarray(initial, dtype=float).copy()
    bias = 0.0
    weights = np.asarray(weights, dtype=float)
    weights /= weights.sum()
    for _ in range(epochs):
        probabilities = 1 / (1 + np.exp(-np.clip(x @ coefficients + bias, -35, 35)))
        error = (probabilities - y) * weights
        coefficients -= rate * (x.T @ error + l2 * coefficients)
        bias -= rate * float(error.sum())
    return coefficients, bias


def fit_model(rows: list[dict], *, epochs: int = 400, rate: float = 0.2, l2: float = 0.001) -> WinModel:
    import numpy as np
    if not rows or len({r["winner"] == r["state"]["us"] for r in rows}) < 2:
        raise ValueError("training requires nonempty battles with both winner labels")
    x = np.asarray([featurize(r["state"]) for r in rows], dtype=float)
    y = np.asarray([float(r["winner"] == r["state"]["us"]) for r in rows])
    means, scales = x.mean(axis=0), x.std(axis=0)
    scales[scales < 1e-8] = 1
    coefficients, bias = _fit((x - means) / scales, y, np.ones(len(rows)), epochs=epochs, rate=rate, l2=l2)
    return WinModel(coefficients.tolist(), means.tolist(), scales.tolist(), bias=bias,
                    metadata={"epochs": epochs, "rate": rate, "l2": l2, "training_rows": len(rows),
                              "training_battles": len({r["battle_id"] for r in rows}),
                              "preprocessing_fit_on": "train"})


def calibrate(model: WinModel, validation: list[dict], *, epochs: int = 400) -> None:
    """Platt calibration fitted only to the caller's validation split, never a test row."""
    import numpy as np
    if not validation or len({r["winner"] == r["state"]["us"] for r in validation}) < 2:
        raise ValueError("validation calibration requires both outcome labels")
    logits = np.asarray([[model.logit(r["state"])] for r in validation])
    labels = np.asarray([float(r["winner"] == r["state"]["us"]) for r in validation])
    slopes, intercept = _fit(logits, labels, np.ones(len(validation)), epochs=epochs, rate=0.05, l2=0.001, initial=[1])
    model.calibration_slope = float(slopes[0])
    model.calibration_intercept = intercept
    model.metadata["calibration_fit_on"] = "validation"
    model.metadata["calibration_battles"] = sorted({r["battle_id"] for r in validation})
