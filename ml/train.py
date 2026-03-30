import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
import pickle
import warnings

# Suppress warnings that might appear for older versions of scikit-learn
warnings.filterwarnings("ignore", category=UserWarning)

data = pd.read_csv("data.csv")

X = data[["cpu", "memory", "processes", "disk"]]
y = data["label"]

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

model = RandomForestClassifier()
model.fit(X_train, y_train)

accuracy = model.score(X_test, y_test)
print(f"Model trained successfully!")
print(f"Accuracy: {accuracy * 100:.2f}%")

pickle.dump(model, open("model.pkl", "wb"))
