from data_layer.data_provider import DataLayer
from backtest.runner import Backtester
import yaml

def run():
    with open('config.yaml') as f:
        cfg = yaml.safe_load(f)

    dl = DataLayer()
    bt = Backtester(dl, cfg)
    bt.run_backtest('2023-01-01', '2023-06-01', top_n=3, holding_period=10)

if __name__ == '__main__':
    run()
