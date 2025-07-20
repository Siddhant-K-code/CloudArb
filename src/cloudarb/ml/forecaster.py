"""
Machine Learning forecasting engine for CloudArb.
Predicts demand, pricing trends, and arbitrage opportunities.
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib
import pickle
from prophet import Prophet
import warnings
warnings.filterwarnings('ignore')

from ..config import get_settings
from ..models.pricing import PricingData
from ..monitoring.metrics import metrics_collector

logger = logging.getLogger(__name__)
settings = get_settings()


class DemandForecaster:
    """ML-powered demand forecasting for GPU workloads."""

    def __init__(self):
        self.models = {}
        self.scalers = {}
        self.feature_columns = [
            'hour_of_day', 'day_of_week', 'day_of_month', 'month',
            'is_weekend', 'is_holiday', 'price_trend_1h', 'price_trend_6h',
            'price_trend_24h', 'demand_trend_1h', 'demand_trend_6h',
            'demand_trend_24h', 'spot_availability', 'provider_utilization'
        ]
        self.target_columns = ['demand', 'price_per_hour', 'spot_price']
        self.model_path = settings.ml.model_storage_path

    def prepare_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Prepare features for ML models."""
        df = data.copy()

        # Time-based features
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['hour_of_day'] = df['timestamp'].dt.hour
        df['day_of_week'] = df['timestamp'].dt.dayofweek
        df['day_of_month'] = df['timestamp'].dt.day
        df['month'] = df['timestamp'].dt.month
        df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)

        # Holiday detection (simplified)
        df['is_holiday'] = self._detect_holidays(df['timestamp'])

        # Price trends
        df['price_trend_1h'] = df['price_per_hour'].pct_change(1)
        df['price_trend_6h'] = df['price_per_hour'].pct_change(6)
        df['price_trend_24h'] = df['price_per_hour'].pct_change(24)

        # Demand trends (using price as proxy for demand)
        df['demand_trend_1h'] = df['price_per_hour'].rolling(1).mean().pct_change(1)
        df['demand_trend_6h'] = df['price_per_hour'].rolling(6).mean().pct_change(6)
        df['demand_trend_24h'] = df['price_per_hour'].rolling(24).mean().pct_change(24)

        # Spot availability (estimated from spot price vs on-demand ratio)
        df['spot_availability'] = (df['spot_price'] / df['price_per_hour']).fillna(0.8)

        # Provider utilization (estimated from price volatility)
        df['provider_utilization'] = df['price_per_hour'].rolling(6).std() / df['price_per_hour'].rolling(6).mean()

        # Fill NaN values
        df = df.fillna(method='ffill').fillna(0)

        return df

    def _detect_holidays(self, timestamps: pd.Series) -> pd.Series:
        """Detect major holidays (simplified implementation)."""
        holidays = []
        for ts in timestamps:
            # Major US holidays
            if ts.month == 1 and ts.day == 1:  # New Year's Day
                holidays.append(1)
            elif ts.month == 7 and ts.day == 4:  # Independence Day
                holidays.append(1)
            elif ts.month == 12 and ts.day == 25:  # Christmas
                holidays.append(1)
            else:
                holidays.append(0)
        return pd.Series(holidays, index=timestamps.index)

    def train_demand_model(self, data: pd.DataFrame, provider: str, instance_type: str) -> Dict[str, float]:
        """Train demand forecasting model."""
        try:
            # Prepare features
            df = self.prepare_features(data)

            # Filter for specific provider and instance type
            df_filtered = df[
                (df['provider_display_name'] == provider) &
                (df['instance_type'] == instance_type)
            ].copy()

            if len(df_filtered) < settings.ml.min_training_samples:
                logger.warning(f"Insufficient data for {provider} {instance_type}: {len(df_filtered)} samples")
                return {"status": "insufficient_data", "samples": len(df_filtered)}

            # Prepare features and target
            X = df_filtered[self.feature_columns].values
            y = df_filtered['price_per_hour'].values  # Using price as demand proxy

            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )

            # Scale features
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)

            # Train model
            model = GradientBoostingRegressor(
                n_estimators=100,
                learning_rate=0.1,
                max_depth=6,
                random_state=42
            )
            model.fit(X_train_scaled, y_train)

            # Evaluate model
            y_pred = model.predict(X_test_scaled)
            mae = mean_absolute_error(y_test, y_pred)
            mse = mean_squared_error(y_test, y_pred)
            r2 = r2_score(y_test, y_pred)

            # Store model and scaler
            model_key = f"{provider}_{instance_type}_demand"
            self.models[model_key] = model
            self.scalers[model_key] = scaler

            # Save model
            self._save_model(model_key, model, scaler)

            metrics = {
                "status": "success",
                "mae": mae,
                "mse": mse,
                "r2": r2,
                "samples": len(df_filtered)
            }

            logger.info(f"Trained demand model for {provider} {instance_type}: R²={r2:.3f}")
            return metrics

        except Exception as e:
            logger.error(f"Error training demand model: {e}")
            return {"status": "error", "error": str(e)}

    def predict_demand(self, provider: str, instance_type: str,
                      hours_ahead: int = 24) -> List[Dict[str, Any]]:
        """Predict demand for the next N hours."""
        try:
            model_key = f"{provider}_{instance_type}_demand"

            if model_key not in self.models:
                # Try to load model
                if not self._load_model(model_key):
                    logger.warning(f"No trained model found for {model_key}")
                    return []

            model = self.models[model_key]
            scaler = self.scalers[model_key]

            # Generate future timestamps
            future_timestamps = pd.date_range(
                start=datetime.utcnow(),
                periods=hours_ahead,
                freq='H'
            )

            # Create future features
            future_data = pd.DataFrame({'timestamp': future_timestamps})
            future_features = self.prepare_features(future_data)

            # Use last known values for trend features
            # In production, you'd use actual historical data
            for col in ['price_trend_1h', 'price_trend_6h', 'price_trend_24h',
                       'demand_trend_1h', 'demand_trend_6h', 'demand_trend_24h',
                       'spot_availability', 'provider_utilization']:
                future_features[col] = 0.0  # Neutral values

            # Make predictions
            X_future = future_features[self.feature_columns].values
            X_future_scaled = scaler.transform(X_future)
            predictions = model.predict(X_future_scaled)

            # Create prediction results
            results = []
            for i, (timestamp, pred) in enumerate(zip(future_timestamps, predictions)):
                results.append({
                    "timestamp": timestamp.isoformat(),
                    "predicted_demand": max(0, pred),  # Demand can't be negative
                    "confidence": self._calculate_confidence(pred, model, X_future_scaled[i]),
                    "hours_ahead": i + 1
                })

            return results

        except Exception as e:
            logger.error(f"Error predicting demand: {e}")
            return []

    def _calculate_confidence(self, prediction: float, model, features: np.ndarray) -> float:
        """Calculate prediction confidence (simplified)."""
        # In production, you'd use proper uncertainty quantification
        # For now, return a simple confidence based on feature values
        confidence = 0.8  # Base confidence

        # Adjust based on feature stability
        feature_stability = 1 - np.std(features)
        confidence *= feature_stability

        return max(0.1, min(0.95, confidence))

    def _save_model(self, model_key: str, model, scaler):
        """Save trained model and scaler."""
        try:
            model_data = {
                'model': model,
                'scaler': scaler,
                'timestamp': datetime.utcnow(),
                'feature_columns': self.feature_columns
            }

            model_file = f"{self.model_path}/{model_key}.pkl"
            with open(model_file, 'wb') as f:
                pickle.dump(model_data, f)

            logger.info(f"Saved model: {model_file}")

        except Exception as e:
            logger.error(f"Error saving model: {e}")

    def _load_model(self, model_key: str) -> bool:
        """Load trained model and scaler."""
        try:
            model_file = f"{self.model_path}/{model_key}.pkl"

            with open(model_file, 'rb') as f:
                model_data = pickle.load(f)

            self.models[model_key] = model_data['model']
            self.scalers[model_key] = model_data['scaler']

            logger.info(f"Loaded model: {model_file}")
            return True

        except Exception as e:
            logger.error(f"Error loading model: {e}")
            return False


