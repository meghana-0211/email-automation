'use client';

import React, { useState, useEffect } from 'react';
import { Upload, Mail, Settings, BarChart2 } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./tabs/tabs";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Textarea } from "./ui/textarea";
import { apiService } from '../services/api';


const Dashboard = () => {
  const [emailTemplate, setEmailTemplate] = useState('');
  const [templateName, setTemplateName] = useState('');
  const [availableFields, setAvailableFields] = useState([]);
  const [csvData, setCsvData] = useState(null);
  const [sheetUrl, setSheetUrl] = useState('');
  const [templates, setTemplates] = useState([]);
  const [analytics, setAnalytics] = useState({
    totalSent: 0,
    pending: 0,
    delivered: 0,
    failed: 0
  });

  useEffect(() => {
    fetchTemplates();
    fetchHourlyAnalytics();
  }, []);

  const fetchTemplates = async () => {
    try {
      const fetchedTemplates = await apiService.listTemplates();
      setTemplates(fetchedTemplates);
    } catch (error) {
      toast.error('Failed to fetch templates');
    }
  };

  const fetchHourlyAnalytics = async () => {
    try {
      const hourlyStats = await apiService.getHourlyAnalytics();
      const totalStats = hourlyStats.reduce((acc, stat) => ({
        totalSent: acc.totalSent + stat.sent,
        pending: acc.pending + stat.sent,
        delivered: acc.delivered + stat.delivered,
        failed: acc.failed + stat.failed
      }), { totalSent: 0, pending: 0, delivered: 0, failed: 0 });

      setAnalytics(totalStats);
    } catch (error) {
      toast.error('Failed to fetch analytics');
    }
  };

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    try {
      const result = await apiService.uploadCsv(file);
      setAvailableFields(result.columns);
      setCsvData(result.preview);
      toast.success('CSV uploaded successfully');
    } catch (error) {
      toast.error('CSV upload failed');
    }
  };

  const handleGoogleSheetConnect = async () => {
    try {
      const result = await apiService.connectGoogleSheet(sheetUrl);
      setAvailableFields(result.columns);
      setCsvData(result.preview);
      toast.success('Google Sheet connected');
    } catch (error) {
      toast.error('Failed to connect Google Sheet');
    }
  };

  const saveTemplate = async () => {
    try {
      const templateData = {
        name: templateName,
        content: emailTemplate,
        subject: 'Automated Email'  // You might want to add a subject input
      };
      const result = await apiService.createTemplate(templateData);
      toast.success('Template saved successfully');
      fetchTemplates();
    } catch (error) {
      toast.error('Failed to save template');
    }
  };

  const createEmailJob = async () => {
    try {
      // This is a simplified example. You'd likely want more configuration
      const jobData = {
        template_id: templates[0].id,  // Use first template as example
        recipients: csvData.map(row => ({
          email: row.Email,
          data: row
        })),
        throttle_rate: 50  // Emails per hour
      };
      const result = await apiService.createEmailJob(jobData);
      toast.success('Email job created');
    } catch (error) {
      toast.error('Failed to create email job');
    }
  };



  const insertField = (field) => {
    setEmailTemplate(prev => `${prev} {${field}}`);
  };


  return (
    <div className="p-6">
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
                  <h3 className="text-lg font-bold text-black">CSV Upload</h3>
                  <Input 
                    type="file" 
                    accept=".csv"
                    onChange={handleFileUpload}
                    className="mt-2"
                  />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-black">Google Sheets Integration</h3>
                  <Input 
                    type="text"
                    placeholder="Enter Google Sheets URL"
                    className="mt-2"
                  />
                  <Button className="mt-2">
                    Connect to Google Sheets
                  </Button>
                </div>
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
                  <h3 className="text-lg font-bold text-black">Available Fields</h3>
                  <div className="flex flex-wrap gap-2 mt-2">
                    {availableFields.map((field, index) => (
                      <Button
                        key={index}
                        variant="outline"
                        onClick={() => insertField(field)}
                      >
                        {field}
                      </Button>
                    ))}
                  </div>
                </div>
                <div>
                  <h3 className="text-lg font-bold text-black">Template Content</h3>
                  <Textarea
                    value={emailTemplate}
                    onChange={(e) => setEmailTemplate(e.target.value)}
                    className="h-64 mt-2"
                    placeholder="Enter your email template here. Use {field_name} to insert dynamic content."
                  />
                </div>
                <Button>
                  Save Template
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
                  <h3 className="text-lg font-bold text-black">Email Service Provider</h3>
                  <Input 
                    type="text"
                    placeholder="API Key"
                    className="mt-2"
                  />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-black">Sending Limits</h3>
                  <div className="grid grid-cols-2 gap-4 mt-2">
                    <Input 
                      type="number"
                      placeholder="Emails per hour"
                    />
                    <Input 
                      type="number"
                      placeholder="Pause between sends (seconds)"
                    />
                  </div>
                </div>
                <Button>
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
                <p className="text-lg font-bold text-black">0</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Pending</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-lg font-bold text-black">0</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Delivered</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-lg font-bold text-black">0</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Failed</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-lg font-bold text-black">0</p>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default Dashboard;