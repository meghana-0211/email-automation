from fastapi import FastAPI, WebSocket
from typing import Dict, List, Optional
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
from scipy import stats

class AnalyticsSystem:
    def __init__(self, db_session):
        self.db = db_session
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """Handle new WebSocket connections"""
        await websocket.accept()
        self.active_connections.append(websocket)
        
        # Send initial data
        initial_data = await self.get_dashboard_data()
        await websocket.send_json(initial_data)

    async def disconnect(self, websocket: WebSocket):
        """Handle WebSocket disconnections"""
        self.active_connections.remove(websocket)

    async def broadcast_update(self, data: Dict):
        """Broadcast updates to all connected clients"""
        for connection in self.active_connections:
            try:
                await connection.send_json(data)
            except:
                await self.disconnect(connection)

    async def get_dashboard_data(self) -> Dict:
        """Get comprehensive dashboard data"""
        now = datetime.now()
        today = now.date()
        
        # Get basic metrics
        basic_metrics = await self.calculate_basic_metrics(today)
        
        # Get trend data
        trends = await self.calculate_trends(today)
        
        # Get performance metrics
        performance = await self.calculate_performance_metrics()
        
        return {
            "metrics": basic_metrics,
            "trends": trends,
            "performance": performance,
            "timestamp": now.isoformat()
        }

    async def calculate_basic_metrics(self, date: datetime.date) -> Dict:
        """Calculate basic email metrics"""
        pipeline = [
            {
                "$match": {
                    "created_at": {
                        "$gte": datetime.combine(date, datetime.min.time())
                    }
                }
            },
            {
                "$group": {
                    "_id": None,
                    "total_sent": {
                        "$sum": {
                            "$cond": [{"$eq": ["$status", "sent"]}, 1, 0]
                        }
                    },
                    "total_delivered": {
                        "$sum": {
                            "$cond": [{"$eq": ["$status", "delivered"]}, 1, 0]
                        }
                    },
                    "total_opened": {
                        "$sum": {
                            "$cond": [{"$eq": ["$status", "opened"]}, 1, 0]
                        }
                    },
                    "total_clicked": {
                        "$sum": {
                            "$cond": [{"$eq": ["$status", "clicked"]}, 1, 0]
                        }
                    },
                    "total_bounced": {
                        "$sum": {
                            "$cond": [{"$eq": ["$status", "bounced"]}, 1, 0]
                        }
                    }
                }
            }
        ]
        
        result = await self.db.email_tracking.aggregate(pipeline).to_list(1)
        metrics = result[0] if result else {}
        
        # Calculate rates
        total_delivered = metrics.get("total_delivered", 0)
        if total_delivered > 0:
            metrics["open_rate"] = (metrics.get("total_opened", 0) / total_delivered) * 100
            metrics["click_rate"] = (metrics.get("total_clicked", 0) / total_delivered) * 100
            
        return metrics

    async def calculate_trends(self, date: datetime.date) -> Dict:
        """Calculate trend data for the past 30 days"""
        start_date = date - timedelta(days=30)
        
        pipeline = [
            {
                "$match": {
                    "created_at": {
                        "$gte": datetime.combine(start_date, datetime.min.time())
                    }
                }
            },
            {
                "$group": {
                    "_id": {
                        "$dateToString": {
                            "format": "%Y-%m-%d",
                            "date": "$created_at"
                        }
                    },
                    "sent": {
                        "$sum": {
                            "$cond": [{"$eq": ["$status", "sent"]}, 1, 0]
                        }
                    },
                    "delivered": {
                        "$sum": {
                            "$cond": [{"$eq": ["$status", "delivered"]}, 1, 0]
                        }
                    },
                    "opened": {
                        "$sum": {
                            "$cond": [{"$eq": ["$status", "opened"]}, 1, 0]
                        }
                    }
                }
            },
            {"$sort": {"_id": 1}}
        ]
        
        results = await self.db.email_tracking.aggregate(pipeline).to_list(None)
        
        # Convert to pandas for trend analysis
        df = pd.DataFrame(results)
        
        # Calculate moving averages
        df['sent_ma'] = df['sent'].rolling(window=7).mean()
        df['delivered_ma'] = df['delivered'].rolling(window=7).mean()
        df['opened_ma'] = df['opened'].rolling(window=7).mean()
        
        return df.to_dict('records')

    async def calculate_performance_metrics(self) -> Dict:
        """Calculate advanced performance metrics"""
        # Get recent campaigns
        campaigns = await self.db.campaigns.find(
            {"status": "completed"},
            sort=[("created_at", -1)],
            limit=10
        ).to_list(None)
        
        performance_data = []
        
        for campaign in campaigns:
            # Get campaign metrics
            metrics = await self.get_campaign_metrics(campaign["_id"])
            
            # Calculate engagement score
            engagement_score = await self.calculate_engagement_score(metrics)
            
            # Calculate optimal send times
            optimal_times = await self.analyze_optimal_send_times(campaign["_id"])
            
            performance_data.append({
                "campaign_id": campaign["_id"],
                "name": campaign["name"],
                "metrics": metrics,
                "engagement_score": engagement_score,
                "optimal_times": optimal_times
            })
            
        return performance_data

    async def analyze_optimal_send_times(self, campaign_id: str) -> Dict:
        """Analyze optimal send times based on engagement"""
        pipeline = [
            {"$match": {"campaign_id": campaign_id}},
            {
                "$project": {
                    "hour": {"$hour": "$sent_time"},
                    "is_opened": {
                        "$cond": [{"$eq": ["$status", "opened"]}, 1, 0]
                    }
                }
            },
            {
                "$group": {
                    "_id": "$hour",
                    "total_sent": {"$sum": 1},
                    "total_opened": {"$sum": "$is_opened"}
                }
            }
        ]
        
        results = await self.db.email_tracking.aggregate(pipeline).to_list(None)
        
        # Calculate open rates by hour
        hourly_rates = {}
        for result in results:
            hour = result["_id"]
            open_rate = (result["total_opened"] / result["total_sent"]) * 100
            hourly_rates[hour] = open_rate
            
        # Find optimal hours
        sorted_hours = sorted(
            hourly_rates.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return {
            "best_hours": sorted_hours[:3],
            "worst_hours": sorted_hours[-3:],
            "hourly_rates": hourly_rates
        }

    async def calculate_engagement_score(self, metrics: Dict) -> float:
        """Calculate overall engagement score"""
        weights = {
            "open_rate": 0.3,
            "click_rate": 0.4,
            "reply_rate": 0.2,
            "conversion_rate": 0.1
        }
        
        engagement_score = sum(
            metrics.get(metric, 0) * weight
            for metric, weight in weights.items()
        )
        
        return round(engagement_score, 2)

    async def perform_ab_test_analysis(
        self,
        campaign_id: str,
        variants: List[str]
    ) -> Dict:
        """Perform statistical analysis of A/B test results"""
        results = {}
        control_data = None
        
        for variant in variants:
            # Get variant metrics
            metrics = await self.get_variant_metrics(campaign_id, variant)
            
            if variant == "control":
                control_data = metrics
            else:
                # Perform statistical tests
                if control_data:
                    t_stat, p_value = stats.ttest_ind(
                        metrics["opens"],
                        control_data["opens"]
                    )
                    
                    results[variant] = {
                        "metrics": metrics,
                        "t_statistic": t_stat,
                        "p_value": p_value,
                        "significant": p_value < 0.05
                    }
        
        return results

    async def generate_campaign_report(self, campaign_id: str) -> Dict:
        """Generate comprehensive campaign report"""
        # Get campaign data
        campaign = await self.db.campaigns.find_one({"_id": campaign_id})
        
        # Get basic metrics
        metrics = await self.get_campaign_metrics(campaign_id)
        
        # Get engagement analysis
        engagement = await self.analyze_engagement(campaign_id)
        
        # Get delivery analysis
        delivery = await self.analyze_delivery(campaign_id)
        
        # Get recipient analysis
        recipients = await self.analyze_recipients(campaign_id)
        
        return {
            "campaign_info": campaign,
            "metrics": metrics,
            "engagement_analysis": engagement,
            "delivery_analysis": delivery,
            "recipient_analysis": recipients,
            "generated_at": datetime.now()
        }