class PriceTrendForecaster:
    """Forecasts price trends and arbitrage opportunities."""

    def __init__(self):
        self.prophet_models = {}
        self.trend_models = {}
        self.model_path = settings.ml.model_storage_path

    def train_price_trend_model(self, data: pd.DataFrame, provider: str,
                               instance_type: str) -> Dict[str, float]:
        """Train Prophet model for price trend forecasting."""
        try:
            # Filter data for specific provider and instance type
            df_filtered = data[
                (data['provider_display_name'] == provider) &
                (data['instance_type'] == instance_type)
            ].copy()

            if len(df_filtered) < settings.ml.min_training_samples:
                return {"status": "insufficient_data", "samples": len(df_filtered)}

            # Prepare data for Prophet
            df_prophet = df_filtered[['timestamp', 'price_per_hour']].copy()
            df_prophet.columns = ['ds', 'y']
            df_prophet['ds'] = pd.to_datetime(df_prophet['ds'])

            # Train Prophet model
            model = Prophet(
                yearly_seasonality=True,
                weekly_seasonality=True,
                daily_seasonality=True,
                seasonality_mode='multiplicative'
            )
            model.fit(df_prophet)

            # Store model
            model_key = f"{provider}_{instance_type}_price_trend"
            self.prophet_models[model_key] = model

            # Save model
            self._save_prophet_model(model_key, model)

            # Calculate model performance
            future = model.make_future_dataframe(periods=24, freq='H')
            forecast = model.predict(future)

            # Calculate metrics on historical data
            historical_forecast = forecast[forecast['ds'] <= df_prophet['ds'].max()]
            mae = mean_absolute_error(df_prophet['y'], historical_forecast['yhat'])

            metrics = {
                "status": "success",
                "mae": mae,
                "samples": len(df_filtered)
            }

            logger.info(f"Trained price trend model for {provider} {instance_type}: MAE={mae:.3f}")
            return metrics

        except Exception as e:
            logger.error(f"Error training price trend model: {e}")
            return {"status": "error", "error": str(e)}

    def predict_price_trends(self, provider: str, instance_type: str,
                           hours_ahead: int = 24) -> List[Dict[str, Any]]:
        """Predict price trends for the next N hours."""
        try:
            model_key = f"{provider}_{instance_type}_price_trend"

            if model_key not in self.prophet_models:
                if not self._load_prophet_model(model_key):
                    return []

            model = self.prophet_models[model_key]

            # Make future predictions
            future = model.make_future_dataframe(periods=hours_ahead, freq='H')
            forecast = model.predict(future)

            # Get only future predictions
            future_forecast = forecast[forecast['ds'] > datetime.utcnow()]

            results = []
            for _, row in future_forecast.iterrows():
                results.append({
                    "timestamp": row['ds'].isoformat(),
                    "predicted_price": max(0, row['yhat']),
                    "lower_bound": max(0, row['yhat_lower']),
                    "upper_bound": max(0, row['yhat_upper']),
                    "trend": "increasing" if row['trend'] > 0 else "decreasing",
                    "confidence": 0.8  # Prophet doesn't provide direct confidence
                })

            return results

        except Exception as e:
            logger.error(f"Error predicting price trends: {e}")
            return []

    def detect_arbitrage_opportunities(self, current_prices: Dict[str, float],
                                     predicted_trends: Dict[str, List[Dict]]) -> List[Dict[str, Any]]:
        """Detect arbitrage opportunities across providers."""
        opportunities = []

        try:
            # Find price differences between providers
            providers = list(current_prices.keys())

            for i, provider1 in enumerate(providers):
                for provider2 in providers[i+1:]:
                    price1 = current_prices[provider1]
                    price2 = current_prices[provider2]

                    # Calculate potential savings
                    if price1 > price2:
                        savings_percent = ((price1 - price2) / price1) * 100
                        if savings_percent > 10:  # Minimum 10% savings
                            opportunities.append({
                                "from_provider": provider1,
                                "to_provider": provider2,
                                "current_savings_percent": savings_percent,
                                "current_savings_per_hour": price1 - price2,
                                "confidence": "high" if savings_percent > 20 else "medium",
                                "recommended_action": "migrate",
                                "timestamp": datetime.utcnow().isoformat()
                            })

            # Sort by savings percentage
            opportunities.sort(key=lambda x: x['current_savings_percent'], reverse=True)

            return opportunities

        except Exception as e:
            logger.error(f"Error detecting arbitrage opportunities: {e}")
            return []

    def _save_prophet_model(self, model_key: str, model):
        """Save Prophet model."""
        try:
            model_file = f"{self.model_path}/{model_key}.pkl"
            with open(model_file, 'wb') as f:
                pickle.dump(model, f)
            logger.info(f"Saved Prophet model: {model_file}")
        except Exception as e:
            logger.error(f"Error saving Prophet model: {e}")

    def _load_prophet_model(self, model_key: str) -> bool:
        """Load Prophet model."""
        try:
            model_file = f"{self.model_path}/{model_key}.pkl"
            with open(model_file, 'rb') as f:
                model = pickle.load(f)
            self.prophet_models[model_key] = model
            logger.info(f"Loaded Prophet model: {model_file}")
            return True
        except Exception as e:
            logger.error(f"Error loading Prophet model: {e}")
            return False


