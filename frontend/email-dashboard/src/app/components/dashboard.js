
'use client';

import React from 'react';
import  { useState} from 'react';
import { useEffect } from 'react';
import { Upload, Mail, Settings, BarChart2 } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./tabs/tabs";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Textarea } from "./ui/textarea";

const Dashboard = () => {
  const [emailTemplate, setEmailTemplate] = useState('');
  const [availableFields, setAvailableFields] = useState([]);
  const [csvData, setCsvData] = useState(null);
  const [isClient, setIsClient] = useState(false); // State to track if it's client-side

  useEffect(() => {
    // This will run only on the client side, as useEffect doesn't run on the server
    setIsClient(true);
  }, []);

  const handleFileUpload = (event) => {
    const file = event.target.files[0];
    const reader = new FileReader();
    
    reader.onload = (e) => {
      const text = e.target.result;
      const rows = text.split('\n');
      const headers = rows[0].split(',');
      setAvailableFields(headers);
      setCsvData(text);
    };
    
    reader.readAsText(file);
  };
  
  const insertField = (field) => {
    setEmailTemplate(prev => `${prev} {${field}}`);
  };

  if (!isClient) {
    return null; // Ensure that it doesn't render on the server side
  }
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