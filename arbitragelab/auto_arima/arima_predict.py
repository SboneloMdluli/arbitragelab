"""
The module implements ARIMA forecast of any time series using Auto-ARIMA approach.
"""
import pandas as pd
import numpy as np
from pmdarima.arima import auto_arima, ADFTest


def get_trend_order(y_train) -> int:
    """
    Get trend order for a time series using 95% ADF test.

    :param y_train: (pd.Series) Series to test.
    :return: (int) trend order, 0 means that `y_train` is already stationary.
    """

    adf_test = ADFTest(alpha=0.05)
    diff_order = 0
    order = 0
    stationarity_flag = False
    while stationarity_flag is False:
        test_series = y_train.copy()
        for _ in range(order):
            test_series = test_series.diff().dropna()
        if bool(adf_test.should_diff(test_series)[1]) is False:
            diff_order = order
            stationarity_flag = True
        order += 1
    return diff_order


class AutoARIMAForecast:
    """
    Auto ARIMA forecast generator function.
    """

    def __init__(self, start_p: int = 0, start_q: int = 0, max_p: int = 5, max_q: int = 5):
        """
        Init AutoARIMA (p, i, q)  prediction class.
        :param start_p: (int) starting value of p (number of time lags) to search in auto ARIMA procedure.
        :param start_q: (int) starting value of q (moving average
        :param max_p: (int) maximum possible value of p.
        :param max_q: (int) maximum possible value of q.
        """

        self.start_p = start_p
        self.start_q = start_q
        self.max_p = max_p
        self.max_q = max_q

        self.arima_model = None
        self.y_train = None

    def get_best_arima_model(self, y_train: pd.Series, verbose=False):
        """
        Using AIC approach from pmdarima library, choose the best fir ARIMA(d, p, q) parameters.

        :param y_train: (pd.Series) training series.
        :param verbose: (bool) Flag to print model fit logs.
        """
        trend_order = get_trend_order(y_train)
        self.y_train = y_train.copy()
        self.arima_model = auto_arima(y=y_train, d=trend_order, start_p=self.start_p, start_q=self.start_q,
                                      max_p=self.max_p,
                                      max_q=self.max_q, max_order=self.max_q + self.max_p + trend_order, trace=verbose)

    # pylint: disable=invalid-name
    # pylint: disable=invalid-unary-operand-type
    def predict(self, y: pd.Series, retrain_freq: int = 1, train_window: int = None) -> pd.Series:
        """
        Predict out-of-sample series using already fit ARIMA model. The algorithm retrains the model with `retrain_freq`
        either by appending new observations to train data (`train_window` = None) or by using latest `train_window`
        observations + latest out-of-sample observations `y`.

        :param y: (pd.Series) out-of-sample series (used to generate rolling forecast).
        :param retrain_freq: (int) model retraining frequency. Model is fit on every `train_freq` step.
        :param train_window: (int) number of data points from train dataset used in model retrain. If None, use all
        train set.
        :return: (pd.Series) of forecasted values.
        """
        prediction = pd.Series(index=y.index, dtype=np.float)
        retrain_idx = 0
        for i in range(1, y.shape[0]):
            if retrain_idx >= retrain_freq:
                retrain_idx = 0
                if train_window is None:
                    # i-1 to avoid look-ahead bias.
                    prediction.loc[y.index[i]] = \
                        self.arima_model.fit_predict(self.y_train.append(y.iloc[:i - 1]), n_periods=1)[0]
                else:
                    prediction.loc[y.index[i]] = \
                        self.arima_model.fit_predict(self.y_train.iloc[-train_window:].append(y.iloc[:i - 1]),
                                                     n_periods=1)[0]
            else:
                prediction.loc[y.index[i]] = self.arima_model.predict(n_periods=1)[0]

            retrain_idx += 1
        return prediction
