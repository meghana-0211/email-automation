import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { LineChart, BarChart, XAxis, YAxis, Tooltip, Legend, Line, Bar, ResponsiveContainer } from 'recharts';
import { AlertCircle, CheckCircle, TrendingUp } from 'lucide-react';

const ABTestingDashboard = ({ campaignId }) => {
  const [testData, setTestData] = useState(null);
  const [selectedMetric, setSelectedMetric] = useState('openRate');
  const [confidenceLevel, setConfidenceLevel] = useState(95);

  useEffect(() => {
    const fetchTestData = async () => {
      const response = await fetch(`/api/ab-test/${campaignId}`);
      const data = await response.json();
      setTestData(data);
    };
    
    fetchTestData();
    const interval = setInterval(fetchTestData, 5000);
    return () => clearInterval(interval);
  }, [campaignId]);

  const getSignificanceIndicator = (variant) => {
    if (!variant.significant) {
      return (
        <div className="flex items-center text-yellow-500">
          <AlertCircle className="w-4 h-4 mr-1" />
          <span>Not Significant</span>
        </div>
      );
    }
    
    return (
      <div className="flex items-center text-green-500">
        <CheckCircle className="w-4 h-4 mr-1" />
        <span>Significant</span>
      </div>
    );
  };

  if (!testData) return <div>Loading...</div>;

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold">A/B Test Results</h2>
        <div className="flex space-x-4">
          <select
            className="border rounded p-2"
            value={selectedMetric}
            onChange={(e) => setSelectedMetric(e.target.value)}
          >
            <option value="openRate">Open Rate</option>
            <option value="clickRate">Click Rate</option>
            <option value="conversionRate">Conversion Rate</option>
          </select>
          
          <select
            className="border rounded p-2"
            value={confidenceLevel}
            onChange={(e) => setConfidenceLevel(Number(e.target.value))}
          >
            <option value="90">90% Confidence</option>
            <option value="95">95% Confidence</option>
            <option value="99">99% Confidence</option>
          </select>
        </div>
      </div>

      {/* Variant Performance Comparison */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {testData.variants.map((variant) => (
          <Card key={variant.name}>
            <CardHeader>
              <CardTitle className="flex justify-between">
                <span>{variant.name}</span>
                {getSignificanceIndicator(variant)}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div>
                  <div className="text-sm text-gray-500">Sample Size</div>
                  <div className="text-2xl font-bold">{variant.sampleSize}</div>
                </div>
                
                <div>
                  <div className="text-sm text-gray-500">{selectedMetric}</div>
                  <div className="text-2xl font-bold">
                    {(variant.metrics[selectedMetric] * 100).toFixed(2)}%
                  </div>
                </div>
                
                <div>
                  <div className="text-sm text-gray-500">Lift vs Control</div>
                  <div className="flex items-center">
                    <TrendingUp 
                      className={`w-4 h-4 mr-1 ${
                        variant.lift > 0 ? 'text-green-500' : 'text-red-500'
                      }`}
                    />
                    <span className={
                      variant.lift > 0 ? 'text-green-500' : 'text-red-500'
                    }>
                      {variant.lift > 0 ? '+' : ''}{variant.lift.toFixed(2)}%
                    </span>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Trend Chart */}
      <Card>
        <CardHeader>
          <CardTitle>Performance Trend</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={testData.trends}>
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip />
                <Legend />
                {testData.variants.map((variant) => (
                  <Line
                    key={variant.name}
                    type="monotone"
                    dataKey={`${variant.name}.${selectedMetric}`}
                    stroke={variant.color}
                    name={variant.name}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
