"""
Test the optimization module.
"""

import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.model_selection import ParameterGrid
from sklearn.multioutput import MultiOutputClassifier
import pytest

from sportsbet.externals import TimeSeriesSplit
from sportsbet.soccer import TARGETS
from sportsbet.soccer.optimization import (
        extract_multi_labels, 
        extract_class_labels,
        calculate_yields,
        extract_yields_stats,
        fit_bet,
        apply_backtesting,
        BettorMixin,
        Bettor,
        MultiBettor
)

X = [[0], [1], [2]] * 10
score1, score2 = [0, 2, 3] * 10, [1, 1, 3] * 10
odds = [[3.0, 1.5], [4.0, 2.0], [2.5, 2.5]] * 10


def test_extract_multi_labels():
    """Test the extraction of multi-labels."""
    score1, score2 = [0, 2, 3], [1, 1, 3]
    targets = ['D', 'H', 'over_2.5']
    multi_labels = np.array([[0, 0, 0], [0, 1, 1], [1, 0, 1]])
    np.testing.assert_array_equal(extract_multi_labels(score1, score2, targets), multi_labels)


def test_extract_class_labels():
    """Test the extraction of class labels."""
    score1, score2 = [0, 2, 3], [1, 1, 3]
    odds = [[3.0, 1.5, 2.0], [4.0, 2.0, 3.0], [2.5, 2.5, 2.0]]
    targets = ['D', 'H', 'over_2.5']
    class_labels = np.array(['-', 'over_2.5', 'D'])
    np.testing.assert_array_equal(extract_class_labels(score1, score2, odds, targets), class_labels)


def test_calculate_yields():
    """Test the calculation of yields."""
    score1, score2 = [0, 2, 3], [1, 1, 3]
    bets = ['-', 'D', 'over_2.5']
    odds = [[3.0, 1.5, 2.0], [4.0, 2.0, 3.0], [2.5, 2.5, 2.5]]
    targets = ['D', 'H', 'over_2.5']
    yields = np.array([0.0, -1.0, 1.5])
    np.testing.assert_array_equal(calculate_yields(score1, score2, bets, odds, targets), yields)


def test_extract_yields_stats():
    """Test the calculation of yields."""
    yields = np.array([0.0, -1.0, 2.0, 0.0])
    np.testing.assert_array_equal(extract_yields_stats(yields), (0.5, 0.5, 1.5))


def test_fit_bet():
    """Test fit and bet function."""

    # Input data
    bettor = Bettor(classifier=DummyClassifier(), targets=['D', 'H'])
    params = {'classifier__strategy': 'constant', 'classifier__constant': 'H'}
    risk_factors = [0.0]
    random_state = 0
    X = np.random.random((100, 2))
    scores = np.repeat([1, 0], 50), np.repeat([0, 1], 50), np.repeat([1, 0], 50), np.repeat([0, 1], 50)
    train_indices, test_indices = np.arange(0, 25), np.arange(25, 100)
    odds = np.repeat([2.0, 2.0], 100).reshape(-1, 2)

    # Output
    data = fit_bet(bettor, params, risk_factors, random_state, X, scores, odds, train_indices, test_indices)
    
    # Expected output
    expected_yields = np.concatenate([np.repeat(1.0, 25), np.repeat(-1.0, 50)])
    expected_data = pd.DataFrame([[str(params), random_state, risk_factors[0], expected_yields]], columns=['parameters', 'experiment', 'risk_factor', 'yields'])
    
    pd.testing.assert_frame_equal(expected_data, data)


def test_apply_backtesting():
    """Test backtesting function."""

    # Input data
    bettor = Bettor(classifier=DummyClassifier(), targets=['D', 'H'])
    param_grid = {'classifier__strategy': ['uniform', 'stratified']}
    risk_factors = [0.0, 0.2, 0.4]
    random_state = 0
    X = np.random.random((100, 2))
    scores = np.repeat([1, 0], 50), np.repeat([0, 1], 50), np.repeat([1, 0], 50), np.repeat([0, 1], 50)
    odds = np.repeat([2.0, 2.0], 100).reshape(-1, 2)
    cv = TimeSeriesSplit(2, 0.3)
    n_runs = 3
    n_jobs = -1

    # Output
    results = apply_backtesting(bettor, param_grid, risk_factors, X, scores, odds, cv, random_state, n_runs, n_jobs)

    assert list(results.columns) == ['parameters', 'risk_factor', 'coverage', 'mean_yield', 'std_yield', 'std_mean_yield']
    assert len(results) == len(risk_factors) * len(ParameterGrid(param_grid))


def test_none_targets_bettor_mixin():
    """Test bettor mixin with none targets."""
    base_bettor = BettorMixin(None).fit()
    np.testing.assert_array_equal(base_bettor.targets_, np.array(list(TARGETS.keys())))


def test_invalid_targets_bettor_mixin():
    """Test bettor mixin with invalid targets."""
    with pytest.raises(ValueError):
        BettorMixin(['Away', 'H']).fit()


def test_valid_targets_bettor_mixin():
    """Test bettor mixin with valid targets."""
    base_bettor = BettorMixin(['A', 'H']).fit()
    np.testing.assert_array_equal(base_bettor.targets_, np.array(['A', 'H']))
    

def test_bettor_fit():
    """Test fit method of bettor."""

    bettor = Bettor(classifier=DummyClassifier(random_state=0), targets=['H', 'D']).fit(X, score1, score2, odds)
    np.testing.assert_array_equal(bettor.classifier_.classes_, np.array(['-', 'D', 'H']))

    bettor = Bettor(classifier=DummyClassifier(random_state=0), targets=['over_2.5', 'under_2.5']).fit(X, score1, score2, odds)
    np.testing.assert_array_equal(bettor.classifier_.classes_, np.array(['over_2.5', 'under_2.5']))

    bettor = Bettor(classifier=DummyClassifier(random_state=0), targets=['over_2.5', 'A']).fit(X, score1, score2, odds)
    np.testing.assert_array_equal(np.unique(bettor.classifier_.classes_), np.array(['A', 'over_2.5']))