class MLForecastingService:
    """Main ML forecasting service that coordinates all forecasting tasks."""

    def __init__(self):
        self.demand_forecaster = DemandForecaster()
        self.price_forecaster = PriceTrendForecaster()
        self.is_training = False

    async def train_all_models(self, pricing_data: pd.DataFrame) -> Dict[str, Any]:
        """Train all forecasting models."""
        if self.is_training:
            return {"status": "already_training"}

        self.is_training = True
        results = {}

        try:
            # Get unique provider-instance combinations
            combinations = pricing_data.groupby(['provider_display_name', 'instance_type']).size().reset_index()

            for _, row in combinations.iterrows():
                provider = row['provider_display_name']
                instance_type = row['instance_type']

                # Train demand model
                demand_result = self.demand_forecaster.train_demand_model(
                    pricing_data, provider, instance_type
                )

                # Train price trend model
                price_result = self.price_forecaster.train_price_trend_model(
                    pricing_data, provider, instance_type
                )

                results[f"{provider}_{instance_type}"] = {
                    "demand_model": demand_result,
                    "price_model": price_result
                }

            logger.info(f"Trained models for {len(combinations)} provider-instance combinations")

        except Exception as e:
            logger.error(f"Error training models: {e}")
            results["error"] = str(e)

        finally:
            self.is_training = False

        return results

    async def get_forecasts(self, provider: str, instance_type: str,
                          hours_ahead: int = 24) -> Dict[str, Any]:
        """Get comprehensive forecasts for a provider-instance combination."""
        try:
            # Get demand forecast
            demand_forecast = self.demand_forecaster.predict_demand(
                provider, instance_type, hours_ahead
            )

            # Get price trend forecast
            price_forecast = self.price_forecaster.predict_price_trends(
                provider, instance_type, hours_ahead
            )

            return {
                "provider": provider,
                "instance_type": instance_type,
                "demand_forecast": demand_forecast,
                "price_forecast": price_forecast,
                "forecast_horizon_hours": hours_ahead,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Error getting forecasts: {e}")
            return {"error": str(e)}

    async def get_arbitrage_opportunities(self, current_prices: Dict[str, float]) -> List[Dict[str, Any]]:
        """Get arbitrage opportunities across providers."""
        try:
            # Get predicted trends for all providers
            predicted_trends = {}
            for provider in current_prices.keys():
                # This would need to be implemented based on your data structure
                predicted_trends[provider] = []

            opportunities = self.price_forecaster.detect_arbitrage_opportunities(
                current_prices, predicted_trends
            )

            return opportunities

        except Exception as e:
            logger.error(f"Error getting arbitrage opportunities: {e}")
            return []

    async def retrain_models(self, new_data: pd.DataFrame) -> Dict[str, Any]:
        """Retrain models with new data."""
        try:
            # Combine with existing data (in production, you'd load from database)
            combined_data = new_data  # Simplified for now

            # Retrain all models
            results = await self.train_all_models(combined_data)

            # Record metrics
            metrics_collector.record_model_retraining(len(combined_data))

            return results

        except Exception as e:
            logger.error(f"Error retraining models: {e}")
            return {"error": str(e)}


# Global ML service instance
ml_service = MLForecastingService()


async def run_ml_forecasting():
    """Run ML forecasting tasks."""
    try:
        # This would load real pricing data from your database
        # For now, we'll create sample data
        sample_data = pd.DataFrame({
            'timestamp': pd.date_range(start='2024-01-01', periods=1000, freq='H'),
            'provider_display_name': ['AWS', 'GCP', 'Azure'] * 333 + ['AWS'],
            'instance_type': ['g4dn.xlarge', 'n1-standard-4', 'Standard_NC6'] * 333 + ['g4dn.xlarge'],
            'price_per_hour': np.random.uniform(0.5, 3.0, 1000),
            'spot_price': np.random.uniform(0.3, 2.0, 1000)
        })

        # Train models
        training_results = await ml_service.train_all_models(sample_data)
        logger.info(f"ML model training completed: {training_results}")

        # Get sample forecasts
        forecast = await ml_service.get_forecasts('AWS', 'g4dn.xlarge', 24)
        logger.info(f"Sample forecast: {forecast}")

        return training_results

    except Exception as e:
        logger.error(f"Error in ML forecasting: {e}")
        return {"error": str(e)}


def start_ml_scheduler():
    """Start the ML forecasting scheduler."""
    async def scheduler():
        while True:
            try:
                await run_ml_forecasting()
                await asyncio.sleep(settings.ml.retrain_interval_hours * 3600)  # Retrain every N hours
            except Exception as e:
                logger.error(f"Error in ML scheduler: {e}")
                await asyncio.sleep(3600)  # Wait 1 hour on error

    asyncio.create_task(scheduler())