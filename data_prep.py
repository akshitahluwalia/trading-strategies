import pandas as pd

FILE_PATH = "candle_data.csv"

def assemble(data, window):
    data["Volume Scaling Factor"] = data["Volume"].rolling(window=window).mean()
    data["Price Scaling Factor"] = data["Heikin Ashi - Close"].rolling(window=window).mean()

    data["Open"] =  data["Open"] / data["Price Scaling Factor"]
    data["Close"] =  data["Close"] / data["Price Scaling Factor"]
    data["Low"] =  data["Low"] / data["Price Scaling Factor"]
    data["High"] =  data["High"] / data["Price Scaling Factor"]
    data["Heikin Ashi - Open"] =  data["Heikin Ashi - Open"] / data["Price Scaling Factor"]
    data["Heikin Ashi - High"] =  data["Heikin Ashi - High"] / data["Price Scaling Factor"]
    data["Heikin Ashi - Low"] =  data["Heikin Ashi - Low"] / data["Price Scaling Factor"]
    data["Heikin Ashi - Close"] =  data["Heikin Ashi - Close"] / data["Price Scaling Factor"]

    # Assemble label column
    data["Heiken Ashi (N+1)th Change is Negative"] = data["Heikin Ashi - Change"].shift(-1).fillna(0) < 0.0
    data["Heiken Ashi (N+2)th Change is Negative"] = data["Heikin Ashi - Change"].shift(-2).fillna(0) < 0.0

    for i in range(window):
        data[f"Volume of (N-{i})th Day"] = data["Volume"].shift(i).fillna(0) / data["Volume Scaling Factor"]
        data[f"Heikin Ashi Change of (N-{i})th Day"] = data["Heikin Ashi - Change"].shift(i).fillna(0) / data["Price Scaling Factor"]

    for idx, row in data.iterrows():
        print(idx,row["Heiken Ashi (N+1)th Change is Negative"] is True and row["Heiken Ashi (N+2)th Change is Negative"] is True)
        if row["Heiken Ashi (N+1)th Change is Negative"] is True and row["Heiken Ashi (N+2)th Change is Negative"] is True:
            data.loc[idx, "Prediction"] = "EXIT-LONG-POSITION"
        else:
            data.loc[idx, "Prediction"] = "MAINTAIN-POSITION"

    return data

# Data is time sorted OHLCVO data
data = pd.read_csv(FILE_PATH)

assembled_data = assemble(data, 10)
assembled_data.to_csv("model.csv")

print(assembled_data)