import os
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split

BASE = os.path.dirname(os.path.abspath(__file__))
data = pd.read_csv(os.path.join(BASE, "data", "placement_data.csv"))

features = [
    "cgpa",
    "technical_score",
    "dsa_score",
    "communication_score",
    "projects",
    "internships"
]

X = data[features]
y = data["placement_score"]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

model = RandomForestRegressor(n_estimators=150, random_state=42)
model.fit(X_train, y_train)

model_dir = os.path.join(BASE, "model")
os.makedirs(model_dir, exist_ok=True)
joblib.dump(model, os.path.join(model_dir, "placement_model.pkl"))

print("Model training completed!")
print("Accuracy:", round(model.score(X_test, y_test), 3))
print("Model saved successfully!")