def test_bettor_predict():
    """Test predict method of bettor."""

    bettor = Bettor(classifier=DummyClassifier(random_state=0), targets=['H', 'D']).fit(X, score1, score2, odds)
    np.testing.assert_array_equal(np.unique(bettor.predict(X)), np.array(['-', 'D', 'H']))

    bettor = Bettor(classifier=DummyClassifier(random_state=0), targets=['over_2.5', 'under_2.5']).fit(X, score1, score2, odds)
    np.testing.assert_array_equal(np.unique(bettor.predict(X)), np.array(['over_2.5', 'under_2.5']))

    bettor = Bettor(classifier=DummyClassifier(random_state=0), targets=['over_2.5', 'A']).fit(X, score1, score2, odds)
    np.testing.assert_array_equal(np.unique(bettor.predict(X)), np.array(['A', 'over_2.5']))


def test_bettor_predict_proba():
    """Test predict probabilities method of bettor."""
    
    bettor = Bettor(classifier=DummyClassifier(random_state=0), targets=['H', 'D']).fit(X, score1, score2, odds)
    assert bettor.predict_proba(X).shape == (30, 3)

    bettor = Bettor(classifier=DummyClassifier(random_state=0), targets=['over_2.5', 'under_2.5']).fit(X, score1, score2, odds)
    assert bettor.predict_proba(X).shape == (30, 2)

    bettor = Bettor(classifier=DummyClassifier(random_state=0), targets=['over_2.5', 'A']).fit(X, score1, score2, odds)
    assert bettor.predict_proba(X).shape == (30, 2)


def test_multi_bettor_fit():
    """Test fit method of multi-bettor."""
    
    multi_bettor = MultiBettor(multi_classifier=MultiOutputClassifier(DummyClassifier()), meta_classifier=DummyClassifier(), targets=['D', 'H']).fit(X, score1, score2, odds)
    assert len(multi_bettor.multi_classifier_.estimators_) == len(multi_bettor.targets_)
    np.testing.assert_array_equal(np.unique(multi_bettor.meta_classifier_.classes_), np.array(['-', 'D', 'H']))

    multi_bettor = MultiBettor(multi_classifier=MultiOutputClassifier(DummyClassifier()), meta_classifier=DummyClassifier(), targets=['over_2.5', 'under_2.5']).fit(X, score1, score2, odds)
    assert len(multi_bettor.multi_classifier_.estimators_) == len(multi_bettor.targets_)
    np.testing.assert_array_equal(np.unique(multi_bettor.meta_classifier_.classes_), np.array(['over_2.5', 'under_2.5']))

    multi_bettor = MultiBettor(multi_classifier=MultiOutputClassifier(DummyClassifier()), meta_classifier=DummyClassifier(), targets=['over_2.5', 'A']).fit(X, score1, score2, odds)
    assert len(multi_bettor.multi_classifier_.estimators_) == len(multi_bettor.targets_)
    np.testing.assert_array_equal(np.unique(multi_bettor.meta_classifier_.classes_), np.array(['A', 'over_2.5']))


def test_multi_bettor_predict():
    """Test predict method of multi-bettor."""
    
    multi_bettor = MultiBettor(multi_classifier=MultiOutputClassifier(DummyClassifier()), meta_classifier=DummyClassifier(), targets=['D', 'H']).fit(X, score1, score2, odds)
    np.testing.assert_array_equal(np.unique(multi_bettor.predict(X)), np.array(['-', 'D', 'H']))

    multi_bettor = MultiBettor(multi_classifier=MultiOutputClassifier(DummyClassifier()), meta_classifier=DummyClassifier(), targets=['over_2.5', 'under_2.5']).fit(X, score1, score2, odds)
    np.testing.assert_array_equal(np.unique(multi_bettor.predict(X)), np.array(['over_2.5', 'under_2.5']))

    multi_bettor = MultiBettor(multi_classifier=MultiOutputClassifier(DummyClassifier()), meta_classifier=DummyClassifier(), targets=['over_2.5', 'A']).fit(X, score1, score2, odds)
    np.testing.assert_array_equal(np.unique(multi_bettor.predict(X)), np.array(['A', 'over_2.5']))


def test_multi_bettor_predict_proba():
    """Test predict probabilities method of multi-bettor."""
    
    multi_bettor = MultiBettor(multi_classifier=MultiOutputClassifier(DummyClassifier()), meta_classifier=DummyClassifier(), targets=['D', 'H']).fit(X, score1, score2, odds)
    assert multi_bettor.predict_proba(X).shape[1] == len(np.array(['-', 'D', 'H']))

    multi_bettor = MultiBettor(multi_classifier=MultiOutputClassifier(DummyClassifier()), meta_classifier=DummyClassifier(), targets=['over_2.5', 'under_2.5']).fit(X, score1, score2, odds)
    assert multi_bettor.predict_proba(X).shape[1] ==  len(np.array(['over_2.5', 'under_2.5']))

    multi_bettor = MultiBettor(multi_classifier=MultiOutputClassifier(DummyClassifier()), meta_classifier=DummyClassifier(), targets=['over_2.5', 'A']).fit(X, score1, score2, odds)
    assert multi_bettor.predict_proba(X).shape[1] ==  len(np.array(['A', 'over_2.5']))

