import React, { useState, useEffect } from 'react';
import { Upload, Mail, Settings, BarChart2 } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Progress } from "@/components/ui/progress";

const Dashboard = () => {
  // State management
  const [emailTemplate, setEmailTemplate] = useState('');
  const [availableFields, setAvailableFields] = useState([]);
  const [csvData, setCsvData] = useState(null);
  const [apiKey, setApiKey] = useState('');
  const [emailsPerHour, setEmailsPerHour] = useState(100);
  const [pauseBetweenSends, setPauseBetweenSends] = useState(5);
  const [analytics, setAnalytics] = useState({
    totalSent: 0,
    pending: 0,
    delivered: 0,
    failed: 0
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [googleSheetUrl, setGoogleSheetUrl] = useState('');
  const [jobStatus, setJobStatus] = useState(null);

  // Fetch analytics data periodically
  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        const response = await fetch('/api/analytics', {
          headers: {
            'X-API-Key': apiKey
          }
        });
        const data = await response.json();
        setAnalytics(data);
      } catch (err) {
        console.error('Failed to fetch analytics:', err);
      }
    };

    const interval = setInterval(fetchAnalytics, 5000);
    return () => clearInterval(interval);
  }, [apiKey]);

  // Handle CSV file upload
  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    setLoading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch('/api/upload/csv', {
        method: 'POST',
        headers: {
          'X-API-Key': apiKey
        },
        body: formData
      });

      if (!response.ok) throw new Error('Failed to upload file');

      const data = await response.json();
      setAvailableFields(data.columns);
      setCsvData(data.preview);
    } catch (err) {
      setError('Failed to upload file: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  // Connect to Google Sheets
  const handleGoogleSheetsConnect = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/connect/sheets', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': apiKey
        },
        body: JSON.stringify({ url: googleSheetUrl })
      });

      if (!response.ok) throw new Error('Failed to connect to Google Sheets');

      const data = await response.json();
      setAvailableFields(data.columns);
      setCsvData(data.preview);
    } catch (err) {
      setError('Failed to connect to Google Sheets: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  // Save email settings
  const handleSaveSettings = async () => {
    try {
      const response = await fetch('/api/settings', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': apiKey
        },
        body: JSON.stringify({
          emailsPerHour,
          pauseBetweenSends
        })
      });

      if (!response.ok) throw new Error('Failed to save settings');
      
      setError(null);
    } catch (err) {
      setError('Failed to save settings: ' + err.message);
    }
  };

  // Start email campaign
  const handleStartCampaign = async () => {
    if (!emailTemplate || !csvData) {
      setError('Please provide both template and recipient data');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/campaign/start', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': apiKey
        },
        body: JSON.stringify({
          template: emailTemplate,
          data: csvData,
          settings: {
            emailsPerHour,
            pauseBetweenSends
          }
        })
      });

      if (!response.ok) throw new Error('Failed to start campaign');

      const { jobId } = await response.json();
      setJobStatus({ id: jobId, status: 'running' });
    } catch (err) {
      setError('Failed to start campaign: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6">
      {error && (
        <Alert variant="destructive" className="mb-4">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <Tabs defaultValue="upload" className="w-full">
        <TabsList>
          <TabsTrigger value="upload" className="flex items-center gap-2">
            <Upload size={16} />
            Data Upload
          </TabsTrigger>
          <TabsTrigger value="template" className="flex items-center gap-2">
            <Mail size={16} />
            Email Template
          </TabsTrigger>
          <TabsTrigger value="settings" className="flex items-center gap-2">
            <Settings size={16} />
            Settings
          </TabsTrigger>
          <TabsTrigger value="analytics" className="flex items-center gap-2">
            <BarChart2 size={16} />
            Analytics
          </TabsTrigger>
        </TabsList>

        <TabsContent value="upload">
          <Card>
            <CardHeader>
              <CardTitle>Upload Data</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div>
                  <h3 className="text-lg font-bold">CSV Upload</h3>
                  <Input 
                    type="file" 
                    accept=".csv"
                    onChange={handleFileUpload}
                    disabled={loading}
                    className="mt-2"
                  />
                </div>
                <div>
                  <h3 className="text-lg font-bold">Google Sheets Integration</h3>
                  <Input 
                    type="text"
                    value={googleSheetUrl}
                    onChange={(e) => setGoogleSheetUrl(e.target.value)}
                    placeholder="Enter Google Sheets URL"
                    className="mt-2"
                  />
                  <Button 
                    onClick={handleGoogleSheetsConnect}
                    disabled={loading || !googleSheetUrl}
                    className="mt-2"
                  >
                    Connect to Google Sheets
                  </Button>
                </div>
                {csvData && (
                  <div>
                    <h3 className="text-lg font-bold">Preview</h3>
                    <div className="mt-2 max-h-48 overflow-auto">
                      <table className="min-w-full divide-y divide-gray-200">
                        <thead>
                          <tr>
                            {availableFields.map((field, i) => (
                              <th key={i} className="px-4 py-2">{field}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {csvData.map((row, i) => (
                            <tr key={i}>
                              {availableFields.map((field, j) => (
                                <td key={j} className="px-4 py-2">{row[field]}</td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="template">
          <Card>
            <CardHeader>
              <CardTitle>Email Template Builder</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div>
                  <h3 className="text-lg font-bold">Available Fields</h3>
                  <div className="flex flex-wrap gap-2 mt-2">
                    {availableFields.map((field, index) => (
                      <Button
                        key={index}
                        variant="outline"
                        onClick={() => setEmailTemplate(prev => `${prev} {${field}}`)}
                      >
                        {field}
                      </Button>
                    ))}
                  </div>
                </div>
                <div>
                  <h3 className="text-lg font-bold">Template Content</h3>
                  <Textarea
                    value={emailTemplate}
                    onChange={(e) => setEmailTemplate(e.target.value)}
                    className="h-64 mt-2"
                    placeholder="Enter your email template here. Use {field_name} to insert dynamic content."
                  />
                </div>
                <Button
                  onClick={handleStartCampaign}
                  disabled={loading || !emailTemplate || !csvData}
                >
                  Start Campaign
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="settings">
          <Card>
            <CardHeader>
              <CardTitle>Email Settings</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div>
                  <h3 className="text-lg font-bold">API Configuration</h3>
                  <Input 
                    type="password"
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    placeholder="API Key"
                    className="mt-2"
                  />
                </div>
                <div>
                  <h3 className="text-lg font-bold">Sending Limits</h3>
                  <div className="grid grid-cols-2 gap-4 mt-2">
                    <Input 
                      type="number"
                      value={emailsPerHour}
                      onChange={(e) => setEmailsPerHour(parseInt(e.target.value))}
                      placeholder="Emails per hour"
                    />
                    <Input 
                      type="number"
                      value={pauseBetweenSends}
                      onChange={(e) => setPauseBetweenSends(parseInt(e.target.value))}
                      placeholder="Pause between sends (seconds)"
                    />
                  </div>
                </div>
                <Button
                  onClick={handleSaveSettings}
                  disabled={loading}
                >
                  Save Settings
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="analytics">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card>
              <CardHeader>
                <CardTitle>Total Sent</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-bold">{analytics.totalSent}</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Pending</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-bold">{analytics.pending}</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Delivered</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-bold">{analytics.delivered}</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Failed</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-bold">{analytics.failed}</p>
              </CardContent>
            </Card>
          </div>
          
          {jobStatus && (
            <Card className="mt-4">
              <CardHeader>
                <CardTitle>Current Campaign Progress</CardTitle>
              </CardHeader>
              <CardContent>
                <Progress value={(analytics.totalSent / (analytics.totalSent + analytics.pending)) * 100} className="w-full" />
                <p className="mt-2">Status: {jobStatus.status}</p>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default Dashboard;