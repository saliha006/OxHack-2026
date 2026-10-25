"""Proper binary scores and calibration measurements for held-out battles."""
import math
from pathlib import Path

from prediction.features import hp_baseline

EPSILON = 1e-6


def binary_metrics(labels: list[float], probabilities: list[float], bins: int = 10) -> dict | None:
    if not labels:
        return None
    if len(labels) != len(probabilities):
        raise ValueError("labels and predictions must have equal length")
    p = [max(EPSILON, min(1 - EPSILON, value)) for value in probabilities]
    calibration = []
    for index in range(bins):
        selected = [i for i, value in enumerate(p) if min(int(value * bins), bins - 1) == index]
        calibration.append({"lower": index / bins, "upper": (index + 1) / bins, "count": len(selected),
                            "predicted": sum(p[i] for i in selected) / len(selected) if selected else None,
                            "observed": sum(labels[i] for i in selected) / len(selected) if selected else None})
    return {"rows": len(labels), "log_loss": -sum(y * math.log(q) + (1 - y) * math.log(1 - q)
                                                  for y, q in zip(labels, p)) / len(labels),
            "brier": sum((y - q) ** 2 for y, q in zip(labels, p)) / len(labels),
            "calibration": calibration, "probability_clip": EPSILON}


def evaluate(model, rows: list[dict], training_constant: float) -> dict:
    labels = [float(row["winner"] == row["state"]["us"]) for row in rows]
    predictors = {"constant_0.5": lambda _: 0.5, "training_constant": lambda _: training_constant,
                  "hp_only": hp_baseline, "logistic": lambda state: model.predict(state, calibrated=False),
                  "calibrated_logistic": model.predict}
    return {name: binary_metrics(labels, [predict(row["state"]) for row in rows]) for name, predict in predictors.items()}


def plot_calibration(results: dict, output: Path) -> None:
    """Standalone standard scientific plot; no learned search or viewer coupling."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    figure, axis = plt.subplots(figsize=(6, 5))
    axis.plot([0, 1], [0, 1], "--", color="gray", label="ideal")
    for name, metrics in results.items():
        if metrics is None:
            continue
        bins = [b for b in metrics["calibration"] if b["count"]]
        axis.plot([b["predicted"] for b in bins], [b["observed"] for b in bins], marker="o", label=name)
    axis.set(xlim=(0, 1), ylim=(0, 1), xlabel="Mean predicted win probability", ylabel="Observed win frequency",
             title="Held-out calibration (turn-weighted)")
    axis.legend(fontsize=8)
    axis.grid(alpha=0.2)
    figure.tight_layout()
    figure.savefig(output.with_suffix(".png"), dpi=160)
    figure.savefig(output.with_suffix(".svg"))
    plt.close(figure)
