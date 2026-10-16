import warnings
import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import GroupKFold, cross_val_predict
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from features import CAT_COLS, NUM_COLS, load_features

warnings.filterwarnings("ignore", message="Found unknown categories")

df = load_features()
X = df[NUM_COLS + CAT_COLS]
y = df["log_value"]
cv = GroupKFold(n_splits=5)


def make_pipeline(estimator):
    pre = ColumnTransformer(
        [("cat", OneHotEncoder(drop="first", handle_unknown="ignore"), CAT_COLS)],
        remainder="passthrough",
    )
    return Pipeline([("pre", pre), ("model", estimator)])


models = {
    "Linear regression (F2)": LinearRegression(),
    "Random forest": RandomForestRegressor(
        n_estimators=300, min_samples_leaf=3, random_state=42, n_jobs=-1),
    "Gradient boosting": GradientBoostingRegressor(
        n_estimators=200, max_depth=3, learning_rate=0.05, random_state=42),
}

print(f"{'Model':<26}{'OOF R2':>8}{'MAE (€M)':>10}")
for name, est in models.items():
    pred = cross_val_predict(make_pipeline(est), X, y, groups=df["player_id"], cv=cv)
    r2 = r2_score(y, pred)
    mae = mean_absolute_error(np.exp(y) / 1e6, np.exp(pred) / 1e6)
    print(f"{name:<26}{r2:>8.3f}{mae:>10.1f}")